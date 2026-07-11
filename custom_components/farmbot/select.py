"""Select entities for FarmBot sequences."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import FarmbotApiError, async_get_resource
from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FarmbotSequenceSelect(manager)], update_before_add=True)


class FarmbotSequenceSelect(FarmbotEntity, SelectEntity):
    """Choose a FarmBot sequence without executing it immediately."""

    _attr_has_entity_name = True
    _attr_name = "Sequence"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._sequences: dict[str, int] = {}
        self._attr_unique_id = f"{manager.device_id}_sequence_select"
        if not hasattr(manager, "selected_sequence_name"):
            manager.selected_sequence_name = None
            manager.selected_sequence_id = None

    @property
    def options(self) -> list[str]:
        return list(self._sequences)

    @property
    def current_option(self) -> str | None:
        return self._manager.selected_sequence_name

    async def async_select_option(self, option: str) -> None:
        self._manager.selected_sequence_name = option
        self._manager.selected_sequence_id = self._sequences[option]
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, SIGNAL_STATE)

    async def async_update(self) -> None:
        try:
            sequences = await async_get_resource(self._manager, "sequences")
        except FarmbotApiError:
            self._attr_available = False
            return
        self._attr_available = True
        self._sequences = {
            str(sequence.get("name") or f"Sequence {sequence['id']}"): int(sequence["id"])
            for sequence in sequences
            if sequence.get("id") is not None
        }
        if self._manager.selected_sequence_name not in self._sequences:
            self._manager.selected_sequence_name = None
            self._manager.selected_sequence_id = None
