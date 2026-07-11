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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.device_id)},
            name=manager.device_name,
            manufacturer="FarmBot",
            model="FarmBot",
            configuration_url="https://my.farm.bot/app",
        )

    @property
    def available(self) -> bool:
        """Return whether MQTT is connected."""
        return self._manager.mqtt_connected
