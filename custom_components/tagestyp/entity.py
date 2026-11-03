"""Basisklassen der Entitäten."""

from __future__ import annotations

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TagestypConfigEntry, TagestypCoordinator, TagestypData
from .engine import DaySnapshot
from .rules import PersonStatus


class TagestypEntity(CoordinatorEntity[TagestypCoordinator]):
    """Globale Entität (ohne Personenbezug)."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: TagestypCoordinator, entry: TagestypConfigEntry, key: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Tagestyp",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def data(self) -> TagestypData:
        return self.coordinator.data


class PersonEntity(CoordinatorEntity[TagestypCoordinator]):
    """Entität einer Person (ein Gerät je Untereintrag)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TagestypCoordinator,
        entry: TagestypConfigEntry,
        sub: ConfigSubentry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._sub_id = sub.subentry_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{sub.subentry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, sub.subentry_id)},
            name=sub.title,
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, entry.entry_id),
        )

    def _status(self, snap: DaySnapshot) -> PersonStatus | None:
        return snap.persons.get(self._sub_id)

    @property
    def status(self) -> PersonStatus | None:
        return self._status(self.coordinator.data.today)

    @property
    def available(self) -> bool:
        return super().available and self.status is not None
