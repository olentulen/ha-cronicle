"""Config flow for Cronicle integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CronicleAPIError, CronicleClient
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_RECENT_JOBS_COUNT,
    CONF_USE_SSL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_RECENT_JOBS_COUNT,
    DOMAIN,
    MAX_RECENT_JOBS_COUNT,
)

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_USE_SSL, default=False): bool,
        vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            int, vol.Range(min=10, max=3600)
        ),
        vol.Optional(
            CONF_RECENT_JOBS_COUNT, default=DEFAULT_RECENT_JOBS_COUNT
        ): vol.All(int, vol.Range(min=1, max=MAX_RECENT_JOBS_COUNT)),
    }
)


class CronicleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Cronicle config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = CronicleClient(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                api_key=user_input[CONF_API_KEY],
                session=session,
                use_ssl=user_input[CONF_USE_SSL],
            )
            try:
                await client.test_connection()
            except CronicleAPIError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Cronicle ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return CronicleOptionsFlow(config_entry)


class CronicleOptionsFlow(config_entries.OptionsFlow):
    """Handle Cronicle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        cur = self._config_entry.options
        data = self._config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=cur.get(
                            CONF_POLL_INTERVAL,
                            data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                        ),
                    ): vol.All(int, vol.Range(min=10, max=3600)),
                    vol.Optional(
                        CONF_RECENT_JOBS_COUNT,
                        default=cur.get(
                            CONF_RECENT_JOBS_COUNT,
                            data.get(CONF_RECENT_JOBS_COUNT, DEFAULT_RECENT_JOBS_COUNT),
                        ),
                    ): vol.All(int, vol.Range(min=1, max=MAX_RECENT_JOBS_COUNT)),
                }
            ),
        )
