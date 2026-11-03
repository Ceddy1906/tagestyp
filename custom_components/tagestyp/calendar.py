"""Kalender mit den Feiertagen (für das Dashboard)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import TagestypConfigEntry, TagestypCoordinator
from .holidays_provider import HolidayLookup

MAX_RANGE_DAYS = 800


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TagestypConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([HolidayCalendar(entry.runtime_data, entry)])


def _events(lookup: HolidayLookup, start: date, end: date) -> list[CalendarEvent]:
    out: list[CalendarEvent] = []
    day = start
    while day <= end and (day - start).days <= MAX_RANGE_DAYS:
        if name := lookup.get(day):
            out.append(CalendarEvent(start=day, end=day + timedelta(days=1), summary=name))
        day += timedelta(days=1)
    return out


class HolidayCalendar(CalendarEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "holidays"

    def __init__(self, coordinator: TagestypCoordinator, entry: TagestypConfigEntry) -> None:
        self._lookup = coordinator.lookup
        self._attr_unique_id = f"{entry.entry_id}_holidays"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Tagestyp",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        nxt = self._lookup.next_holiday(dt_util.now().date())
        if nxt is None:
            return None
        day, name = nxt
        return CalendarEvent(start=day, end=day + timedelta(days=1), summary=name)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        last = end_date.date()
        if end_date.time() == datetime.min.time():  # Ende ist exklusiv
            last -= timedelta(days=1)
        return _events(self._lookup, start_date.date(), last)
