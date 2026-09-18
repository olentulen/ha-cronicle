"""Cronicle REST API client."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import aiohttp

_LOGGER = logging.getLogger(__name__)


@dataclass
class ActiveJob:
    """Represents a currently running Cronicle job."""

    id: str
    event: str
    title: str
    source: str
    elapsed: float
    progress: float
    hostname: str
    nice_target: str
    category: str
    plugin: str
    time_start: float
    timeout: int
    pid: int | None
    cpu_current: float
    mem_current: int


@dataclass
class CompletedJob:
    """Represents one row in get_history."""

    id: str
    event: str
    title: str
    code: int
    elapsed: float
    hostname: str
    category: str
    plugin: str
    source: str
    description: str
    time_start: float
    time_end: float


@dataclass
class CronicleData:
    """Single collected Cronicle data snapshot."""

    scheduler_enabled: bool = False
    active_jobs: list[ActiveJob] = field(default_factory=list)
    total_events: int = 0
    enabled_events: int = 0
    disabled_events: int = 0
    recent_jobs: list[CompletedJob] = field(default_factory=list)
    history_total: int = 0
    errors: list[str] = field(default_factory=list)


class CronicleAPIError(Exception):
    """Raised when a Cronicle API call fails or returns a non-zero code."""


class CronicleClient:
    """Async wrapper for the Cronicle REST API."""

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        session: aiohttp.ClientSession,
        use_ssl: bool = False,
        history_limit: int = 5,
    ) -> None:
        scheme = "https" if use_ssl else "http"
        self._base = f"{scheme}://{host}:{port}/api/app"
        self._headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self._session = session
        self._history_limit = max(1, history_limit)

    async def _get(self, endpoint: str) -> dict:
        url = f"{self._base}/{endpoint}/v1"
        try:
            async with self._session.get(
                url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as err:
            raise CronicleAPIError(f"HTTP error on {endpoint}: {err}") from err
        return _validate_response(endpoint, data)

    async def _post(self, endpoint: str, payload: dict | None = None) -> dict:
        url = f"{self._base}/{endpoint}/v1"
        try:
            async with self._session.post(
                url,
                headers=self._headers,
                json=payload or {},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as err:
            raise CronicleAPIError(f"HTTP error on {endpoint}: {err}") from err
        return _validate_response(endpoint, data)

    async def fetch_all(self) -> CronicleData:
        """Fetch the Cronicle state used by entities."""
        results = await asyncio.gather(
            self._get("get_master_state"),
            self._get("get_active_jobs"),
            self._post("get_schedule", {"offset": 0, "limit": 1000}),
            self._post("get_history", {"offset": 0, "limit": self._history_limit}),
            return_exceptions=True,
        )

        data = CronicleData()

        if isinstance(results[0], dict):
            data.scheduler_enabled = bool(results[0].get("state", {}).get("enabled", 0))
        else:
            _append_error(data, "get_master_state", results[0])

        if isinstance(results[1], dict):
            jobs_raw = results[1].get("jobs", {}) or {}
            data.active_jobs = [_parse_active_job(job) for job in jobs_raw.values()]
        else:
            _append_error(data, "get_active_jobs", results[1])

        if isinstance(results[2], dict):
            rows = results[2].get("rows", []) or []
            data.total_events = int(results[2].get("list", {}).get("length", len(rows)) or 0)
            data.enabled_events = sum(1 for event in rows if event.get("enabled"))
            data.disabled_events = max(data.total_events - data.enabled_events, 0)
        else:
            _append_error(data, "get_schedule", results[2])

        if isinstance(results[3], dict):
            rows = results[3].get("rows", []) or []
            data.recent_jobs = [_parse_completed_job(row) for row in rows]
            data.history_total = int(results[3].get("list", {}).get("length", len(rows)) or 0)
        else:
            _append_error(data, "get_history", results[3])

        return data

    async def test_connection(self) -> None:
        """Validate API connectivity."""
        await self._get("get_master_state")

    async def run_event(self, event_id: str | None = None, title: str | None = None) -> dict:
        """Run an event immediately by ID or exact title."""
        payload = _id_or_title_payload(event_id, title)
        return await self._post("run_event", payload)

    async def abort_job(self, job_id: str) -> dict:
        """Abort a running job."""
        return await self._post("abort_job", {"id": job_id})

    async def update_job(self, job_id: str, **kwargs) -> dict:
        """Update a running job."""
        payload = {"id": job_id}
        payload.update({key: value for key, value in kwargs.items() if value is not None})
        return await self._post("update_job", payload)

    async def set_scheduler_enabled(self, enabled: bool) -> dict:
        """Enable or disable the Cronicle scheduler."""
        return await self._post("update_master_state", {"enabled": 1 if enabled else 0})

    async def get_job_status(self, job_id: str) -> dict:
        """Fetch status for one job."""
        return await self._post("get_job_status", {"id": job_id})


def _validate_response(endpoint: str, data: dict) -> dict:
    if data.get("code") != 0:
        raise CronicleAPIError(
            f"Cronicle returned code={data.get('code')} on {endpoint}: {data.get('description')}"
        )
    return data


def _append_error(data: CronicleData, endpoint: str, err) -> None:
    message = f"{endpoint}: {err}"
    data.errors.append(message)
    _LOGGER.warning("Cronicle API call failed: %s", message)


def _id_or_title_payload(event_id: str | None, title: str | None) -> dict:
    if event_id:
        return {"id": event_id}
    if title:
        return {"title": title}
    raise CronicleAPIError("Either id or title is required")


def _parse_active_job(raw: dict) -> ActiveJob:
    cpu_obj = raw.get("cpu") or {}
    mem_obj = raw.get("mem") or {}
    return ActiveJob(
        id=raw.get("id", ""),
        event=raw.get("event", ""),
        title=raw.get("event_title", raw.get("id", "Unknown")),
        source=raw.get("source", ""),
        elapsed=_to_float(raw.get("elapsed")),
        progress=_to_float(raw.get("progress")),
        hostname=raw.get("hostname", ""),
        nice_target=raw.get("nice_target") or raw.get("target", ""),
        category=raw.get("category_title") or raw.get("category", ""),
        plugin=raw.get("plugin_title") or raw.get("plugin", ""),
        time_start=_to_float(raw.get("time_start")),
        timeout=int(raw.get("timeout") or 0),
        pid=raw.get("pid"),
        cpu_current=_to_float(cpu_obj.get("current")),
        mem_current=int(mem_obj.get("current") or 0),
    )


def _parse_completed_job(raw: dict) -> CompletedJob:
    return CompletedJob(
        id=raw.get("id", ""),
        event=raw.get("event", ""),
        title=raw.get("event_title", raw.get("title", "Unknown")),
        code=int(raw.get("code") or 0),
        elapsed=_to_float(raw.get("elapsed")),
        hostname=raw.get("hostname", ""),
        category=raw.get("category_title") or raw.get("category", ""),
        plugin=raw.get("plugin_title") or raw.get("plugin", ""),
        source=raw.get("source", ""),
        description=raw.get("description", ""),
        time_start=_to_float(raw.get("time_start")),
        time_end=_to_float(raw.get("time_end")),
    )


def _to_float(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
