"""Config flow for FarmBot."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import aiohttp_client

from .const import API_BASE_URL, CONF_DEVICE_ID, CONF_MQTT_HOST, CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class FarmbotAuthenticationError(Exception):
    """Raised when FarmBot rejects the supplied credentials."""


class FarmbotConnectionError(Exception):
    """Raised when the FarmBot API cannot be reached."""


class FarmbotResponseError(Exception):
    """Raised when FarmBot returns an incomplete token response."""


async def async_request_token(hass, email: str, password: str) -> dict[str, Any]:
    """Authenticate with FarmBot and return its token object."""
    session = aiohttp_client.async_get_clientsession(hass)

    try:
        async with session.post(
            f"{API_BASE_URL}/tokens",
            json={"user": {"email": email, "password": password}},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            if response.status in (401, 422):
                raise FarmbotAuthenticationError

            if response.status != 200:
                _LOGGER.error(
                    "FarmBot authentication request failed with HTTP %s",
                    response.status,
                )
                raise FarmbotConnectionError

            payload = await response.json()
    except FarmbotAuthenticationError:
        raise
    except (aiohttp.ClientError, TimeoutError) as err:
        raise FarmbotConnectionError from err
    except (ValueError, TypeError) as err:
        raise FarmbotResponseError from err

    token = payload.get("token") or {}
    unencoded = token.get("unencoded") or {}
    if not token.get("encoded") or not unencoded.get("bot") or not unencoded.get("mqtt"):
        raise FarmbotResponseError

    return token


class FarmbotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a FarmBot connection."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Authenticate with the user's FarmBot account."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = str(user_input[CONF_EMAIL]).strip().lower()
            try:
                token = await async_request_token(
                    self.hass,
                    email,
                    user_input[CONF_PASSWORD],
                )
            except FarmbotAuthenticationError:
                errors["base"] = "invalid_auth"
            except FarmbotConnectionError:
                errors["base"] = "cannot_connect"
            except FarmbotResponseError:
                errors["base"] = "invalid_response"
            except Exception:  # pragma: no cover - defensive config-flow guard
                _LOGGER.exception("Unexpected FarmBot authentication error")
                errors["base"] = "unknown"
            else:
                unencoded = token["unencoded"]
                device_id = str(unencoded["bot"]).strip().removeprefix("device_")
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"FarmBot {device_id}",
                    data={
                        CONF_TOKEN: token["encoded"],
                        CONF_DEVICE_ID: device_id,
                        CONF_MQTT_HOST: str(unencoded["mqtt"]).strip(),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Start reauthentication for an expired FarmBot token."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Refresh credentials using the user's FarmBot sign-in."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                token = await async_request_token(
                    self.hass,
                    str(user_input[CONF_EMAIL]).strip().lower(),
                    user_input[CONF_PASSWORD],
                )
            except FarmbotAuthenticationError:
                errors["base"] = "invalid_auth"
            except FarmbotConnectionError:
                errors["base"] = "cannot_connect"
            except FarmbotResponseError:
                errors["base"] = "invalid_response"
            except Exception:  # pragma: no cover - defensive config-flow guard
                _LOGGER.exception("Unexpected FarmBot reauthentication error")
                errors["base"] = "unknown"
            else:
                unencoded = token["unencoded"]
                device_id = str(unencoded["bot"]).strip().removeprefix("device_")
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_TOKEN: token["encoded"],
                        CONF_DEVICE_ID: device_id,
                        CONF_MQTT_HOST: str(unencoded["mqtt"]).strip(),
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
