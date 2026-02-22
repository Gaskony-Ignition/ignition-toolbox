"""
Tests for ignition_toolkit/playbook/parameters.py

Covers: ParameterResolver construction, plain string pass-through,
        parameter / variable resolution, missing reference errors,
        non-string primitive pass-through, and no-vault credential behaviour.
"""

import pytest

from ignition_toolkit.playbook.parameters import ParameterResolver
from ignition_toolkit.playbook.exceptions import ParameterResolutionError


class TestParameterResolverConstruction:
    """ParameterResolver can be built with various argument combinations."""

    def test_no_args(self):
        """Constructing with no arguments must not raise."""
        resolver = ParameterResolver()
        assert resolver is not None

    def test_with_parameters(self):
        resolver = ParameterResolver(parameters={"foo": "bar"})
        assert resolver.parameters == {"foo": "bar"}

    def test_with_variables(self):
        resolver = ParameterResolver(variables={"x": "42"})
        assert resolver.variables == {"x": "42"}

    def test_defaults_to_empty_dicts(self):
        resolver = ParameterResolver()
        assert resolver.parameters == {}
        assert resolver.variables == {}
        assert resolver.step_results == {}
        assert resolver.credential_vault is None


class TestResolvePassThrough:
    """Strings with no {{ }} markers are returned unchanged."""

    def test_plain_string_unchanged(self):
        resolver = ParameterResolver()
        assert resolver.resolve("hello world") == "hello world"

    def test_empty_string_unchanged(self):
        resolver = ParameterResolver()
        assert resolver.resolve("") == ""

    def test_string_without_braces_unchanged(self):
        resolver = ParameterResolver()
        assert resolver.resolve("no references here") == "no references here"


class TestResolvePrimitives:
    """Non-string primitives are returned without modification."""

    def test_integer_returned_as_is(self):
        resolver = ParameterResolver()
        assert resolver.resolve(42) == 42

    def test_float_returned_as_is(self):
        resolver = ParameterResolver()
        assert resolver.resolve(3.14) == 3.14

    def test_bool_true_returned_as_is(self):
        resolver = ParameterResolver()
        assert resolver.resolve(True) is True

    def test_bool_false_returned_as_is(self):
        resolver = ParameterResolver()
        assert resolver.resolve(False) is False

    def test_none_returned_as_is(self):
        resolver = ParameterResolver()
        assert resolver.resolve(None) is None


class TestResolveParameter:
    """{{ parameter.name }} references are substituted from the parameters dict."""

    def test_parameter_reference_resolved(self):
        resolver = ParameterResolver(parameters={"foo": "bar"})
        result = resolver.resolve("{{ parameter.foo }}")
        assert result == "bar"

    def test_parameter_embedded_in_string(self):
        resolver = ParameterResolver(parameters={"host": "localhost"})
        result = resolver.resolve("http://{{ parameter.host }}:8088")
        assert result == "http://localhost:8088"

    def test_missing_parameter_raises(self):
        resolver = ParameterResolver(parameters={})
        with pytest.raises(ParameterResolutionError):
            resolver.resolve("{{ parameter.missing }}")

    def test_parameter_integer_value_becomes_string_in_template(self):
        """When a parameter ref is embedded in a larger string, the value is coerced to str."""
        resolver = ParameterResolver(parameters={"port": 8088})
        result = resolver.resolve("host:{{ parameter.port }}")
        assert result == "host:8088"

    def test_parameter_integer_value_returned_as_string_when_sole_ref(self):
        """When the whole string is a single parameter ref, value is cast to str."""
        resolver = ParameterResolver(parameters={"count": 5})
        result = resolver.resolve("{{ parameter.count }}")
        # Single-reference whole-string: returns str() of the value
        assert result == "5"


class TestResolveVariable:
    """{{ variable.name }} references are substituted from the variables dict."""

    def test_variable_reference_resolved(self):
        resolver = ParameterResolver(variables={"x": "42"})
        result = resolver.resolve("{{ variable.x }}")
        assert result == "42"

    def test_missing_variable_raises(self):
        resolver = ParameterResolver(variables={})
        with pytest.raises(ParameterResolutionError):
            resolver.resolve("{{ variable.missing }}")

    def test_variable_in_mixed_string(self):
        resolver = ParameterResolver(variables={"name": "World"})
        result = resolver.resolve("Hello {{ variable.name }}!")
        assert result == "Hello World!"


class TestResolveCredential:
    """Credential references require a vault; without one a ParameterResolutionError is raised."""

    def test_no_vault_raises_on_credential_ref(self):
        resolver = ParameterResolver(credential_vault=None)
        with pytest.raises(ParameterResolutionError):
            resolver.resolve("{{ credential.my_cred }}")


class TestResolveUnknownType:
    """An unknown reference type raises ParameterResolutionError."""

    def test_unknown_ref_type_raises(self):
        resolver = ParameterResolver()
        with pytest.raises(ParameterResolutionError):
            resolver.resolve("{{ unknown.something }}")


class TestResolveCollections:
    """resolve() recurses into dicts and lists."""

    def test_dict_values_are_resolved(self):
        resolver = ParameterResolver(parameters={"env": "prod"})
        result = resolver.resolve({"key": "{{ parameter.env }}"})
        assert result == {"key": "prod"}

    def test_list_items_are_resolved(self):
        resolver = ParameterResolver(variables={"item": "alpha"})
        result = resolver.resolve(["plain", "{{ variable.item }}"])
        assert result == ["plain", "alpha"]

    def test_nested_dict_resolved(self):
        resolver = ParameterResolver(parameters={"val": "deep"})
        result = resolver.resolve({"outer": {"inner": "{{ parameter.val }}"}})
        assert result == {"outer": {"inner": "deep"}}
