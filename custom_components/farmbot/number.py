"""Writable FarmBot motion target entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import FarmbotEntity


@dataclass(frozen=True, kw_only=True)
class FarmbotMotionNumberDescription(NumberEntityDescription):
    """Describe a writable FarmBot motion value."""

    manager_attribute: str


MOTION_NUMBERS = (
    FarmbotMotionNumberDescription(
        key="target_x",
        name="Target X",
        icon="mdi:axis-x-arrow",
        native_min_value=0,
        native_max_value=3000,
        native_step=1,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        mode=NumberMode.BOX,
        manager_attribute="target_x",
    ),
    FarmbotMotionNumberDescription(
        key="target_y",
        name="Target Y",
        icon="mdi:axis-y-arrow",
        native_min_value=0,
        native_max_value=1500,
        native_step=1,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        mode=NumberMode.BOX,
        manager_attribute="target_y",
    ),
    FarmbotMotionNumberDescription(
        key="target_z",
        name="Target Z",
        icon="mdi:axis-z-arrow",
        native_min_value=-500,
        native_max_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        mode=NumberMode.BOX,
        manager_attribute="target_z",
    ),
    FarmbotMotionNumberDescription(
        key="movement_speed",
        name="Movement speed",
        icon="mdi:speedometer",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        manager_attribute="movement_speed",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FarmBot motion target numbers."""
    manager = hass.data[DOMAIN][entry.entry_id]

    defaults = {
        "target_x": 0.0,
        "target_y": 0.0,
        "target_z": 0.0,
        "movement_speed": 50.0,
    }
    for attribute, value in defaults.items():
        if not hasattr(manager, attribute):
            setattr(manager, attribute, value)

    async_add_entities(
        FarmbotMotionNumber(manager, description) for description in MOTION_NUMBERS
    )


class FarmbotMotionNumber(FarmbotEntity, NumberEntity):
    """Store a FarmBot movement target without moving immediately."""

    _attr_has_entity_name = True

    def __init__(
        self,
        manager,
        description: FarmbotMotionNumberDescription,
    ) -> None:
        super().__init__(manager)
        self.entity_description = description
        self._attr_unique_id = f"{manager.device_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Return whether movement settings can be edited."""
        return bool(self._manager.mqtt_connected and not self._manager.emergency_stopped)

    @property
    def native_value(self) -> float:
        """Return the currently configured target value."""
        return float(getattr(self._manager, self.entity_description.manager_attribute))

    async def async_set_native_value(self, value: float) -> None:
        """Store a target value for the separate Move to target command."""
        setattr(
            self._manager,
            self.entity_description.manager_attribute,
            float(value),
        )
        self.async_write_ha_state()
