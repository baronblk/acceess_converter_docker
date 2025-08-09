# Portainer Stack Setup für Ugreen NAS

## 📋 Anleitung zur Einrichtung

### 1. Stack in Portainer erstellen

1. **Portainer öffnen** → Ihr Ugreen NAS Portainer Interface
2. **Stacks** → **Add stack**
3. **Name eingeben:** `access-converter`
4. **Build method:** `Web editor`
5. **Stack-Inhalt:** Kopieren Sie den Inhalt aus `portainer-stack.yml`

### 2. Konfiguration

#### Port-Einstellungen
- **Standard:** Port `8080` (extern) → `8000` (intern)
- **Anpassung:** Ändern Sie `8080:8000` falls Port 8080 bereits belegt ist

#### Volume-Einstellungen
**Option A: Docker Volumes (empfohlen)**
```yaml
volumes:
  - access-converter-uploads:/app/data/uploads
  - access-converter-exports:/app/data/exports
  - access-converter-logs:/app/logs
```

**Option B: Host Bind Mounts (für direkten NAS-Zugriff)**
```yaml
volumes:
  - /volume1/docker/access-converter/uploads:/app/data/uploads
  - /volume1/docker/access-converter/exports:/app/data/exports
  - /volume1/docker/access-converter/logs:/app/logs
```

### 3. Umgebungsvariablen

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `LOG_LEVEL` | `INFO` | Logging-Level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_UPLOAD_SIZE` | `104857600` | Max. Upload-Größe in Bytes (100MB) |
| `MAX_CONCURRENT_JOBS` | `3` | Gleichzeitige Konvertierungen |
| `CLEANUP_INTERVAL_MINUTES` | `60` | Cleanup-Intervall in Minuten |

### 4. Deployment

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
