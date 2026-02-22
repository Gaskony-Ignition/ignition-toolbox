"""
Tests for step type registry completeness and correctness.

Ensures the STEP_REGISTRY in step_type_registry.py stays in sync with
the StepType enum in models.py.
"""

import pytest

KNOWN_DOMAINS = {"browser", "gateway", "designer", "perspective", "utility", "playbook", "fat"}
EXPECTED_COUNT = 44


class TestRegistryCompleteness:
    def test_no_missing_step_types(self):
        """validate_registry_completeness returns empty list when registry is complete."""
        from ignition_toolkit.playbook.step_type_registry import validate_registry_completeness

        missing = validate_registry_completeness()
        assert missing == [], f"Step types missing from registry: {missing}"

    def test_registry_has_expected_count(self):
        """Registry has exactly 44 step type definitions."""
        from ignition_toolkit.playbook.step_type_registry import get_all_definitions

        definitions = get_all_definitions()
        assert len(definitions) == EXPECTED_COUNT, (
            f"Expected {EXPECTED_COUNT} definitions, got {len(definitions)}"
        )

    def test_all_step_type_enum_values_covered(self):
        """Every StepType enum member has an entry in the registry."""
        from ignition_toolkit.playbook.step_type_registry import get_all_definitions
        from ignition_toolkit.playbook.models import StepType

        definitions = get_all_definitions()
        registered_types = {defn.step_type for defn in definitions}
        all_types = set(StepType)
        missing = all_types - registered_types
        assert not missing, f"Step types not in registry: {[t.value for t in missing]}"

    def test_step_type_domain_property(self):
        """StepType.domain returns the correct domain prefix for all types."""
        from ignition_toolkit.playbook.models import StepType

        for step_type in StepType:
            expected_domain = step_type.value.split(".")[0]
            assert step_type.domain == expected_domain, (
                f"{step_type.value}.domain: expected '{expected_domain}', got '{step_type.domain}'"
            )

    def test_get_all_definitions_returns_non_empty_list(self):
        """get_all_definitions returns a non-empty list of StepTypeDefinition objects."""
        from ignition_toolkit.playbook.step_type_registry import get_all_definitions, StepTypeDefinition

        definitions = get_all_definitions()
        assert isinstance(definitions, list)
        assert len(definitions) > 0
        assert all(isinstance(d, StepTypeDefinition) for d in definitions)

    def test_definitions_have_valid_domains(self):
        """All definitions report domains within the known set."""
        from ignition_toolkit.playbook.step_type_registry import get_all_definitions

        definitions = get_all_definitions()
        for defn in definitions:
            assert defn.domain in KNOWN_DOMAINS, (
                f"Definition '{defn.type_value}' has unknown domain: '{defn.domain}'"
            )

    def test_definitions_have_non_empty_descriptions(self):
        """All definitions have a non-empty description string."""
        from ignition_toolkit.playbook.step_type_registry import get_all_definitions

        definitions = get_all_definitions()
        for defn in definitions:
            assert defn.description, (
                f"Definition '{defn.type_value}' has empty description"
            )
