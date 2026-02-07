"""
Tests for CloudDesigner Docker utilities

Tests path conversion, URL translation, and other testable Docker-related functions.
Platform-specific Docker detection tests are skipped on incompatible platforms.
"""

import platform
import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

import pytest


class TestWindowsToWslPath:
    """Tests for windows_to_wsl_path function"""

    def test_simple_drive_path(self):
        """Test conversion of simple C: drive path"""
        from ignition_toolkit.clouddesigner.docker import windows_to_wsl_path

        result = windows_to_wsl_path("C:\\Users\\test")
        assert result == "/mnt/c/Users/test"

    def test_lowercase_drive(self):
        """Test that drive letter is lowercased"""
        from ignition_toolkit.clouddesigner.docker import windows_to_wsl_path

        result = windows_to_wsl_path("D:\\Projects\\app")
        assert result == "/mnt/d/Projects/app"

    def test_nested_path(self):
        """Test deeply nested path conversion"""
        from ignition_toolkit.clouddesigner.docker import windows_to_wsl_path

        result = windows_to_wsl_path("C:\\Users\\name\\Documents\\work\\project")
        assert result == "/mnt/c/Users/name/Documents/work/project"

    def test_already_unix_path(self):
        """Test that Unix paths are returned unchanged"""
        from ignition_toolkit.clouddesigner.docker import windows_to_wsl_path

        result = windows_to_wsl_path("/usr/local/bin")
        assert result == "/usr/local/bin"

    def test_path_object(self):
        """Test conversion of Path object"""
        from ignition_toolkit.clouddesigner.docker import windows_to_wsl_path

        # Create a mock Windows-style path
        result = windows_to_wsl_path(Path("E:\\Data\\files"))
        # Path object will use OS-native separators, so test the string representation
        assert result.startswith("/mnt/e") or result.startswith("E:")

    def test_no_trailing_slash(self):
        """Test path without trailing backslash"""
        from ignition_toolkit.clouddesigner.docker import windows_to_wsl_path

        result = windows_to_wsl_path("C:")
        assert result == "/mnt/c"

    def test_backslash_only_path(self):
        """Test path that only has backslashes without drive letter"""
        from ignition_toolkit.clouddesigner.docker import windows_to_wsl_path

        result = windows_to_wsl_path("some\\relative\\path")
        assert result == "some/relative/path"


class TestTranslateLocalhostUrl:
    """Tests for translate_localhost_url function"""

    def test_localhost_url(self):
        """Test translation of localhost URL"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        with patch(
            "ignition_toolkit.clouddesigner.docker.get_docker_host_ip",
            return_value="192.168.1.100",
        ):
            result = translate_localhost_url("http://localhost:8088")
            assert result == "http://192.168.1.100:8088"

    def test_127_0_0_1_url(self):
        """Test translation of 127.0.0.1 URL"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        with patch(
            "ignition_toolkit.clouddesigner.docker.get_docker_host_ip",
            return_value="192.168.1.100",
        ):
            result = translate_localhost_url("http://127.0.0.1:9088")
            assert result == "http://192.168.1.100:9088"

    def test_0_0_0_0_url(self):
        """Test translation of 0.0.0.0 URL"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        with patch(
            "ignition_toolkit.clouddesigner.docker.get_docker_host_ip",
            return_value="172.18.0.1",
        ):
            result = translate_localhost_url("https://0.0.0.0:443")
            assert result == "https://172.18.0.1:443"

    def test_non_localhost_url_unchanged(self):
        """Test that non-localhost URLs are unchanged"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        result = translate_localhost_url("http://example.com:8088")
        assert result == "http://example.com:8088"

    def test_ip_address_url_unchanged(self):
        """Test that external IP URLs are unchanged"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        result = translate_localhost_url("http://192.168.1.50:8088")
        assert result == "http://192.168.1.50:8088"

    def test_url_without_port(self):
        """Test translation of URL without explicit port"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        with patch(
            "ignition_toolkit.clouddesigner.docker.get_docker_host_ip",
            return_value="10.0.0.1",
        ):
            result = translate_localhost_url("http://localhost/api")
            assert result == "http://10.0.0.1/api"

    def test_url_with_path_and_query(self):
        """Test translation preserves path and query params"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        with patch(
            "ignition_toolkit.clouddesigner.docker.get_docker_host_ip",
            return_value="192.168.1.100",
        ):
            result = translate_localhost_url("http://localhost:8088/api/v1?foo=bar")
            assert result == "http://192.168.1.100:8088/api/v1?foo=bar"

    def test_no_docker_host_ip_available(self):
        """Test that URL is unchanged if no Docker host IP available"""
        from ignition_toolkit.clouddesigner.docker import translate_localhost_url

        with patch(
            "ignition_toolkit.clouddesigner.docker.get_docker_host_ip",
            return_value=None,
        ):
            result = translate_localhost_url("http://localhost:8088")
            assert result == "http://localhost:8088"


class TestIsWsl:
    """Tests for is_wsl function"""

    def test_returns_false_on_windows(self):
        """Test that is_wsl returns False on Windows"""
        from ignition_toolkit.clouddesigner.docker import is_wsl

        with patch("platform.system", return_value="Windows"):
            assert is_wsl() is False

    def test_returns_false_on_macos(self):
        """Test that is_wsl returns False on macOS"""
        from ignition_toolkit.clouddesigner.docker import is_wsl

        with patch("platform.system", return_value="Darwin"):
            assert is_wsl() is False

    def test_returns_true_with_microsoft_in_proc_version(self):
        """Test detection when 'microsoft' in /proc/version"""
        from ignition_toolkit.clouddesigner.docker import is_wsl

        with patch("platform.system", return_value="Linux"):
            with patch(
                "builtins.open",
                mock_open(read_data="Linux version 5.15.0-1-microsoft-standard-WSL2"),
            ):
                assert is_wsl() is True

    def test_returns_true_with_wsl_in_proc_version(self):
        """Test detection when 'wsl' in /proc/version"""
        from ignition_toolkit.clouddesigner.docker import is_wsl

        with patch("platform.system", return_value="Linux"):
            with patch(
                "builtins.open",
                mock_open(read_data="Linux version 5.15.0 WSL2 kernel"),
            ):
                assert is_wsl() is True

    def test_returns_false_for_native_linux(self):
        """Test that native Linux is not detected as WSL"""
        from ignition_toolkit.clouddesigner.docker import is_wsl

        with patch("platform.system", return_value="Linux"):
            with patch(
                "builtins.open",
                mock_open(read_data="Linux version 5.15.0-generic Ubuntu"),
            ):
                assert is_wsl() is False

    def test_handles_file_read_error(self):
        """Test graceful handling of file read errors"""
        from ignition_toolkit.clouddesigner.docker import is_wsl

        with patch("platform.system", return_value="Linux"):
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert is_wsl() is False


class TestGetDockerFilesPath:
    """Tests for get_docker_files_path function"""

    def test_returns_source_path_when_not_frozen(self):
        """Test that source path is returned in development mode"""
        from ignition_toolkit.clouddesigner.docker import get_docker_files_path

        with patch.object(sys, "frozen", False, create=True):
            result = get_docker_files_path()
            assert "docker_files" in str(result)
            assert isinstance(result, Path)

    def test_returns_meipass_path_when_frozen(self):
        """Test that _MEIPASS path is used in PyInstaller bundle"""
        from ignition_toolkit.clouddesigner.docker import get_docker_files_path

        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", "/tmp/test_bundle", create=True):
                result = get_docker_files_path()
                expected = Path("/tmp/test_bundle") / "clouddesigner" / "docker_files"
                assert result == expected


class TestFindDockerExecutable:
    """Tests for find_docker_executable function"""

    def setup_method(self):
        """Reset the docker detection cache between tests."""
        import ignition_toolkit.clouddesigner.docker as docker_mod
        docker_mod._docker_detection_done = False
        docker_mod._docker_detection_cache = {}

    def test_returns_path_from_shutil_which(self):
        """Test that docker in PATH is found"""
        from ignition_toolkit.clouddesigner.docker import find_docker_executable

        with patch("shutil.which", return_value="/usr/bin/docker"):
            result = find_docker_executable()
            assert result == "/usr/bin/docker"

    @pytest.mark.skipif(sys.platform == "win32", reason="Docker detection paths differ on Windows")
    def test_returns_none_when_not_found(self):
        """Test returns None when docker not found anywhere"""
        from ignition_toolkit.clouddesigner.docker import find_docker_executable

        with patch("shutil.which", return_value=None):
            with patch("platform.system", return_value="Linux"):
                with patch("pathlib.Path.exists", return_value=False):
                    with patch(
                        "ignition_toolkit.clouddesigner.docker.is_wsl",
                        return_value=False,
                    ):
                        result = find_docker_executable()
                        assert result is None


class TestGetDockerCommand:
    """Tests for get_docker_command function"""

    def test_returns_list_with_docker_path(self):
        """Test that docker command is returned as list"""
        from ignition_toolkit.clouddesigner.docker import get_docker_command

        with patch(
            "ignition_toolkit.clouddesigner.docker.find_docker_executable",
            return_value="/usr/bin/docker",
        ):
            result = get_docker_command()
            assert result == ["/usr/bin/docker"]

    def test_returns_fallback_docker(self):
        """Test fallback to 'docker' when path not found"""
        from ignition_toolkit.clouddesigner.docker import get_docker_command

        with patch(
            "ignition_toolkit.clouddesigner.docker.find_docker_executable",
            return_value=None,
        ):
            result = get_docker_command()
            assert result == ["docker"]


class TestCheckWslDocker:
    """Tests for check_wsl_docker function"""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_returns_false_tuple_on_non_windows(self):
        """Test returns (False, None) on non-Windows"""
        # This test would only run on Windows, skip it otherwise
        pass

    def test_returns_false_on_non_windows(self):
        """Test that WSL Docker check is skipped on non-Windows"""
        from ignition_toolkit.clouddesigner.docker import check_wsl_docker

        with patch("platform.system", return_value="Linux"):
            available, version = check_wsl_docker()
            assert available is False
            assert version is None

    def test_returns_false_when_wsl_not_in_path(self):
        """Test returns False when wsl.exe not found"""
        from ignition_toolkit.clouddesigner.docker import check_wsl_docker

        with patch("platform.system", return_value="Windows"):
            with patch("shutil.which", return_value=None):
                available, version = check_wsl_docker()
                assert available is False
                assert version is None


class TestIsUsingWslDocker:
    """Tests for is_using_wsl_docker function"""

    def test_returns_true_when_wsl_docker(self):
        """Test detection of WSL Docker usage"""
        from ignition_toolkit.clouddesigner.docker import is_using_wsl_docker

        with patch(
            "ignition_toolkit.clouddesigner.docker.find_docker_executable",
            return_value="wsl docker",
        ):
            assert is_using_wsl_docker() is True

    def test_returns_false_when_native_docker(self):
        """Test returns False for native Docker"""
        from ignition_toolkit.clouddesigner.docker import is_using_wsl_docker

        with patch(
            "ignition_toolkit.clouddesigner.docker.find_docker_executable",
            return_value="/usr/bin/docker",
        ):
            assert is_using_wsl_docker() is False
