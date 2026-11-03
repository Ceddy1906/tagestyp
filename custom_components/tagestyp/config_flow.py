"""Config Flow: globale Einstellungen + Personen als Untereinträge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_CALENDAR,
    CONF_COUNTRY,
    CONF_EXTRA_HOLIDAYS,
    CONF_LANGUAGE,
    CONF_PERSON,
    CONF_RULE_MODE,
    CONF_RULE_SEARCH,
    CONF_RULE_TYPE,
    CONF_RULES,
    CONF_SCHOOL_HOLIDAYS,
    CONF_SUBDIVISION,
    DEFAULT_COUNTRY,
    DEFAULT_LANGUAGE,
    DOMAIN,
    SUBDIVISION_NAMES,
    SUBENTRY_PERSON,
    SUPPORTED_COUNTRIES,
)
from .holidays_provider import build_lookup, list_subdivisions
from .rules import MatchMode, RuleType

LANGUAGES = ("de", "en")


def _select(options: list[SelectOptionDict] | list[str], **kw: Any) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=options, mode=SelectSelectorMode.DROPDOWN, **kw
        )
    )


def _subdivision_options(country: str) -> list[SelectOptionDict]:
    names = SUBDIVISION_NAMES.get(country, {})
    return [
        SelectOptionDict(value=code, label=names.get(code, code))
        for code in list_subdivisions(country)
    ]


def _extra_to_text(items: list[str] | None) -> str:
    return "\n".join(items or [])


def _text_to_extra(text: str | None) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


async def _async_validate(
    hass: HomeAssistant,
    country: str,
    subdivision: str | None,
    language: str,
    extra: list[str],
) -> str | None:
    """Gibt einen Fehlerschlüssel zurück oder None (im Executor, `holidays` lädt Module)."""
    try:
        await hass.async_add_executor_job(
            build_lookup, country, subdivision, language, extra
        )
    except ValueError as err:
        return "invalid_subdivision" if "Unterteilung" in str(err) else "invalid_extra_holidays"
    return None


async def _async_details_schema(
    hass: HomeAssistant, country: str, defaults: dict[str, Any]
) -> vol.Schema:
    subdivisions = await hass.async_add_executor_job(_subdivision_options, country)
    return vol.Schema(
        {
            vol.Optional(
                CONF_SUBDIVISION,
                description={"suggested_value": defaults.get(CONF_SUBDIVISION)},
            ): _select(subdivisions),
            vol.Required(
                CONF_LANGUAGE, default=defaults.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
            ): _select(list(LANGUAGES)),
            vol.Optional(
                CONF_EXTRA_HOLIDAYS,
                description={
                    "suggested_value": _extra_to_text(defaults.get(CONF_EXTRA_HOLIDAYS))
                },
            ): TextSelector(TextSelectorConfig(multiline=True)),
            vol.Required(
                CONF_SCHOOL_HOLIDAYS,
                default=defaults.get(CONF_SCHOOL_HOLIDAYS, False),
            ): BooleanSelector(),
        }
    )


class TagestypConfigFlow(ConfigFlow, domain=DOMAIN):
    """Globale Einrichtung (ein Eintrag je HA)."""

    VERSION = 1

    def __init__(self) -> None:
        self._country = DEFAULT_COUNTRY

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return TagestypOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_PERSON: PersonSubentryFlow}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._country = user_input[CONF_COUNTRY]
            return await self.async_step_details()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): _select(
                        list(SUPPORTED_COUNTRIES), translation_key=CONF_COUNTRY
                    )
                }
            ),
        )

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}
        if user_input is not None:
            extra = _text_to_extra(user_input.get(CONF_EXTRA_HOLIDAYS))
            subdivision = user_input.get(CONF_SUBDIVISION)
            language = user_input[CONF_LANGUAGE]
            error = await _async_validate(
                self.hass, self._country, subdivision, language, extra
            )
            if error is None:
                return self.async_create_entry(
                    title=f"Tagestyp {self._country}"
                    + (f" {subdivision}" if subdivision else ""),
                    data={CONF_COUNTRY: self._country},
                    options={
                        CONF_SUBDIVISION: subdivision,
                        CONF_LANGUAGE: language,
                        CONF_EXTRA_HOLIDAYS: extra,
                        CONF_SCHOOL_HOLIDAYS: user_input[CONF_SCHOOL_HOLIDAYS],
                    },
                )
            errors["base"] = error
            defaults = user_input
        return self.async_show_form(
            step_id="details",
            data_schema=await _async_details_schema(self.hass, self._country, defaults),
            errors=errors,
        )


class TagestypOptionsFlow(OptionsFlow):
    """Globale Einstellungen ändern (das Land ist fest, wie bei Workday)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        country = self.config_entry.data[CONF_COUNTRY]
        defaults = dict(self.config_entry.options)
        if user_input is not None:
            extra = _text_to_extra(user_input.get(CONF_EXTRA_HOLIDAYS))
            subdivision = user_input.get(CONF_SUBDIVISION)
            language = user_input[CONF_LANGUAGE]
            error = await _async_validate(
                self.hass, country, subdivision, language, extra
            )
            if error is None:
                return self.async_create_entry(
                    data={
                        CONF_SUBDIVISION: subdivision,
                        CONF_LANGUAGE: language,
                        CONF_EXTRA_HOLIDAYS: extra,
                        CONF_SCHOOL_HOLIDAYS: user_input[CONF_SCHOOL_HOLIDAYS],
                    }
                )
            errors["base"] = error
            defaults = {**user_input, CONF_EXTRA_HOLIDAYS: extra}
        return self.async_show_form(
            step_id="init",
            data_schema=await _async_details_schema(self.hass, country, defaults),
            errors=errors,
        )


def _person_unique_id(hass, entity_id: str) -> str:
    """Interne Registry-ID (stabil bei Umbenennung); Fallback: entity_id."""
    entry = er.async_get(hass).async_get(entity_id)
    return entry.id if entry else entity_id


def _person_title(hass, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    return state.name if state else entity_id


def _rule_label(rule: dict[str, str]) -> str:
    return f"{rule[CONF_RULE_TYPE]}: {rule[CONF_RULE_SEARCH]} ({rule[CONF_RULE_MODE]})"


class PersonSubentryFlow(ConfigSubentryFlow):
    """Person hinzufügen/ändern: Kalender + Regeln."""

    def __init__(self) -> None:
        self._person: str | None = None
        self._calendar: str | None = None
        self._rules: list[dict[str, str]] = []

    # --- Hinzufügen -----------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            uid = _person_unique_id(self.hass, user_input[CONF_PERSON])
            taken = any(
                s.unique_id == uid for s in self._get_entry().subentries.values()
            )
            if taken:
                errors["base"] = "already_configured"
            else:
                self._person = user_input[CONF_PERSON]
                self._calendar = user_input.get(CONF_CALENDAR)
                return await self.async_step_menu()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PERSON): EntitySelector(
                        EntitySelectorConfig(domain="person")
                    ),
                    vol.Optional(CONF_CALENDAR): EntitySelector(
                        EntitySelectorConfig(domain="calendar")
                    ),
                }
            ),
            errors=errors,
        )

    # --- Ändern ---------------------------------------------------------
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        sub = self._get_reconfigure_subentry()
        self._person = sub.data[CONF_PERSON]
        self._calendar = sub.data.get(CONF_CALENDAR)
        self._rules = [dict(r) for r in sub.data.get(CONF_RULES, [])]
        return await self.async_step_menu()

    # --- gemeinsames Menü -----------------------------------------------
    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        options = ["edit_calendar", "add_rule"]
        if self._rules:
            options.append("remove_rule")
        options.append("finish")
        return self.async_show_menu(
            step_id="menu",
            menu_options=options,
            description_placeholders={
                "person": _person_title(self.hass, self._person or ""),
                "rules": "\n".join(f"- {_rule_label(r)}" for r in self._rules)
                or "(keine)",
            },
        )

    async def async_step_edit_calendar(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._calendar = user_input.get(CONF_CALENDAR)
            return await self.async_step_menu()
        return self.async_show_form(
            step_id="edit_calendar",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CALENDAR, description={"suggested_value": self._calendar}
                    ): EntitySelector(EntitySelectorConfig(domain="calendar"))
                }
            ),
        )

    async def async_step_add_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            search = user_input[CONF_RULE_SEARCH].strip()
            if not search:
                errors[CONF_RULE_SEARCH] = "empty_search"
            else:
                self._rules.append(
                    {
                        CONF_RULE_SEARCH: search,
                        CONF_RULE_MODE: user_input[CONF_RULE_MODE],
                        CONF_RULE_TYPE: user_input[CONF_RULE_TYPE],
                    }
                )
                return await self.async_step_menu()
        return self.async_show_form(
            step_id="add_rule",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RULE_SEARCH): str,
                    vol.Required(
                        CONF_RULE_TYPE, default=RuleType.ARBEIT.value
                    ): _select([t.value for t in RuleType], translation_key=CONF_RULE_TYPE),
                    vol.Required(
                        CONF_RULE_MODE, default=MatchMode.CONTAINS.value
                    ): _select([m.value for m in MatchMode], translation_key=CONF_RULE_MODE),
                }
            ),
            errors=errors,
        )

    async def async_step_remove_rule(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            drop = {int(i) for i in user_input.get("rules", [])}
            self._rules = [r for i, r in enumerate(self._rules) if i not in drop]
            return await self.async_step_menu()
        return self.async_show_form(
            step_id="remove_rule",
            data_schema=vol.Schema(
                {
                    vol.Required("rules"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=str(i), label=_rule_label(r))
                                for i, r in enumerate(self._rules)
                            ],
                            multiple=True,
                        )
                    )
                }
            ),
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        assert self._person is not None
        data = {
            CONF_PERSON: self._person,
            CONF_CALENDAR: self._calendar,
            CONF_RULES: self._rules,
        }
        if self.source == "reconfigure":
            return self.async_update_and_abort(
                self._get_entry(), self._get_reconfigure_subentry(), data=data
            )
        return self.async_create_entry(
            title=_person_title(self.hass, self._person),
            data=data,
            unique_id=_person_unique_id(self.hass, self._person),
        )
