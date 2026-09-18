"""Cronicle button platform."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    async_add_entities(CronicleButton(coordinator, entry, desc) for desc in BUTTON_DESCRIPTIONS)


class CronicleButton(CoordinatorEntity[CronicleCoordinator], ButtonEntity):
    """Cronicle button."""

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
