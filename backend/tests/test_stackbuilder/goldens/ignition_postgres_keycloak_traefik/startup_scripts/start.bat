@echo off
REM Ignition Stack Startup Script
REM Handles proper initialization of Ignition data volumes

echo Starting iiot-stack...

docker compose up -d

echo.
echo Stack started successfully!
echo Access Ignition Gateway at http://localhost:8088
echo.
echo To view logs: docker compose logs -f
echo To stop: docker compose down
