"""
FastAPI server for Ignition Automation Toolkit

Provides REST API and WebSocket endpoints for playbook execution and control.
"""

from ignition_toolkit.api.app import app

__all__ = ["app"]
