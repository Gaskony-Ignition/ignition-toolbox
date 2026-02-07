"""
Utility step handlers

Handles all utility step types using Strategy Pattern.
"""

import asyncio
import io
import logging
import sys
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
    Handle utility.python step for Designer automation

    SECURITY WARNING: This handler provides FULL Python access including:
    - Complete builtins (__import__, eval, exec, etc.)
    - File system access (os, pathlib)
    - Process execution (subprocess)
    - XML/JSON parsing
    - Any Python operations

    This is intentional for Designer playbook automation which requires
    file operations, process management, and system access.

    DO NOT execute untrusted playbooks! Only run playbooks from trusted sources.

    For safer execution without file/process access, use a different step type
    or implement sandboxing in a separate handler.
    """

    # Whitelist of safe builtins
    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
        'float', 'int', 'len', 'list', 'map', 'max', 'min', 'print',
        'range', 'reversed', 'round', 'sorted', 'str', 'sum', 'tuple',
        'zip', 'isinstance', 'type', 'ValueError', 'TypeError', 'KeyError',
    }

    def __init__(self, parameter_resolver=None):
        """Initialize handler with optional parameter resolver for variable access"""
        self.parameter_resolver = parameter_resolver

    # Dangerous patterns that should not appear in sandboxed scripts
    DANGEROUS_MODULES = ['os', 'subprocess', 'sys', 'shutil', 'socket', 'ctypes']
    DANGEROUS_BUILTINS = ['__import__', 'eval', 'exec', 'compile', 'open', 'globals', 'locals']

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        script = params.get("script")
        if not script:
            raise StepExecutionError("utility", "Python script is required")

        # SECURITY: Validate script before execution
        self._validate_script(script)

        # SECURITY: Execute in sandboxed environment (in thread pool to avoid blocking event loop)
        def _run_sandboxed_script():
            output_buffer = io.StringIO()
            result = {}

            try:
                # Create restricted builtins (v4 security)
                import builtins
                safe_builtins = {
                    name: getattr(builtins, name)
                    for name in self.SAFE_BUILTINS
                    if hasattr(builtins, name)
                }

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

                # Create execution environment with safe libraries only
                exec_globals = {
                    "__builtins__": safe_builtins,
                    "Path": __import__("pathlib").Path,
                    "zipfile": __import__("zipfile"),
                    "ET": __import__("xml.etree.ElementTree"),
                    "json": __import__("json"),
                    "time": __import__("time"),
                    "set_variable": set_variable,
                    "get_variable": get_variable,
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
        return await loop.run_in_executor(None, _run_sandboxed_script)

    def _validate_script(self, script: str) -> None:
        """Validate script does not contain dangerous imports or patterns."""
        code_lower = script.lower()

        for module in self.DANGEROUS_MODULES:
            if f'import {module}' in code_lower or f'from {module}' in code_lower:
                raise StepExecutionError(
                    "utility.python",
                    f"Blocked import of '{module}' — not allowed in sandboxed scripts"
                )

        for builtin in self.DANGEROUS_BUILTINS:
            if builtin in script:
                raise StepExecutionError(
                    "utility.python",
                    f"Blocked use of '{builtin}' — not allowed in sandboxed scripts"
                )
