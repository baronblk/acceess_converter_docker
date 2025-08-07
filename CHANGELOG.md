# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt der [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Hinzugefügt
- Initiale Projektstruktur für Access Database Converter
- Backend-Setup mit FastAPI, Python 3.11
- Frontend-Setup mit React + Vite + Tailwind CSS
- Docker-Konfiguration mit docker-compose
- Grundlegende API-Routen-Struktur
- Logging-System mit strukturierten Logs
- Konfigurationssystem mit Umgebungsvariablen
- UCanAccess-Integration für Access-DB-Zugriff unter Linux
- Grundlegende Modelle für Jobs, Uploads, und Fortschritt

### Geplant
- [ ] Upload-Funktionalität implementieren
- [ ] Tabellen-Auflistung über UCanAccess
- [ ] Job-System mit Redis Queue (RQ)
- [ ] Export-Funktionen (CSV, XLSX, JSON, PDF)
- [ ] Frontend Upload-Interface
- [ ] Fortschrittsanzeige und Job-Überwachung
- [ ] WebSocket-Integration für Live-Updates
- [ ] Cleanup-System für alte Dateien
- [ ] Tests und Dokumentation

## [1.0.0] - TBD

### Hinzugefügt
- Vollständige Implementierung aller Core Features
- Docker-Deployment ready
- Umfassende Tests
- Produktionsbereite Konfiguration
