"""FarmBot integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, CONF_MQTT_HOST, CONF_TOKEN, DOMAIN, PLATFORMS
from .manager import FarmbotManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FarmBot from a config entry."""
    manager = FarmbotManager(
        hass=hass,
        token=entry.data[CONF_TOKEN],
        device_id=entry.data[CONF_DEVICE_ID],
        mqtt_host=entry.data[CONF_MQTT_HOST],
        entry=entry,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    if not await manager.async_check_and_refresh_token():
        return False

    await manager.connect_mqtt()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a FarmBot config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unloaded:
        return False

    manager: FarmbotManager = hass.data[DOMAIN].pop(entry.entry_id)
    await manager.disconnect_mqtt()

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return True
