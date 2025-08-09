# Access Database Converter v2.0

Ein professioneller Docker-basierter Converter für Microsoft Access Datenbanken (.accdb/.mdb) zu Excel (XLSX) und CSV-Formaten.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)

## 🚀 Features

- **Vollständige Access-Unterstützung**: Konvertierung von .accdb und .mdb Dateien
- **Multiple Export-Formate**: Excel (XLSX) und CSV-Export
- **Moderne Web-UI**: Responsive Design mit Tailwind CSS und DaisyUI
- **Docker-basiert**: Einfache Bereitstellung ohne komplexe Setup-Schritte
- **Internationale Unterstützung**: Deutsche Umlaute und internationale Zeichen
- **Echtzeit-Progress**: Live-Fortschrittsverfolgung der Konvertierung
- **Robuste Architektur**: FastAPI Backend mit UCanAccess Integration
## 🏗️ Architektur

```
access_converter_docker/
├── app/                     # Python FastAPI Anwendung
│   ├── core/               # Kern-Funktionalitäten
│   ├── services/           # Business Logic
│   │   ├── ucan.py        # UCanAccess Integration
│   │   └── export.py      # Export-Services
│   ├── templates/          # HTML Templates
│   └── main.py            # FastAPI Haupt-App
├── docker/                 # Docker-Konfiguration
│   └── Dockerfile         # Multi-Stage Build
└── requirements.txt       # Python Dependencies
```

## 🛠️ Installation & Setup

### Voraussetzungen
- Docker Desktop
- Git

### 1. Repository klonen
```bash
git clone https://github.com/baronblk/access_converter_docker.git
cd access_converter_docker
```

### 2. Docker Container bauen und starten
```bash
# Container bauen
docker build -f docker/Dockerfile -t access-converter .

# Container starten
docker run --rm -d -p 8093:8000 --name access-converter access-converter
```

### 3. Anwendung öffnen
Öffnen Sie Ihren Browser und navigieren Sie zu: `http://localhost:8093`

## 📋 Verwendung

1. **Access-Datei hochladen**: Ziehen Sie Ihre .accdb/.mdb Datei in den Upload-Bereich
2. **Tabellen auswählen**: Wählen Sie die zu konvertierenden Tabellen aus
3. **Export-Format wählen**: CSV oder Excel (XLSX)
4. **Konvertierung starten**: Verfolgen Sie den Fortschritt in Echtzeit
5. **Download**: Laden Sie die konvertierten Dateien als ZIP-Archiv herunter

## 🔧 Technische Details

### Backend-Stack
- **FastAPI**: Moderne, schnelle Web-API
- **UCanAccess**: Java-basierter Access-Treiber
- **Pandas**: Datenverarbeitung und Export
- **Docker**: Containerisierung mit Multi-Stage Build

### Frontend-Stack
- **Alpine.js**: Reaktive JavaScript-Funktionalität
- **Tailwind CSS**: Utility-First CSS Framework
- **DaisyUI**: UI-Komponenten-Bibliothek

### Unterstützte Formate
- **Input**: Microsoft Access (.accdb, .mdb)
- **Output**: Excel (.xlsx), CSV (.csv)
## 🐛 Fehlerbehebung

### Container-Logs anzeigen
```bash
docker logs access-converter --tail 50
```

### Container neu starten
```bash
docker stop access-converter
docker rm access-converter
docker run --rm -d -p 8093:8000 --name access-converter access-converter
```

### Häufige Probleme
- **Port 8093 bereits belegt**: Verwenden Sie einen anderen Port: `-p 8094:8000`
- **Tabellen werden nicht erkannt**: Überprüfen Sie, ob die Access-Datei nicht beschädigt ist
- **Scroll-Probleme**: Aktualisieren Sie die Seite (F5)
- **UCanAccess Fehler**: Prüfen Sie die Container-Logs auf JAR-Datei-Probleme

## 📊 Entwicklung

### Lokale Entwicklung
```bash
# Python-Umgebung einrichten
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r requirements.txt

# Entwicklungsserver starten
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development Build
```bash
# Development Build mit Volume-Mounting für Live-Reload
docker run --rm -it -p 8093:8000 -v "$(pwd)/app:/app/app" access-converter
```

## 🤝 Beitragen

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'Add some AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request erstellen

## 📝 Changelog

### v2.0.0 (2025-08-09)
- **Vollständige Überarbeitung**: Neue moderne Web-UI mit Tailwind CSS und DaisyUI
- **Docker-Integration**: Komplette Containerisierung mit Multi-Stage Build
- **UCanAccess-Update**: Aktuelle Version 5.0.1 mit direkten Maven Central Downloads
- **Internationale Unterstützung**: Deutsche Umlaute und Sonderzeichen vollständig unterstützt
- **Responsive Design**: Optimiert für alle Bildschirmgrößen mit natürlichem Scrolling
- **Echtzeit-Progress**: Live-Updates während der Konvertierung mit Progress-Modal
- **Robuste Fehlerbehandlung**: Umfassende Validierung und Logging auf allen Ebenen
- **Alpine.js Integration**: Moderne reaktive Frontend-Funktionalität
- **Optimierte Architektur**: FastAPI Backend mit strukturierter Service-Schicht

### v1.0.0
- Grundlegende Access-zu-CSV-Konvertierung

## 🔧 API Referenz

### Hauptendpunkte
- `GET /` - Upload-Interface
- `POST /upload` - Datei hochladen
- `GET /tables/{job_id}` - Tabellen-Metadaten abrufen
- `GET /tables/{job_id}/page` - Tabellen-Auswahl-UI
- `POST /convert/{job_id}` - Konvertierung starten
- `GET /status/{job_id}` - Konvertierungsstatus
- `GET /download/{job_id}` - ZIP-Download der Ergebnisse
- `GET /health` - System-Health-Check

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz veröffentlicht. Siehe [LICENSE](LICENSE) Datei für Details.

## 🙏 Danksagungen

- [UCanAccess](http://ucanaccess.sourceforge.net/) - Java-basierter Access-Treiber
- [FastAPI](https://fastapi.tiangolo.com/) - Modernes Python Web Framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-First CSS Framework
- [DaisyUI](https://daisyui.com/) - Tailwind CSS Komponenten
- [Alpine.js](https://alpinejs.dev/) - Minimales JavaScript Framework

## 📞 Support

Bei Fragen oder Problemen erstellen Sie bitte ein [Issue](https://github.com/baronblk/access_converter_docker/issues) auf GitHub.

## 🚀 Performance

- **Multi-Threading**: Parallele Verarbeitung von Tabellen
- **Memory-Optimierung**: Effiziente Speichernutzung bei großen Dateien
- **Stream-Processing**: Minimaler Memory-Footprint
- **Docker-Optimierung**: Multi-Stage Build für kleinere Images

---

**Access Database Converter v2.0** - Entwickelt mit ❤️ für die Community

## Sicherheit

- **File Validation**: Nur .mdb/.accdb Dateien erlaubt
- **Size Limits**: Standard 100MB Upload-Limit
- **Path Sanitization**: Sichere Dateinamen und Pfade
- **Temporary Files**: Automatisches Cleanup nach Job-Completion
- **No External Dependencies**: Alle Libraries in Container eingebettet

## Performance

- **Concurrent Jobs**: Standard 3 parallele Konvertierungen
- **Memory Management**: Optimierte JVM-Settings für UCanAccess
- **File Streaming**: Efficient file handling für große Datenbanken
- **Progress Tracking**: Real-time Status Updates

## Lizenz

MIT License - siehe LICENSE Datei für Details.

## Support

Für Fragen und Support:
- Issue Tracker: GitHub Issues
- Dokumentation: Siehe `/docs` Ordner
- API Docs: http://localhost:8000/docs (FastAPI Swagger UI)

---

**Access Database Converter v2.0** - Entwickelt für moderne, containerisierte Umgebungen.
