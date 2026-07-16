"""Parse FarmBot MQTT log messages into diagnostic state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_ERROR_TYPES = {"error", "fatal"}
_WARNING_TYPES = {"warn", "warning"}
_FARMDUINO_MARKERS = (
    "farmduino",
    "firmware",
    "movement timeout",
    "emergency lock",
    "stall",
    "missed step",
    "calibration",
    "encoder",
    "end stop",
    "end-stop",
    "axis",
    "r03",
    "r05",
    "r06",
    "r71",
    "r72",
    "r73",
    "r81",
    "r82",
    "r83",
    "r84",
    "r85",
    "r87",
    "r89",
)


@dataclass(frozen=True, slots=True)
class FarmbotLogEntry:
    """Normalized FarmBot MQTT log entry."""

    message: str
    severity: str
    created_at: datetime
    is_farmduino: bool
    raw: dict[str, Any]


def parse_log_payload(payload: Any) -> FarmbotLogEntry | None:
    """Normalize a FarmBot MQTT log payload.

    FarmBot log envelopes have changed over time, so this accepts both a
    top-level log object and an object wrapped in ``body``.
    """
    if not isinstance(payload, dict):
        return None

    body = payload.get("body", payload)
    if not isinstance(body, dict):
        return None

    message_value = body.get("message", body.get("text", body.get("msg")))
    if message_value is None:
        return None

    message = str(message_value).strip()
    if not message:
        return None

    severity_value = body.get("type", body.get("severity", body.get("level", "info")))
    severity = str(severity_value).strip().lower() or "info"
    if severity in _ERROR_TYPES:
        severity = "error"
    elif severity in _WARNING_TYPES:
        severity = "warning"
    else:
        severity = "info"

    created_at = datetime.now(timezone.utc)
    timestamp = body.get("created_at", body.get("createdAt", body.get("time")))
    if timestamp:
        try:
            created_at = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass

    lower_message = message.lower()
    channels = body.get("channels", [])
    if isinstance(channels, str):
        channels = [channels]
    channel_text = " ".join(str(channel).lower() for channel in channels)
    is_farmduino = "firmware" in channel_text or any(
        marker in lower_message for marker in _FARMDUINO_MARKERS
    )

    return FarmbotLogEntry(
        message=message,
        severity=severity,
        created_at=created_at,
        is_farmduino=is_farmduino,
        raw=body,
    )
