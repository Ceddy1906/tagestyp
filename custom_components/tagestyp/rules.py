"""Personenstatus aus Kalenderterminen und Regeln (reine Logik, ohne HA-Importe).

Priorität: urlaub > frei > arbeit.

Kein Treffer:
- Gibt es mindestens eine `arbeit`-Regel (Dienstplan im Kalender), bedeutet kein
  passender Termin "frei" (source "kein_termin").
- Gibt es keine `arbeit`-Regel, gilt der Tagestyp (Werktag = arbeit, sonst frei).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from enum import StrEnum

from .daytype import DayInfo, DayKind


class RuleType(StrEnum):
    ARBEIT = "arbeit"
    FREI = "frei"
    URLAUB = "urlaub"


class MatchMode(StrEnum):
    CONTAINS = "contains"
    EXACT = "exact"


class PersonState(StrEnum):
    ARBEIT = "arbeit"
    FREI = "frei"
    URLAUB = "urlaub"


# Auswertungsreihenfolge
PRIORITY: tuple[RuleType, ...] = (RuleType.URLAUB, RuleType.FREI, RuleType.ARBEIT)

_STATE_FOR_RULE = {
    RuleType.URLAUB: PersonState.URLAUB,
    RuleType.FREI: PersonState.FREI,
    RuleType.ARBEIT: PersonState.ARBEIT,
}


@dataclass(frozen=True)
class Rule:
    search: str
    type: RuleType
    mode: MatchMode = MatchMode.CONTAINS

    def matches(self, summary: str) -> bool:
        needle = self.search.strip().casefold()
        if not needle:
            return False
        hay = (summary or "").strip().casefold()
        if self.mode is MatchMode.EXACT:
            return hay == needle
        return needle in hay


@dataclass(frozen=True)
class CalendarEvent:
    """Kalendertermin. Ganztägig: date-Objekte, Ende exklusiv (HA-Konvention)."""

    summary: str
    start: date | datetime
    end: date | datetime | None = None


@dataclass(frozen=True)
class PersonStatus:
    state: PersonState
    source: str  # "regel" oder "tagestyp"
    matched_rule: Rule | None = None
    matched_event: CalendarEvent | None = None

    @property
    def is_working(self) -> bool:
        return self.state is PersonState.ARBEIT


def _as_aware(value: datetime, tz: tzinfo) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=tz)


def _bounds(event: CalendarEvent, tz: tzinfo) -> tuple[datetime, datetime]:
    """Start/Ende (exklusiv) des Termins als tz-aware datetimes."""
    start, end = event.start, event.end
    if isinstance(start, datetime):
        start_dt = _as_aware(start, tz)
        if isinstance(end, datetime):
            end_dt = _as_aware(end, tz)
        elif isinstance(end, date):
            end_dt = datetime.combine(end, time.min, tzinfo=tz)
        else:
            end_dt = start_dt
        return start_dt, end_dt
    start_dt = datetime.combine(start, time.min, tzinfo=tz)
    if isinstance(end, datetime):
        end_dt = _as_aware(end, tz)
    elif isinstance(end, date) and end > start:
        end_dt = datetime.combine(end, time.min, tzinfo=tz)
    else:
        end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt


def event_covers_day(event: CalendarEvent, day: date, tz: tzinfo) -> bool:
    day_start = datetime.combine(day, time.min, tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    start, end = _bounds(event, tz)
    if end <= start:  # Termin ohne Dauer: zählt, wenn er am Tag beginnt
        return day_start <= start < day_end
    return start < day_end and end > day_start


def evaluate(
    day: date,
    day_info: DayInfo,
    events: list[CalendarEvent],
    rules: list[Rule],
    tz: tzinfo,
) -> PersonStatus:
    """Status einer Person für einen Tag."""
    todays = [e for e in events if event_covers_day(e, day, tz)]
    for rule_type in PRIORITY:
        for rule in (r for r in rules if r.type is rule_type):
            for event in todays:
                if rule.matches(event.summary):
                    return PersonStatus(
                        state=_STATE_FOR_RULE[rule_type],
                        source="regel",
                        matched_rule=rule,
                        matched_event=event,
                    )
    if any(r.type is RuleType.ARBEIT for r in rules):
        return PersonStatus(state=PersonState.FREI, source="kein_termin")
    state = (
        PersonState.ARBEIT if day_info.kind is DayKind.WERKTAG else PersonState.FREI
    )
    return PersonStatus(state=state, source="tagestyp")
