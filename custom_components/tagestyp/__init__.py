"""Tagestyp: Werktag / Feiertag / Wochenende und kalenderbasierter Arbeitstag pro Person."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SUBENTRY_PERSON
from .coordinator import TagestypConfigEntry, TagestypCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]
SERVICE_CHECK_DATE = "check_date"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def _check_date(call: ServiceCall) -> ServiceResponse:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError("Tagestyp ist nicht eingerichtet.")
        return await entries[0].runtime_data.async_check_date(call.data["date"])

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_DATE,
        _check_date,
        schema=vol.Schema({vol.Required("date"): cv.date}),
        supports_response=SupportsResponse.ONLY,
    )
    return True


def _update_person_issues(hass: HomeAssistant, coordinator: TagestypCoordinator, entry: TagestypConfigEntry) -> None:
    """Reparatur-Hinweis, wenn eine zugeordnete Person nicht mehr existiert."""
    for sub in entry.subentries.values():
        if sub.subentry_type != SUBENTRY_PERSON:
            continue
        issue_id = f"person_missing_{sub.subentry_id}"
        if coordinator.person_entity_id(sub) is None:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="person_missing",
                translation_placeholders={"person": sub.title},
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)


async def async_setup_entry(hass: HomeAssistant, entry: TagestypConfigEntry) -> bool:
    """Änderungen an Optionen/Personen laden die Integration neu."""
    coordinator = await TagestypCoordinator.async_create(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    _update_person_issues(hass, coordinator, entry)
    coordinator.async_start_triggers()
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TagestypConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_change(hass: HomeAssistant, entry: TagestypConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
