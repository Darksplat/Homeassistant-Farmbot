"""Constants for the FarmBot integration."""

from typing import Final

DOMAIN: Final = "farmbot"
PLATFORMS: Final = ["binary_sensor", "sensor", "switch", "select", "button"]

CONF_TOKEN: Final = "token"
CONF_DEVICE_ID: Final = "device_id"
CONF_MQTT_HOST: Final = "mqtt_host"

API_BASE_URL: Final = "https://my.farm.bot/api"
MQTT_PORT: Final = 8883
TOKEN_REFRESH_WINDOW: Final = 24 * 60 * 60
STATUS_FRESHNESS_SECONDS: Final = 120

TOPIC_STATUS: Final = "bot/device_{device_id}/status"
TOPIC_COMMAND: Final = "bot/device_{device_id}/from_clients"
TOPIC_LOGS: Final = "bot/device_{device_id}/logs"

SIGNAL_STATE: Final = "farmbot_state_update"
