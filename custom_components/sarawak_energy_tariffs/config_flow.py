"""Config and options flow for Sarawak Energy Tariffs."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BILLING_DAY,
    CONF_MINIMUM_CHARGE,
    CONF_MODE,
    CONF_SOURCE,
    CONF_TIERS,
    CURRENCY,
    DEFAULT_BILLING_DAY,
    DEFAULT_NAME,
    DOMAIN,
)
from .tariff import (
    DEFAULT_MINIMUM_CHARGE,
    DEFAULT_TIERS,
    MODE_BLOCK,
    MODE_FLAT,
    TariffError,
    parse_tiers,
)

DEFAULTS: dict[str, Any] = {
    CONF_NAME: DEFAULT_NAME,
    CONF_BILLING_DAY: DEFAULT_BILLING_DAY,
    CONF_MODE: MODE_FLAT,
    CONF_TIERS: DEFAULT_TIERS,
    CONF_MINIMUM_CHARGE: DEFAULT_MINIMUM_CHARGE,
}


def _schema(values: dict[str, Any], include_name: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_name:
        fields[vol.Required(CONF_NAME, default=values[CONF_NAME])] = selector.TextSelector()
    fields.update(
        {
            vol.Required(
                CONF_SOURCE, default=values.get(CONF_SOURCE, vol.UNDEFINED)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            vol.Required(
                CONF_BILLING_DAY, default=values[CONF_BILLING_DAY]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=28, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(CONF_MODE, default=values[CONF_MODE]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[MODE_FLAT, MODE_BLOCK],
                    translation_key="mode",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_TIERS, default=values[CONF_TIERS]): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            vol.Required(
                CONF_MINIMUM_CHARGE, default=values[CONF_MINIMUM_CHARGE]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    step=0.01,
                    unit_of_measurement=CURRENCY,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )
    return vol.Schema(fields)


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    try:
        parse_tiers(user_input[CONF_TIERS])
    except TariffError:
        return {CONF_TIERS: "invalid_tiers"}
    return {}


def _normalise(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        **user_input,
        CONF_BILLING_DAY: int(user_input[CONF_BILLING_DAY]),
        CONF_MINIMUM_CHARGE: float(user_input[CONF_MINIMUM_CHARGE]),
    }


class SarawakEnergyTariffsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_SOURCE])
                self._abort_if_unique_id_configured()
                data = _normalise(user_input)
                title = data.pop(CONF_NAME)
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema({**DEFAULTS, **(user_input or {})}, include_name=True),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SarawakEnergyTariffsOptionsFlow()


class SarawakEnergyTariffsOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data=_normalise(user_input))

        current = {
            **DEFAULTS,
            **self.config_entry.data,
            **self.config_entry.options,
            **(user_input or {}),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current, include_name=False),
            errors=errors,
        )
