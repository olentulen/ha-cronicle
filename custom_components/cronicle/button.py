"""Cronicle button platform."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CronicleEvent
from .const import CONF_HOST, CONF_PORT, CONF_USE_SSL, DOMAIN
from .coordinator import CronicleCoordinator


@dataclass(frozen=True)
class CronicleButtonDescription(ButtonEntityDescription):
    """Cronicle button description."""

    action: str = ""


BUTTON_DESCRIPTIONS: tuple[CronicleButtonDescription, ...] = (
    CronicleButtonDescription(
        key="refresh",
        name="Refresh",
        icon="mdi:refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        action="refresh",
    ),
    CronicleButtonDescription(
        key="enable_scheduler",
        name="Enable Scheduler",
        icon="mdi:calendar-check",
        entity_category=EntityCategory.CONFIG,
        action="enable_scheduler",
    ),
    CronicleButtonDescription(
        key="disable_scheduler",
        name="Disable Scheduler",
        icon="mdi:calendar-remove",
        entity_category=EntityCategory.CONFIG,
        action="disable_scheduler",
    ),
)


def _device_info(entry: ConfigEntry) -> dict:
    scheme = "https" if entry.data.get(CONF_USE_SSL) else "http"
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "Cronicle",
        "manufacturer": "Cronicle",
        "model": "Job Scheduler",
        "configuration_url": f"{scheme}://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}",
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CronicleCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[CronicleButton] = [
        CronicleButton(coordinator, entry, description)
        for description in BUTTON_DESCRIPTIONS
    ]

    initial_events = {
        event.id: event
        for event in coordinator.data.events
        if event.id
    }

    entities.extend(
        CronicleEventButton(coordinator, entry, event)
        for event in initial_events.values()
    )

    async_add_entities(entities)

    known_event_ids = set(initial_events)

    @callback
    def _check_events() -> None:
        """Add buttons for newly discovered Cronicle events."""
        current_events = {
            event.id: event
            for event in coordinator.data.events
            if event.id
        }

        new_event_ids = set(current_events) - known_event_ids

        if not new_event_ids:
            return

        known_event_ids.update(new_event_ids)

        async_add_entities(
            CronicleEventButton(
                coordinator,
                entry,
                current_events[event_id],
            )
            for event_id in new_event_ids
        )

    _check_events()
    entry.async_on_unload(coordinator.async_add_listener(_check_events))


class CronicleButton(CoordinatorEntity[CronicleCoordinator], ButtonEntity):
    """Cronicle control button."""

    entity_description: CronicleButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CronicleCoordinator,
        entry: ConfigEntry,
        description: CronicleButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        action = self.entity_description.action

        if action == "refresh":
            await self.coordinator.async_request_refresh()
            return

        if action == "enable_scheduler":
            await self.coordinator.client.set_scheduler_enabled(True)
            await self.coordinator.async_request_refresh()
            return

        if action == "disable_scheduler":
            await self.coordinator.client.set_scheduler_enabled(False)
            await self.coordinator.async_request_refresh()


class CronicleEventButton(CoordinatorEntity[CronicleCoordinator], ButtonEntity):
    """Button for running a Cronicle event."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CronicleCoordinator,
        entry: ConfigEntry,
        event: CronicleEvent,
    ) -> None:
        super().__init__(coordinator)
        self._event_id = event.id
        self._attr_name = event.title
        self._attr_icon = "mdi:play-circle"
        self._attr_unique_id = f"{entry.entry_id}_event_{event.id}"
        self._attr_device_info = _device_info(entry)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update the button when the Cronicle event changes."""
        event = next(
            (
                event
                for event in self.coordinator.data.events
                if event.id == self._event_id
            ),
            None,
        )

        if event is None:
            self._attr_available = False
        else:
            self._attr_available = True
            self._attr_name = event.title

        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Run the Cronicle event immediately."""
        await self.coordinator.client.run_event(event_id=self._event_id)
        await self.coordinator.async_request_refresh()