"""Schulferien von OpenHolidays mit lokalem Cache (Offline-Fallback).

Das Datenformat stammt aus der Dokumentation Dritter (Clients der API), nicht aus
einem Live-Test: SchoolHolidays liefert eine Liste mit startDate/endDate (inklusive),
name[{language,text}], nationwide, subdivisions[{code,shortName}].
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    OPENHOLIDAYS_URL,
    SCHOOL_HTTP_TIMEOUT,
    SCHOOL_REFRESH_HOURS,
    SCHOOL_STORE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SchoolHoliday:
    start: date
    end: date  # inklusive
    name: str

    def covers(self, day: date) -> bool:
        return self.start <= day <= self.end


def _pick_name(names: list[dict[str, Any]] | None, language: str) -> str:
    names = names or []
    wanted = language.lower()
    for item in names:
        if str(item.get("language", "")).lower() == wanted:
            return str(item.get("text", ""))
    for item in names:
        if str(item.get("language", "")).lower() == "en":
            return str(item.get("text", ""))
    return str(names[0].get("text", "")) if names else "Schulferien"


def _applies(item: dict[str, Any], country: str, subdivision: str | None) -> bool:
    """Bundesweit gilt immer; regional nur bei passender Unterteilung."""
    if item.get("nationwide"):
        return True
    if not subdivision:
        return False
    wanted = f"{country}-{subdivision}".lower()
    for sub in item.get("subdivisions") or []:
        code = str(sub.get("code", "")).lower()
        if code == wanted or code.endswith(f"-{subdivision.lower()}"):
            return True
    return False


def parse_school_holidays(
    payload: list[dict[str, Any]],
    country: str,
    subdivision: str | None,
    language: str,
) -> list[SchoolHoliday]:
    """Wandelt die API-Antwort in eine sortierte Liste um; unbrauchbare Einträge werden übersprungen."""
    result: list[SchoolHoliday] = []
    for item in payload:
        if item.get("type") not in (None, "School"):
            continue
        if not _applies(item, country, subdivision):
            continue
        try:
            start = date.fromisoformat(str(item["startDate"]))
            end = date.fromisoformat(str(item["endDate"]))
        except (KeyError, ValueError):
            continue
        if end < start:
            continue
        result.append(SchoolHoliday(start, end, _pick_name(item.get("name"), language)))
    result.sort(key=lambda h: (h.start, h.end))
    return result


class SchoolHolidays:
    """Hält die Schulferien, aktualisiert täglich und fällt bei Ausfall auf den Cache zurück."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        country: str,
        subdivision: str | None,
        language: str,
    ) -> None:
        self.hass = hass
        self.country = country
        self.subdivision = subdivision
        self.language = language
        self.holidays: list[SchoolHoliday] = []
        self.last_updated: datetime | None = None
        self.stale = False
        self.has_data = False
        self._store: Store[dict[str, Any]] = Store(
            hass, SCHOOL_STORE_VERSION, f"{DOMAIN}.school_{entry_id}"
        )

    # --- Cache ------------------------------------------------------------
    def _matches(self, data: dict[str, Any]) -> bool:
        return (
            data.get("country") == self.country
            and data.get("subdivision") == self.subdivision
            and data.get("language") == self.language
        )

    async def async_load_cache(self) -> None:
        data = await self._store.async_load()
        if not data or not self._matches(data):
            return
        try:
            self.holidays = [
                SchoolHoliday(date.fromisoformat(i["start"]), date.fromisoformat(i["end"]), i["name"])
                for i in data["items"]
            ]
            self.last_updated = datetime.fromisoformat(data["fetched"])
        except (KeyError, ValueError):
            self.holidays = []
            return
        self.has_data = True
        self.stale = True  # bis zur ersten erfolgreichen Aktualisierung

    async def _async_save_cache(self) -> None:
        await self._store.async_save(
            {
                "country": self.country,
                "subdivision": self.subdivision,
                "language": self.language,
                "fetched": (self.last_updated or datetime.now(timezone.utc)).isoformat(),
                "items": [
                    {"start": h.start.isoformat(), "end": h.end.isoformat(), "name": h.name}
                    for h in self.holidays
                ],
            }
        )

    # --- Abruf ------------------------------------------------------------
    async def _async_fetch_raw(self, valid_from: date, valid_to: date) -> list[dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        params = {
            "countryIsoCode": self.country,
            "languageIsoCode": self.language.upper(),
            "validFrom": valid_from.isoformat(),
            "validTo": valid_to.isoformat(),
        }
        async with session.get(
            OPENHOLIDAYS_URL,
            params=params,
            headers={"accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=SCHOOL_HTTP_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
        if not isinstance(data, list):
            raise ValueError("Unerwartete Antwort der OpenHolidays-API")
        return data

    async def async_refresh(self, today: date | None = None) -> bool:
        """Holt neue Daten. Bei Fehler bleiben Cache/alte Daten erhalten (stale)."""
        today = today or datetime.now().date()
        try:
            raw = await self._async_fetch_raw(
                date(today.year, 1, 1), date(today.year + 1, 12, 31)
            )
            parsed = parse_school_holidays(raw, self.country, self.subdivision, self.language)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            _LOGGER.warning("Schulferien konnten nicht geladen werden (nutze Cache): %s", err)
            self.stale = True
            return False
        self.holidays = parsed
        self.last_updated = datetime.now(timezone.utc)
        self.stale = False
        self.has_data = True
        await self._async_save_cache()
        return True

    @staticmethod
    def refresh_interval() -> timedelta:
        return timedelta(hours=SCHOOL_REFRESH_HOURS)

    # --- Abfragen -----------------------------------------------------------
    def current(self, day: date) -> SchoolHoliday | None:
        return next((h for h in self.holidays if h.covers(day)), None)

    def upcoming(self, day: date) -> SchoolHoliday | None:
        return next((h for h in self.holidays if h.start > day), None)
