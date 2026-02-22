"""
Tests for ignition_toolkit/gateway/models.py and gateway/exceptions.py

Covers: dataclass construction, enum values, property calculations, and
        exception hierarchy / message formatting.
"""

from datetime import datetime

import pytest


# ============================================================================
# Enum tests
# ============================================================================


class TestModuleState:
    def test_running_value(self):
        from ignition_toolkit.gateway.models import ModuleState

        assert ModuleState.RUNNING == "running"

    def test_loaded_value(self):
        from ignition_toolkit.gateway.models import ModuleState

        assert ModuleState.LOADED == "loaded"

    def test_installed_value(self):
        from ignition_toolkit.gateway.models import ModuleState

        assert ModuleState.INSTALLED == "installed"

    def test_failed_value(self):
        from ignition_toolkit.gateway.models import ModuleState

        assert ModuleState.FAILED == "failed"


class TestProjectStatus:
    def test_enabled_value(self):
        from ignition_toolkit.gateway.models import ProjectStatus

        assert ProjectStatus.ENABLED == "enabled"

    def test_disabled_value(self):
        from ignition_toolkit.gateway.models import ProjectStatus

        assert ProjectStatus.DISABLED == "disabled"


class TestTagQuality:
    def test_good_value(self):
        from ignition_toolkit.gateway.models import TagQuality

        assert TagQuality.GOOD == "Good"

    def test_bad_value(self):
        from ignition_toolkit.gateway.models import TagQuality

        assert TagQuality.BAD == "Bad"

    def test_error_value(self):
        from ignition_toolkit.gateway.models import TagQuality

        assert TagQuality.ERROR == "Error"

    def test_uncertain_value(self):
        from ignition_toolkit.gateway.models import TagQuality

        assert TagQuality.UNCERTAIN == "Uncertain"


# ============================================================================
# Dataclass model tests
# ============================================================================


class TestModule:
    def test_construction(self):
        from ignition_toolkit.gateway.models import Module, ModuleState

        m = Module(name="Perspective", version="3.3.0", state=ModuleState.RUNNING)
        assert m.name == "Perspective"
        assert m.version == "3.3.0"
        assert m.state == ModuleState.RUNNING

    def test_default_license_required_false(self):
        from ignition_toolkit.gateway.models import Module, ModuleState

        m = Module(name="Perspective", version="3.3.0", state=ModuleState.RUNNING)
        assert m.license_required is False

    def test_repr_contains_name(self):
        from ignition_toolkit.gateway.models import Module, ModuleState

        m = Module(name="Perspective", version="3.3.0", state=ModuleState.RUNNING)
        assert "Perspective" in repr(m)


class TestProject:
    def test_construction(self):
        from ignition_toolkit.gateway.models import Project

        p = Project(name="my_project", title="My Project", enabled=True)
        assert p.name == "my_project"
        assert p.title == "My Project"
        assert p.enabled is True

    def test_repr_shows_enabled_status(self):
        from ignition_toolkit.gateway.models import Project

        p = Project(name="proj", title="Proj", enabled=True)
        assert "enabled" in repr(p)

    def test_repr_shows_disabled_status(self):
        from ignition_toolkit.gateway.models import Project

        p = Project(name="proj", title="Proj", enabled=False)
        assert "disabled" in repr(p)

    def test_optional_fields_default_none(self):
        from ignition_toolkit.gateway.models import Project

        p = Project(name="proj", title="Proj", enabled=True)
        assert p.description is None
        assert p.parent is None
        assert p.version is None


class TestTag:
    def test_construction(self):
        from ignition_toolkit.gateway.models import Tag, TagQuality

        t = Tag(name="Temp", path="/Sensors/Temp", value=72.5, quality=TagQuality.GOOD)
        assert t.name == "Temp"
        assert t.value == 72.5
        assert t.quality == TagQuality.GOOD

    def test_repr_contains_path(self):
        from ignition_toolkit.gateway.models import Tag, TagQuality

        t = Tag(name="T", path="/foo/bar", value=1, quality=TagQuality.GOOD)
        assert "/foo/bar" in repr(t)


class TestGatewayInfo:
    def test_construction(self):
        from ignition_toolkit.gateway.models import GatewayInfo

        info = GatewayInfo(version="8.3.4", platform_version="b2024", edition="standard")
        assert info.version == "8.3.4"
        assert info.edition == "standard"

    def test_optional_fields_default_none(self):
        from ignition_toolkit.gateway.models import GatewayInfo

        info = GatewayInfo(version="8.3.4", platform_version="b2024", edition="standard")
        assert info.license_key is None
        assert info.uptime_seconds is None

    def test_repr_contains_version(self):
        from ignition_toolkit.gateway.models import GatewayInfo

        info = GatewayInfo(version="8.3.4", platform_version="b2024", edition="standard")
        assert "8.3.4" in repr(info)


class TestHealthStatus:
    def test_construction(self):
        from ignition_toolkit.gateway.models import HealthStatus

        h = HealthStatus(healthy=True, uptime_seconds=3600)
        assert h.healthy is True
        assert h.uptime_seconds == 3600

    def test_memory_usage_percent_calculated(self):
        from ignition_toolkit.gateway.models import HealthStatus

        h = HealthStatus(healthy=True, uptime_seconds=100, memory_used_mb=256.0, memory_max_mb=512.0)
        assert h.memory_usage_percent == pytest.approx(50.0)

    def test_memory_usage_percent_none_when_missing(self):
        from ignition_toolkit.gateway.models import HealthStatus

        h = HealthStatus(healthy=True, uptime_seconds=100)
        assert h.memory_usage_percent is None

    def test_repr_shows_healthy(self):
        from ignition_toolkit.gateway.models import HealthStatus

        h = HealthStatus(healthy=True, uptime_seconds=100)
        assert "healthy" in repr(h)

    def test_repr_shows_unhealthy(self):
        from ignition_toolkit.gateway.models import HealthStatus

        h = HealthStatus(healthy=False, uptime_seconds=100)
        assert "unhealthy" in repr(h)


# ============================================================================
# Exception tests
# ============================================================================


class TestGatewayException:
    def test_base_exception_can_be_raised(self):
        from ignition_toolkit.gateway.exceptions import GatewayException

        with pytest.raises(GatewayException):
            raise GatewayException("test error")

    def test_message_stored(self):
        from ignition_toolkit.gateway.exceptions import GatewayException

        exc = GatewayException("something went wrong")
        assert exc.message == "something went wrong"

    def test_context_defaults_to_empty_dict(self):
        from ignition_toolkit.gateway.exceptions import GatewayException

        exc = GatewayException("error")
        assert exc.context == {}

    def test_context_stored(self):
        from ignition_toolkit.gateway.exceptions import GatewayException

        exc = GatewayException("error", context={"url": "http://localhost"})
        assert exc.context["url"] == "http://localhost"

    def test_recovery_hint_in_str(self):
        from ignition_toolkit.gateway.exceptions import GatewayException

        exc = GatewayException("error", recovery_hint="try again")
        assert "try again" in str(exc)


class TestAuthenticationError:
    def test_is_gateway_exception(self):
        from ignition_toolkit.gateway.exceptions import AuthenticationError, GatewayException

        exc = AuthenticationError()
        assert isinstance(exc, GatewayException)

    def test_default_message(self):
        from ignition_toolkit.gateway.exceptions import AuthenticationError

        exc = AuthenticationError()
        assert "Authentication" in exc.message

    def test_custom_message(self):
        from ignition_toolkit.gateway.exceptions import AuthenticationError

        exc = AuthenticationError("bad password")
        assert exc.message == "bad password"


class TestGatewayConnectionError:
    def test_is_gateway_exception(self):
        from ignition_toolkit.gateway.exceptions import GatewayConnectionError, GatewayException

        assert isinstance(GatewayConnectionError(), GatewayException)

    def test_default_message_contains_connect(self):
        from ignition_toolkit.gateway.exceptions import GatewayConnectionError

        exc = GatewayConnectionError()
        assert "connect" in exc.message.lower()


class TestModuleInstallationError:
    def test_is_gateway_exception(self):
        from ignition_toolkit.gateway.exceptions import ModuleInstallationError, GatewayException

        assert isinstance(ModuleInstallationError(), GatewayException)

    def test_has_recovery_hint(self):
        from ignition_toolkit.gateway.exceptions import ModuleInstallationError

        exc = ModuleInstallationError()
        assert exc.recovery_hint != ""


class TestGatewayRestartError:
    def test_is_gateway_exception(self):
        from ignition_toolkit.gateway.exceptions import GatewayRestartError, GatewayException

        assert isinstance(GatewayRestartError(), GatewayException)


class TestResourceNotFoundError:
    def test_is_gateway_exception(self):
        from ignition_toolkit.gateway.exceptions import ResourceNotFoundError, GatewayException

        assert isinstance(ResourceNotFoundError(), GatewayException)


class TestInvalidParameterError:
    def test_is_gateway_exception(self):
        from ignition_toolkit.gateway.exceptions import InvalidParameterError, GatewayException

        assert isinstance(InvalidParameterError(), GatewayException)

    def test_custom_message(self):
        from ignition_toolkit.gateway.exceptions import InvalidParameterError

        exc = InvalidParameterError("bad url format")
        assert exc.message == "bad url format"
