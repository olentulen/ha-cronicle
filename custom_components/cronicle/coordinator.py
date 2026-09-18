"""Cronicle DataUpdateCoordinator."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from time import monotonic

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CronicleAPIError, CronicleClient, CronicleData

_LOGGER = logging.getLogger(__name__)


class CronicleCoordinator(DataUpdateCoordinator[CronicleData]):
    """Coordinates Cronicle API polling and diagnostics."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: CronicleClient,
        poll_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Cronicle",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.client = client
        self.last_update: datetime | None = None
        self.last_successful_update: datetime | None = None
        self.last_error: str | None = None
        self.api_response_time_ms: int | None = None
        self.api_failures = 0

    async def _async_update_data(self) -> CronicleData:
        start = monotonic()
        self.last_update = datetime.now(timezone.utc)
        try:
            data = await self.client.fetch_all()
        except CronicleAPIError as err:
            self.api_failures += 1
            self.last_error = str(err)
            self.api_response_time_ms = round((monotonic() - start) * 1000)
            raise UpdateFailed(f"Cronicle API error: {err}") from err

        self.api_response_time_ms = round((monotonic() - start) * 1000)
        if data.errors:
            self.api_failures += len(data.errors)
            self.last_error = "; ".join(data.errors)
        else:
            self.last_error = None
            self.last_successful_update = self.last_update
        return data
