"""Cronicle sensor platform."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, CONF_PORT, CONF_RECENT_JOBS_COUNT, CONF_USE_SSL, DOMAIN
from .coordinator import CronicleCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CronicleSensorDescription(SensorEntityDescription):
    """Cronicle sensor description."""


SENSOR_DESCRIPTIONS: tuple[CronicleSensorDescription, ...] = (
    CronicleSensorDescription(
        key="active_jobs",
        name="Active Jobs",
        icon="mdi:play-circle-multiple",
        native_unit_of_measurement="jobs",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(
        key="total_events",
        name="Total Events",
        icon="mdi:calendar-multiple",
        native_unit_of_measurement="events",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(
        key="enabled_events",
        name="Enabled Events",
        icon="mdi:calendar-check",
        native_unit_of_measurement="events",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(
        key="disabled_events",
        name="Disabled Events",
        icon="mdi:calendar-remove",
        native_unit_of_measurement="events",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(key="last_job", name="Last Job", icon="mdi:history"),
    CronicleSensorDescription(key="last_job_code", name="Last Job Code", icon="mdi:check-circle-outline"),
    CronicleSensorDescription(
        key="last_job_duration",
        name="Last Job Duration",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(
        key="last_job_finished",
        name="Last Job Finished",
        icon="mdi:clock-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    CronicleSensorDescription(
        key="recent_jobs",
        name="Recent Jobs",
        icon="mdi:format-list-bulleted",
        native_unit_of_measurement="jobs",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(
        key="failed_recent_jobs",
        name="Failed Recent Jobs",
        icon="mdi:alert-circle-outline",
        native_unit_of_measurement="jobs",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(
        key="success_rate",
        name="Success Rate",
        icon="mdi:percent-circle-outline",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CronicleSensorDescription(
        key="api_status",
        name="API Status",
        icon="mdi:api",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleSensorDescription(
        key="last_update",
        name="Last Update",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleSensorDescription(
        key="last_successful_update",
        name="Last Successful Update",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleSensorDescription(
        key="last_error",
        name="Last Error",
        icon="mdi:alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleSensorDescription(
        key="api_response_time",
        name="API Response Time",
        icon="mdi:timer-sand",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleSensorDescription(
        key="api_failures",
        name="API Failures",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleSensorDescription(
        key="history_total",
        name="History Total",
        icon="mdi:history",
        native_unit_of_measurement="jobs",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CronicleSensorDescription(
        key="recent_jobs_limit",
        name="Recent Jobs Limit",
        icon="mdi:format-list-numbered",
        native_unit_of_measurement="jobs",
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
    async_add_entities(CronicleSensor(coordinator, entry, desc) for desc in SENSOR_DESCRIPTIONS)


class CronicleSensor(CoordinatorEntity[CronicleCoordinator], SensorEntity):
    """Cronicle sensor."""

    entity_description: CronicleSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CronicleCoordinator,
        entry: ConfigEntry,
        description: CronicleSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    def _last_job(self):
        jobs = self.coordinator.data.recent_jobs
        return jobs[0] if jobs else None

    @property
    def native_value(self):
        data = self.coordinator.data
        key = self.entity_description.key

        if key == "active_jobs":
            return len(data.active_jobs)
        if key == "total_events":
            return data.total_events
        if key == "enabled_events":
            return data.enabled_events
        if key == "disabled_events":
            return data.disabled_events
        if key == "recent_jobs":
            return len(data.recent_jobs)
        if key == "failed_recent_jobs":
            return sum(1 for job in data.recent_jobs if job.code != 0)
        if key == "success_rate":
            if not data.recent_jobs:
                return None
            success = sum(1 for job in data.recent_jobs if job.code == 0)
            return round((success / len(data.recent_jobs)) * 100, 1)

        if key == "api_status":
            return "Error" if self.coordinator.last_error else "Connected"
        if key == "last_update":
            return self.coordinator.last_update
        if key == "last_successful_update":
            return self.coordinator.last_successful_update
        if key == "last_error":
            return self.coordinator.last_error
        if key == "api_response_time":
            return self.coordinator.api_response_time_ms
        if key == "api_failures":
            return self.coordinator.api_failures
        if key == "history_total":
            return data.history_total
        if key == "recent_jobs_limit":
            return self._entry.options.get(
                CONF_RECENT_JOBS_COUNT,
                self._entry.data.get(CONF_RECENT_JOBS_COUNT),
            )

        last = self._last_job()
        if last is None:
            return None
        if key == "last_job":
            return last.title
        if key == "last_job_code":
            return last.code
        if key == "last_job_duration":
            return round(last.elapsed)
        if key == "last_job_finished":
            timestamp = last.time_end
            if timestamp <= 0 and last.time_start > 0:
                timestamp = last.time_start + last.elapsed
                _LOGGER.debug("Using time_start + elapsed for last_job_finished: %s", timestamp)
            if timestamp <= 0:
                return None
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        key = self.entity_description.key

        if key == "active_jobs":
            return {
                "jobs": [
                    {
                        "id": job.id,
                        "event": job.event,
                        "title": job.title,
                        "source": job.source,
                        "elapsed_s": round(job.elapsed),
                        "progress_pct": round(job.progress * 100, 1),
                        "hostname": job.hostname,
                        "target": job.nice_target,
                        "category": job.category,
                        "plugin": job.plugin,
                        "cpu_pct": round(job.cpu_current, 1),
                        "memory_mb": round(job.mem_current / 1024 / 1024, 1) if job.mem_current else 0,
                    }
                    for job in data.active_jobs
                ]
            }

        if key == "recent_jobs":
            return {
                "jobs": [
                    {
                        "id": job.id,
                        "event": job.event,
                        "title": job.title,
                        "exit_code": job.code,
                        "success": job.code == 0,
                        "elapsed_s": round(job.elapsed),
                        "hostname": job.hostname,
                        "category": job.category,
                        "plugin": job.plugin,
                        "source": job.source,
                        "description": job.description,
                        "time_start": job.time_start,
                        "time_end": job.time_end,
                        "finished": _fmt_ts(
                            job.time_end if job.time_end > 0 else (job.time_start + job.elapsed if job.time_start > 0 else 0)
                        ),
                    }
                    for job in data.recent_jobs
                ]
            }

        last = self._last_job()
        if last is not None and key == "last_job":
            return {
                "job_id": last.id,
                "event": last.event,
                "exit_code": last.code,
                "elapsed_s": round(last.elapsed),
                "hostname": last.hostname,
                "category": last.category,
                "plugin": last.plugin,
                "source": last.source,
                "description": last.description,
                "time_start": last.time_start,
                "time_end": last.time_end,
            }

        if key == "api_status":
            return {"errors": data.errors}

        return {}


def _fmt_ts(epoch: float) -> str | None:
    if not epoch or epoch <= 0:
        return None
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None
