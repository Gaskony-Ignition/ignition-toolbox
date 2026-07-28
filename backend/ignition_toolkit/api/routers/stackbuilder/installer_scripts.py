"""
Docker installer scripts for Linux and Windows.

These are shell/PowerShell scripts that users can download to install Docker
on their systems.
"""

DOCKER_INSTALL_LINUX = """#!/bin/bash
# Docker Installation Script for Linux
# Supports: Ubuntu, Debian, CentOS, RHEL, Fedora, Arch

set -e

echo "=========================================="
echo "     Docker Installation Script"
echo "=========================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "Cannot detect OS. Please install Docker manually."
    exit 1
fi

echo "Detected OS: $OS $VERSION"
echo ""

install_docker_debian() {
    echo "Installing Docker on Debian/Ubuntu..."

    # Remove old versions
    sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Install dependencies
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # Add Docker GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_rhel() {
    echo "Installing Docker on RHEL/CentOS/Fedora..."

    # Remove old versions
    sudo yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true

    # Install dependencies
    sudo yum install -y yum-utils

    # Set up repository
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

    # Install Docker
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_docker_arch() {
    echo "Installing Docker on Arch Linux..."
    sudo pacman -Sy docker docker-compose --noconfirm
}

# Install based on OS
case $OS in
    ubuntu|debian)
        install_docker_debian
        ;;
    centos|rhel|fedora)
        install_docker_rhel
        ;;
    arch)
        install_docker_arch
        ;;
    *)
        echo "Unsupported OS: $OS"
        echo "Please install Docker manually from https://docs.docker.com/engine/install/"
        exit 1
        ;;
esac

# Start Docker service
echo ""
echo "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group
echo "Adding $USER to docker group..."
sudo usermod -aG docker $USER

echo ""
echo "=========================================="
echo "     Docker Installation Complete!"
echo "=========================================="
echo ""
echo "Please log out and back in for group changes to take effect."
echo ""
echo "Verify installation:"
echo "  docker --version"
echo "  docker compose version"
echo ""
"""

DOCKER_INSTALL_WINDOWS = """# Docker Desktop Installation Script for Windows
# Run in PowerShell as Administrator

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "     Docker Desktop Installation Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check Windows version
$osInfo = Get-WmiObject -Class Win32_OperatingSystem
$osVersion = [System.Version]$osInfo.Version
if ($osVersion.Major -lt 10) {
    Write-Host "ERROR: Docker Desktop requires Windows 10 or later" -ForegroundColor Red
    exit 1
}

Write-Host "Detected: $($osInfo.Caption)" -ForegroundColor Green
Write-Host ""

# Check if Docker is already installed
$dockerPath = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerPath) {
    Write-Host "Docker is already installed at: $($dockerPath.Source)" -ForegroundColor Yellow
    docker --version
    Write-Host ""
    $continue = Read-Host "Continue with reinstallation? (y/n)"
    if ($continue -ne "y") {
        exit 0
    }
}

# Enable WSL2
Write-Host "Enabling Windows Subsystem for Linux..." -ForegroundColor Cyan
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Write-Host "Enabling Virtual Machine Platform..." -ForegroundColor Cyan
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Download Docker Desktop installer
$installerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installerPath = "$env:TEMP\\DockerDesktopInstaller.exe"

Write-Host ""
Write-Host "Downloading Docker Desktop installer..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing

# Install Docker Desktop
Write-Host "Installing Docker Desktop..." -ForegroundColor Cyan
Start-Process -FilePath $installerPath -ArgumentList "install --quiet --accept-license" -Wait

# Clean up
Remove-Item $installerPath -Force

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "     Docker Desktop Installation Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Please restart your computer to complete the installation." -ForegroundColor Yellow
Write-Host ""
Write-Host "After restart:" -ForegroundColor Cyan
Write-Host "  1. Launch Docker Desktop from the Start menu"
Write-Host "  2. Complete the initial setup wizard"
Write-Host "  3. Verify installation: docker --version"
Write-Host ""
"""
