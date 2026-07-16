"""FarmBot integration for Home Assistant."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import CONF_DEVICE_ID, CONF_MQTT_HOST, CONF_TOKEN, DOMAIN, PLATFORMS
from .manager import FarmbotManager

SERVICE_EXECUTE_SEQUENCE = "execute_sequence"
SERVICE_MOVE_TO = "move_to"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_SEQUENCE_ID = "sequence_id"
ATTR_X = "x"
ATTR_Y = "y"
ATTR_Z = "z"
ATTR_SPEED = "speed"

EXECUTE_SEQUENCE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_SEQUENCE_ID): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

MOVE_TO_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_X): vol.Coerce(float),
        vol.Required(ATTR_Y): vol.Coerce(float),
        vol.Required(ATTR_Z): vol.Coerce(float),
        vol.Optional(ATTR_SPEED, default=100): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
    }
)


def _get_manager(hass: HomeAssistant, call: ServiceCall) -> FarmbotManager:
    """Resolve the FarmBot manager targeted by a service call."""
    managers: dict[str, FarmbotManager] = hass.data.get(DOMAIN, {})
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)

    if entry_id:
        manager = managers.get(entry_id)
        if manager is None:
            raise HomeAssistantError(
                f"No configured FarmBot was found for config entry {entry_id}"
            )
        return manager

    if len(managers) == 1:
        return next(iter(managers.values()))

    if not managers:
        raise HomeAssistantError("No FarmBot integrations are currently loaded")

    raise HomeAssistantError(
        "Multiple FarmBot integrations are loaded; provide config_entry_id"
    )


async def _async_execute_sequence(hass: HomeAssistant, call: ServiceCall) -> None:
    """Execute a FarmBot sequence."""
    manager = _get_manager(hass, call)
    manager.execute_sequence(call.data[ATTR_SEQUENCE_ID])


async def _async_move_to(hass: HomeAssistant, call: ServiceCall) -> None:
    """Move FarmBot to an absolute XYZ coordinate."""
    manager = _get_manager(hass, call)
    manager.move_to(
        x=call.data[ATTR_X],
        y=call.data[ATTR_Y],
        z=call.data[ATTR_Z],
        speed=call.data[ATTR_SPEED],
    )


def _register_services(hass: HomeAssistant) -> None:
    """Register FarmBot integration services once."""
    if not hass.services.has_service(DOMAIN, SERVICE_EXECUTE_SEQUENCE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_EXECUTE_SEQUENCE,
            lambda call: _async_execute_sequence(hass, call),
            schema=EXECUTE_SEQUENCE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_MOVE_TO):
        hass.services.async_register(
            DOMAIN,
            SERVICE_MOVE_TO,
            lambda call: _async_move_to(hass, call),
            schema=MOVE_TO_SCHEMA,
        )


def _remove_services(hass: HomeAssistant) -> None:
    """Remove FarmBot services after the final config entry unloads."""
    for service in (SERVICE_EXECUTE_SEQUENCE, SERVICE_MOVE_TO):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)


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
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
        return False

    await manager.connect_mqtt()
    _register_services(hass)
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
        _remove_services(hass)

    return True
