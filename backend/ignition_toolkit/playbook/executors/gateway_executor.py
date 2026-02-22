"""
Gateway step handlers

Handles all gateway operation step types using Strategy Pattern.
"""

import logging
from pathlib import Path
from typing import Any

from ignition_toolkit.core.timeouts import TimeoutDefaults
from ignition_toolkit.gateway import GatewayClient
from ignition_toolkit.playbook.executors.base import StepHandler
from ignition_toolkit.playbook.parameters import ParameterResolver

logger = logging.getLogger(__name__)


class GatewayLoginHandler(StepHandler):
    """Handle gateway.login step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        username = params.get("username")
        password = params.get("password")

        # Handle credential object
        if hasattr(password, "password"):
            password = password.password

        await self.client.login(username, password)
        return {"status": "logged_in"}


class GatewayLogoutHandler(StepHandler):
    """Handle gateway.logout step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        await self.client.logout()
        return {"status": "logged_out"}


class GatewayPingHandler(StepHandler):
    """Handle gateway.ping step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        result = await self.client.ping()
        return {"status": "ok", "response": result}


class GatewayGetInfoHandler(StepHandler):
    """Handle gateway.get_info step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        info = await self.client.get_info()
        return {"info": info.__dict__}


class GatewayGetHealthHandler(StepHandler):
    """Handle gateway.get_health step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        health = await self.client.get_health()
        return {"health": health.__dict__}


class GatewayListModulesHandler(StepHandler):
    """Handle gateway.list_modules step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        modules = await self.client.list_modules()
        return {"modules": [m.__dict__ for m in modules], "count": len(modules)}


class GatewayUploadModuleHandler(StepHandler):
    """Handle gateway.upload_module step"""

    def __init__(self, client: GatewayClient, resolver: ParameterResolver | None, base_path: Path):
        self.client = client
        self.resolver = resolver
        self.base_path = base_path

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        file_path = params.get("file")

        if self.resolver:
            file_path = self.resolver.resolve_file_path(file_path, self.base_path)
        else:
            file_path = Path(file_path)

        module_id = await self.client.upload_module(file_path)
        return {"module_id": module_id}


class GatewayWaitModuleHandler(StepHandler):
    """Handle gateway.wait_module step"""

    def __init__(self, client: GatewayClient, default_timeout: int = TimeoutDefaults.MODULE_INSTALL):
        self.client = client
        self.default_timeout = default_timeout

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        module_name = params.get("module_name")
        timeout = params.get("timeout", self.default_timeout)
        await self.client.wait_for_module_installation(module_name, timeout)
        return {"status": "installed", "module_name": module_name}


class GatewayListProjectsHandler(StepHandler):
    """Handle gateway.list_projects step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        projects = await self.client.list_projects()
        return {"projects": [p.__dict__ for p in projects], "count": len(projects)}


class GatewayGetProjectHandler(StepHandler):
    """Handle gateway.get_project step"""

    def __init__(self, client: GatewayClient):
        self.client = client

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        project_name = params.get("project_name")
        project = await self.client.get_project(project_name)
        return {"project": project.__dict__}


class GatewayRestartHandler(StepHandler):
    """Handle gateway.restart step"""

    def __init__(self, client: GatewayClient, default_timeout: int = TimeoutDefaults.GATEWAY_RESTART):
        self.client = client
        self.default_timeout = default_timeout

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        wait_for_ready = params.get("wait_for_ready", False)
        timeout = params.get("timeout", self.default_timeout)
        await self.client.restart(wait_for_ready=wait_for_ready, timeout=timeout)
        return {"status": "restarted"}


class GatewayWaitReadyHandler(StepHandler):
    """Handle gateway.wait_ready step"""

    def __init__(self, client: GatewayClient, default_timeout: int = TimeoutDefaults.GATEWAY_RESTART):
        self.client = client
        self.default_timeout = default_timeout

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        timeout = params.get("timeout", self.default_timeout)
        await self.client.wait_for_ready(timeout)
        return {"status": "ready"}
