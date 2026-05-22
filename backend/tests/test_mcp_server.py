"""Tests for the MCP server bridge fixes.

Covers:
  #2 - _request never surfaces an empty/uninformative error
  #3 - WSL absolute paths are translated to Windows UNC for path parameters
  #4 - wait_for_execution honours the caller timeout and returns fresh state
"""

import httpx
import pytest

from ignition_toolkit import mcp_server

# ---------------------------------------------------------------------------
# #3 - WSL → Windows path translation
# ---------------------------------------------------------------------------


class TestWslPathTranslation:
    def test_translates_wsl_absolute_path(self, monkeypatch):
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        result = mcp_server._to_windows_path_if_wsl("/modules/build")
        assert result == r"\\wsl.localhost\Ubuntu\modules\build"

    def test_no_distro_leaves_path_unchanged(self, monkeypatch):
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        assert mcp_server._to_windows_path_if_wsl("/modules/build") == "/modules/build"

    def test_windows_path_unchanged(self, monkeypatch):
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        assert mcp_server._to_windows_path_if_wsl(r"C:\temp\x") == r"C:\temp\x"

    def test_unc_path_unchanged(self, monkeypatch):
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        assert mcp_server._to_windows_path_if_wsl("//server/share") == "//server/share"

    def test_url_unchanged(self, monkeypatch):
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        assert mcp_server._to_windows_path_if_wsl("http://localhost:8088") == "http://localhost:8088"

    def test_only_path_keys_translated(self, monkeypatch):
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
        params = {
            "module_folder": "/modules/build",
            "download_path": "/tmp/out",
            "gateway_url": "/not-a-real-path-but-not-a-path-key",
            "prefer_unsigned": False,
        }
        out = mcp_server._translate_path_parameters(params)
        assert out["module_folder"] == r"\\wsl.localhost\Ubuntu\modules\build"
        assert out["download_path"] == r"\\wsl.localhost\Ubuntu\tmp\out"
        # gateway_url is not a path-hint key → left untouched
        assert out["gateway_url"] == "/not-a-real-path-but-not-a-path-key"
        assert out["prefer_unsigned"] is False


# ---------------------------------------------------------------------------
# #2 - _request error hardening
# ---------------------------------------------------------------------------


class TestRequestErrorHardening:
    @pytest.mark.asyncio
    async def test_empty_exception_message_is_named(self, monkeypatch):
        class _EmptyError(Exception):
            def __str__(self):
                return ""

        class _FailingClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def request(self, *a, **k):
                raise _EmptyError()

        monkeypatch.setattr(mcp_server.httpx, "AsyncClient", _FailingClient)
        result = await mcp_server._request("GET", "/api/credentials")
        # Must not be the old opaque {"error": ""}
        assert result["error"]
        assert "_EmptyError" in result["error"]
        assert result["request"] == "GET /api/credentials"

    @pytest.mark.asyncio
    async def test_timeout_message_names_the_cause(self, monkeypatch):
        class _TimeoutClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def request(self, *a, **k):
                raise httpx.ReadTimeout("")

        monkeypatch.setattr(mcp_server.httpx, "AsyncClient", _TimeoutClient)
        result = await mcp_server._request("GET", "/api/playbooks")
        assert "timed out" in result["error"].lower()
        assert "ReadTimeout" in result["error"]


# ---------------------------------------------------------------------------
# #4 - wait_for_execution timeout handling
# ---------------------------------------------------------------------------


class TestWaitForExecution:
    @pytest.mark.asyncio
    async def test_returns_terminal_status_promptly(self, monkeypatch):
        async def fake_get(path, **kw):
            return {"status": "completed", "execution_id": "x"}

        monkeypatch.setattr(mcp_server, "_get", fake_get)
        text = await mcp_server._handle_tool(
            "wait_for_execution", {"execution_id": "x", "timeout": 30}
        )
        assert '"completed"' in text

    @pytest.mark.asyncio
    async def test_caller_timeout_capped_and_surfaces_note(self, monkeypatch):
        async def fake_get(path, **kw):
            return {"status": "running"}

        async def fake_sleep(_seconds):
            return None  # don't actually wait

        monkeypatch.setattr(mcp_server, "_get", fake_get)
        monkeypatch.setattr(mcp_server.asyncio, "sleep", fake_sleep)
        monkeypatch.setattr(mcp_server, "EXECUTION_POLL_MAX_TIMEOUT", 2.0)

        # Ask for far more than the ceiling; the result must say it was capped
        # rather than silently honouring or silently clamping it.
        text = await mcp_server._handle_tool(
            "wait_for_execution",
            {"execution_id": "x", "timeout": 99999, "poll_interval": 1},
        )
        assert "Still running" in text
        assert "capped at 2" in text
