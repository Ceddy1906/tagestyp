"""Binärsensoren: frei heute, Brückentag, Person arbeitet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SUBENTRY_PERSON
from .coordinator import TagestypConfigEntry
from .daytype import DayKind
from .entity import PersonEntity, TagestypEntity
from .holidays_provider import format_date


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TagestypConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[TagestypEntity] = [
        FreeTodaySensor(coordinator, entry),
        BridgeDaySensor(coordinator, entry),
    ]
    if coordinator.school is not None:
        entities.append(SchoolHolidaySensor(coordinator, entry))
    async_add_entities(entities)
    for sub in entry.subentries.values():
        if sub.subentry_type == SUBENTRY_PERSON:
            async_add_entities(
                [PersonWorkingSensor(coordinator, entry, sub, "working")],
                config_subentry_id=sub.subentry_id,
            )


class FreeTodaySensor(TagestypEntity, BinarySensorEntity):
    """An, wenn heute Wochenende oder Feiertag ist."""

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "free_today")

    @property
    def is_on(self) -> bool:
        return self.data.today.info.kind is not DayKind.WERKTAG


class BridgeDaySensor(TagestypEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "bridge_day")

    @property
    def is_on(self) -> bool:
        return self.data.today.info.is_bridge_day


class SchoolHolidaySensor(TagestypEntity, BinarySensorEntity):
    """An, wenn heute Schulferien sind (OpenHolidays, mit Cache)."""

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "school_holiday")

    @property
    def available(self) -> bool:
        school = self.coordinator.school
        return super().available and school is not None and school.has_data

    @property
    def is_on(self) -> bool | None:
        school = self.coordinator.school
        return school.current(dt_util.now().date()) is not None if school else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        school = self.coordinator.school
        if school is None:
            return {}
        today = dt_util.now().date()
        current = school.current(today)
        nxt = school.upcoming(today)
        return {
            "name": current.name if current else None,
            "start": format_date(current.start) if current else None,
            "end": format_date(current.end) if current else None,
            "next_name": nxt.name if nxt else None,
            "next_start": format_date(nxt.start) if nxt else None,
            "next_end": format_date(nxt.end) if nxt else None,
            "days_until_next": (nxt.start - today).days if nxt else None,
            "data_stale": school.stale,
            "last_updated": dt_util.as_local(school.last_updated).strftime("%d.%m.%Y %H:%M")
            if school.last_updated
            else None,
        }


class PersonWorkingSensor(PersonEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool | None:
        status = self.status
        return status.is_working if status else None
