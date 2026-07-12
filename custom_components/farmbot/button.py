"""Button entities for FarmBot commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STATE
from .entity import FarmbotEntity


@dataclass(frozen=True, kw_only=True)
class FarmbotButtonDescription(ButtonEntityDescription):
    """Describe a FarmBot command button."""

    command_fn: Callable
    available_fn: Callable = lambda manager: manager.mqtt_connected


COMMAND_DESCRIPTIONS = (
    FarmbotButtonDescription(
        key="sync",
        translation_key="sync",
        icon="mdi:sync",
        entity_category=EntityCategory.CONFIG,
        command_fn=lambda manager: manager.sync(),
    ),
    FarmbotButtonDescription(
        key="emergency_stop",
        translation_key="emergency_stop",
        icon="mdi:alert-octagon",
        command_fn=lambda manager: manager.emergency_lock(),
        available_fn=lambda manager: manager.mqtt_connected and not manager.emergency_stopped,
    ),
    FarmbotButtonDescription(
        key="unlock",
        translation_key="unlock",
        icon="mdi:lock-open-variant",
        command_fn=lambda manager: manager.emergency_unlock(),
        available_fn=lambda manager: manager.mqtt_connected and manager.emergency_stopped,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FarmBot buttons."""
    manager = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            FarmbotRunSequenceButton(manager),
            *(FarmbotCommandButton(manager, description) for description in COMMAND_DESCRIPTIONS),
        ]
    )


class FarmbotCommandButton(FarmbotEntity, ButtonEntity):
    """Run a direct FarmBot command."""

    def __init__(self, manager, description: FarmbotButtonDescription) -> None:
        super().__init__(manager)
        self.entity_description = description
        self._attr_unique_id = f"{manager.device_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Return whether the command can currently be used."""
        return bool(self.entity_description.available_fn(self._manager))

    async def async_press(self) -> None:
        """Send the command without blocking Home Assistant's event loop."""
        await self.hass.async_add_executor_job(
            self.entity_description.command_fn,
            self._manager,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class FarmbotRunSequenceButton(FarmbotEntity, ButtonEntity):
    """Run the sequence chosen by the FarmBot sequence selector."""

    _attr_has_entity_name = True
    _attr_name = "Run selected sequence"
    _attr_icon = "mdi:play-circle-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self._attr_unique_id = f"{manager.device_id}_run_selected_sequence"

    @property
    def available(self) -> bool:
        return bool(
            self._manager.mqtt_connected
            and getattr(self._manager, "selected_sequence_id", None) is not None
        )

    async def async_press(self) -> None:
        sequence_id = getattr(self._manager, "selected_sequence_id", None)
        if sequence_id is not None:
            await self.hass.async_add_executor_job(
                self._manager.execute_sequence,
                sequence_id,
            )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_STATE, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
