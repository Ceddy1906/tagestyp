from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tagestyp.const import DOMAIN


async def _create_main(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"country": "AT"})
    assert result["step_id"] == "details"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "subdivision": "4",
            "language": "de",
            "extra_holidays": "24.12.2026\n28.12.2026,30.12.2026",
            "school_holidays": True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return result["result"]


async def test_global_flow_creates_entry(hass):
    entry = await _create_main(hass)
    assert entry.data == {"country": "AT"}
    assert entry.options["subdivision"] == "4"
    assert entry.options["extra_holidays"] == ["24.12.2026", "28.12.2026,30.12.2026"]
    assert entry.options["school_holidays"] is True


async def test_single_instance(hass):
    await _create_main(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_invalid_extra_holidays(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"country": "AT"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"subdivision": "4", "language": "de", "extra_holidays": "morgen", "school_holidays": False},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_extra_holidays"}


async def test_options_flow(hass):
    entry = await _create_main(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"subdivision": "9", "language": "de", "extra_holidays": "", "school_holidays": False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["subdivision"] == "9"
    assert entry.options["extra_holidays"] == []


async def _add_person(hass, entry, person="person.lissy"):
    flow = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "person"), context={"source": SOURCE_USER}
    )
    assert flow["step_id"] == "user"
    flow = await hass.config_entries.subentries.async_configure(
        flow["flow_id"], {"person": person, "calendar": "calendar.dienst"}
    )
    assert flow["type"] is FlowResultType.MENU
    return flow


async def test_subentry_add_person_with_rules(hass):
    hass.states.async_set("person.lissy", "home", {"friendly_name": "Lissy"})
    entry = await _create_main(hass)
    flow = await _add_person(hass, entry)

    for search, typ, mode in (("Lissy Arbeiten", "arbeit", "contains"), ("Lissy Urlaub", "urlaub", "exact")):
        flow = await hass.config_entries.subentries.async_configure(
            flow["flow_id"], {"next_step_id": "add_rule"}
        )
        flow = await hass.config_entries.subentries.async_configure(
            flow["flow_id"], {"search": search, "type": typ, "mode": mode}
        )
        assert flow["type"] is FlowResultType.MENU

    flow = await hass.config_entries.subentries.async_configure(
        flow["flow_id"], {"next_step_id": "finish"}
    )
    assert flow["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    subs = list(entry.subentries.values())
    assert len(subs) == 1
    assert subs[0].title == "Lissy"
    assert subs[0].data["calendar"] == "calendar.dienst"
    assert [r["search"] for r in subs[0].data["rules"]] == ["Lissy Arbeiten", "Lissy Urlaub"]


async def test_subentry_duplicate_person(hass):
    hass.states.async_set("person.lissy", "home", {"friendly_name": "Lissy"})
    entry = await _create_main(hass)
    flow = await _add_person(hass, entry)
    flow = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"next_step_id": "finish"})
    assert flow["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    flow = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "person"), context={"source": SOURCE_USER}
    )
    flow = await hass.config_entries.subentries.async_configure(
        flow["flow_id"], {"person": "person.lissy"}
    )
    assert flow["errors"] == {"base": "already_configured"}


async def test_subentry_reconfigure_remove_rule(hass):
    hass.states.async_set("person.lissy", "home", {"friendly_name": "Lissy"})
    entry = await _create_main(hass)
    flow = await _add_person(hass, entry)
    flow = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"next_step_id": "add_rule"})
    flow = await hass.config_entries.subentries.async_configure(
        flow["flow_id"], {"search": "Lissy Arbeiten", "type": "arbeit", "mode": "contains"}
    )
    flow = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"next_step_id": "finish"})
    await hass.async_block_till_done()
    sub = next(iter(entry.subentries.values()))

    flow = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "person"),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": sub.subentry_id},
    )
    assert flow["type"] is FlowResultType.MENU
    assert "remove_rule" in flow["menu_options"]
    flow = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"next_step_id": "remove_rule"})
    flow = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"rules": ["0"]})
    flow = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"next_step_id": "finish"})
    assert flow["type"] is FlowResultType.ABORT and flow["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert next(iter(entry.subentries.values())).data["rules"] == []


async def test_empty_search_rejected(hass):
    hass.states.async_set("person.lissy", "home", {"friendly_name": "Lissy"})
    entry = await _create_main(hass)
    flow = await _add_person(hass, entry)
    flow = await hass.config_entries.subentries.async_configure(flow["flow_id"], {"next_step_id": "add_rule"})
    flow = await hass.config_entries.subentries.async_configure(
        flow["flow_id"], {"search": "   ", "type": "arbeit", "mode": "contains"}
    )
    assert flow["errors"] == {"search": "empty_search"}
