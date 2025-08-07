# Backend Dockerfile for Access Database Converter
FROM python:3.11-slim

# Install system dependencies including OpenJDK
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Create ucanaccess directory and download JARs
RUN mkdir -p /opt/ucanaccess
WORKDIR /opt/ucanaccess

# Download UCanAccess JARs
RUN wget -q https://github.com/spannm/ucanaccess/releases/download/v5.0.1/ucanaccess-5.0.1-bin.zip \
    && unzip ucanaccess-5.0.1-bin.zip \
    && mv ucanaccess-5.0.1/* . \
    && rm -rf ucanaccess-5.0.1 ucanaccess-5.0.1-bin.zip

# Set working directory for the application
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/uploads /app/data/exports /app/data/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV UCANACCESS_PATH=/opt/ucanaccess
ENV APP_ENV=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
