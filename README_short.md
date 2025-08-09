# Access Database Converter v2.0

Ein moderner, containerisierter Service zum Konvertieren von Microsoft Access Datenbanken (.mdb/.accdb) in verschiedene Formate.

## Schnellstart

```bash
# Container bauen
make build

# Anwendung starten  
make run

# Verfügbar unter: http://localhost:8000
```

## Features

- 🐳 Single-Container Deployment
- 🎨 Moderne UI mit Tailwind CSS + daisyUI
- 📊 Export: CSV, Excel, JSON, PDF
- ⚡ Hintergrund-Jobs mit ThreadPoolExecutor
- 🔧 UCanAccess JDBC Integration

## Befehle

```bash
make build          # Container bauen
make run            # Container starten  
make stop           # Container stoppen
make logs           # Logs anzeigen
make clean          # Aufräumen
```
