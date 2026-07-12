"""FarmBot API and MQTT manager."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import logging
import ssl
import time
from typing import Any
import uuid

from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.dispatcher import async_dispatcher_send
import paho.mqtt.client as mqtt

from .const import (
    API_BASE_URL,
    MQTT_PORT,
    SIGNAL_STATE,
    STATUS_FRESHNESS_SECONDS,
    TOKEN_REFRESH_WINDOW,
    TOPIC_COMMAND,
    TOPIC_LOGS,
    TOPIC_STATUS,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_username(device_id: str) -> str:
    device_id = str(device_id).strip()
    return device_id if device_id.startswith("device_") else f"device_{device_id}"


def _topic_device_id(device_id: str) -> str:
    """Return the numeric/device topic identifier without a duplicate prefix."""
    value = str(device_id).strip()
    return value.removeprefix("device_")


def _split_host_port(raw_host: str, default_port: int) -> tuple[str, int]:
    host = (raw_host or "").strip()
    for scheme in ("mqtts://", "mqtt://", "amqps://", "amqp://", "ssl://", "tcp://"):
        if host.lower().startswith(scheme):
            host = host[len(scheme) :]
            break

    port = default_port
    if ":" in host:
        candidate_host, candidate_port = host.rsplit(":", 1)
        if candidate_port.isdigit():
            host, port = candidate_host, int(candidate_port)
    return host, port


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return None


class FarmbotManager:
    """Maintain FarmBot credentials, MQTT state and RPC commands."""

    def __init__(self, hass, token: str, device_id: str, mqtt_host: str, entry=None) -> None:
        self.hass = hass
        self.token = str(token).strip()
        self.device_id = str(device_id).strip()
        self.mqtt_host_raw = str(mqtt_host).strip()
        self.device_name = f"FarmBot {_topic_device_id(self.device_id)}"
        self.status: dict[str, Any] = {}
        self.mqtt_connected = False
        self.last_status_received: datetime | None = None
        self._mqtt: mqtt.Client | None = None
        self._entry = entry
        self._auth_failed = False
        self._last_rc4_log_time = 0.0

    @property
    def informational_settings(self) -> dict[str, Any]:
        """Return FarmBot informational settings from the latest status payload."""
        settings = self.status.get("informational_settings", {})
        return settings if isinstance(settings, dict) else {}

    @property
    def configuration(self) -> dict[str, Any]:
        """Return FarmBot configuration data from the latest status payload."""
        configuration = self.status.get("configuration", {})
        return configuration if isinstance(configuration, dict) else {}

    @property
    def status_fresh(self) -> bool:
        """Return whether a status payload was received recently."""
        if self.last_status_received is None:
            return False
        age = (datetime.now(timezone.utc) - self.last_status_received).total_seconds()
        return age <= STATUS_FRESHNESS_SECONDS

    @property
    def emergency_stopped(self) -> bool:
        return bool(self.informational_settings.get("locked", False))

    @property
    def busy(self) -> bool:
        return bool(self.informational_settings.get("busy", False))

    @property
    def fully_online(self) -> bool:
        return self.mqtt_connected and self.status_fresh

    @property
    def model(self) -> str:
        """Return the best available FarmBot model/target identifier."""
        target = self.informational_settings.get("target")
        return str(target).strip() if target else "FarmBot"

    @property
    def firmware_version(self) -> str | None:
        """Return the microcontroller firmware version when reported."""
        value = self.informational_settings.get("firmware_version")
        return str(value).strip() if value else None

    @property
    def controller_version(self) -> str | None:
        """Return the FarmBot OS/controller version when reported."""
        value = self.informational_settings.get("controller_version")
        return str(value).strip() if value else None

    @property
    def uptime(self) -> int | None:
        """Return reported uptime in seconds when available."""
        value = self.informational_settings.get("uptime")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def selected_tool_slot(self) -> int | None:
        """Return the currently mounted tool slot when reported."""
        value = self.informational_settings.get("selected_tool_slot")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _dispatch_state(self) -> None:
        self.hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self.hass,
            SIGNAL_STATE,
        )

    def _should_refresh_token(self) -> bool:
        payload = _decode_jwt_payload(self.token)
        if not payload or not payload.get("exp"):
            _LOGGER.warning("Unable to determine FarmBot token expiry")
            return False
        return int(payload["exp"]) - int(time.time()) < TOKEN_REFRESH_WINDOW

    async def async_refresh_token(self) -> bool:
        """Refresh the JWT using the existing FarmBot API workflow."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{API_BASE_URL}/tokens",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("FarmBot token refresh failed with HTTP %s", response.status)
                    return False

                token_data = (await response.json()).get("token", {})
                encoded = token_data.get("encoded")
                unencoded = token_data.get("unencoded", {})
                if not encoded or not unencoded:
                    _LOGGER.error("FarmBot token refresh response was incomplete")
                    return False

                self.token = encoded
                self.device_id = str(unencoded.get("bot", self.device_id))
                self.mqtt_host_raw = str(unencoded.get("mqtt", self.mqtt_host_raw))

                if self._entry:
                    self.hass.config_entries.async_update_entry(
                        self._entry,
                        data={
                            **self._entry.data,
                            "token": self.token,
                            "device_id": self.device_id,
                            "mqtt_host": self.mqtt_host_raw,
                        },
                    )
                return True
        except Exception:
            _LOGGER.exception("FarmBot token refresh raised an exception")
            return False

    async def async_check_and_refresh_token(self) -> bool:
        if not self._should_refresh_token():
            return True
        success = await self.async_refresh_token()
        if not success and self._entry and not self._auth_failed:
            self._auth_failed = True
            self._entry.async_start_reauth(self.hass)
        return success

    def _connect_mqtt_blocking(self) -> None:
        """Create and start the FarmBot MQTT client once."""
        if self._mqtt is not None:
            if self.mqtt_connected:
                _LOGGER.debug("FarmBot MQTT is already connected")
            else:
                _LOGGER.debug("FarmBot MQTT client already exists and is reconnecting")
            return

        username = _normalize_username(self.device_id)
        host, port = _split_host_port(self.mqtt_host_raw, MQTT_PORT)
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=f"homeassistant-{username}",
            protocol=mqtt.MQTTv311,
        )
        client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
        client.tls_insecure_set(False)
        client.username_pw_set(username=username, password=self.token)
        client.reconnect_delay_set(min_delay=5, max_delay=300)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        self._mqtt = client
        try:
            client.connect(host, port, keepalive=60)
            client.loop_start()
        except Exception:
            self._mqtt = None
            raise

    async def connect_mqtt(self) -> None:
        await self.hass.async_add_executor_job(self._connect_mqtt_blocking)

    def _disconnect_mqtt_blocking(self) -> None:
        """Disconnect and dispose of the FarmBot MQTT client."""
        client = self._mqtt
        if client is None:
            return

        self._mqtt = None
        self.mqtt_connected = False
        try:
            client.disconnect()
        finally:
            client.loop_stop()
        self._dispatch_state()

    async def disconnect_mqtt(self) -> None:
        await self.hass.async_add_executor_job(self._disconnect_mqtt_blocking)

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if client is not self._mqtt:
            _LOGGER.debug("Ignoring connection callback from obsolete MQTT client")
            return

        self.mqtt_connected = rc == 0
        if rc == 0:
            topic_id = _topic_device_id(self.device_id)
            client.subscribe(TOPIC_STATUS.format(device_id=topic_id))
            client.subscribe(TOPIC_LOGS.format(device_id=topic_id))
            self._auth_failed = False
            _LOGGER.info("Connected to FarmBot MQTT for device %s", topic_id)
        elif rc == 4:
            now = time.time()
            if now - self._last_rc4_log_time > 60:
                _LOGGER.error("FarmBot MQTT authentication failed; token may be expired")
                self._last_rc4_log_time = now
            if self._entry and not self._auth_failed:
                self._auth_failed = True
                self.hass.loop.call_soon_threadsafe(self._entry.async_start_reauth, self.hass)
        else:
            _LOGGER.error("FarmBot MQTT connection failed with return code %s", rc)
        self._dispatch_state()

    def _on_disconnect(self, client, userdata, rc) -> None:
        if client is not self._mqtt:
            _LOGGER.debug("Ignoring disconnect callback from obsolete MQTT client")
            return

        self.mqtt_connected = False
        if rc == 0:
            _LOGGER.debug("FarmBot MQTT disconnected normally")
        else:
            _LOGGER.warning(
                "FarmBot MQTT connection lost with return code %s; "
                "automatic reconnection will be attempted",
                rc,
            )
        self._dispatch_state()

    def _on_message(self, client, userdata, message) -> None:
        status_topic = TOPIC_STATUS.format(device_id=_topic_device_id(self.device_id))
        if message.topic != status_topic:
            return
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _LOGGER.exception("Unable to decode FarmBot MQTT status payload")
            return

        self.status = payload.get("body", payload) or {}
        self.last_status_received = datetime.now(timezone.utc)
        self._dispatch_state()

    def _publish_rpc(self, rpc: dict[str, Any]) -> None:
        if not self._mqtt or not self.mqtt_connected:
            raise RuntimeError("FarmBot MQTT is not connected")
        topic = TOPIC_COMMAND.format(device_id=_topic_device_id(self.device_id))
        result = self._mqtt.publish(topic, json.dumps(rpc))
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"FarmBot MQTT publish failed with code {result.rc}")

    def send_rpc_request(self, commands: list[dict[str, Any]], priority: int = 600, label: str | None = None) -> None:
        self._publish_rpc(
            {
                "kind": "rpc_request",
                "args": {"label": label or f"ha-{uuid.uuid4()}", "priority": priority},
                "body": commands,
            }
        )

    def send_write_pin(self, pin: int, value: int) -> None:
        self.send_rpc_request([
            {
                "kind": "write_pin",
                "args": {"pin_number": int(pin), "pin_value": int(value), "pin_mode": 0},
            }
        ])

    def send_toggle_pin(self, pin: int) -> None:
        self.send_rpc_request([
            {"kind": "toggle_pin", "args": {"pin_number": int(pin)}}
        ])

    def execute_sequence(self, sequence_id: int) -> None:
        self.send_rpc_request([
            {"kind": "execute", "args": {"sequence_id": int(sequence_id)}}
        ])

    def move_to(self, x=None, y=None, z=None, speed: int = 100) -> None:
        args: dict[str, Any] = {"speed": int(speed)}
        if x is not None:
            args["x"] = float(x)
        if y is not None:
            args["y"] = float(y)
        if z is not None:
            args["z"] = float(z)
        self.send_rpc_request([{"kind": "move", "args": args}])

    def sync(self) -> None:
        """Request a FarmBot data sync."""
        self.send_rpc_request([{"kind": "sync", "args": {}}])

    def emergency_lock(self) -> None:
        """Immediately emergency-stop FarmBot."""
        self.send_rpc_request([{"kind": "emergency_lock", "args": {}}], priority=900)

    def emergency_unlock(self) -> None:
        """Unlock FarmBot after an emergency stop."""
        self.send_rpc_request([{"kind": "emergency_unlock", "args": {}}], priority=900)
