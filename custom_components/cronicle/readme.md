# Cronicle for Home Assistant

A custom Home Assistant integration for monitoring and controlling a local [Cronicle](https://github.com/jhuckaby/Cronicle) job scheduler instance.

The integration connects to the Cronicle REST API and exposes scheduler state, active jobs, schedule counts, recent job history, diagnostics, buttons, and services as Home Assistant entities.

## Features

- UI-based setup through Home Assistant
- HTTP and HTTPS support
- Local polling
- Configurable poll interval
- Configurable recent job history limit
- Device page with direct link back to the Cronicle web UI
- Sensors for scheduler state, active jobs, scheduled events, and recent job history
- Diagnostic entities for API health and update status
- Binary sensors for scheduler status, job failure state, API connectivity, and problem state
- Buttons for refresh and scheduler control
- Services for running events, aborting jobs, updating jobs, scheduler control, and manual refresh

## Requirements

- Home Assistant
- A reachable Cronicle instance
- Cronicle API key
- Network access from Home Assistant to Cronicle

Default Cronicle port is `3012`.

## Installation

Copy the integration folder into your Home Assistant `custom_components` directory:

```text
config/custom_components/cronicle/
```

Expected structure:

```text
custom_components/cronicle/
├── __init__.py
├── api.py
├── binary_sensor.py
├── button.py
├── config_flow.py
├── const.py
├── coordinator.py
├── manifest.json
├── sensor.py
├── services.yaml
├── strings.json
└── translations/
    └── en.json
```

Restart Home Assistant after copying the files.

## Setup

1. Go to **Settings → Devices & services**
2. Click **Add integration**
3. Search for **Cronicle**
4. Enter:
   - **Host**
   - **Port**
   - **API Key**
   - **Use HTTPS**
   - **Poll interval**
   - **Recent jobs count**
5. Submit the form

The integration validates the connection during setup by calling Cronicle's `get_master_state` endpoint.

## Configuration Options

After setup, the following options can be changed from the integration options menu:

| Option | Default | Range | Description |
|---|---:|---:|---|
| Poll interval | `30` seconds | `10–3600` | How often Home Assistant polls Cronicle |
| Recent jobs count | `5` | `1–25` | Number of completed jobs kept in attributes |

## Entities

### Sensors

| Entity | Category | Description |
|---|---|---|
| `sensor.cronicle_active_jobs` | Regular | Number of currently running jobs |
| `sensor.cronicle_total_events` | Regular | Total number of scheduled events |
| `sensor.cronicle_enabled_events` | Regular | Number of enabled scheduled events |
| `sensor.cronicle_disabled_events` | Regular | Number of disabled scheduled events |
| `sensor.cronicle_last_job` | Regular | Title of the most recent completed job |
| `sensor.cronicle_last_job_code` | Regular | Exit code of the most recent completed job |
| `sensor.cronicle_last_job_duration` | Regular | Runtime of the most recent completed job |
| `sensor.cronicle_last_job_finished` | Regular | Timestamp when the most recent job finished |
| `sensor.cronicle_recent_jobs` | Regular | Number of recent jobs returned by Cronicle |
| `sensor.cronicle_failed_recent_jobs` | Regular | Number of failed jobs in the recent job list |
| `sensor.cronicle_success_rate` | Regular | Success percentage based on the recent job list |
| `sensor.cronicle_api_status` | Diagnostic | Current integration API status |
| `sensor.cronicle_last_update` | Diagnostic | Timestamp of the latest update attempt |
| `sensor.cronicle_last_successful_update` | Diagnostic | Timestamp of the latest successful update |
| `sensor.cronicle_last_error` | Diagnostic | Last API or update error |
| `sensor.cronicle_api_response_time` | Diagnostic | Latest API response time in milliseconds |
| `sensor.cronicle_api_failures` | Diagnostic | Total counted API failures since integration load |
| `sensor.cronicle_history_total` | Diagnostic | Total number of available history rows reported by Cronicle |
| `sensor.cronicle_recent_jobs_limit` | Diagnostic | Configured recent jobs limit |

### Binary Sensors

| Entity | Category | Description |
|---|---|---|
| `binary_sensor.cronicle_scheduler` | Regular | Whether the Cronicle scheduler is enabled |
| `binary_sensor.cronicle_last_job_failed` | Regular | Whether the most recent completed job failed |
| `binary_sensor.cronicle_active_jobs_running` | Regular | Whether one or more jobs are currently running |
| `binary_sensor.cronicle_api_connected` | Diagnostic | Whether the integration currently has no API error |
| `binary_sensor.cronicle_problem` | Diagnostic | Whether the integration has an API error or the latest job failed |

### Buttons

| Entity | Category | Description |
|---|---|---|
| `button.cronicle_refresh` | Diagnostic | Requests an immediate refresh |
| `button.cronicle_enable_scheduler` | Configuration | Enables the Cronicle scheduler |
| `button.cronicle_disable_scheduler` | Configuration | Disables the Cronicle scheduler |

## Services

### `cronicle.run_event`

Runs a Cronicle event immediately by event ID or exact title.

```yaml
service: cronicle.run_event
data:
  id: "3c182051"
```

```yaml
service: cronicle.run_event
data:
  title: "Backup Logs"
```

### `cronicle.abort_job`

Aborts a running job by job ID.

```yaml
service: cronicle.abort_job
data:
  id: "jiinxhh5203"
```

### `cronicle.update_job`

Updates allowed properties on a running job.

```yaml
service: cronicle.update_job
data:
  id: "jiinxhh5203"
  timeout: 300
  retries: 1
```

Supported service fields:

- `timeout`
- `retries`
- `retry_delay`
- `chain`
- `chain_error`
- `notify_success`
- `notify_fail`
- `web_hook`
- `cpu_limit`
- `cpu_sustain`
- `memory_limit`
- `memory_sustain`
- `log_max_size`

### `cronicle.enable_scheduler`

Enables the Cronicle scheduler.

```yaml
service: cronicle.enable_scheduler
```

### `cronicle.disable_scheduler`

Disables the Cronicle scheduler.

```yaml
service: cronicle.disable_scheduler
```

### `cronicle.refresh`

Requests an immediate refresh from Cronicle.

```yaml
service: cronicle.refresh
```

If multiple Cronicle instances are configured, add `config_entry_id` to target one instance.

```yaml
service: cronicle.refresh
data:
  config_entry_id: "your_config_entry_id"
```

## Attributes

Some entities include additional job details as attributes.

### Active Jobs

`sensor.cronicle_active_jobs` includes a `jobs` attribute with details such as:

- Job ID
- Event ID
- Title
- Source
- Runtime
- Progress
- Hostname
- Target
- Category
- Plugin
- CPU usage
- Memory usage

### Recent Jobs

`sensor.cronicle_recent_jobs` includes a `jobs` attribute with details such as:

- Job ID
- Event ID
- Title
- Exit code
- Success state
- Runtime
- Hostname
- Category
- Plugin
- Source
- Description
- Start time
- End time
- Finished timestamp

### Last Job

`sensor.cronicle_last_job` includes attributes for the most recent completed job, including job ID, event, exit code, runtime, host, category, plugin, source, description, and timestamps.

## API Endpoints Used

The integration uses the following Cronicle API endpoints:

- `get_master_state`
- `get_active_jobs`
- `get_schedule`
- `get_history`
- `run_event`
- `abort_job`
- `update_job`
- `update_master_state`
- `get_job_status`

Connection testing uses `get_master_state`.

## API Key Privileges

Cronicle API key permissions depend on which features you use:

- Read-only monitoring requires access to state, active jobs, schedule, and history endpoints.
- Running events requires the `run_events` privilege.
- Aborting jobs requires the `abort_events` privilege.
- Updating running jobs requires the `edit_events` privilege.
- Enabling or disabling the scheduler requires the `state_update` privilege.

## Troubleshooting

### Cannot connect during setup

Check that:

- The host is reachable from Home Assistant
- The port is correct
- The API key is valid
- HTTPS is only enabled if Cronicle is actually served over HTTPS
- Firewalls or reverse proxies are not blocking Home Assistant

### Entities are unavailable

Check the Home Assistant logs for Cronicle API errors. The integration raises update failures when the API client cannot complete a refresh.

### Services fail

Check that the API key has the required Cronicle privilege for the action.

### No recent job data

Cronicle must have completed job history available. If no history rows are returned, last job sensors may be empty.

## Notes

- This integration uses local polling.
- No external Python requirements are needed.
- The integration stores API data in a Home Assistant `DataUpdateCoordinator`.
- Partial API failures are logged and exposed through diagnostic entities.

## License

This project is licensed under the MIT License.
