# Tagestyp & Arbeitstage für Home Assistant

Zeigt in Home Assistant, ob heute **Werktag**, **gesetzlicher Feiertag** oder **Wochenende** ist, und ermittelt für jede Person aus einem bestehenden Kalender, ob sie **arbeitet**, **frei** hat oder **Urlaub** hat. Optional kommen die **Schulferien** dazu.

Die Integration deckt Österreich, Deutschland und die Schweiz ab, jeweils mit Bundesland bzw. Kanton.

## Funktionen

| Funktion | Beschreibung |
|---|---|
| Tagestyp | Werktag, Feiertag oder Wochenende, dazu Feiertagsname, Brückentag und der Ausblick auf morgen und übermorgen |
| Nächster Feiertag | Datum, Name und Tage bis dahin |
| Feiertagskalender | alle Feiertage als Kalender, z. B. für das Dashboard |
| Zusatzfeiertage | eigene freie Tage wie Betriebsurlaub, als Einzeltag oder Bereich |
| Personen | je Person ein eigener Status (arbeit / frei / urlaub), gesteuert durch Suchbegriffe in einem Kalender deiner Wahl |
| Schulferien | optional, mit Name und Zeitraum der aktuellen und der nächsten Ferien |
| Service `check_date` | Tagestyp und Personenstatus für ein beliebiges Datum abfragen |

Die Feiertage werden lokal berechnet und funktionieren auch ohne Internet. Nur die Schulferien werden online abgerufen und für Ausfälle zwischengespeichert.

## Installation

### Über HACS (empfohlen)

1. In Home Assistant **HACS** öffnen.
2. Oben rechts das Menü (⋮) → **Benutzerdefinierte Repositories**.
3. Repository `https://github.com/Ceddy1906/tagestyp` eintragen, Typ **Integration**, hinzufügen.
4. „Tagestyp & Arbeitstage“ in HACS suchen und herunterladen.
5. **Home Assistant neu starten.**

### Manuell

1. Den Ordner `custom_components/tagestyp` aus diesem Repository nach `/config/custom_components/` kopieren.
2. **Home Assistant neu starten.**

> **Wichtig bei Updates:** Nach jedem Update ist ein vollständiger Neustart von Home Assistant nötig. Ein „Neu laden“ der Integration liest geänderten Programmcode nicht neu ein.

## Einrichtung

Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Tagestyp & Arbeitstage“.

### 1. Globale Einstellungen

| Einstellung | Bedeutung |
|---|---|
| Land | Österreich, Deutschland oder Schweiz (später nicht mehr änderbar) |
| Bundesland / Kanton | bestimmt die regionalen Feiertage |
| Sprache | Sprache der Feiertagsnamen (Deutsch oder Englisch) |
| Zusatzfeiertage | eine Angabe pro Zeile: `TT.MM.JJJJ` oder ein Bereich `TT.MM.JJJJ,TT.MM.JJJJ` |
| Schulferien anzeigen | schaltet den Schulferien-Sensor ein |

Alle Werte lassen sich später über das Zahnrad der Integration (**Konfigurieren**) ändern.

### 2. Personen hinzufügen

Auf der Integrationskarte **Person hinzufügen** wählen:

1. Eine Person aus Home Assistant (`person.…`) auswählen und optional einen Kalender.
2. **Regeln** anlegen. Jede Regel besteht aus:
   - einem **Suchstring**, den du selbst festlegst (z. B. `Lissy Arbeiten`), gesucht im Titel der Kalendertermine,
   - einem **Typ**: `arbeit`, `frei` oder `urlaub`,
   - einem **Vergleich**: `enthält` oder `exakt` (Groß-/Kleinschreibung spielt keine Rolle).

Pro Person sind beliebig viele Regeln möglich. Regeln und Kalender lassen sich jederzeit über die Person ändern.

**Beispiel Dienstplan:** Im Kalender stehen Termine „Lissy Arbeiten“. Regel: `Lissy Arbeiten`, Typ `arbeit`. An Tagen mit Termin steht der Status auf *arbeit*, an allen anderen auf *frei*.

**Beispiel Urlaub:** Zusätzlich Regel `Lissy Urlaub`, Typ `urlaub`. Ein Urlaubstermin hat Vorrang vor einem Arbeitstermin.

## So wird der Personenstatus bestimmt

| Situation | Status |
|---|---|
| Eine Regel vom Typ `urlaub` trifft zu | urlaub |
| Eine Regel vom Typ `frei` trifft zu | frei |
| Eine Regel vom Typ `arbeit` trifft zu | arbeit |
| Es gibt eine `arbeit`-Regel, aber kein passender Termin | frei |
| Es gibt keine `arbeit`-Regel (nur `frei`/`urlaub`) oder keinen Kalender | nach Tagestyp: Werktag = arbeit, Wochenende und Feiertag = frei |

Treffen mehrere Regeln zu, gilt die Reihenfolge urlaub vor frei vor arbeit. Ein Termin, der um 00:00 Uhr endet, zählt nicht für den Folgetag.

## Entitäten

Die Entity-IDs richten sich nach der Systemsprache von Home Assistant.

| Entität | Inhalt |
|---|---|
| Tagestyp (Sensor) | `werktag`, `feiertag` oder `wochenende`; Attribute u. a. `holiday_name`, `is_bridge_day`, `tomorrow`, `day_after_tomorrow` |
| Frei heute (Binärsensor) | an bei Wochenende oder Feiertag |
| Brückentag (Binärsensor) | an, wenn der Tag zwischen einem Feiertag und dem Wochenende liegt |
| Nächster Feiertag (Sensor) | Zustand als `TT.MM.JJJJ`; Attribute `date` (ISO-Format für Automationen), `holiday_name`, `days_until` |
| Feiertage (Kalender) | Feiertage als ganztägige Termine |
| Schulferien (Binärsensor, optional) | an in den Ferien; Attribute `name`, `start`, `end`, `next_name`, `next_start`, `next_end`, `days_until_next`, `data_stale`, `last_updated` |
| Status (Sensor, je Person) | `arbeit`, `frei` oder `urlaub`; Attribute `source`, `matched_rule`, `matched_event`, `configured_rules`, `tomorrow`, `day_after_tomorrow` |
| Status morgen (Sensor, je Person) | wie *Status*, aber für den morgigen Tag; Attribute `source`, `matched_rule`, `matched_event`, `date` |
| Arbeitet (Binärsensor, je Person) | an, wenn der Status `arbeit` ist |

Das Attribut `source` zeigt, warum ein Status zustande kam: `regel` (eine Regel hat getroffen), `kein_termin` (Dienstplan ohne Termin) oder `tagestyp` (Rückfall auf den Tagestyp).

## Service `tagestyp.check_date`

Liefert Tagestyp, Feiertagsname, Brückentag und den Status aller Personen für ein beliebiges Datum.

```yaml
action: tagestyp.check_date
data:
  date: "2026-12-24"
response_variable: ergebnis
```

## Hinweise

- **Kalender nicht erreichbar:** Dann ist nur der Status der betroffenen Person `nicht verfügbar`. Alle anderen Entitäten laufen weiter.
- **Person gelöscht:** Home Assistant zeigt einen Reparaturhinweis. Entferne dann den Eintrag der Person in der Integration.
- **Schulferien:** Abruf beim Start und danach alle 24 Stunden. Bei einem Ausfall der Quelle gelten die zuletzt gespeicherten Daten (`data_stale: true`).
- **Entity-ID oder Name stimmt nicht nach einem Update:** Home Assistant vollständig neu starten.

## Datenquellen

- Feiertage: Python-Bibliothek [`holidays`](https://github.com/vacanza/holidays)
- Schulferien: [OpenHolidays API](https://www.openholidaysapi.org/en/)

## Fehler melden

Bitte als [Issue](https://github.com/Ceddy1906/tagestyp/issues) melden, möglichst mit Version, Home-Assistant-Version und einem Auszug aus dem Protokoll.

## Lizenz

[MIT](LICENSE) © 2026 Ceddy1906
