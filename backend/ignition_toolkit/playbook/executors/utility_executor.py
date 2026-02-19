"""
Utility step handlers

Handles all utility step types using Strategy Pattern.
"""

import asyncio
import io
import logging
from contextlib import redirect_stdout
from typing import Any

from ignition_toolkit.playbook.cancellation import cancellable_sleep
from ignition_toolkit.playbook.exceptions import StepExecutionError
from ignition_toolkit.playbook.executors.base import StepHandler

logger = logging.getLogger(__name__)


class UtilitySleepHandler(StepHandler):
    """
    Handle utility.sleep step with cancellation support

    Uses cancellable_sleep which checks for cancellation every 0.5 seconds,
    ensuring responsive cancellation even during long sleep periods.
    """

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert to float in case it comes as string from parameter resolution
        seconds_param = params.get("seconds", 1)
        seconds = float(seconds_param) if isinstance(seconds_param, (str, int, float)) else 1.0

        logger.info(f"Sleeping for {seconds} seconds (cancellable)")
        await cancellable_sleep(seconds)
        logger.debug(f"Sleep completed ({seconds}s)")
        return {"slept": seconds}


class UtilityLogHandler(StepHandler):
    """Handle utility.log step"""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        message = params.get("message", "")
        level = params.get("level", "info").lower()

        if level == "debug":
            logger.debug(message)
        elif level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)

        return {"logged": message, "level": level}


class UtilitySetVariableHandler(StepHandler):
    """Handle utility.set_variable step"""

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        value = params.get("value")

        if not name:
            raise StepExecutionError("utility", "Variable name is required")

        # Variable will be set by the engine
        return {"variable": name, "value": value}


class UtilityPythonHandler(StepHandler):
    """
    Handle utility.python step for playbook automation

    This handler provides full Python access for playbook scripts including:
    - Standard library imports (zipfile, pathlib, subprocess, os, etc.)
    - File system access for module installation/upgrade workflows
    - Process execution for Designer automation
    - XML/JSON parsing for module metadata extraction
    - HTTP requests for gateway polling

    SECURITY MODEL: Trust-based. Only run playbooks from trusted sources.
    The handler does NOT sandbox execution — playbooks have the same
    access as the backend process itself.
    """

    def __init__(self, parameter_resolver=None, timeout_overrides=None):
        """Initialize handler with optional parameter resolver for variable access"""
        self.parameter_resolver = parameter_resolver
        self.timeout_overrides = timeout_overrides or {}

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        script = params.get("script")
        if not script:
            raise StepExecutionError("utility", "Python script is required")

        # Execute in thread pool to avoid blocking event loop
        def _run_script():
            output_buffer = io.StringIO()
            result = {}

            try:
                # Get variable storage from parameter resolver
                variables_dict = {}
                if self.parameter_resolver:
                    variables_dict = self.parameter_resolver.variables

                # Define set_variable and get_variable functions
                def set_variable(name: str, value: Any) -> None:
                    """Store a variable for use in later steps"""
                    variables_dict[name] = value

                def get_variable(name: str, default: Any = None) -> Any:
                    """Retrieve a previously stored variable"""
                    return variables_dict.get(name, default)

                # Create execution environment with full builtins
                # and commonly-used modules pre-injected for convenience
                exec_globals = {
                    "__builtins__": __builtins__,
                    "Path": __import__("pathlib").Path,
                    "zipfile": __import__("zipfile"),
                    "ET": __import__("xml.etree.ElementTree"),
                    "json": __import__("json"),
                    "time": __import__("time"),
                    "set_variable": set_variable,
                    "get_variable": get_variable,
                    "timeout_overrides": self.timeout_overrides,
                }

                # Redirect stdout to capture print() statements
                with redirect_stdout(output_buffer):
                    exec(script, exec_globals)

                # Parse output for key=value pairs (e.g., DETECTED_MODULE_FILE=/path/to/file)
                output = output_buffer.getvalue()
                for line in output.strip().split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        result[key.strip()] = value.strip()

                # Also include raw output
                result["_output"] = output

                return result

            except Exception as e:
                raise StepExecutionError("utility.python", f"Script execution failed: {str(e)}")

        # Run in thread pool to avoid blocking event loop (v3.45.7 bug fix)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run_script)
