"""
Regression tests for BrowserVerifyHandler's exists/absent logic.

Found during Perspective playbook work (06/07/2026): the handler caught only
Python's builtin ``TimeoutError``, but Playwright raises its own
``TimeoutError`` which is *not* a subclass of the builtin — so
``exists: false`` verification could never pass when the element was
(correctly) absent: the Playwright timeout propagated as a step failure
instead of setting ``element_found = False``.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ignition_toolkit.playbook.exceptions import StepExecutionError
from ignition_toolkit.playbook.executors.browser_executor import BrowserVerifyHandler


def _manager_with_wait(side_effect=None) -> MagicMock:
    manager = MagicMock()
    manager.wait_for_selector = AsyncMock(side_effect=side_effect)
    return manager


class TestBrowserVerifyExistsFalse:
    async def test_absent_element_passes_when_playwright_timeout(self) -> None:
        """exists: false must treat a Playwright TimeoutError as 'not found'."""
        handler = BrowserVerifyHandler(_manager_with_wait(PlaywrightTimeoutError("timed out")))
        result = await handler.execute({"selector": "#gone", "exists": False, "timeout": 10})
        assert result["status"] == "verified"
        assert result["exists"] is False

    async def test_absent_element_passes_when_builtin_timeout(self) -> None:
        """The original builtin TimeoutError path must keep working too."""
        handler = BrowserVerifyHandler(_manager_with_wait(TimeoutError("timed out")))
        result = await handler.execute({"selector": "#gone", "exists": False, "timeout": 10})
        assert result["status"] == "verified"

    async def test_present_element_fails_exists_false(self) -> None:
        handler = BrowserVerifyHandler(_manager_with_wait())  # resolves -> found
        with pytest.raises(StepExecutionError, match="NOT exist"):
            await handler.execute({"selector": "#here", "exists": False, "timeout": 10})


class TestBrowserVerifyExistsTrue:
    async def test_absent_element_fails_exists_true(self) -> None:
        handler = BrowserVerifyHandler(_manager_with_wait(PlaywrightTimeoutError("timed out")))
        with pytest.raises(StepExecutionError, match="to exist"):
            await handler.execute({"selector": "#gone", "exists": True, "timeout": 10})

    async def test_present_element_passes_exists_true(self) -> None:
        handler = BrowserVerifyHandler(_manager_with_wait())
        result = await handler.execute({"selector": "#here", "timeout": 10})
        assert result["status"] == "verified"
        assert result["exists"] is True
