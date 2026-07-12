"""Base entity for FarmBot."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class FarmbotEntity(Entity):
    """Base class shared by FarmBot entities."""

    _attr_has_entity_name = True

    def __init__(self, manager) -> None:
        self._manager = manager

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata from the latest FarmBot status payload."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._manager.device_id)},
            name=self._manager.device_name,
            manufacturer="FarmBot Inc.",
            model=self._manager.model,
            sw_version=self._manager.controller_version,
            hw_version=self._manager.firmware_version,
            configuration_url="https://my.farm.bot/app",
        )

    @property
    def available(self) -> bool:
        """Return whether MQTT is connected."""
        return self._manager.mqtt_connected
