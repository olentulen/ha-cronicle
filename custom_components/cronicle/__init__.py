"""Cronicle integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TIMEOUT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CronicleAPIError, CronicleClient
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_ID,
    ATTR_TITLE,
    CONF_API_KEY,
    CONF_HOST,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_RECENT_JOBS_COUNT,
    CONF_USE_SSL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RECENT_JOBS_COUNT,
    DOMAIN,
    SERVICE_ABORT_JOB,
    SERVICE_DISABLE_SCHEDULER,
    SERVICE_ENABLE_SCHEDULER,
    SERVICE_REFRESH,
    SERVICE_RUN_EVENT,
    SERVICE_UPDATE_JOB,
)
from .coordinator import CronicleCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

UPDATE_JOB_FIELDS = {
    CONF_TIMEOUT,
    "retries",
    "retry_delay",
    "chain",
    "chain_error",
    "notify_success",
    "notify_fail",
    "web_hook",
    "cpu_limit",
    "cpu_sustain",
    "memory_limit",
    "memory_sustain",
    "log_max_size",
}


def _opt(entry: ConfigEntry, key: str, default):
    """Get option value with fallback to data, then default."""
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cronicle from a config entry."""
    poll_interval = _opt(entry, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    history_limit = _opt(entry, CONF_RECENT_JOBS_COUNT, DEFAULT_RECENT_JOBS_COUNT)

    session = async_get_clientsession(hass)
    client = CronicleClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        api_key=entry.data[CONF_API_KEY],
        session=session,
        use_ssl=entry.data.get(CONF_USE_SSL, False),
        history_limit=history_limit,
    )

    coordinator = CronicleCoordinator(hass, client, poll_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_RUN_EVENT,
                SERVICE_ABORT_JOB,
                SERVICE_UPDATE_JOB,
                SERVICE_ENABLE_SCHEDULER,
                SERVICE_DISABLE_SCHEDULER,
                SERVICE_REFRESH,
            ):
                hass.services.async_remove(DOMAIN, service)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Cronicle services once."""
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        return

    async def async_run_event(call: ServiceCall) -> None:
        for coordinator in _coordinators_from_call(hass, call):
            try:
                await coordinator.client.run_event(call.data.get(ATTR_ID), call.data.get(ATTR_TITLE))
            except CronicleAPIError as err:
                raise HomeAssistantError(str(err)) from err
            await coordinator.async_request_refresh()

    async def async_abort_job(call: ServiceCall) -> None:
        for coordinator in _coordinators_from_call(hass, call):
            try:
                await coordinator.client.abort_job(call.data[ATTR_ID])
            except CronicleAPIError as err:
                raise HomeAssistantError(str(err)) from err
            await coordinator.async_request_refresh()

    async def async_update_job(call: ServiceCall) -> None:
        kwargs = {key: call.data.get(key) for key in UPDATE_JOB_FIELDS if key in call.data}
        for coordinator in _coordinators_from_call(hass, call):
            try:
                await coordinator.client.update_job(call.data[ATTR_ID], **kwargs)
            except CronicleAPIError as err:
                raise HomeAssistantError(str(err)) from err
            await coordinator.async_request_refresh()

    async def async_enable_scheduler(call: ServiceCall) -> None:
        await _set_scheduler(hass, call, True)

    async def async_disable_scheduler(call: ServiceCall) -> None:
        await _set_scheduler(hass, call, False)

    async def async_refresh(call: ServiceCall) -> None:
        for coordinator in _coordinators_from_call(hass, call):
            await coordinator.async_request_refresh()

    entry_key = vol.Optional(ATTR_CONFIG_ENTRY_ID)
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_EVENT,
        async_run_event,
        schema=vol.Schema(
            {
                entry_key: cv.string,
                vol.Optional(ATTR_ID): cv.string,
                vol.Optional(ATTR_TITLE): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ABORT_JOB,
        async_abort_job,
        schema=vol.Schema({entry_key: cv.string, vol.Required(ATTR_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_JOB,
        async_update_job,
        schema=vol.Schema(
            {
                entry_key: cv.string,
                vol.Required(ATTR_ID): cv.string,
                vol.Optional(CONF_TIMEOUT): cv.positive_int,
                vol.Optional("retries"): vol.All(int, vol.Range(min=0)),
                vol.Optional("retry_delay"): vol.All(int, vol.Range(min=0)),
                vol.Optional("chain"): cv.string,
                vol.Optional("chain_error"): cv.string,
                vol.Optional("notify_success"): cv.string,
                vol.Optional("notify_fail"): cv.string,
                vol.Optional("web_hook"): cv.string,
                vol.Optional("cpu_limit"): vol.All(int, vol.Range(min=0)),
                vol.Optional("cpu_sustain"): vol.All(int, vol.Range(min=0)),
                vol.Optional("memory_limit"): vol.All(int, vol.Range(min=0)),
                vol.Optional("memory_sustain"): vol.All(int, vol.Range(min=0)),
                vol.Optional("log_max_size"): vol.All(int, vol.Range(min=0)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_SCHEDULER,
        async_enable_scheduler,
        schema=vol.Schema({entry_key: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_SCHEDULER,
        async_disable_scheduler,
        schema=vol.Schema({entry_key: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        async_refresh,
        schema=vol.Schema({entry_key: cv.string}),
    )


async def _set_scheduler(hass: HomeAssistant, call: ServiceCall, enabled: bool) -> None:
    for coordinator in _coordinators_from_call(hass, call):
        try:
            await coordinator.client.set_scheduler_enabled(enabled)
        except CronicleAPIError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()


def _coordinators_from_call(hass: HomeAssistant, call: ServiceCall) -> list[CronicleCoordinator]:
    coordinators = hass.data.get(DOMAIN, {})
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Cronicle config entry not found: {entry_id}")
        return [coordinator]
    return list(coordinators.values())
