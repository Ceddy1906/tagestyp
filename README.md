# Tagestyp & Arbeitstage (Home Assistant)

Custom Integration (Domain `tagestyp`): Tagestyp (Werktag/Feiertag/Wochenende) für AT/DE/CH
inkl. Bundesland/Kanton und kalenderbasierter Arbeitstag-Status pro Person.

## Stand: Schritt 3 von 4 (Entitäten)

| Baustein | Status |
|---|---|
| Feiertage offline (`holidays`), Zusatzfeiertage | fertig, getestet |
| Tagestyp inkl. Brückentag | fertig, getestet |
| Personenregeln (urlaub > frei > arbeit > Tagestyp) | fertig, getestet |
| Config Flow: global (Land, Bundesland, Sprache, Zusatzfeiertage, Schulferien-Schalter) + Personen als Untereinträge (`person.*`, Kalender, Regeln), Einstellungen jederzeit änderbar | fertig, getestet |
| Coordinator (15 min, Mitternacht, Kalenderänderung), Sensoren, Feiertagskalender, Service `tagestyp.check_date`, Reparaturhinweis bei gelöschter Person | fertig, getestet |
| Schulferien (OpenHolidays + Cache), HACS-Feinschliff | offen (Schritt 4) |

## Entwicklung

```
pip install -r requirements_test.txt
pytest
```

## Offene Prüfpunkte

- `manifest.json`: `documentation`/`issue_tracker` sind Platzhalter, `holidays>=0.70` ist nicht gegen HA 2026.10.4 geprüft (getestet gegen HA 2026.2.3, dort pinnt Workday `holidays==0.84`).
- Österreich: Codes der `holidays`-Lib sind `1`–`9` (OÖ = `4`), nicht Kürzel wie `OÖ`.
- Subentry-Daten speichern `person` als entity_id; stabile ID ist `subentry.unique_id` (Registry-ID). Schritt 3 löst die aktuelle entity_id darüber auf.
- Das Land ist nach der Einrichtung nicht änderbar (wie bei Workday).

## Entitäten

| Entität (Schlüssel) | Zustand |
|---|---|
| `sensor.tagestyp` | werktag / feiertag / wochenende, Attribute: holiday_name, holiday_on_weekend, is_bridge_day, tomorrow, day_after_tomorrow |
| Frei heute, Brückentag (binary_sensor) | an/aus |
| Nächster Feiertag (sensor) | Zustand als Text `TT.MM.JJJJ`; Attribute: `date` (ISO, für Automationen), holiday_name, days_until |
| Feiertage (calendar) | Feiertage als ganztägige Termine |
| je Person: Status (sensor), Arbeitet (binary_sensor) | arbeit / frei / urlaub, Attribute: source, matched_rule, matched_event, tomorrow, day_after_tomorrow |

Entity-IDs richten sich nach der HA-Systemsprache (z. B. `sensor.tagestyp_naechster_feiertag` auf Deutsch).
Fällt ein Kalender aus, wird nur der Status dieser Person `nicht verfügbar`, die globalen Sensoren laufen weiter.

## Logik des Personenstatus

| Situation | Status | `source` |
|---|---|---|
| Regel `urlaub` trifft zu | urlaub | regel |
| Regel `frei` trifft zu | frei | regel |
| Regel `arbeit` trifft zu | arbeit | regel |
| Person hat mindestens eine `arbeit`-Regel, aber kein Termin passt (Dienstplan im Kalender) | frei | kein_termin |
| Person hat keine `arbeit`-Regel (nur `frei`/`urlaub`) oder keinen Kalender | Tagestyp: Werktag = arbeit, sonst frei | tagestyp |
