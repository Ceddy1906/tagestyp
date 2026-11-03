# Entwicklung

## Tests

```
pip install -r requirements_test.txt
pytest
```

Die Tests greifen nie auf die echte OpenHolidays-API zu. Sie laufen gegen `pytest-homeassistant-custom-component`; die Mindestversion in `hacs.json` entspricht der damit getesteten Home-Assistant-Version.

## Aufbau

| Datei | Aufgabe |
|---|---|
| `holidays_provider.py` | Feiertage offline (`holidays`), Zusatzfeiertage |
| `daytype.py` | Tagestyp und Brückentag (ohne HA-Importe) |
| `rules.py`, `engine.py` | Personenstatus aus Kalenderterminen und Regeln (ohne HA-Importe) |
| `school_provider.py` | Schulferien von OpenHolidays mit Cache |
| `coordinator.py` | Aktualisierung (15 Minuten, Mitternacht, Kalenderänderung), Kalenderzugriff |
| `config_flow.py` | Einrichtung global, Personen als Untereinträge, Optionen |
| `sensor.py`, `binary_sensor.py`, `calendar.py` | Entitäten |

## Annahmen zur OpenHolidays-API

Das Antwortformat (`startDate`/`endDate` inklusive, `nationwide`, `subdivisions[].code` wie `AT-4`) stammt aus der Dokumentation von API-Clients. Es wurde im Betrieb mit Oberösterreich gegen einen bestehenden Schulferien-Kalender abgeglichen, andere Länder und Bundesländer sind nicht einzeln geprüft.

## Release

1. `version` in `custom_components/tagestyp/manifest.json` erhöhen und `CHANGELOG.md` ergänzen.
2. Committen und nach Gitea pushen.
3. In Gitea den Tag setzen, z. B. `git tag v0.2.0 && git push origin v0.2.0`, und den Spiegel nach GitHub abwarten.
4. Auf GitHub: Releases → **Draft a new release** → vorhandenen Tag `v0.2.0` wählen, Titel `v0.2.0`, den Abschnitt aus `CHANGELOG.md` einfügen, veröffentlichen.

Der Tag muss zur Version im Manifest passen. HACS bietet Anwendern die veröffentlichten Releases als Versionen an.
