"""Data coordinator for Ubian."""

from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UbianApiClient, UbianApiError, UbianCard
from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class UbianDataUpdateCoordinator(DataUpdateCoordinator[list[UbianCard]]):
    """Fetch Ubian data on a configured interval."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )

        self._client = UbianApiClient(
            async_get_clientsession(hass),
            entry.data[CONF_EMAIL],
            entry.data[CONF_PASSWORD],
        )

    async def _async_update_data(self) -> list[UbianCard]:
        """Fetch cards from Ubian."""
        try:
            return await self._client.async_get_cards()
        except (ClientError, UbianApiError) as err:
            raise UpdateFailed(str(err)) from err
