# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-08-09

### Hinzugefügt
- **Vollständige UI-Überarbeitung**: Neue moderne Web-Interface mit Tailwind CSS und DaisyUI
- **Docker-Integration**: Komplette Containerisierung mit Multi-Stage Build
- **UCanAccess 5.0.1**: Aktualisierte UCanAccess-Version mit Maven Central Downloads
- **Internationale Unterstützung**: Deutsche Umlaute (ä, ö, ü, ß) und internationale Zeichen
- **Responsive Design**: Optimiert für alle Bildschirmgrößen
- **Echtzeit-Progress**: Live-Updates während der Konvertierung mit Progress-Modal
- **Alpine.js Integration**: Moderne reaktive Frontend-Funktionalität ohne jQuery
- **Natürliches Scrolling**: Vollständig funktionsfähiges Scrolling auf allen Seiten
- **Robuste Fehlerbehandlung**: Umfassende Validierung und Logging
- **JAR-Validierung**: Automatische Überprüfung aller erforderlichen UCanAccess-JARs
- **Debug-Logging**: Erweiterte Debug-Funktionen für Entwicklung und Troubleshooting

### Geändert
- **Backend-Architektur**: Strukturierte Service-Schicht mit FastAPI
- **Frontend-Framework**: Wechsel von jQuery zu Alpine.js
- **CSS-Framework**: Migration von Bootstrap zu Tailwind CSS + DaisyUI
- **UCanAccess-Installation**: Direkte JAR-Downloads von Maven Central statt SourceForge
- **Tabellen-Validierung**: Erweiterte Regex-Patterns für internationale Zeichen
- **Container-Optimierung**: Multi-Stage Docker Build für kleinere Images
- **Logging-System**: Strukturiertes Logging mit Request-IDs

### Behoben
- **Scrolling-Probleme**: Vollständig behobene CSS-Layout-Issues
- **UCanAccess-JARs**: Korrekte Installation aller erforderlichen Abhängigkeiten
- **Tabellennamen-Validierung**: Unterstützung für deutsche Umlaute und Sonderzeichen
- **Progress-Modal**: Korrekte Anzeige des Konvertierungsfortschritts
- **Memory-Leaks**: Optimierte Speicherverwaltung bei großen Dateien
- **Template-Routing**: Korrekte Template-Pfade im Backend

### Entfernt
- **jQuery-Abhängigkeiten**: Ersetzt durch Alpine.js
- **Bootstrap**: Ersetzt durch Tailwind CSS
- **Legacy-Code**: Veraltete Upload-Handler und Template-Logik

## [1.0.0] - 2024-XX-XX

### Hinzugefügt
- Grundlegende Access-zu-CSV-Konvertierung
- Einfache Web-Interface
- Docker-Support
- UCanAccess-Integration

---

## Dokumentationsformat

### [Version] - YYYY-MM-DD

#### Hinzugefügt
Für neue Features.

#### Geändert
Für Änderungen an bestehender Funktionalität.

#### Veraltet
Für Features, die bald entfernt werden.

#### Entfernt
Für Features, die in dieser Version entfernt wurden.

#### Behoben
Für Bugfixes.

#### Sicherheit
Für sicherheitsrelevante Änderungen.
