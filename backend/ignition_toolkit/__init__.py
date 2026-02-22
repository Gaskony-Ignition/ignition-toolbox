"""
Ignition Automation Toolkit

Lightweight, transferable automation platform for Ignition SCADA Gateway operations.
"""

__version__ = "3.0.3"  # Updated: 2026-02-22  # Updated: 2026-02-22
__build_date__ = "2026-02-21"
__phases_complete__ = "10/10 (100%) + Plugin Architecture Complete"
__author__ = "Nigel G"
__license__ = "MIT"

from ignition_toolkit.gateway.client import GatewayClient
from ignition_toolkit.playbook.engine import PlaybookEngine
from ignition_toolkit.playbook.models import ExecutionState, Playbook, PlaybookStep

__all__ = [
    "GatewayClient",
    "PlaybookEngine",
    "Playbook",
    "PlaybookStep",
    "ExecutionState",
]
