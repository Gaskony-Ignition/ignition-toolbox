"""
Utility step helpers for testing and direct invocation

Provides standalone functions that wrap the executor classes
for easier testing and programmatic use.
"""

import asyncio
import io
from contextlib import redirect_stdout
from typing import Any

from ignition_toolkit.playbook.exceptions import StepExecutionError


def execute_python_safely(code: str, context: dict[str, Any], timeout: int = 5) -> None:
    """
    Execute Python code safely in a sandboxed environment

    ⚠️  SECURITY WARNING ⚠️
    This function executes arbitrary Python code with restrictions. While it attempts
    to sandbox execution, it is NOT a complete security boundary. Use only with
    trusted playbooks. Potential risks:
    - Sandbox escape via Python internals
    - Resource exhaustion (CPU/memory)
    - ReDoS attacks via regex module

    For production environments, consider:
    - Running in isolated containers
    - Implementing stricter process-level sandboxing
    - Using a domain-specific language instead

    SECURITY FEATURES:
    - Limited builtins (no eval, compile, __import__, etc.)
    - No dangerous modules (os, subprocess, sys)
    - Configurable timeout
    - No file write access

    Args:
        code: Python code to execute
        context: Dictionary to use as execution context (modified in-place)
        timeout: Maximum execution time in seconds (default: 5)

    Raises:
        ValueError: If code contains dangerous imports or patterns
        TimeoutError: If execution exceeds timeout
        StepExecutionError: If execution fails

    Examples:
        >>> context = {}
        >>> execute_python_safely("result = 2 + 2", context, timeout=1)
        >>> print(context['result'])
        4
    """
    # SECURITY: Check for dangerous imports before execution
    dangerous_modules = ['os', 'subprocess', 'sys', 'shutil', 'socket']
    dangerous_builtins = ['__import__', 'eval', 'exec', 'compile', 'open']

    code_lower = code.lower()

    # Check for dangerous imports
    for module in dangerous_modules:
        if f'import {module}' in code_lower or f'from {module}' in code_lower:
            raise ValueError(f"Dangerous import not allowed: {module}")

    # Check for dangerous builtins
    for builtin in dangerous_builtins:
        if builtin in code:
            raise ValueError(f"Dangerous builtin not allowed: {builtin}")

    # Whitelist of safe builtins
    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
        'float', 'int', 'len', 'list', 'map', 'max', 'min', 'print',
        'range', 'reversed', 'round', 'sorted', 'str', 'sum', 'tuple',
        'zip', 'isinstance', 'type', 'ValueError', 'TypeError', 'KeyError',
    }

    try:
        # Create restricted builtins
        import builtins
        safe_builtins = {
            name: getattr(builtins, name)
            for name in SAFE_BUILTINS
            if hasattr(builtins, name)
        }

        # SECURITY: Restricted execution environment
        exec_globals = {
            "__builtins__": safe_builtins,
            "json": __import__("json"),
            "re": __import__("re"),
            "datetime": __import__("datetime"),
        }

        # Merge context into globals
        exec_globals.update(context)

        # Set timeout using signal (Unix only)
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Script execution timed out ({timeout}s limit)")

        # Only set signal handler on Unix systems
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

        try:
            # Execute code
            output_buffer = io.StringIO()
            with redirect_stdout(output_buffer):
                exec(code, exec_globals)

            # Update context with results (exclude __builtins__)
            for key, value in exec_globals.items():
                if key not in ['__builtins__', 'json', 're', 'datetime']:
                    context[key] = value

        finally:
            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)

    except TimeoutError:
        raise
    except Exception as e:
        raise StepExecutionError("utility.python", f"Script execution failed: {str(e)}")


__all__ = ['execute_python_safely']
