"""FarmBot REST API helpers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers import aiohttp_client

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class FarmbotApiError(RuntimeError):
    """Raised when a FarmBot API resource cannot be loaded."""


async def async_get_resource(manager, resource: str) -> list[dict[str, Any]]:
    """Fetch a list resource from the FarmBot API."""
    session = aiohttp_client.async_get_clientsession(manager.hass)
    try:
        async with session.get(
            f"{API_BASE_URL}/{resource}",
            headers={"Authorization": f"Bearer {manager.token}"},
            timeout=15,
        ) as response:
            if response.status in (401, 403):
                if manager._entry and not manager._auth_failed:  # noqa: SLF001
                    manager._auth_failed = True  # noqa: SLF001
                    manager._entry.async_start_reauth(manager.hass)  # noqa: SLF001
                raise FarmbotApiError("FarmBot authentication expired")
            if response.status != 200:
                body = await response.text()
                raise FarmbotApiError(
                    f"FarmBot API returned HTTP {response.status}: {body[:200]}"
                )
            data = await response.json()
    except FarmbotApiError:
        raise
    except Exception as err:
        raise FarmbotApiError(f"Unable to load FarmBot {resource}") from err

    if not isinstance(data, list):
        raise FarmbotApiError(f"FarmBot {resource} response was not a list")
    return [item for item in data if isinstance(item, dict)]
