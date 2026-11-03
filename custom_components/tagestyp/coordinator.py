"""Coordinator: berechnet heute/morgen/übermorgen und liest Kalender."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CALENDAR,
    CONF_EXTRA_HOLIDAYS,
    CONF_LANGUAGE,
    CONF_RULES,
    CONF_SUBDIVISION,
    CONF_COUNTRY,
    DOMAIN,
    SUBENTRY_PERSON,
    UPDATE_INTERVAL_MINUTES,
)
from .engine import DaySnapshot, PersonConfig, compute_day, rules_from_data
from .holidays_provider import HolidayLookup, build_lookup, format_date
from .rules import CalendarEvent

_LOGGER = logging.getLogger(__name__)

type TagestypConfigEntry = ConfigEntry[TagestypCoordinator]


@dataclass(frozen=True)
class TagestypData:
    today: DaySnapshot
    tomorrow: DaySnapshot
    day_after: DaySnapshot
    next_holiday: tuple[date, str] | None


def _parse_when(value: Any) -> date | datetime | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value
    text = str(value)
    if len(text) == 10:
        return date.fromisoformat(text)
    return dt_util.parse_datetime(text)


class TagestypCoordinator(DataUpdateCoordinator[TagestypData]):
    """Eine Instanz je Config Entry."""

    config_entry: TagestypConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TagestypConfigEntry, lookup: HolidayLookup
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.lookup = lookup
        self.persons: dict[str, PersonConfig] = {}
        for sub in entry.subentries.values():
            if sub.subentry_type == SUBENTRY_PERSON:
                self.persons[sub.subentry_id] = PersonConfig(
                    key=sub.subentry_id,
                    title=sub.title,
                    calendar=sub.data.get(CONF_CALENDAR),
                    rules=rules_from_data(sub.data.get(CONF_RULES, [])),
                )

    # --- Aufbau -----------------------------------------------------------
    @classmethod
    async def async_create(
        cls, hass: HomeAssistant, entry: TagestypConfigEntry
    ) -> TagestypCoordinator:
        opts = entry.options
        lookup = await hass.async_add_executor_job(
            build_lookup,
            entry.data[CONF_COUNTRY],
            opts.get(CONF_SUBDIVISION),
            opts.get(CONF_LANGUAGE, "de"),
            opts.get(CONF_EXTRA_HOLIDAYS, []),
        )
        return cls(hass, entry, lookup)

    @callback
    def async_start_triggers(self) -> None:
        """Mitternacht und Kalenderänderungen lösen eine Neuberechnung aus."""
        entry = self.config_entry

        async def _refresh(*_: Any) -> None:
            await self.async_request_refresh()

        entry.async_on_unload(
            async_track_time_change(self.hass, _refresh, hour=0, minute=0, second=5)
        )
        calendars = [p.calendar for p in self.persons.values() if p.calendar]
        if calendars:
            entry.async_on_unload(
                async_track_state_change_event(self.hass, calendars, _refresh)
            )

    # --- Kalender ----------------------------------------------------------
    async def _async_fetch_events(
        self, entity_id: str, start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        response = await self.hass.services.async_call(
            "calendar",
            "get_events",
            {"entity_id": entity_id, "start_date_time": start, "end_date_time": end},
            blocking=True,
            return_response=True,
        )
        raw = (response or {}).get(entity_id, {}).get("events", [])
        events: list[CalendarEvent] = []
        for item in raw:
            begin = _parse_when(item.get("start"))
            if begin is None:
                continue
            events.append(
                CalendarEvent(
                    summary=item.get("summary") or "",
                    start=begin,
                    end=_parse_when(item.get("end")),
                )
            )
        return events

    async def _async_events_for_range(
        self, start_day: date, days: int
    ) -> dict[str, list[CalendarEvent] | None]:
        tz = dt_util.get_default_time_zone()
        start = datetime.combine(start_day, time.min, tzinfo=tz)
        end = start + timedelta(days=days)
        result: dict[str, list[CalendarEvent] | None] = {}
        for person in self.persons.values():
            if person.calendar is None:
                result[person.key] = []
                continue
            try:
                result[person.key] = await self._async_fetch_events(
                    person.calendar, start, end
                )
            except (HomeAssistantError, ValueError) as err:
                _LOGGER.warning(
                    "Kalender %s für %s nicht lesbar: %s", person.calendar, person.title, err
                )
                result[person.key] = None
        return result

    # --- Berechnung ----------------------------------------------------------
    async def _async_update_data(self) -> TagestypData:
        tz = dt_util.get_default_time_zone()
        today = dt_util.now().date()
        events = await self._async_events_for_range(today, 3)
        persons = list(self.persons.values())
        snaps = [
            compute_day(today + timedelta(days=i), self.lookup, persons, events, tz)
            for i in range(3)
        ]
        return TagestypData(
            today=snaps[0],
            tomorrow=snaps[1],
            day_after=snaps[2],
            next_holiday=self.lookup.next_holiday(today),
        )

    async def async_check_date(self, day: date) -> dict[str, Any]:
        """Für den Service `check_date`: Tagestyp und Personenstatus eines Tages."""
        tz = dt_util.get_default_time_zone()
        events = await self._async_events_for_range(day, 1)
        snap = compute_day(day, self.lookup, list(self.persons.values()), events, tz)
        return {
            "date": day.isoformat(),
            "date_formatted": format_date(day),
            "kind": snap.info.kind.value,
            "holiday_name": snap.info.holiday_name,
            "holiday_on_weekend": snap.info.holiday_on_weekend,
            "is_bridge_day": snap.info.is_bridge_day,
            "persons": {
                self.persons[key].title: (
                    None if status is None else {"state": status.state.value, "source": status.source}
                )
                for key, status in snap.persons.items()
            },
        }

    # --- Personen-Auflösung -------------------------------------------------
    def person_entity_id(self, sub: ConfigSubentry) -> str | None:
        """Aktuelle entity_id der Person (über die stabile Registry-ID)."""
        registry = er.async_get(self.hass)
        if sub.unique_id and (item := registry.entities.get_entry(sub.unique_id)):
            return item.entity_id
        entity_id = sub.data.get("person")
        return entity_id if entity_id and self.hass.states.get(entity_id) else None
