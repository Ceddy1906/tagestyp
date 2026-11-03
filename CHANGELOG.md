# Änderungen

## 0.2.0 – Erste Veröffentlichung

### Neu

- **Tagestyp:** Werktag, Feiertag oder Wochenende für Österreich, Deutschland und die Schweiz, inklusive Bundesland bzw. Kanton. Feiertage werden lokal berechnet und funktionieren ohne Internet.
- **Brückentag, nächster Feiertag, Feiertagskalender** sowie ein Ausblick auf morgen und übermorgen.
- **Zusatzfeiertage** (z. B. Betriebsurlaub) als Einzeltag oder Bereich im Format `TT.MM.JJJJ`.
- **Personen mit eigenem Status:** Der Status (arbeit / frei / urlaub) wird aus einem beliebigen Home-Assistant-Kalender anhand frei wählbarer Suchstrings ermittelt. Pro Person sind mehrere Regeln möglich, Vergleich wahlweise „enthält“ oder „exakt“. Fehlt bei einer Person mit `arbeit`-Regel ein passender Termin, gilt sie als frei.
- **Schulferien** (optional) über die OpenHolidays API, mit lokalem Zwischenspeicher für Ausfälle.
- **Service `tagestyp.check_date`:** Tagestyp und Personenstatus für ein beliebiges Datum.
- Einstellungen, Personen und Regeln lassen sich jederzeit in der Oberfläche ändern. Texte auf Deutsch und Englisch.
- Reparaturhinweis, wenn eine zugeordnete Person in Home Assistant nicht mehr existiert.

### Hinweise

- Nach jedem Update Home Assistant **vollständig neu starten**; ein „Neu laden“ der Integration genügt nicht.
- Fällt ein Kalender aus, wird nur der Status der betroffenen Person `nicht verfügbar`.
- Getestet mit Home Assistant 2026.2 und im Betrieb mit 2026.10. Ältere Versionen sind nicht geprüft.
