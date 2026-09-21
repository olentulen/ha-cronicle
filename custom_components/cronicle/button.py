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
        "configuration_url": (
            f"{scheme}://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
        ),
    }


def _event_key(event: CronicleEvent) -> str:
    """Return the stable identity key for an event.

    Git-managed events are identified by their script name.
    Manual Cronicle events are identified by their Cronicle event ID.
    """

    if event.script_name:
        return f"script:{event.script_name}"

    return f"id:{event.id}"


def _event_unique_id(
    entry: ConfigEntry,
    event: CronicleEvent,
) -> str:
    """Build a stable Home Assistant unique ID for an event."""

    if event.script_name:
        return f"{entry.entry_id}_event_{event.script_name}"

    return f"{entry.entry_id}_event_{event.id}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CronicleCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ButtonEntity] = [
        CronicleButton(coordinator, entry, description)
        for description in BUTTON_DESCRIPTIONS
    ]

    event_entities: dict[str, CronicleEventButton] = {}

    for event in coordinator.data.events:
        if not event.id:
            continue

        key = _event_key(event)

        if key in event_entities:
            continue

        event_entities[key] = CronicleEventButton(
            coordinator,
            entry,
            event,
        )

    entities.extend(event_entities.values())

    async_add_entities(entities)

    @callback
    def _check_events() -> None:
        """Update existing event buttons and add newly discovered events."""

        current_events: dict[str, CronicleEvent] = {}

        for event in coordinator.data.events:
            if not event.id:
                continue

            key = _event_key(event)

            # Avoid duplicate entities if Cronicle somehow returns
            # duplicate events with the same logical identity.
            if key in current_events:
                continue

            current_events[key] = event

        # Update existing entities.
        for key, entity in event_entities.items():
            event = current_events.get(key)

            if event is None:
                entity._event_id = None
                entity._attr_available = False
            else:
                entity._event_id = event.id
                entity._attr_available = True
                entity._attr_name = event.title
                entity._attr_icon = "mdi:play-circle"

            entity.async_write_ha_state()

        # Add newly discovered events.
        for key, event in current_events.items():
            if key in event_entities:
                continue

            entity = CronicleEventButton(
                coordinator,
                entry,
                event,
            )

            event_entities[key] = entity
            async_add_entities([entity])

    _check_events()

    entry.async_on_unload(
        coordinator.async_add_listener(_check_events)
    )


class CronicleButton(
    CoordinatorEntity[CronicleCoordinator],
    ButtonEntity,
):
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


class CronicleEventButton(
    CoordinatorEntity[CronicleCoordinator],
    ButtonEntity,
):
    """Button for running a Cronicle event."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CronicleCoordinator,
        entry: ConfigEntry,
        event: CronicleEvent,
    ) -> None:
        super().__init__(coordinator)

        self._event_id: str | None = event.id
        self._event_key = _event_key(event)

        self._attr_name = event.title
        self._attr_icon = "mdi:play-circle"
        self._attr_unique_id = _event_unique_id(entry, event)
        self._attr_device_info = _device_info(entry)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update the button when Cronicle changes."""

        event = next(
            (
                event
                for event in self.coordinator.data.events
                if _event_key(event) == self._event_key
            ),
            None,
        )

        if event is None:
            self._event_id = None
            self._attr_available = False
        else:
            self._event_id = event.id
            self._attr_available = True
            self._attr_name = event.title

        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Run the Cronicle event immediately."""

        if self._event_id is None:
            return

        await self.coordinator.client.run_event(
            event_id=self._event_id
        )

        await self.coordinator.async_request_refresh()