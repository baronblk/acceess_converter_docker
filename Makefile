# Access Database Converter - Docker Build and Run

.PHONY: help build run dev stop clean logs test

# Default target
help:
	@echo "Access Database Converter v2.0"
	@echo ""
	@echo "Available targets:"
	@echo "  build     - Build Docker image"
	@echo "  run       - Run container"
	@echo "  dev       - Run in development mode with auto-reload"
	@echo "  stop      - Stop running container"
	@echo "  clean     - Clean up containers and images"
	@echo "  logs      - Show container logs"
	@echo "  test      - Run tests"
	@echo "  shell     - Open shell in running container"

# Build Docker image
build:
	@echo "Building Access Database Converter..."
	docker build -f docker/Dockerfile -t access-converter:latest .
	@echo "Build complete!"

# Run container
run:
	@echo "Starting Access Database Converter..."
	docker run -d \
		--name access-converter \
		-p 8000:8000 \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/exports:/app/exports \
		-v $(PWD)/logs:/app/logs \
		--restart unless-stopped \
		access-converter:latest
	@echo "Container started at http://localhost:8000"

# Development mode
dev:
	@echo "Starting development server..."
	docker run -it --rm \
		--name access-converter-dev \
		-p 8000:8000 \
		-v $(PWD)/app:/app/app \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/exports:/app/exports \
		-v $(PWD)/logs:/app/logs \
		-e DEBUG=true \
		access-converter:latest \
		python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
	@echo "Development server started at http://localhost:8000"

# Stop container
stop:
	@echo "Stopping Access Database Converter..."
	-docker stop access-converter
	-docker rm access-converter
	@echo "Container stopped"

# Clean up
clean: stop
	@echo "Cleaning up Docker resources..."
	-docker rmi access-converter:latest
	-docker system prune -f
	@echo "Cleanup complete"

# Show logs
logs:
	docker logs -f access-converter

# Run tests
test:
	@echo "Running tests..."
	docker run --rm \
		-v $(PWD)/app:/app/app \
		access-converter:latest \
		python -m pytest app/tests/ -v
	@echo "Tests complete"

# Open shell in container
shell:
	docker exec -it access-converter /bin/bash

# Quick restart
restart: stop run

# Check container status
status:
	@echo "Container status:"
	docker ps -a --filter name=access-converter

# Create required directories
init:
	@echo "Creating required directories..."
	mkdir -p uploads exports logs
	@echo "Directories created"

# Setup development environment
setup: init build
	@echo "Development environment ready!"
	@echo "Run 'make dev' to start development server"
	@echo "Run 'make run' to start production container"
