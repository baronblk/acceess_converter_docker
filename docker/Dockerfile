# Access Database Converter v2.2.1
# Copyright © 2025 GCNG Software - Rene Süß
#
# Lizenziert unter der Business Source License 1.1
# Nicht-kommerzielle Nutzung gestattet.
# Kommerzielle Nutzung nur mit schriftlicher Genehmigung.
#
# Diese Software wird automatisch am 09. August 2030 unter MIT-Lizenz freigegeben.
#
# Vollständige Lizenz: siehe LICENSE-Datei im Projektverzeichnis
# Kontakt für kommerzielle Lizenz: baronblk@googlemail.com

# Multi-stage build for Access Database Converter
FROM python:3.11-slim

# Build arguments for versioning
ARG VERSION=2.2.1
ARG BUILD_DATE
ARG VCS_REF

# OCI Image Labels (https://github.com/opencontainers/image-spec)
LABEL org.opencontainers.image.title="Access Database Converter" \
      org.opencontainers.image.description="Convert Access databases (.mdb/.accdb) to CSV, XLSX, JSON, PDF" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/baronblk/acceess_converter_docker" \
      org.opencontainers.image.vendor="GCNG Software - Rene Süß" \
      org.opencontainers.image.licenses="BSL-1.1"

# Install system dependencies (Java JRE + Tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# UCanAccess Version
ARG UCANACCESS_VERSION=5.0.1

# Download and setup UCanAccess with robust error handling
WORKDIR /opt/ucanaccess
RUN set -eux; \
    echo "=== Downloading UCanAccess ${UCANACCESS_VERSION} ===" && \
    # Try SourceForge primary
    curl -fL --retry 5 --retry-delay 2 -o ucanaccess.zip \
        "https://downloads.sourceforge.net/project/ucanaccess/UCanAccess-${UCANACCESS_VERSION}/ucanaccess-${UCANACCESS_VERSION}.zip" \
    || \
    # Fallback to mirror
    curl -fL --retry 5 --retry-delay 2 -o ucanaccess.zip \
        "https://sourceforge.net/projects/ucanaccess/files/UCanAccess-${UCANACCESS_VERSION}/ucanaccess-${UCANACCESS_VERSION}.zip/download" \
    || \
    # Emergency fallback - Maven Central individual JARs
    (echo "SourceForge failed, using Maven Central..." && \
     mkdir -p lib && cd lib && \
     curl -fL --retry 3 -o ucanaccess-${UCANACCESS_VERSION}.jar \
        "https://repo1.maven.org/maven2/net/sf/ucanaccess/ucanaccess/${UCANACCESS_VERSION}/ucanaccess-${UCANACCESS_VERSION}.jar" && \
     curl -fL --retry 3 -o commons-logging-1.2.jar \
        "https://repo1.maven.org/maven2/commons-logging/commons-logging/1.2/commons-logging-1.2.jar" && \
     curl -fL --retry 3 -o commons-lang3-3.12.0.jar \
        "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar" && \
     curl -fL --retry 3 -o hsqldb-2.7.1.jar \
        "https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.1/hsqldb-2.7.1.jar" && \
     curl -fL --retry 3 -o jackcess-4.0.4.jar \
        "https://repo1.maven.org/maven2/com/healthmarketscience/jackcess/jackcess/4.0.4/jackcess-4.0.4.jar" && \
     curl -fL --retry 3 -o jackcess-encrypt-4.0.2.jar \
        "https://repo1.maven.org/maven2/com/healthmarketscience/jackcess/jackcess-encrypt/4.0.2/jackcess-encrypt-4.0.2.jar" && \
     cd .. && touch ucanaccess.zip); \
    \
    # Extract if we got a ZIP file
    if [ -s ucanaccess.zip ] && [ "$(file ucanaccess.zip | grep -c ZIP)" -gt 0 ]; then \
        echo "=== Extracting UCanAccess archive ===" && \
        unzip -q ucanaccess.zip && \
        rm ucanaccess.zip && \
        # Find the actual directory (might be UCanAccess-5.0.1 or similar)
        UCAN_DIR=$(find . -maxdepth 1 -name "*[Uu][Cc]an[Aa]ccess*" -type d | head -1) && \
        if [ -n "$UCAN_DIR" ]; then \
            mv "$UCAN_DIR"/* . && rmdir "$UCAN_DIR" 2>/dev/null || true; \
        fi; \
    fi; \
    \
    # Verify required JARs exist
    echo "=== Verifying UCanAccess installation ===" && \
    ls -la && \
    REQUIRED_JARS="ucanaccess commons-logging hsqldb jackcess" && \
    for jar in $REQUIRED_JARS; do \
        find . -name "*${jar}*.jar" -type f | head -1 | grep -q jar || \
        (echo "ERROR: Missing required JAR: $jar" && exit 1); \
    done && \
    echo "=== UCanAccess installation verified ==="

# Set Java classpath for UCanAccess
ENV CLASSPATH="/opt/ucanaccess:/opt/ucanaccess/lib:/opt/ucanaccess/*:/opt/ucanaccess/lib/*"

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create necessary directories
# Create application directories
RUN mkdir -p /app/data/uploads /app/data/exports /app/logs

# Set permissions
RUN chmod +x /app/app/main.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with controlled logging and proxy headers support
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "--forwarded-allow-ips", "*", "--proxy-headers"]
