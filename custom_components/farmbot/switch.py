"""Switch entities for FarmBot peripherals."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import async_get_resource
from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity


def _icon_for_peripheral(label: str) -> str:
    """Return a useful icon based on the peripheral label."""
    value = label.casefold()
    if "water" in value or "pump" in value:
        return "mdi:water-pump"
    if "vacuum" in value:
        return "mdi:vacuum"
    if "light" in value or "led" in value:
        return "mdi:lightbulb"
    if "rotary" in value or "tool" in value:
        return "mdi:saw-blade"
    if "fan" in value:
        return "mdi:fan"
    if "camera" in value:
        return "mdi:camera"
    return "mdi:toggle-switch"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up switches for peripherals configured in FarmBot."""
    manager = hass.data[DOMAIN][entry.entry_id]
    peripherals = await async_get_resource(manager, "peripherals")
    async_add_entities(
        FarmbotPeripheralSwitch(manager, peripheral)
        for peripheral in peripherals
        if peripheral.get("pin") is not None
    )


class FarmbotPeripheralSwitch(FarmbotEntity, SwitchEntity):
    """Control one FarmBot peripheral pin."""

    _attr_has_entity_name = True

    def __init__(self, manager, peripheral: dict[str, Any]) -> None:
        super().__init__(manager)
        self._pin = int(peripheral["pin"])
        label = str(peripheral.get("label") or f"Peripheral {self._pin}")
        self._attr_name = label
        self._attr_icon = _icon_for_peripheral(label)
        peripheral_id = peripheral.get("id", self._pin)
        self._attr_unique_id = f"{manager.device_id}_peripheral_{peripheral_id}"

    @property
    def available(self) -> bool:
        return self._manager.mqtt_connected

    @property
    def is_on(self) -> bool:
        pin_state = self._manager.status.get("pins", {}).get(str(self._pin), {})
        if isinstance(pin_state, dict):
            return bool(pin_state.get("value", 0))
        return bool(pin_state)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._manager.send_write_pin, self._pin, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(self._manager.send_write_pin, self._pin, 0)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
