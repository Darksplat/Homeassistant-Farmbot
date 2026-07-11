"""Button entities for FarmBot commands."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FarmBot command buttons."""
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FarmbotRunSequenceButton(manager)])


class FarmbotRunSequenceButton(FarmbotEntity, ButtonEntity):
    """Run the sequence chosen by the FarmBot sequence selector."""

    _attr_has_entity_name = True
    _attr_name = "Run selected sequence"

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.device_id}_run_selected_sequence"

    @property
    def available(self) -> bool:
        """Return whether a sequence can currently be executed."""
        return bool(
            self._manager.mqtt_connected
            and getattr(self._manager, "selected_sequence_id", None) is not None
        )

    async def async_press(self) -> None:
        """Execute the selected FarmBot sequence."""
        sequence_id = getattr(self._manager, "selected_sequence_id", None)
        if sequence_id is None:
            return
        await self.hass.async_add_executor_job(
            self._manager.execute_sequence,
            sequence_id,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to connectivity and sequence-selection changes."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        """Refresh button availability."""
        self.async_write_ha_state()
