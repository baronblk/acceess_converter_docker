# === PORTAINER STACK KONFIGURATIONEN ===
# Verschiedene vorkonfigurierte Setups für unterschiedliche NAS-Umgebungen

## 🏠 KLEINE NAS (1-2 TB, 2-4 GB RAM)
# Optimiert für begrenzte Ressourcen
version: '3.8'
services:
  access-converter:
    image: ghcr.io/baronblk/access-converter:latest
    container_name: access-converter
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - access-converter-uploads:/app/data/uploads
      - access-converter-exports:/app/data/exports
      - access-converter-logs:/app/logs
    environment:
      - LOG_LEVEL=INFO
      - MAX_UPLOAD_SIZE=52428800           # 50MB
      - MAX_CONCURRENT_JOBS=1              # Ein Job gleichzeitig
      - CLEANUP_INTERVAL_MINUTES=30        # Häufigere Bereinigung
      - MAX_TABLES_PER_DB=50              # Weniger Tabellen pro DB
      - TEMP_DIR_SIZE_LIMIT=536870912     # 512MB Temp-Limit
      - WORKER_TIMEOUT=180                # 3 Minuten Timeout

volumes:
  access-converter-uploads:
  access-converter-exports:
  access-converter-logs:

---

## 🏢 MITTLERE NAS (4-8 TB, 8+ GB RAM)
# Ausgewogene Konfiguration für Standard-NAS
version: '3.8'
services:
  access-converter:
    image: ghcr.io/baronblk/access-converter:latest
    container_name: access-converter
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - access-converter-uploads:/app/data/uploads
      - access-converter-exports:/app/data/exports
      - access-converter-logs:/app/logs
    environment:
      - LOG_LEVEL=INFO
      - MAX_UPLOAD_SIZE=209715200          # 200MB
      - MAX_CONCURRENT_JOBS=3              # Drei Jobs gleichzeitig
      - CLEANUP_INTERVAL_MINUTES=60        # Standard Bereinigung
      - MAX_TABLES_PER_DB=100             # Standard Tabellen-Limit
      - TEMP_DIR_SIZE_LIMIT=1073741824    # 1GB Temp-Limit
      - WORKER_TIMEOUT=300                # 5 Minuten Timeout

volumes:
  access-converter-uploads:
  access-converter-exports:
  access-converter-logs:

---

## 🏭 GROSSE NAS / SERVER (16+ TB, 16+ GB RAM)
# Maximale Performance für Server-Umgebungen
version: '3.8'
services:
  access-converter:
    image: ghcr.io/baronblk/access-converter:latest
    container_name: access-converter
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      # Host-Bind-Mounts für bessere Performance
      - /volume1/docker/access-converter/uploads:/app/data/uploads
      - /volume1/docker/access-converter/exports:/app/data/exports
      - /volume1/docker/access-converter/logs:/app/logs
    environment:
      - LOG_LEVEL=INFO
      - MAX_UPLOAD_SIZE=1073741824         # 1GB
      - MAX_CONCURRENT_JOBS=5              # Fünf Jobs gleichzeitig
      - CLEANUP_INTERVAL_MINUTES=120       # Weniger häufige Bereinigung
      - MAX_TABLES_PER_DB=200             # Mehr Tabellen pro DB
      - TEMP_DIR_SIZE_LIMIT=5368709120    # 5GB Temp-Limit
      - WORKER_TIMEOUT=600                # 10 Minuten Timeout

# Hinweis: Stellen Sie sicher, dass die Host-Pfade existieren:
# mkdir -p /volume1/docker/access-converter/{uploads,exports,logs}
# chown -R 1000:1000 /volume1/docker/access-converter

---

## 🔧 ENTWICKLUNG / DEBUG
# Für Entwicklung und Fehlerbehebung
version: '3.8'
services:
  access-converter:
    image: ghcr.io/baronblk/access-converter:latest
    container_name: access-converter-dev
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - access-converter-uploads:/app/data/uploads
      - access-converter-exports:/app/data/exports
      - access-converter-logs:/app/logs
    environment:
      - LOG_LEVEL=DEBUG                   # Verbose Logging
      - MAX_UPLOAD_SIZE=104857600         # 100MB
      - MAX_CONCURRENT_JOBS=2             # Moderate Parallelität
      - CLEANUP_INTERVAL_MINUTES=15       # Schnelle Bereinigung
      - MAX_TABLES_PER_DB=100
      - TEMP_DIR_SIZE_LIMIT=1073741824
      - WORKER_TIMEOUT=600                # Längere Timeouts für Debug

volumes:
  access-converter-uploads:
  access-converter-exports:
  access-converter-logs:

---

## 📊 HOCHVOLUMEN-VERARBEITUNG
# Für häufige, große Konvertierungen
version: '3.8'
services:
  access-converter:
    image: ghcr.io/baronblk/access-converter:latest
    container_name: access-converter-hv
    restart: unless-stopped
    ports:
      - "8080:8000"
    volumes:
      - /volume1/docker/access-converter/uploads:/app/data/uploads
      - /volume1/docker/access-converter/exports:/app/data/exports
      - /volume1/docker/access-converter/logs:/app/logs
    environment:
      - LOG_LEVEL=WARNING                 # Weniger Logs für Performance
      - MAX_UPLOAD_SIZE=2147483648        # 2GB
      - MAX_CONCURRENT_JOBS=8             # Maximale Parallelität
      - CLEANUP_INTERVAL_MINUTES=180      # Seltene Bereinigung
      - MAX_TABLES_PER_DB=500            # Viele Tabellen
      - TEMP_DIR_SIZE_LIMIT=10737418240  # 10GB Temp-Limit
      - WORKER_TIMEOUT=1800              # 30 Minuten Timeout

# WARNUNG: Benötigt mindestens 32GB RAM und schnelle SSDs

---

## 💡 ANPASSUNGSHINWEISE

### CPU-Kerne bestimmen:
```bash
# In Portainer Terminal oder SSH:
nproc
# Empfehlung: MAX_CONCURRENT_JOBS = CPU-Kerne / 2
```

### RAM-Verbrauch schätzen:
```bash
# Pro gleichzeitiger Job ca. 200-500MB RAM
# Bei MAX_CONCURRENT_JOBS=3: ca. 1.5GB RAM needed
# Plus OS und andere Container
```

### Storage-Requirements:
```bash
# Temp-Space: TEMP_DIR_SIZE_LIMIT
# Uploads: Temporär, MAX_UPLOAD_SIZE * MAX_CONCURRENT_JOBS
# Exports: Permanent, je nach Nutzung
```

### Port-Konflikte lösen:
```yaml
# Anderen Port verwenden:
ports:
  - "8081:8000"  # Statt 8080
```
