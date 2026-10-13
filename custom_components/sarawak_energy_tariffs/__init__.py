"""Sarawak Energy Tariffs: tiered electricity cost sensors."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_VERSION
from .tracker import UsageTracker, storage_key

PLATFORMS = [Platform.SENSOR]

type SarawakEnergyConfigEntry = ConfigEntry[UsageTracker]


async def async_setup_entry(hass: HomeAssistant, entry: SarawakEnergyConfigEntry) -> bool:
    tracker = UsageTracker(hass, entry)
    await tracker.async_load()
    entry.runtime_data = tracker

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    tracker.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SarawakEnergyConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await Store(hass, STORAGE_VERSION, storage_key(entry.entry_id)).async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
