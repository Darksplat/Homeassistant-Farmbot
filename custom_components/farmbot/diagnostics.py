"""Diagnostics support for the FarmBot integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, CONF_MQTT_HOST, CONF_TOKEN, DOMAIN

TO_REDACT = {CONF_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a FarmBot config entry."""
    manager = hass.data[DOMAIN][entry.entry_id]

    return {
        "config_entry": async_redact_data(
            {
                CONF_DEVICE_ID: entry.data.get(CONF_DEVICE_ID),
                CONF_MQTT_HOST: entry.data.get(CONF_MQTT_HOST),
                CONF_TOKEN: entry.data.get(CONF_TOKEN),
            },
            TO_REDACT,
        ),
        "connection": {
            "mqtt_connected": manager.mqtt_connected,
            "status_fresh": manager.status_fresh,
            "last_status_received": (
                manager.last_status_received.isoformat()
                if manager.last_status_received
                else None
            ),
        },
        "device": {
            "device_id": manager.device_id,
            "model": manager.model,
            "controller_version": manager.controller_version,
            "firmware_version": manager.firmware_version,
            "uptime": manager.uptime,
        },
        "status": manager.status,
    }
