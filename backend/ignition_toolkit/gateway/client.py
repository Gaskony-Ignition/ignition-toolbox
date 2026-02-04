"""
Async Ignition Gateway REST API client
"""

import asyncio
import logging
from pathlib import Path

import httpx

from ignition_toolkit.gateway.endpoints import GatewayEndpoints
from ignition_toolkit.gateway.exceptions import (
    AuthenticationError,
    GatewayConnectionError,
    ModuleInstallationError,
)
from ignition_toolkit.gateway.models import (
    GatewayInfo,
    HealthStatus,
    Module,
    ModuleState,
    Project,
)

logger = logging.getLogger(__name__)


class GatewayClient:
    """
    Async client for Ignition Gateway REST API operations

    Provides a clean, type-safe interface for common Gateway operations including:
    - Authentication and session management
    - Module installation and management
    - Project CRUD operations
    - Tag read/write operations
    - System operations (restart, backup, health checks)

    Example:
        async with GatewayClient("http://localhost:8088") as client:
            await client.login("admin", "password")
            modules = await client.list_modules()
            for module in modules:
                print(f"{module.name} - {module.version}")
    """

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize Gateway client

        Args:
            base_url: Gateway base URL (e.g., "http://localhost:8088")
            username: Gateway admin username (optional, can login later)
            password: Gateway admin password (optional, can login later)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout

        # HTTP client with cookie support for session management
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True,
        )

        self._authenticated = False

    async def __aenter__(self):
        """Async context manager entry"""
        if self.username and self.password:
            await self.login(self.username, self.password)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client connection"""
        await self.client.aclose()

    # Authentication

    async def login(self, username: str, password: str) -> bool:
        """
        Authenticate with Gateway

        Args:
            username: Gateway admin username
            password: Gateway admin password

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
            GatewayConnectionError: If unable to connect to Gateway
        """
        try:
            response = await self.client.post(
                GatewayEndpoints.LOGIN,
                data={
                    "username": username,
                    "password": password,
                },
            )

            if response.status_code == 200:
                self._authenticated = True
                self.username = username
                self.password = password
                logger.info(f"Successfully authenticated to Gateway at {self.base_url}")
                return True
            elif response.status_code == 401:
                raise AuthenticationError("Invalid username or password")
            else:
                raise AuthenticationError(f"Authentication failed: {response.status_code}")

        except httpx.ConnectError as e:
            raise GatewayConnectionError(f"Unable to connect to Gateway at {self.base_url}: {e}")
        except httpx.TimeoutException as e:
            raise GatewayConnectionError(f"Connection timeout: {e}")

    async def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated, re-authenticate if necessary"""
        if not self._authenticated:
            if self.username and self.password:
                await self.login(self.username, self.password)
            else:
                raise AuthenticationError("Not authenticated. Call login() first.")

    # System Information

    async def ping(self) -> bool:
        """
        Check if Gateway is reachable

        Returns:
            True if Gateway responds to status ping
        """
        try:
            response = await self.client.get(GatewayEndpoints.STATUS_PING)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def get_info(self) -> GatewayInfo:
        """
        Get Gateway system information

        Returns:
            GatewayInfo object with version, edition, etc.

        Raises:
            GatewayException: If unable to retrieve info
        """
        await self._ensure_authenticated()

        response = await self.client.get(GatewayEndpoints.GATEWAY_INFO)
        response.raise_for_status()

        data = response.json()
        return GatewayInfo(
            version=data.get("version", "unknown"),
            platform_version=data.get("platformVersion", "unknown"),
            edition=data.get("edition", "unknown"),
            license_key=data.get("licenseKey"),
        )

    async def get_health(self) -> HealthStatus:
        """
        Get Gateway health status

        Returns:
            HealthStatus object

        Raises:
            GatewayException: If unable to retrieve health status
        """
        await self._ensure_authenticated()

        # StatusPing is a simple health check
        ping_ok = await self.ping()

        # Get system info for uptime
        try:
            info = await self.get_info()
            return HealthStatus(
                healthy=ping_ok,
                uptime_seconds=0,  # Would need to parse from logs or system API
            )
        except Exception as e:
            logger.warning(f"Could not get full health info: {e}")
            return HealthStatus(healthy=ping_ok, uptime_seconds=0)

    # Module Operations

    async def list_modules(self) -> list[Module]:
        """
        List all installed modules

        Returns:
            List of Module objects

        Raises:
            GatewayException: If unable to list modules
        """
        await self._ensure_authenticated()

        response = await self.client.get(GatewayEndpoints.MODULES_LIST)
        response.raise_for_status()

        modules_data = response.json()
        modules = []

        for module_data in modules_data:
            modules.append(
                Module(
                    name=module_data.get("name", "unknown"),
                    version=module_data.get("version", "unknown"),
                    state=ModuleState(module_data.get("state", "unknown")),
                    description=module_data.get("description"),
                    license_required=module_data.get("licenseRequired", False),
                )
            )

        return modules

    async def upload_module(self, module_file_path: Path) -> str:
        """
        Upload a module file (.modl) to Gateway

        Args:
            module_file_path: Path to .modl file

        Returns:
            Module ID or name

        Raises:
            ModuleInstallationError: If upload fails
            FileNotFoundError: If module file doesn't exist
        """
        await self._ensure_authenticated()

        if not module_file_path.exists():
            raise FileNotFoundError(f"Module file not found: {module_file_path}")

        with open(module_file_path, "rb") as f:
            files = {"file": (module_file_path.name, f, "application/octet-stream")}

            response = await self.client.post(
                GatewayEndpoints.MODULE_UPLOAD,
                files=files,
            )

            if response.status_code != 200:
                raise ModuleInstallationError(f"Module upload failed: {response.text}")

            logger.info(f"Module uploaded: {module_file_path.name}")
            return response.json().get("moduleId", module_file_path.stem)

    async def wait_for_module_installation(
        self,
        module_name: str,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> bool:
        """
        Wait for module installation to complete

        Args:
            module_name: Module name to wait for
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            True if module installed successfully

        Raises:
            TimeoutError: If installation doesn't complete within timeout
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Check if task was cancelled (allows immediate exit on cancel)
            if asyncio.current_task().cancelled():
                logger.info(f"Module installation wait cancelled for '{module_name}'")
                raise asyncio.CancelledError()

            modules = await self.list_modules()

            for module in modules:
                if module.name == module_name:
                    if module.state == ModuleState.RUNNING:
                        logger.info(f"Module '{module_name}' is now running")
                        return True
                    elif module.state == ModuleState.FAILED:
                        raise ModuleInstallationError(f"Module '{module_name}' failed to install")

            # Use shorter sleep with cancellation check
            try:
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                logger.info(f"Module installation wait cancelled during sleep for '{module_name}'")
                raise

        raise TimeoutError(f"Module '{module_name}' installation timed out after {timeout}s")

    # Project Operations

    async def list_projects(self) -> list[Project]:
        """
        List all projects

        Returns:
            List of Project objects

        Raises:
            GatewayException: If unable to list projects
        """
        await self._ensure_authenticated()

        response = await self.client.get(GatewayEndpoints.PROJECTS_LIST)
        response.raise_for_status()

        projects_data = response.json()
        projects = []

        for project_data in projects_data:
            projects.append(
                Project(
                    name=project_data.get("name", "unknown"),
                    title=project_data.get("title", project_data.get("name", "unknown")),
                    enabled=project_data.get("enabled", False),
                    description=project_data.get("description"),
                    parent=project_data.get("parent"),
                    version=project_data.get("version"),
                )
            )

        return projects

    async def get_project(self, project_name: str) -> Project | None:
        """
        Get project details

        Args:
            project_name: Project name

        Returns:
            Project object or None if not found
        """
        await self._ensure_authenticated()

        endpoint = GatewayEndpoints.PROJECT_GET.format(project_name=project_name)
        response = await self.client.get(endpoint)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        project_data = response.json()

        return Project(
            name=project_data.get("name", project_name),
            title=project_data.get("title", project_name),
            enabled=project_data.get("enabled", False),
            description=project_data.get("description"),
            parent=project_data.get("parent"),
            version=project_data.get("version"),
        )

    # System Operations

    async def restart(self, wait_for_ready: bool = True, timeout: int = 120) -> bool:
        """
        Restart Gateway

        Args:
            wait_for_ready: Wait for Gateway to come back online
            timeout: Maximum wait time in seconds

        Returns:
            True if restart successful

        Raises:
            GatewayRestartError: If restart fails
        """
        await self._ensure_authenticated()

        logger.info("Initiating Gateway restart...")

        try:
            await self.client.post(GatewayEndpoints.RESTART)
        except Exception as e:
            # Gateway may close connection during restart
            logger.debug(f"Expected connection error during restart: {e}")

        if wait_for_ready:
            logger.info(f"Waiting for Gateway to come back online (timeout: {timeout}s)...")
            return await self.wait_for_ready(timeout)

        return True

    async def wait_for_ready(self, timeout: int = 120, poll_interval: int = 5) -> bool:
        """
        Wait for Gateway to be ready (after restart or startup)

        Args:
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            True if Gateway becomes ready

        Raises:
            TimeoutError: If Gateway doesn't become ready within timeout
        """
        start_time = asyncio.get_event_loop().time()

        # Wait a few seconds for Gateway to start shutting down
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.info("Gateway restart wait cancelled during initial delay")
            raise

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Check if task was cancelled (allows immediate exit on cancel)
            if asyncio.current_task().cancelled():
                logger.info("Gateway ready wait cancelled")
                raise asyncio.CancelledError()

            if await self.ping():
                logger.info("Gateway is ready")

                # Re-authenticate after restart
                if self.username and self.password:
                    try:
                        await asyncio.sleep(5)  # Give Gateway a few more seconds
                    except asyncio.CancelledError:
                        logger.info("Gateway restart wait cancelled during re-auth delay")
                        raise
                    try:
                        await self.login(self.username, self.password)
                        return True
                    except (httpx.HTTPError, AuthenticationError):
                        # May still be initializing
                        pass

            # Use shorter sleep with cancellation check
            try:
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                logger.info("Gateway ready wait cancelled during sleep")
                raise

        raise TimeoutError(f"Gateway did not become ready within {timeout}s")
