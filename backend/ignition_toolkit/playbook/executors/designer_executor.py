"""
Designer step handlers

Handles all Designer desktop application step types using Strategy Pattern.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ignition_toolkit.designer import DesignerManager
from ignition_toolkit.playbook.exceptions import StepExecutionError
from ignition_toolkit.playbook.executors.base import StepHandler

logger = logging.getLogger(__name__)


class DesignerLaunchHandler(StepHandler):
    """Handle designer.launch step (file-based launch)"""

    def __init__(self, manager: DesignerManager):
        self.manager = manager

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        launcher_file = params.get("launcher_file")
        if not launcher_file:
            raise StepExecutionError("designer", "launcher_file parameter is required")

        launcher_path = Path(launcher_file)
        success = await self.manager.launch_via_file(launcher_path)

        if not success:
            raise StepExecutionError("designer", "Failed to launch Designer")

        return {"status": "launched", "launcher_file": str(launcher_path)}


class DesignerLaunchShortcutHandler(StepHandler):
    """Handle designer.launch_shortcut step (WSL/PowerShell-based launch)"""

    def __init__(self, manager: DesignerManager):
        self.manager = manager

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        designer_shortcut = params.get("designer_shortcut")
        project_name = params.get("project_name")
        username = params.get("username")
        password = params.get("password")
        gateway_credential = params.get("gateway_credential")

        # DEBUG logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DESIGNER HANDLER] Received params: {list(params.keys())}")
        logger.info(f"[DESIGNER HANDLER] gateway_credential type: {type(gateway_credential)}, value: {gateway_credential}")
        logger.info(f"[DESIGNER HANDLER] username: {username}, password: {'***' if password else None}")

        # Validate required parameters
        if not designer_shortcut:
            raise StepExecutionError("designer", "designer_shortcut parameter is required")
        if not project_name:
            raise StepExecutionError("designer", "project_name parameter is required")

        # Handle credential object (preferred method - single credential parameter)
        if gateway_credential:
            # Extract username and password from credential object
            if hasattr(gateway_credential, "username"):
                username = gateway_credential.username
            if hasattr(gateway_credential, "password"):
                password = gateway_credential.password

        # Fallback: handle separate username/password parameters (for backward compatibility)
        if not username or not password:
            if not username:
                raise StepExecutionError("designer", "username parameter or gateway_credential is required")
            if not password:
                raise StepExecutionError("designer", "password parameter or gateway_credential is required")

        # Handle credential object passed as password parameter (legacy compatibility)
        if hasattr(password, "password"):
            password = password.password
        if hasattr(username, "username"):
            username = username.username

        timeout = params.get("timeout", 60)
        success = await self.manager.launch_with_shortcut(
            designer_shortcut=designer_shortcut,
            username=username,
            password=password,
            project_name=project_name,
            timeout=timeout
        )

        if not success:
            raise StepExecutionError("designer", "Failed to launch Designer with shortcut")

        return {
            "status": "launched_and_opened",
            "project": project_name,
            "username": username
        }


class DesignerLoginHandler(StepHandler):
    """Handle designer.login step"""

    def __init__(self, manager: DesignerManager):
        self.manager = manager

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        username = params.get("username")
        password = params.get("password")

        # Handle credential object
        if hasattr(password, "password"):
            password = password.password

        timeout = params.get("timeout", 30)
        success = await self.manager.login(username, password, timeout=timeout)

        if not success:
            raise StepExecutionError("designer", "Designer login failed")

        return {"status": "logged_in", "username": username}


class DesignerOpenProjectHandler(StepHandler):
    """Handle designer.open_project step"""

    def __init__(self, manager: DesignerManager):
        self.manager = manager

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        project_name = params.get("project_name")
        if not project_name:
            # No project specified - stop here for manual selection
            logger.info("No project_name specified - waiting for manual project selection")
            return {"status": "awaiting_manual_selection"}

        timeout = params.get("timeout", 30)
        success = await self.manager.open_project(project_name, timeout=timeout)

        if not success:
            raise StepExecutionError("designer", f"Failed to open project: {project_name}")

        return {"status": "project_opened", "project": project_name}


class DesignerCloseHandler(StepHandler):
    """Handle designer.close step"""

    def __init__(self, manager: DesignerManager):
        self.manager = manager

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        success = await self.manager.close()

        if not success:
            raise StepExecutionError("designer", "Failed to close Designer")

        return {"status": "closed"}


class DesignerScreenshotHandler(StepHandler):
    """Handle designer.screenshot step"""

    def __init__(self, manager: DesignerManager):
        self.manager = manager

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", f"designer_screenshot_{datetime.now().timestamp()}")
        screenshot_path = await self.manager.screenshot(name)
        return {"screenshot": str(screenshot_path), "status": "captured"}


class DesignerWaitHandler(StepHandler):
    """Handle designer.wait step"""

    def __init__(self, manager: DesignerManager):
        self.manager = manager

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        timeout = params.get("timeout", 30)
        success = await self.manager.wait_for_window(timeout=timeout)

        if not success:
            raise StepExecutionError("designer", "Designer window did not appear")

        return {"status": "window_found"}
