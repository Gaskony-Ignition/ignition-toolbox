"""
Tests for ignition_toolkit/core/validation_limits.py

Covers: ValidationLimits class fields are present and have positive integer values.
"""

import pytest


class TestValidationLimits:
    """Tests for the ValidationLimits class."""

    def test_class_exists(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits is not None

    # --- Parameter limits ---

    def test_parameter_count_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PARAMETER_COUNT_MAX > 0

    def test_parameter_count_max_is_int(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert isinstance(ValidationLimits.PARAMETER_COUNT_MAX, int)

    def test_parameter_name_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PARAMETER_NAME_MAX > 0

    def test_parameter_name_max_is_int(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert isinstance(ValidationLimits.PARAMETER_NAME_MAX, int)

    def test_parameter_value_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PARAMETER_VALUE_MAX > 0

    def test_parameter_value_max_is_int(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert isinstance(ValidationLimits.PARAMETER_VALUE_MAX, int)

    # --- URL / path limits ---

    def test_gateway_url_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.GATEWAY_URL_MAX > 0

    def test_playbook_path_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PLAYBOOK_PATH_MAX > 0

    # --- Metadata limits ---

    def test_playbook_name_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PLAYBOOK_NAME_MAX > 0

    def test_playbook_description_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PLAYBOOK_DESCRIPTION_MAX > 0

    def test_tag_max_length_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.TAG_MAX_LENGTH > 0

    def test_tag_count_max_is_positive(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.TAG_COUNT_MAX > 0

    # --- Specific expected values ---

    def test_parameter_count_max_expected_value(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PARAMETER_COUNT_MAX == 50

    def test_parameter_name_max_expected_value(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PARAMETER_NAME_MAX == 255

    def test_parameter_value_max_expected_value(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PARAMETER_VALUE_MAX == 10000

    def test_playbook_name_max_expected_value(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PLAYBOOK_NAME_MAX == 200

    def test_playbook_description_max_expected_value(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.PLAYBOOK_DESCRIPTION_MAX == 2000

    def test_tag_max_length_expected_value(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.TAG_MAX_LENGTH == 50

    def test_tag_count_max_expected_value(self):
        from ignition_toolkit.core.validation_limits import ValidationLimits

        assert ValidationLimits.TAG_COUNT_MAX == 20

    def test_all_limits_are_positive_ints(self):
        """Comprehensive check: every public attribute must be a positive int."""
        from ignition_toolkit.core.validation_limits import ValidationLimits

        attrs = [a for a in dir(ValidationLimits) if not a.startswith("_")]
        assert len(attrs) > 0, "ValidationLimits has no public attributes"
        for attr in attrs:
            value = getattr(ValidationLimits, attr)
            assert isinstance(value, int), f"{attr} must be int, got {type(value)}"
            assert value > 0, f"{attr} must be positive, got {value}"
