"""Konstanten für Tagestyp."""

from __future__ import annotations

DOMAIN = "tagestyp"

# Globale Optionen
CONF_COUNTRY = "country"
CONF_SUBDIVISION = "subdivision"
CONF_LANGUAGE = "language"
CONF_EXTRA_HOLIDAYS = "extra_holidays"
CONF_SCHOOL_HOLIDAYS = "school_holidays"

# Person
CONF_PERSON = "person"  # interne Registry-ID der person-Entität
CONF_CALENDAR = "calendar"
CONF_RULES = "rules"
CONF_RULE_SEARCH = "search"
CONF_RULE_MODE = "mode"
CONF_RULE_TYPE = "type"

SUPPORTED_COUNTRIES = ("AT", "DE", "CH")
DEFAULT_COUNTRY = "AT"
DEFAULT_LANGUAGE = "de"

# Wie weit voraus der nächste Feiertag gesucht wird (Tage)
NEXT_HOLIDAY_LOOKAHEAD_DAYS = 400

SUBENTRY_PERSON = "person"

# Anzeigenamen der Unterteilungen (Fallback: Code)
SUBDIVISION_NAMES: dict[str, dict[str, str]] = {
    "AT": {
        "1": "Burgenland", "2": "Kärnten", "3": "Niederösterreich",
        "4": "Oberösterreich", "5": "Salzburg", "6": "Steiermark",
        "7": "Tirol", "8": "Vorarlberg", "9": "Wien",
    },
    "DE": {
        "BB": "Brandenburg", "BE": "Berlin", "BW": "Baden-Württemberg",
        "BY": "Bayern", "HB": "Bremen", "HE": "Hessen", "HH": "Hamburg",
        "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
        "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz",
        "SH": "Schleswig-Holstein", "SL": "Saarland", "SN": "Sachsen",
        "ST": "Sachsen-Anhalt", "TH": "Thüringen", "Augsburg": "Augsburg (Friedensfest)",
    },
    "CH": {
        "AG": "Aargau", "AI": "Appenzell Innerrhoden", "AR": "Appenzell Ausserrhoden",
        "BE": "Bern", "BL": "Basel-Landschaft", "BS": "Basel-Stadt", "FR": "Freiburg",
        "GE": "Genf", "GL": "Glarus", "GR": "Graubünden", "JU": "Jura", "LU": "Luzern",
        "NE": "Neuenburg", "NW": "Nidwalden", "OW": "Obwalden", "SG": "St. Gallen",
        "SH": "Schaffhausen", "SO": "Solothurn", "SZ": "Schwyz", "TG": "Thurgau",
        "TI": "Tessin", "UR": "Uri", "VD": "Waadt", "VS": "Wallis", "ZG": "Zug",
        "ZH": "Zürich", "Stadt Zurich": "Stadt Zürich",
    },
}

UPDATE_INTERVAL_MINUTES = 15
