"""Binary sensors for FarmBot diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity


@dataclass(frozen=True, kw_only=True)
class FarmbotBinarySensorDescription:
    key: str
    translation_key: str
    value_fn: Callable


DESCRIPTIONS = (
    FarmbotBinarySensorDescription(key="mqtt_connected", translation_key="mqtt_connected", value_fn=lambda manager: manager.mqtt_connected),
    FarmbotBinarySensorDescription(key="status_fresh", translation_key="status_fresh", value_fn=lambda manager: manager.status_fresh),
    FarmbotBinarySensorDescription(key="emergency_stop", translation_key="emergency_stop", value_fn=lambda manager: manager.emergency_stopped),
    FarmbotBinarySensorDescription(key="busy", translation_key="busy", value_fn=lambda manager: manager.busy),
    FarmbotBinarySensorDescription(key="fully_online", translation_key="fully_online", value_fn=lambda manager: manager.fully_online),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(FarmbotBinarySensor(manager, description) for description in DESCRIPTIONS)


class FarmbotBinarySensor(FarmbotEntity, BinarySensorEntity):
    """A FarmBot diagnostic binary sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, manager, description: FarmbotBinarySensorDescription) -> None:
        super().__init__(manager)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{manager.device_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return bool(self.entity_description.value_fn(self._manager))

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update)
        )

    def _handle_update(self) -> None:
        self.async_write_ha_state()
