# Portainer Stack Setup für Ugreen NAS

## 📋 Anleitung zur Einrichtung

### 1. Stack in Portainer erstellen

1. **Portainer öffnen** → Ihr Ugreen NAS Portainer Interface
2. **Stacks** → **Add stack**
3. **Name eingeben:** `access-converter`
4. **Build method:** `Web editor`
5. **Stack-Inhalt:** Kopieren Sie den Inhalt aus `portainer-stack.yml`

### 2. Flexible Konfiguration

#### 🔧 Umgebungsvariablen (Environment Variables)
Der Stack unterstützt flexible Konfiguration über Umgebungsvariablen:

**In Portainer Stack Editor:**
```yaml
# Direkt im Stack definieren:
environment:
  - MAX_UPLOAD_SIZE=209715200  # 200MB statt Standard 100MB
  - EXTERNAL_PORT=8081         # Port 8081 statt 8080
```

**Mit .env Datei (Advanced):**
1. Kopieren Sie `.env.template` nach `.env`
2. Passen Sie die Werte an
3. In Portainer: `Advanced mode` → `.env` hochladen

#### 📊 Dateigrössen-Konfiguration
**Vordefinierte Größen:**
```bash
# 50MB (für kleine NAS)
MAX_UPLOAD_SIZE=52428800

# 100MB (Standard)
MAX_UPLOAD_SIZE=104857600

# 200MB (empfohlen für NAS)
MAX_UPLOAD_SIZE=209715200

# 500MB (große Datenbanken)
MAX_UPLOAD_SIZE=524288000

# 1GB (Server-Umgebung)
MAX_UPLOAD_SIZE=1073741824
```

#### 🚀 Performance-Tuning
```yaml
# Kleine NAS (1-2 CPU Kerne):
environment:
  - MAX_CONCURRENT_JOBS=1
  - CLEANUP_INTERVAL_MINUTES=30
  - MAX_UPLOAD_SIZE=52428800

# Mittlere NAS (4+ CPU Kerne):
environment:
  - MAX_CONCURRENT_JOBS=3
  - CLEANUP_INTERVAL_MINUTES=60
  - MAX_UPLOAD_SIZE=209715200

# Server-Umgebung:
environment:
  - MAX_CONCURRENT_JOBS=5
  - CLEANUP_INTERVAL_MINUTES=120
  - MAX_UPLOAD_SIZE=1073741824
```

#### Port-Einstellungen
#### Port-Einstellungen
- **Standard:** Port `8080` (extern) → `8000` (intern)
- **Flexibel:** `EXTERNAL_PORT=8081` für anderen Port
- **Stack-Variable:** `"${EXTERNAL_PORT:-8080}:8000"`

#### Volume-Einstellungen
**Option A: Docker Volumes (empfohlen)**
```yaml
volumes:
  - access-converter-uploads:/app/data/uploads
  - access-converter-exports:/app/data/exports
  - access-converter-logs:/app/logs
```

**Option B: Host Bind Mounts (direkter NAS-Zugriff)**
```yaml
# In der Stack-Konfiguration ändern:
volumes:
  - /volume1/docker/access-converter/uploads:/app/data/uploads
  - /volume1/docker/access-converter/exports:/app/data/exports
  - /volume1/docker/access-converter/logs:/app/logs
```

**Option C: Flexible Pfade via Environment**
```yaml
environment:
  - UPLOADS_PATH=/meine/nas/uploads
  - EXPORTS_PATH=/meine/nas/exports
  - LOGS_PATH=/meine/nas/logs
# Dann in volumes: Option B aktivieren
```

### 3. Deployment mit Konfiguration

#### Basis-Deployment
```yaml
# Minimale Konfiguration - nutzt alle Standardwerte
version: '3.8'
services:
  access-converter:
    image: ghcr.io/baronblk/access-converter:latest
    ports:
      - "8080:8000"
```

#### Erweiterte Konfiguration
```yaml
# Vollständige Konfiguration mit allen Optionen
environment:
  - LOG_LEVEL=INFO
  - MAX_UPLOAD_SIZE=209715200      # 200MB
  - MAX_CONCURRENT_JOBS=3
  - CLEANUP_INTERVAL_MINUTES=60
  - EXTERNAL_PORT=8080
  - MAX_TABLES_PER_DB=100
  - WORKER_TIMEOUT=300
```

### 4. Deployment-Prozess

1. **Stack deployen:** Klicken Sie auf `Deploy the stack`
2. **Status prüfen:** Warten Sie bis Status `Running` anzeigt
3. **Health Check:** Container sollte "healthy" anzeigen
4. **Zugriff testen:** `http://NAS-IP:8080`

### 5. Troubleshooting

#### Container startet nicht
```bash
# Logs überprüfen in Portainer:
# Stacks → access-converter → Container → Logs
```

#### Port-Konflikte
```yaml
# Port ändern (z.B. 8081):
ports:
  - "8081:8000"
```

#### Volume-Probleme
```bash
# Host-Pfade erstellen (SSH ins NAS):
mkdir -p /volume1/docker/access-converter/{uploads,exports,logs}
chown -R 1000:1000 /volume1/docker/access-converter
```

### 6. Update-Prozess

1. **Image pullen:**
   - Stacks → access-converter → Container → Recreate
   - Oder: `Pull latest image` aktivieren

2. **Automatische Updates:**
   - Watchtower Container einrichten (optional)

### 7. Backup

#### Wichtige Daten
- **Uploads:** `/app/data/uploads` (temporär)
- **Exports:** `/app/data/exports` (wichtig!)
- **Logs:** `/app/logs` (optional)
- **Stack Config:** Portainer Stack-Definition

#### Backup-Script (optional)
```bash
#!/bin/bash
# Backup der Export-Daten
docker run --rm -v access-converter-exports:/source -v /volume1/backups:/backup \
  alpine tar czf /backup/access-converter-exports-$(date +%Y%m%d).tar.gz -C /source .
```

### 8. Monitoring

#### Health Check URL
```
http://NAS-IP:8080/health
```

#### Portainer Labels
- Automatische Organisation in Portainer
- Team- und User-Zugriffskontrolle
- Beschreibungen und Maintainer-Info

## 🚀 Features v2.2

- ✅ **Advanced Exports:** Pivot-Tabellen, Query-Export, Schema-ER-Diagramme
- ✅ **Automatic Cleanup:** 60-Minuten-Intervall
- ✅ **Multi-Format:** Excel, CSV, JSON Export
- ✅ **Health Monitoring:** Eingebaute Health Checks
- ✅ **Production Ready:** Optimierte Performance und Stabilität

## 📞 Support

Bei Problemen:
1. Container-Logs in Portainer prüfen
2. Health Check URL testen
3. GitHub Issues: https://github.com/baronblk/access_converter_docker

---
**Version:** v2.2.0  
**Maintainer:** baronblk@googlemail.com  
**Image:** ghcr.io/baronblk/access-converter:latest
