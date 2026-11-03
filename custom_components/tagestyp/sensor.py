"""Sensoren: Tagestyp, nächster Feiertag, Personenstatus."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import SUBENTRY_PERSON
from .coordinator import TagestypConfigEntry
from .daytype import DayKind
from .entity import PersonEntity, TagestypEntity
from .holidays_provider import format_date
from .rules import PersonState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TagestypConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [DayTypeSensor(coordinator, entry), NextHolidaySensor(coordinator, entry)]
    )
    for sub in entry.subentries.values():
        if sub.subentry_type == SUBENTRY_PERSON:
            async_add_entities(
                [
                    PersonStatusSensor(coordinator, entry, sub, "status"),
                    PersonStatusTomorrowSensor(coordinator, entry, sub, "status_tomorrow"),
                ],
                config_subentry_id=sub.subentry_id,
            )


class DayTypeSensor(TagestypEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [k.value for k in DayKind]
    _attr_name = None  # Entity-ID: sensor.tagestyp

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "tagestyp")

    @property
    def native_value(self) -> str:
        return self.data.today.info.kind.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        info = self.data.today.info
        return {
            "holiday_name": info.holiday_name,
            "holiday_on_weekend": info.holiday_on_weekend,
            "is_bridge_day": info.is_bridge_day,
            "tomorrow": self.data.tomorrow.info.kind.value,
            "tomorrow_holiday_name": self.data.tomorrow.info.holiday_name,
            "day_after_tomorrow": self.data.day_after.info.kind.value,
            "day_after_tomorrow_holiday_name": self.data.day_after.info.holiday_name,
        }


class NextHolidaySensor(TagestypEntity, SensorEntity):
    """Zustand als Text TT.MM.JJJJ; das echte Datum steht im Attribut `date` (ISO)."""

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "next_holiday")

    @property
    def native_value(self) -> str | None:
        nxt = self.data.next_holiday
        return format_date(nxt[0]) if nxt else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        nxt = self.data.next_holiday
        if not nxt:
            return {}
        return {
            "holiday_name": nxt[1],
            "date": nxt[0].isoformat(),
            "days_until": (nxt[0] - dt_util.now().date()).days,
        }


class PersonStatusSensor(PersonEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [s.value for s in PersonState]

    @property
    def native_value(self) -> str | None:
        status = self.status
        return status.state.value if status else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self.status
        person = self.coordinator.persons.get(self._sub_id)
        configured = (
            [f"{r.type.value}: {r.search} ({r.mode.value})" for r in person.rules]
            if person
            else []
        )
        if status is None:
            return {"calendar": person.calendar if person else None, "configured_rules": configured}
        rule = status.matched_rule
        event = status.matched_event
        attrs = {
            "calendar": person.calendar if person else None,
            "configured_rules": configured,
            "source": status.source,
            "matched_rule": f"{rule.type.value}: {rule.search}" if rule else None,
            "matched_event": event.summary if event else None,
        }
        if self._snapshot() is self.coordinator.data.today:
            tomorrow = self._status(self.coordinator.data.tomorrow)
            after = self._status(self.coordinator.data.day_after)
            attrs["tomorrow"] = tomorrow.state.value if tomorrow else None
            attrs["day_after_tomorrow"] = after.state.value if after else None
        else:
            attrs["date"] = (dt_util.now().date() + timedelta(days=1)).isoformat()
        return attrs


class PersonStatusTomorrowSensor(PersonStatusSensor):
    """Status der Person für morgen (gleiche Regeln wie heute)."""

    def _snapshot(self):
        return self.coordinator.data.tomorrow
