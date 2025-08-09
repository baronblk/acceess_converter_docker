# Access Database Converter v2.0

Ein moderner, containerisierter Service zur Konvertierung von Microsoft Access-Datenbanken (.mdb/.accdb) in verschiedene Formate (CSV, Excel, JSON, PDF) - ohne Windows-Abhängigkeiten.

## Features

- 🚀 **Single-Container-Architektur** - Einfaches Deployment ohne komplexe Abhängigkeiten
- 📊 **Multi-Format-Export** - CSV, Excel (XLSX), JSON, und PDF Unterstützung
- 🎨 **Moderne Web-UI** - Responsive Design mit Tailwind CSS und daisyUI
- ⚡ **Threading-basierte Jobs** - Parallele Verarbeitung mit ThreadPoolExecutor
- 🔒 **Sichere Uploads** - Validierung und Größenbeschränkungen
- 📁 **Batch-Download** - Alle Exports als ZIP-Archiv
- 🐳 **Docker-Ready** - Komplette Containerisierung mit Java/Python Integration

## Technologie-Stack

- **Backend**: FastAPI (Python 3.11) + UCanAccess (Java JDBC)
- **Frontend**: Jinja2 Templates + Tailwind CSS + Alpine.js
- **Database**: UCanAccess für .mdb/.accdb Dateien
- **Export**: pandas, openpyxl, reportlab
- **Container**: Docker mit OpenJDK 17 + Python 3.11

## Quick Start

### Mit Docker

```bash
# Repository klonen
git clone <your-repo-url>
cd access_converter_docker

# Container bauen und starten
make build
make run

# Oder direkt mit Docker
docker build -f docker/Dockerfile -t access-converter .
docker run -p 8000:8000 access-converter
```

### Ohne Docker (Entwicklung)

```bash
# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r requirements.txt

# Java installieren (OpenJDK 17+)
# UCanAccess JARs herunterladen (siehe Dockerfile)

# Anwendung starten
cd app
python main.py
```

## Verwendung

1. **Öffnen Sie** http://localhost:8000 in Ihrem Browser
2. **Laden Sie** Ihre .mdb oder .accdb Datei hoch (max. 100MB)
3. **Wählen Sie** die gewünschten Tabellen aus
4. **Bestimmen Sie** das Export-Format (CSV/Excel/JSON/PDF)
5. **Downloaden Sie** die konvertierten Dateien als ZIP-Archiv

## API Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/` | GET | Upload-Interface |
| `/upload` | POST | Datei hochladen |
| `/tables/{job_id}` | GET | Tabellen auflisten |
| `/tables/{job_id}/page` | GET | Tabellen-Auswahl-Interface |
| `/convert/{job_id}` | POST | Konvertierung starten |
| `/status/{job_id}` | GET | Job-Status abfragen |
| `/download/{job_id}` | GET | Ergebnisse downloaden |
| `/health` | GET | Health Check |

## Konfiguration

Umgebungsvariablen können in `.env` gesetzt werden:

```env
# Upload-Einstellungen
MAX_UPLOAD_SIZE=104857600  # 100MB
UPLOAD_DIR=/app/uploads
EXPORT_DIR=/app/exports

# Job-Einstellungen
MAX_CONCURRENT_JOBS=3
JOB_TIMEOUT_MINUTES=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log
```

## Entwicklung

### Projektstruktur

```
access_converter_docker/
├── docker/
│   └── Dockerfile              # Multi-stage Docker build
├── app/
│   ├── main.py                 # FastAPI application
│   ├── jobs.py                 # Job management
│   ├── models.py               # Pydantic models
│   ├── core/
│   │   ├── config.py           # Configuration
│   │   └── logging.py          # Logging setup
│   ├── services/
│   │   ├── ucan.py             # UCanAccess integration
│   │   └── export.py           # Export services
│   └── templates/
│       ├── index.html          # Upload interface
│       └── tables.html         # Table selection
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── Makefile                   # Build/run commands
└── README.md                  # This file
```

### Lokale Entwicklung

```bash
# Development server mit Auto-Reload
make dev

# Tests ausführen
make test

# Logs anzeigen
make logs

# Container cleanup
make clean
```

### UCanAccess Integration

Die Anwendung verwendet UCanAccess für den direkten Zugriff auf Access-Datenbanken:

- **Java Integration**: JPype1 für Python-Java Bridge
- **JDBC Driver**: UCanAccess 5.0.1 mit allen Abhängigkeiten
- **Memory Management**: Optimierte JVM-Einstellungen
- **Thread Safety**: Single-threaded JDBC operations

## Deployment

### Produktions-Deployment

```bash
# Production build
docker build -f docker/Dockerfile -t access-converter:prod .

# Mit docker-compose
version: '3.8'
services:
  access-converter:
    image: access-converter:prod
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=WARNING
      - MAX_CONCURRENT_JOBS=5
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: access-converter
spec:
  replicas: 2
  selector:
    matchLabels:
      app: access-converter
  template:
    metadata:
      labels:
        app: access-converter
    spec:
      containers:
      - name: access-converter
        image: access-converter:prod
        ports:
        - containerPort: 8000
        env:
        - name: MAX_CONCURRENT_JOBS
          value: "3"
        resources:
          limits:
            memory: "2Gi"
            cpu: "1000m"
          requests:
            memory: "1Gi"
            cpu: "500m"
```

## Troubleshooting

### Häufige Probleme

**UCanAccess ClassNotFound:**
```bash
# Prüfen Sie die Java-Classpath
echo $CLASSPATH
# Stelle sicher, dass alle JAR-Dateien vorhanden sind
ls -la /app/lib/
```

**Upload-Fehler:**
```bash
# Prüfen Sie Dateiberechtigungen
chmod 755 /app/uploads
# Prüfen Sie Festplattenspeicher
df -h
```

**Memory-Probleme:**
```bash
# Erhöhen Sie Java Heap Size
export JAVA_HEAP_SIZE=2048m
# Oder in der .env Datei
echo "JAVA_HEAP_SIZE=2048m" >> .env
```

### Logs

```bash
# Application logs
docker logs <container-id>

# File logs
tail -f /app/logs/app.log

# Java/JVM logs
# JVM logs werden in den Application logs ausgegeben
```

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
