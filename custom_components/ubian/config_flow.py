"""Config flow for Ubian."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN


class UbianConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Ubian config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_EMAIL],
                data={
                    CONF_EMAIL: user_input[CONF_EMAIL],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                },
                options={
                    CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL]),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UbianOptionsFlow:
        """Create the options flow."""
        return UbianOptionsFlow(config_entry)


class UbianOptionsFlow(config_entries.OptionsFlow):
    """Handle Ubian options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Ubian options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL])},
            )

        current_interval = self._config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=current_interval
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    ),
                }
            ),
        )
