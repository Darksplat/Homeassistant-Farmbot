"""Config flow for FarmBot."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import CONF_DEVICE_ID, CONF_MQTT_HOST, CONF_TOKEN, DOMAIN


class FarmbotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a FarmBot connection."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle manual FarmBot credential entry."""
        if user_input is not None:
            device_id = str(user_input[CONF_DEVICE_ID]).strip().removeprefix("device_")
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"FarmBot {device_id}",
                data={
                    CONF_TOKEN: str(user_input[CONF_TOKEN]).strip(),
                    CONF_DEVICE_ID: device_id,
                    CONF_MQTT_HOST: str(user_input[CONF_MQTT_HOST]).strip(),
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_MQTT_HOST): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reauth(self, entry_data):
        """Start reauthentication for an expired token."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Accept a replacement FarmBot token."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data={**self._reauth_entry.data, CONF_TOKEN: str(user_input[CONF_TOKEN]).strip()},
            )
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
        )
