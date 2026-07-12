"""Sensors for FarmBot diagnostics."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up FarmBot sensors."""
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FarmbotLastStatusSensor(manager)])


class FarmbotLastStatusSensor(FarmbotEntity, SensorEntity):
    """Timestamp of the most recently received FarmBot status payload."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_status_received"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.device_id}_last_status_received"

    @property
    def native_value(self):
        return self._manager.last_status_received

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
