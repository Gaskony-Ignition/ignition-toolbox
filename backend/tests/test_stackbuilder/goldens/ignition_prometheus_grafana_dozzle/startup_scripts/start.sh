#!/bin/bash
# Ignition Stack Startup Script
# Handles proper initialization of Ignition data volumes

echo "Starting iiot-stack..."

# Start all services
docker compose up -d

echo ""
echo "Stack started successfully!"
echo "Access Ignition Gateway at http://localhost:8088"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop: docker compose down"
