#!/usr/bin/env python3
"""
Ignition Gateway Database Auto-Registration Script
Automatically configures database connections in Ignition Gateway
"""
import requests
import time
import sys
from urllib.parse import urljoin

# Configuration
GATEWAY_URL = "http://ignition-primary:8088"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"

# Database configurations
DATABASES = [
    {
        "name": "MARIADB-mariadb",
        "jdbc_url": "jdbc:mysql://mariadb:3306/mysql",
        "driver": "com.mysql.cj.jdbc.Driver",
        "username": "root",
        "password": "password",
        "validation_query": "SELECT 1"
    }
]

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


def log_info(message):
    print(f"{BLUE}[INFO]{RESET} {message}")


def log_success(message):
    print(f"{GREEN}[SUCCESS]{RESET} {message}")


def log_warning(message):
    print(f"{YELLOW}[WARNING]{RESET} {message}")


def log_error(message):
    print(f"{RED}[ERROR]{RESET} {message}")


def wait_for_gateway(max_wait=300):
    """Wait for Ignition Gateway to be ready"""
    log_info(f"Waiting for Ignition Gateway at {GATEWAY_URL}...")

    start_time = time.time()
    while (time.time() - start_time) < max_wait:
        try:
            response = requests.get(
                urljoin(GATEWAY_URL, "/StatusPing"),
                timeout=5
            )
            if response.status_code == 200:
                log_success("Ignition Gateway is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        time.sleep(5)
        elapsed = int(time.time() - start_time)
        log_info(f"Still waiting... ({elapsed}s/{max_wait}s)")

    log_error("Gateway did not become ready in time")
    return False


def get_gateway_session():
    """Create an authenticated session with the Gateway"""
    session = requests.Session()
    login_url = urljoin(GATEWAY_URL, "/data/login")

    try:
        response = session.post(
            login_url,
            json={
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            },
            timeout=10
        )

        if response.status_code == 200:
            log_success("Successfully authenticated with Gateway")
            return session
        else:
            log_error(f"Authentication failed: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        log_error(f"Failed to authenticate: {e}")
        return None


def check_connection_exists(session, connection_name):
    """Check if a database connection already exists"""
    try:
        response = session.get(
            urljoin(GATEWAY_URL, "/data/db-connections"),
            timeout=10
        )

        if response.status_code == 200:
            connections = response.json()
            return any(conn.get("name") == connection_name for conn in connections)

    except Exception as e:
        log_warning(f"Could not check existing connections: {e}")

    return False


def create_database_connection(session, db_config):
    """Create a database connection in Ignition"""
    connection_name = db_config["name"]

    log_info(f"Creating database connection: {connection_name}")

    if check_connection_exists(session, connection_name):
        log_warning(f"Connection '{connection_name}' already exists, skipping")
        return True

    payload = {
        "name": connection_name,
        "description": f"Auto-configured connection to {connection_name}",
        "enabled": True,
        "jdbcUrl": db_config["jdbc_url"],
        "driverClassName": db_config["driver"],
        "username": db_config["username"],
        "password": db_config["password"],
        "validationQuery": db_config["validation_query"],
        "maxConnections": 8,
        "maxIdleConnections": 3,
        "maxIdleTime": 600000,
        "maxConnectionAge": 0,
        "maxQueryTime": 0,
        "testConnOnBorrow": True,
        "testConnOnReturn": False,
        "testConnWhileIdle": True,
        "idleConnectionTestPeriod": 60000,
    }

    try:
        response = session.post(
            urljoin(GATEWAY_URL, "/data/db-connections"),
            json=payload,
            timeout=30
        )

        if response.status_code in [200, 201]:
            log_success(f"Created connection: {connection_name}")
            return True
        else:
            log_error(f"Failed to create connection: {response.status_code}")
            log_error(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        log_error(f"Exception creating connection: {e}")
        return False


def main():
    """Main execution function"""
    print("=" * 60)
    print("Ignition Database Auto-Registration")
    print("=" * 60)
    print()

    if not wait_for_gateway():
        log_error("Exiting: Gateway not ready")
        sys.exit(1)

    session = get_gateway_session()
    if not session:
        log_error("Exiting: Could not authenticate")
        sys.exit(1)

    print()
    log_info(f"Configuring {len(DATABASES)} database connection(s)...")
    print()

    success_count = 0
    failed_count = 0

    for db_config in DATABASES:
        if create_database_connection(session, db_config):
            success_count += 1
        else:
            failed_count += 1
        print()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    log_success(f"Successfully configured: {success_count}")
    if failed_count > 0:
        log_error(f"Failed: {failed_count}")

    print()
    log_info("Database auto-registration complete!")
    print()
    print("Next steps:")
    print(f"  1. Open Ignition Gateway: {GATEWAY_URL}")
    print("  2. Go to Config -> Databases -> Connections")
    print("  3. Verify connections are listed and enabled")
    print()

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
