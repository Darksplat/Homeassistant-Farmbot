"""Sensors for FarmBot status and position."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity


@dataclass(frozen=True, kw_only=True)
class FarmbotPositionSensorDescription(SensorEntityDescription):
    """Describe a FarmBot position sensor."""

    value_fn: Callable[[dict[str, Any]], float | None]


def _axis_position(status: dict[str, Any], axis: str) -> float | None:
    """Return one axis from the latest FarmBot status payload."""
    value = (
        status.get("location_data", {})
        .get("position", {})
        .get(axis)
    )
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


POSITION_DESCRIPTIONS = (
    FarmbotPositionSensorDescription(
        key="position_x",
        translation_key="position_x",
        icon="mdi:axis-x-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda status: _axis_position(status, "x"),
    ),
    FarmbotPositionSensorDescription(
        key="position_y",
        translation_key="position_y",
        icon="mdi:axis-y-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda status: _axis_position(status, "y"),
    ),
    FarmbotPositionSensorDescription(
        key="position_z",
        translation_key="position_z",
        icon="mdi:axis-z-arrow",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda status: _axis_position(status, "z"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FarmBot sensors."""
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            FarmbotLastStatusSensor(manager),
            *(FarmbotPositionSensor(manager, description) for description in POSITION_DESCRIPTIONS),
        ]
    )


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


class FarmbotPositionSensor(FarmbotEntity, SensorEntity):
    """Current position of one FarmBot axis."""

    entity_description: FarmbotPositionSensorDescription

    def __init__(self, manager, description: FarmbotPositionSensorDescription) -> None:
        super().__init__(manager)
        self.entity_description = description
        self._attr_unique_id = f"{manager.device_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current axis position in millimetres."""
        return self.entity_description.value_fn(self._manager.status)

    @property
    def available(self) -> bool:
        """Return whether a fresh position value is available."""
        return bool(
            self._manager.mqtt_connected
            and self._manager.status_fresh
            and self.native_value is not None
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
