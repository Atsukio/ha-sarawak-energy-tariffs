"""Sensors exposing billing-period usage, rate, tier and estimated bill."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SarawakEnergyConfigEntry
from .const import CURRENCY, DOMAIN
from .tracker import UsageTracker


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SarawakEnergyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    tracker = entry.runtime_data
    async_add_entities(
        cls(tracker, entry)
        for cls in (UsageSensor, BillSensor, RateSensor, TierSensor)
    )


class _TrackerSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, tracker: UsageTracker, entry: SarawakEnergyConfigEntry) -> None:
        self._tracker = tracker
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_translation_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            model="Tariff D - Domestic",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._tracker.async_add_listener(self.async_write_ha_state))


class UsageSensor(_TrackerSensor):
    _attr_translation_key = "period_usage"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return round(self._tracker.usage, 3)

    @property
    def last_reset(self) -> datetime:
        return self._tracker.period_start


class BillSensor(_TrackerSensor):
    _attr_translation_key = "estimated_bill"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY
    _attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        return round(self._tracker.bill, 2)

    @property
    def last_reset(self) -> datetime:
        return self._tracker.period_start

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tracker = self._tracker
        return {
            "energy_charge": round(tracker.energy_charge, 2),
            "minimum_charge": tracker.minimum_charge,
            "minimum_charge_applied": tracker.energy_charge < tracker.minimum_charge,
            "billing_mode": tracker.mode,
            "period_start": tracker.period_start.isoformat(),
        }


class RateSensor(_TrackerSensor):
    _attr_translation_key = "current_rate"
    _attr_native_unit_of_measurement = f"{CURRENCY}/{UnitOfEnergy.KILO_WATT_HOUR}"
    _attr_suggested_display_precision = 3

    @property
    def native_value(self) -> float:
        return self._tracker.tier.rate

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tier = self._tracker.tier
        to_next = None if math.isinf(tier.upper) else round(tier.upper - self._tracker.usage, 3)
        return {"tier": tier.label, "kwh_to_next_tier": to_next}


class TierSensor(_TrackerSensor):
    _attr_translation_key = "current_tier"

    @property
    def native_value(self) -> str:
        return self._tracker.tier.label
