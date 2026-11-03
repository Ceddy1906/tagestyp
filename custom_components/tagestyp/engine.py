"""Berechnung der Tages- und Personenstände (reine Logik, ohne HA-Importe)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, tzinfo
from typing import Any, Mapping

from .daytype import DayInfo, classify
from .holidays_provider import HolidayLookup
from .rules import CalendarEvent, MatchMode, PersonStatus, Rule, RuleType, evaluate


@dataclass(frozen=True)
class PersonConfig:
    key: str  # subentry_id
    title: str
    calendar: str | None
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class DaySnapshot:
    info: DayInfo
    # None = Kalender nicht lesbar -> Status unbekannt (Entität nicht verfügbar)
    persons: dict[str, PersonStatus | None] = field(default_factory=dict)


def rules_from_data(raw: list[Mapping[str, Any]]) -> tuple[Rule, ...]:
    return tuple(
        Rule(
            search=r["search"],
            type=RuleType(r["type"]),
            mode=MatchMode(r.get("mode", MatchMode.CONTAINS.value)),
        )
        for r in raw
    )


def compute_day(
    day: date,
    lookup: HolidayLookup,
    persons: list[PersonConfig],
    events_by_key: Mapping[str, list[CalendarEvent] | None],
    tz: tzinfo,
) -> DaySnapshot:
    info = classify(day, lookup)
    statuses: dict[str, PersonStatus | None] = {}
    for person in persons:
        events = events_by_key.get(person.key)
        # Ohne Kalender sind Regeln wirkungslos -> reiner Tagestyp
        rules = [] if person.calendar is None else list(person.rules)
        if person.calendar is None:
            events = []
        statuses[person.key] = (
            None if events is None else evaluate(day, info, events, rules, tz)
        )
    return DaySnapshot(info=info, persons=statuses)
