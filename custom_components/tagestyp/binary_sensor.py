"""Binärsensoren: frei heute, Brückentag, Person arbeitet."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SUBENTRY_PERSON
from .coordinator import TagestypConfigEntry
from .daytype import DayKind
from .entity import PersonEntity, TagestypEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TagestypConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [FreeTodaySensor(coordinator, entry), BridgeDaySensor(coordinator, entry)]
    )
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


class PersonWorkingSensor(PersonEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool | None:
        status = self.status
        return status.is_working if status else None
