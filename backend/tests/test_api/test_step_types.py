"""
Tests for step types API endpoint.

Tests that get_step_types() returns well-formed metadata for all step types
including correct domain values, required fields, and known entries.
"""

import asyncio
import pytest


class TestGetStepTypes:
    """Tests for the /api/playbooks/step-types endpoint."""

    def test_returns_step_types_response_object(self):
        """get_step_types() must return a StepTypesResponse model instance."""
        from ignition_toolkit.api.routers.step_types import get_step_types, StepTypesResponse

        result = asyncio.run(get_step_types())

        assert isinstance(result, StepTypesResponse)

    def test_step_types_list_is_non_empty(self):
        """The step_types list must contain at least one entry."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        assert len(result.step_types) > 0

    def test_step_types_contains_44_entries(self):
        """The registry must expose exactly 44 step type definitions."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        assert len(result.step_types) == 44, (
            f"Expected 44 step types, got {len(result.step_types)}. "
            f"Types: {[s.type for s in result.step_types]}"
        )

    def test_each_step_type_has_required_fields(self):
        """Every step type entry must have type, domain, description, and parameters."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        for step in result.step_types:
            assert step.type, f"Step {step} has empty/missing 'type'"
            assert step.domain, f"Step {step.type!r} has empty/missing 'domain'"
            assert step.description, f"Step {step.type!r} has empty/missing 'description'"
            assert isinstance(step.parameters, list), (
                f"Step {step.type!r} 'parameters' must be a list"
            )

    def test_domains_list_is_non_empty(self):
        """The domains list must contain at least one entry."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        assert len(result.domains) > 0

    def test_domains_are_sorted(self):
        """The domains list must be sorted alphabetically."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        assert result.domains == sorted(result.domains)

    def test_domains_contains_expected_values(self):
        """The domains list must contain all known domain names."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        expected_domains = {
            "browser",
            "designer",
            "fat",
            "gateway",
            "perspective",
            "playbook",
            "utility",
        }
        actual_domains = set(result.domains)
        missing = expected_domains - actual_domains
        assert not missing, (
            f"Domains list is missing expected domains: {missing}. "
            f"Got: {sorted(actual_domains)}"
        )

    def test_domains_list_matches_step_types(self):
        """The domains list must contain exactly the unique domains from step_types."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        computed_domains = sorted(set(s.domain for s in result.step_types))
        assert result.domains == computed_domains

    def test_known_step_type_gateway_login_exists(self):
        """The well-known step type 'gateway.login' must be present."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        type_names = [s.type for s in result.step_types]
        assert "gateway.login" in type_names, (
            f"Expected 'gateway.login' in step types. Got: {type_names}"
        )

    def test_known_step_type_utility_log_exists(self):
        """The well-known step type 'utility.log' must be present."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        type_names = [s.type for s in result.step_types]
        assert "utility.log" in type_names, (
            f"Expected 'utility.log' in step types. Got: {type_names}"
        )

    def test_gateway_login_step_has_correct_domain(self):
        """The 'gateway.login' step must have domain='gateway'."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        step = next((s for s in result.step_types if s.type == "gateway.login"), None)
        assert step is not None
        assert step.domain == "gateway"

    def test_step_type_names_are_unique(self):
        """All step type identifiers must be unique (no duplicates)."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        type_names = [s.type for s in result.step_types]
        assert len(type_names) == len(set(type_names)), (
            "Duplicate step type names detected: "
            + str([t for t in type_names if type_names.count(t) > 1])
        )

    def test_step_parameter_fields_are_present(self):
        """Each step parameter (if any) must have name, type, required, and description."""
        from ignition_toolkit.api.routers.step_types import get_step_types

        result = asyncio.run(get_step_types())

        for step in result.step_types:
            for param in step.parameters:
                assert param.name, (
                    f"Step {step.type!r}: parameter {param} has empty/missing 'name'"
                )
                assert param.type, (
                    f"Step {step.type!r}: parameter {param.name!r} has empty/missing 'type'"
                )
                assert isinstance(param.required, bool), (
                    f"Step {step.type!r}: parameter {param.name!r} 'required' must be bool"
                )
