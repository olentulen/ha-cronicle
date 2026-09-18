"""Constants for the Cronicle integration."""

DOMAIN = "cronicle"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_API_KEY = "api_key"
CONF_USE_SSL = "use_ssl"
CONF_POLL_INTERVAL = "poll_interval"
CONF_RECENT_JOBS_COUNT = "recent_jobs_count"

DEFAULT_PORT = 3012
DEFAULT_POLL_INTERVAL = 30
DEFAULT_RECENT_JOBS_COUNT = 5
MAX_RECENT_JOBS_COUNT = 25

SERVICE_RUN_EVENT = "run_event"
SERVICE_ABORT_JOB = "abort_job"
SERVICE_UPDATE_JOB = "update_job"
SERVICE_ENABLE_SCHEDULER = "enable_scheduler"
SERVICE_DISABLE_SCHEDULER = "disable_scheduler"
SERVICE_REFRESH = "refresh"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_ID = "id"
ATTR_TITLE = "title"
