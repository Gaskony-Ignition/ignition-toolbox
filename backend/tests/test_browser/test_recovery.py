"""
Tests for BrowserManager connection-recovery behaviour.

Large module installs can sever Chromium's single CDP pipe; the failure
surfaces on the next driver read (typically the post-install navigate) as
"Connection closed while reading from the driver". These tests verify that
navigate() rebuilds the browser and retries once, restoring the captured
session, instead of aborting the playbook.

All browser internals are mocked — no real Chromium is launched.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ignition_toolkit.browser.manager import (
    BrowserManager,
    _is_fatal_connection_error,
)


def test_fatal_connection_error_detection():
    """The "connection closed while reading from the driver" crash is fatal."""
    assert _is_fatal_connection_error(
        Exception("Connection closed while reading from the driver")
    )
    assert _is_fatal_connection_error(Exception("Target page, context or browser has been closed"))
    # A plain per-call timeout is recoverable, not a dead connection.
    assert not _is_fatal_connection_error(Exception("Timeout 30000ms exceeded"))


@pytest.mark.asyncio
async def test_navigate_recovers_and_retries_on_fatal_connection_error():
    """
    navigate() should rebuild the browser and retry once when the first goto
    fails with a fatal connection error.
    """
    manager = BrowserManager(headless=True)

    # First page: its goto dies with the CDP "connection closed" error.
    dead_page = MagicMock()
    dead_page.goto = AsyncMock(side_effect=Exception("Connection closed while reading from the driver"))
    dead_page.is_closed = MagicMock(return_value=True)

    # Second page (after recovery): goto succeeds.
    fresh_page = MagicMock()
    fresh_page.goto = AsyncMock(return_value=None)
    fresh_page.is_closed = MagicMock(return_value=False)

    manager._page = dead_page
    manager._browser = MagicMock()
    manager._context = MagicMock()

    recover_mock = AsyncMock(return_value=True)

    async def _do_recover():
        manager._page = fresh_page
        return True

    recover_mock.side_effect = _do_recover

    with patch.object(manager, "recover", recover_mock), \
         patch.object(manager, "_capture_storage_state", AsyncMock()):
        await manager.navigate("http://localhost:8088/web/config/system.modules")

    recover_mock.assert_awaited_once()
    fresh_page.goto.assert_awaited_once()
    assert manager._last_url == "http://localhost:8088/web/config/system.modules"


@pytest.mark.asyncio
async def test_navigate_raises_if_recovery_fails():
    """If recovery cannot rebuild the browser, the original failure propagates."""
    manager = BrowserManager(headless=True)
    dead_page = MagicMock()
    dead_page.goto = AsyncMock(side_effect=Exception("Connection closed while reading from the driver"))
    manager._page = dead_page

    with patch.object(manager, "recover", AsyncMock(return_value=False)), \
         patch.object(manager, "_capture_storage_state", AsyncMock()):
        with pytest.raises(Exception, match="Connection closed"):
            await manager.navigate("http://localhost:8088/")


@pytest.mark.asyncio
async def test_navigate_does_not_recover_on_ordinary_timeout():
    """A normal timeout is not a dead connection — no recovery, error propagates."""
    manager = BrowserManager(headless=True)
    page = MagicMock()
    page.goto = AsyncMock(side_effect=Exception("Timeout 30000ms exceeded"))
    manager._page = page

    recover_mock = AsyncMock(return_value=True)
    with patch.object(manager, "recover", recover_mock), \
         patch.object(manager, "_capture_storage_state", AsyncMock()):
        with pytest.raises(Exception, match="Timeout"):
            await manager.navigate("http://localhost:8088/")
    recover_mock.assert_not_awaited()


def test_is_connected_false_when_no_browser():
    """is_connected() is False before start() (no browser/page)."""
    manager = BrowserManager(headless=True)
    assert manager.is_connected() is False


def test_is_connected_reflects_browser_and_page_state():
    """is_connected() is True only when both browser and page are alive."""
    manager = BrowserManager(headless=True)

    manager._browser = MagicMock()
    manager._browser.is_connected = MagicMock(return_value=True)
    manager._page = MagicMock()
    manager._page.is_closed = MagicMock(return_value=False)
    assert manager.is_connected() is True

    # Browser pipe dropped.
    manager._browser.is_connected = MagicMock(return_value=False)
    assert manager.is_connected() is False

    # Browser alive but page closed.
    manager._browser.is_connected = MagicMock(return_value=True)
    manager._page.is_closed = MagicMock(return_value=True)
    assert manager.is_connected() is False


@pytest.mark.asyncio
async def test_recover_relaunches_with_captured_storage_state():
    """recover() relaunches the browser seeding the captured session state."""
    manager = BrowserManager(headless=True)
    manager._storage_state = {"cookies": [{"name": "session", "value": "abc"}]}
    manager._browser = MagicMock()
    manager._context = MagicMock()
    manager._playwright = MagicMock()

    launch_mock = MagicMock()

    async def _fake_launch(storage_state=None):
        # Simulate a healthy relaunched browser/page.
        manager._browser = MagicMock()
        manager._browser.is_connected = MagicMock(return_value=True)
        manager._page = MagicMock()
        manager._page.is_closed = MagicMock(return_value=False)
        launch_mock(storage_state=storage_state)

    with patch.object(manager, "stop_screenshot_streaming", AsyncMock()), \
         patch.object(manager, "_launch_browser", side_effect=_fake_launch):
        ok = await manager.recover()

    assert ok is True
    launch_mock.assert_called_once_with(storage_state={"cookies": [{"name": "session", "value": "abc"}]})
