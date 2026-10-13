"""Tracks billing-period consumption from a cumulative energy sensor."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BILLING_DAY,
    CONF_MINIMUM_CHARGE,
    CONF_MODE,
    CONF_SOURCE,
    CONF_TIERS,
    DOMAIN,
    STORAGE_VERSION,
)
from .tariff import Tier, bill_amount, energy_charge, find_tier, parse_tiers, period_start

_UNIT_TO_KWH = {
    UnitOfEnergy.WATT_HOUR: 0.001,
    UnitOfEnergy.KILO_WATT_HOUR: 1.0,
    UnitOfEnergy.MEGA_WATT_HOUR: 1000.0,
}
_SAVE_DELAY = 30


def storage_key(entry_id: str) -> str:
    return f"{DOMAIN}.{entry_id}"


class UsageTracker:
    """Accumulates kWh used in the current billing period and prices it."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        config = {**entry.data, **entry.options}
        self.source: str = config[CONF_SOURCE]
        self.billing_day = int(config[CONF_BILLING_DAY])
        self.mode: str = config[CONF_MODE]
        self.tiers: list[Tier] = parse_tiers(config[CONF_TIERS])
        self.minimum_charge = float(config[CONF_MINIMUM_CHARGE])

        self.usage = 0.0
        self.period_start: datetime = period_start(dt_util.now(), self.billing_day)
        self._last_reading: float | None = None
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, storage_key(entry.entry_id)
        )
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[Callable[[], None]] = []

    @property
    def tier(self) -> Tier:
        return find_tier(self.tiers, self.usage)

    @property
    def energy_charge(self) -> float:
        return energy_charge(self.tiers, self.usage, self.mode)

    @property
    def bill(self) -> float:
        return bill_amount(self.tiers, self.usage, self.mode, self.minimum_charge)

    async def async_load(self) -> None:
        if data := await self._store.async_load():
            if stored_start := dt_util.parse_datetime(data["period_start"]):
                self.period_start = stored_start
                self.usage = float(data["usage"])
            # A reading from a different source sensor is not a valid baseline.
            if data.get("source") == self.source:
                self._last_reading = data.get("last_reading")
        self._check_rollover()

    @callback
    def async_start(self) -> None:
        self._unsubs.append(
            async_track_state_change_event(
                self.hass, [self.source], self._handle_source_event
            )
        )
        self._unsubs.append(
            async_track_time_change(
                self.hass, self._handle_midnight, hour=0, minute=0, second=1
            )
        )
        self._process_state(self.hass.states.get(self.source))

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._store.async_save(self._data())

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)
        return lambda: self._listeners.remove(update)

    @callback
    def _handle_source_event(self, event: Event[EventStateChangedData]) -> None:
        self._process_state(event.data["new_state"])

    @callback
    def _handle_midnight(self, _now: datetime) -> None:
        if self._check_rollover():
            self._changed()

    @callback
    def _process_state(self, state: State | None) -> None:
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        factor = _UNIT_TO_KWH.get(state.attributes.get(ATTR_UNIT_OF_MEASUREMENT), 1.0)
        try:
            reading = float(state.state) * factor
        except ValueError:
            return

        self._check_rollover()
        if self._last_reading is not None:
            delta = reading - self._last_reading
            if delta < 0:
                # The source meter reset (e.g. utility_meter cycle or new device).
                delta = reading
            self.usage += delta
        self._last_reading = reading
        self._changed()

    def _check_rollover(self) -> bool:
        current = period_start(dt_util.now(), self.billing_day)
        if current <= self.period_start:
            return False
        self.period_start = current
        self.usage = 0.0
        return True

    @callback
    def _changed(self) -> None:
        self._store.async_delay_save(self._data, _SAVE_DELAY)
        for update in list(self._listeners):
            update()

    def _data(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "period_start": self.period_start.isoformat(),
            "usage": self.usage,
            "last_reading": self._last_reading,
        }
