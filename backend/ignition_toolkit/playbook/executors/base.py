"""
Base interface for step handlers

All step handlers implement the StepHandler interface with an async execute method.
"""

from abc import ABC, abstractmethod
from typing import Any


class StepHandler(ABC):
    """Base interface for step execution handlers"""

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a step with the given parameters

        Args:
            params: Resolved step parameters

        Returns:
            Step output dictionary

        Raises:
            StepExecutionError: If step execution fails
        """
        pass
