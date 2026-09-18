"""Cronicle binary sensor platform."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, CONF_PORT, CONF_USE_SSL, DOMAIN
from .coordinator import CronicleCoordinator


@dataclass(frozen=True)
class CronicleBinarySensorDescription(BinarySensorEntityDescription):
    """Cronicle binary sensor description."""


BINARY_SENSOR_DESCRIPTIONS: tuple[CronicleBinarySensorDescription, ...] = (
    CronicleBinarySensorDescription(
        key="scheduler_enabled",
        name="Scheduler",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:calendar-clock",
    ),
    CronicleBinarySensorDescription(
        key="last_job_failed",
        name="Last Job Failed",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle-outline",
    ),
    CronicleBinarySensorDescription(
        key="active_jobs_running",
        name="Active Jobs Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:play-circle-outline",
    ),
    CronicleBinarySensorDescription(
        key="api_connected",
        name="API Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleBinarySensorDescription(
        key="problem",
        name="Problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
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
    async_add_entities(
        CronicleBinarySensor(coordinator, entry, desc) for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class CronicleBinarySensor(CoordinatorEntity[CronicleCoordinator], BinarySensorEntity):
    """Cronicle binary sensor."""

    entity_description: CronicleBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CronicleCoordinator,
        entry: ConfigEntry,
        description: CronicleBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    def _last_job(self):
        jobs = self.coordinator.data.recent_jobs
        return jobs[0] if jobs else None

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        key = self.entity_description.key

        if key == "scheduler_enabled":
            return data.scheduler_enabled
        if key == "last_job_failed":
            last = self._last_job()
            return None if last is None else last.code != 0
        if key == "active_jobs_running":
            return bool(data.active_jobs)
        if key == "api_connected":
            return self.coordinator.last_error is None
        if key == "problem":
            last = self._last_job()
            return self.coordinator.last_error is not None or (last is not None and last.code != 0)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        key = self.entity_description.key
        if key == "last_job_failed":
            last = self._last_job()
            if last is not None:
                return {
                    "job_title": last.title,
                    "exit_code": last.code,
                    "description": last.description,
                    "hostname": last.hostname,
                }
        if key == "problem":
            return {"last_error": self.coordinator.last_error}
        return {}
