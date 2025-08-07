# Access Database Converter

Eine professionelle Webanwendung zur Konvertierung von Microsoft Access-Datenbanken (.accdb/.mdb) in verschiedene Formate (CSV, XLSX, JSON, PDF) mit Browser-basierter Benutzeroberfläche.

## 🏗️ Architektur

### Backend
- **Python 3.11** mit **FastAPI**
- **UCanAccess** (JDBC) via jaydebeapi + OpenJDK 17 für Access-DB-Zugriff unter Linux
- **RQ (Redis Queue)** für asynchrone Job-Verarbeitung
- **Redis** als Message Broker und Cache
- Strukturierte Logs mit Request-IDs und Job-IDs

### Frontend
- **React** mit **Vite** Build-System
- **Tailwind CSS** für professionelles Styling
- Drag & Drop Upload-Interface
- Echtzeit-Fortschrittsanzeige
- Job-Historie und Log-Viewer

### Deployment
- **Docker** mit docker-compose
- **Linux-kompatibel** (kein Windows erforderlich)
- **nginx** als Reverse Proxy für Frontend

## 🚀 Features

### Core Features
- ✅ Upload von .accdb/.mdb Dateien (Drag & Drop)
- ✅ Automatische Erkennung und Auflistung aller Tabellen
- ✅ Auswahl von Zieltabellen (alle oder Teilmenge)
- ✅ Export in mehrere Formate:
  - **CSV** (UTF-8 BOM, Separator ";")
  - **XLSX** (eine Datei pro Tabelle)
  - **JSON** (orient="records")
  - **PDF** (einfache Tabellendarstellung)
- ✅ Echtzeit-Fortschrittsanzeige
- ✅ Download einzelner Dateien oder ZIP-Gesamtpaket
- ✅ Job-Historie mit Status und Fehleranzeige
- ✅ Automatisches Aufräumen alter Uploads/Exports

### Security & Robustheit
- Konfigurierbare max. Upload-Größe (Standard: 200 MB)
- Dateifilter auf .accdb/.mdb Endungen
- Sichere Pfadbehandlung mit pathlib
- Zeitlimits pro Job
- Keine Makro-Ausführung, nur Tabellen-Lesen
- Saubere Fehlerbehandlung pro Tabelle

## 📡 API Endpunkte

```
POST /api/upload                     → Datei hochladen, ID zurückgeben
GET  /api/tables?file_id=...         → Tabellen/Views auflisten
POST /api/jobs                       → Job starten
GET  /api/jobs/{job_id}              → Job-Status + Fortschritt
GET  /api/jobs/{job_id}/download     → ZIP aller Ergebnisse
GET  /api/logs/{job_id}              → Protokollauszug
WS   /api/jobs/{job_id}/ws           → Live-Fortschritt (WebSocket)
```

## 🐳 Docker Setup

```bash
# Projekt klonen
git clone https://github.com/baronblk/acceess_converter_docker.git
cd access_converter_docker

# Starten mit docker-compose
docker-compose up --build

# App verfügbar unter:
http://localhost:8080
```

## 🔧 Entwicklung

### Backend (Python/FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React/Vite)
```bash
cd frontend
npm install
npm run dev
```

### Worker (RQ)
```bash
cd backend
python -m rq worker --url redis://localhost:6379/0
```

## 📁 Projektstruktur

```
access_converter_docker/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI Router & Endpunkte
│   │   ├── core/         # Konfiguration & Logging
│   │   ├── services/     # Business Logic (UCanAccess, Export, Jobs)
│   │   ├── models.py     # Pydantic Schemas
│   │   ├── utils.py      # Hilfsfunktionen
│   │   └── main.py       # FastAPI App
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── ucanaccess/           # UCanAccess JAR-Dateien
├── data/
│   ├── uploads/          # Temporäre Upload-Dateien
│   ├── exports/          # Exportierte Dateien
│   └── logs/             # Anwendungsprotokoll
├── docker-compose.yml
└── README.md
```

## ⚙️ Umgebungsvariablen

```env
APP_ENV=prod
MAX_UPLOAD_MB=200
CLEANUP_AFTER_HOURS=24
REDIS_URL=redis://redis:6379/0
UCANACCESS_PATH=/opt/ucanaccess
```

## 🎯 Roadmap

- [x] Projektinitialisierung & Grundstruktur
- [ ] Backend: Upload & Tabellen-Auflistung
- [ ] Backend: Job-System mit RQ
- [ ] Backend: Export-Funktionen (CSV, XLSX, JSON, PDF)
- [ ] Frontend: Upload-Interface
- [ ] Frontend: Tabellen-Auswahl & Job-Management
- [ ] Frontend: Fortschrittsanzeige & Downloads
- [ ] Docker-Setup & Deployment
- [ ] Tests & Dokumentation

## 📄 Lizenz

MIT License

## 🤝 Beitragen

Contributions sind willkommen! Bitte erstelle ein Issue oder Pull Request.
