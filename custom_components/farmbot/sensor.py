"""Sensors for FarmBot status, versions, position and diagnostics."""

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
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity


@dataclass(frozen=True, kw_only=True)
class FarmbotSensorDescription(SensorEntityDescription):
    """Describe a FarmBot sensor."""

    value_fn: Callable[[Any], Any]


DIAGNOSTIC_DESCRIPTIONS = (
    FarmbotSensorDescription(
        key="controller_version",
        translation_key="controller_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager: manager.controller_version,
    ),
    FarmbotSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager: manager.firmware_version,
    ),
    FarmbotSensorDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda manager: manager.uptime,
    ),
    FarmbotSensorDescription(
        key="selected_tool_slot",
        translation_key="selected_tool_slot",
        icon="mdi:tools",
        value_fn=lambda manager: manager.selected_tool_slot,
    ),
    FarmbotSensorDescription(
        key="diagnostic_health",
        translation_key="diagnostic_health",
        icon="mdi:heart-pulse",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager: manager.diagnostic_health,
    ),
    FarmbotSensorDescription(
        key="last_log_message",
        translation_key="last_log_message",
        icon="mdi:text-box-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager: manager.last_log.message if manager.last_log else None,
    ),
    FarmbotSensorDescription(
        key="last_log_severity",
        translation_key="last_log_severity",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager: manager.last_log.severity if manager.last_log else None,
    ),
    FarmbotSensorDescription(
        key="last_error_message",
        translation_key="last_error_message",
        icon="mdi:alert-octagon-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager: manager.last_error_log.message if manager.last_error_log else None,
    ),
    FarmbotSensorDescription(
        key="last_farmduino_message",
        translation_key="last_farmduino_message",
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda manager: manager.last_farmduino_log.message if manager.last_farmduino_log else None,
    ),
    FarmbotSensorDescription(
        key="log_count",
        translation_key="log_count",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda manager: manager.log_count,
    ),
    FarmbotSensorDescription(
        key="error_count",
        translation_key="error_count",
        icon="mdi:alert-box-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda manager: manager.error_count,
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
            FarmbotPositionSensor(manager, "x", "X position", "mdi:axis-x-arrow"),
            FarmbotPositionSensor(manager, "y", "Y position", "mdi:axis-y-arrow"),
            FarmbotPositionSensor(manager, "z", "Z position", "mdi:axis-z-arrow"),
            *(FarmbotStatusSensor(manager, description) for description in DIAGNOSTIC_DESCRIPTIONS),
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


class FarmbotStatusSensor(FarmbotEntity, SensorEntity):
    """A value extracted from the FarmBot manager."""

    def __init__(self, manager, description: FarmbotSensorDescription) -> None:
        super().__init__(manager)
        self.entity_description = description
        self._attr_unique_id = f"{manager.device_id}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value_fn(self._manager)

    @property
    def available(self) -> bool:
        return bool(self._manager.mqtt_connected and self.native_value is not None)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class FarmbotPositionSensor(FarmbotEntity, SensorEntity):
    """Current position of one FarmBot axis."""

    _attr_native_unit_of_measurement = "mm"
    _attr_suggested_display_precision = 1

    def __init__(self, manager, axis: str, name: str, icon: str) -> None:
        super().__init__(manager)
        self._axis = axis
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{manager.device_id}_position_{axis}"

    def _position_value(self) -> float | None:
        location_data = self._manager.status.get("location_data")
        if not isinstance(location_data, dict):
            return None
        position = location_data.get("position")
        if not isinstance(position, dict):
            return None
        value = position.get(self._axis)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def native_value(self) -> float | None:
        return self._position_value()

    @property
    def available(self) -> bool:
        return bool(self._manager.mqtt_connected and self._manager.status_fresh and self._position_value() is not None)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
