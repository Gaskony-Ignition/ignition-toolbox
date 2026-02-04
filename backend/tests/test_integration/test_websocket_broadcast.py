"""
Integration tests for WebSocket message broadcasting.

Tests the WebSocket message queue and broadcasting functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

from ignition_toolkit.api.services.websocket_manager import WebSocketManager


@pytest.fixture
def ws_manager():
    """Create a fresh WebSocket manager for testing."""
    manager = WebSocketManager(keepalive_interval=60, enable_batching=False)
    yield manager
    # Cleanup - cancel any running tasks
    for task in manager._keepalive_tasks.values():
        task.cancel()


class TestWebSocketManager:
    """Test WebSocket manager functionality."""

    @pytest.mark.asyncio
    async def test_connect_client(self, ws_manager):
        """Test connecting a WebSocket client."""
        mock_ws = AsyncMock()
        mock_ws.client = "test-client"

        await ws_manager.connect(mock_ws)

        assert mock_ws in ws_manager._connections
        mock_ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_client(self, ws_manager):
        """Test disconnecting a WebSocket client."""
        mock_ws = AsyncMock()
        mock_ws.client = "test-client"

        await ws_manager.connect(mock_ws)
        assert mock_ws in ws_manager._connections

        await ws_manager.disconnect(mock_ws)
        assert mock_ws not in ws_manager._connections

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, ws_manager):
        """Test broadcasting message to all connected clients."""
        # Connect multiple clients
        clients = []
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.client = f"test-client-{i}"
            await ws_manager.connect(mock_ws)
            clients.append(mock_ws)

        # Broadcast message
        message = {"type": "test", "data": "hello"}
        await ws_manager._broadcast(message)

        # Verify all clients received the message
        for client in clients:
            client.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_client(self, ws_manager):
        """Test that broadcast handles disconnected clients gracefully."""
        # Connect clients
        good_client = AsyncMock()
        good_client.client = "good-client"

        bad_client = AsyncMock()
        bad_client.client = "bad-client"
        bad_client.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await ws_manager.connect(good_client)
        await ws_manager.connect(bad_client)

        # Broadcast should not raise even if one client fails
        message = {"type": "test", "data": "hello"}
        await ws_manager._broadcast(message)

        # Good client should have received the message
        good_client.send_json.assert_called_once_with(message)

        # Bad client should have been removed
        assert bad_client not in ws_manager._connections


class TestExecutionUpdates:
    """Test execution update broadcasting."""

    @pytest.mark.asyncio
    async def test_send_screenshot(self, ws_manager):
        """Test sending screenshot to clients."""
        mock_ws = AsyncMock()
        mock_ws.client = "test-client"

        await ws_manager.connect(mock_ws)

        await ws_manager.broadcast_screenshot(
            execution_id="test-123",
            screenshot_b64="base64data"
        )

        # Screenshot should have been sent
        assert mock_ws.send_json.called
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "screenshot_frame"
        assert call_args["data"]["executionId"] == "test-123"


class TestConnectionManagement:
    """Test WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_multiple_connections(self, ws_manager):
        """Test managing multiple simultaneous connections."""
        # Connect many clients
        clients = []
        for i in range(10):
            mock_ws = AsyncMock()
            mock_ws.client = f"client-{i}"
            await ws_manager.connect(mock_ws)
            clients.append(mock_ws)

        assert ws_manager.get_connection_count() == 10

        # Disconnect some
        for client in clients[:5]:
            await ws_manager.disconnect(client)

        assert ws_manager.get_connection_count() == 5

    @pytest.mark.asyncio
    async def test_connection_count(self, ws_manager):
        """Test getting connection count."""
        for i in range(5):
            mock_ws = AsyncMock()
            mock_ws.client = f"client-{i}"
            await ws_manager.connect(mock_ws)

        assert ws_manager.get_connection_count() == 5


class TestMessageBatching:
    """Test message batching for high-frequency updates."""

    @pytest.mark.asyncio
    async def test_batching_disabled(self):
        """Test that batching can be disabled."""
        manager = WebSocketManager(keepalive_interval=60, enable_batching=False)

        mock_ws = AsyncMock()
        mock_ws.client = "test-client"

        await manager.connect(mock_ws)

        # Send screenshot (would normally be batched)
        await manager.broadcast_screenshot("test-123", "base64data")

        # Should be sent immediately (not batched)
        assert mock_ws.send_json.called

        # Cleanup
        for task in manager._keepalive_tasks.values():
            task.cancel()

    @pytest.mark.asyncio
    async def test_close_all(self):
        """Test closing all connections."""
        manager = WebSocketManager(keepalive_interval=60, enable_batching=False)

        # Connect clients
        clients = []
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.client = f"client-{i}"
            await manager.connect(mock_ws)
            clients.append(mock_ws)

        assert manager.get_connection_count() == 3

        # Close all
        await manager.close_all()

        assert manager.get_connection_count() == 0


class TestManagerInstantiation:
    """Test WebSocket manager instantiation."""

    def test_create_manager_instance(self):
        """Test creating a new WebSocketManager instance."""
        manager = WebSocketManager()
        assert manager is not None
        assert hasattr(manager, '_connections')
        assert manager.get_connection_count() == 0

    def test_custom_keepalive_interval(self):
        """Test creating manager with custom keepalive interval."""
        manager = WebSocketManager(keepalive_interval=30)
        assert manager._keepalive_interval == 30

    def test_batching_enabled_by_default(self):
        """Test that batching is enabled by default."""
        manager = WebSocketManager()
        assert manager._enable_batching is True
