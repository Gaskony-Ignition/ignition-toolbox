"""
Tests for playbook loader functionality

Tests YAML parsing, validation, and error handling.
"""

import pytest

from ignition_toolkit.playbook.exceptions import (
    PlaybookLoadError,
    PlaybookValidationError,
    YAMLParseError,
)
from ignition_toolkit.playbook.loader import PlaybookLoader
from ignition_toolkit.playbook.models import (
    ParameterType,
    StepType,
)


class TestPlaybookLoaderBasic:
    """Test basic playbook loading functionality"""

    def test_load_valid_playbook_from_string(self):
        """Test loading a valid playbook from YAML string"""
        yaml_content = """
name: Test Playbook
version: "1.0"
description: A test playbook
steps:
  - id: step1
    name: First Step
    type: utility.log
    parameters:
      message: "Hello"
"""
        playbook = PlaybookLoader.load_from_string(yaml_content)

        assert playbook.name == "Test Playbook"
        assert playbook.version == "1.0"
        assert playbook.description == "A test playbook"
        assert len(playbook.steps) == 1
        assert playbook.steps[0].id == "step1"
        assert playbook.steps[0].type == StepType.LOG

    def test_load_playbook_with_parameters(self):
        """Test loading a playbook with parameter definitions"""
        yaml_content = """
name: Parameterized Playbook
version: "1.0"
parameters:
  - name: gateway_url
    type: string
    required: true
    description: URL of the gateway
  - name: timeout
    type: integer
    required: false
    default: 30
steps:
  - id: step1
    name: Connect
    type: utility.log
    parameters:
      message: "Connecting to {{ gateway_url }}"
"""
        playbook = PlaybookLoader.load_from_string(yaml_content)

        assert len(playbook.parameters) == 2
        assert playbook.parameters[0].name == "gateway_url"
        assert playbook.parameters[0].type == ParameterType.STRING
        assert playbook.parameters[0].required is True
        assert playbook.parameters[1].name == "timeout"
        assert playbook.parameters[1].default == 30

    def test_load_playbook_from_file(self, tmp_path):
        """Test loading a playbook from a file"""
        playbook_file = tmp_path / "test_playbook.yaml"
        playbook_file.write_text("""
name: File Playbook
version: "1.0"
steps:
  - id: step1
    name: Test Step
    type: utility.log
    parameters:
      message: "Test"
""")
        playbook = PlaybookLoader.load_from_file(playbook_file)

        assert playbook.name == "File Playbook"
        assert len(playbook.steps) == 1

    def test_load_playbook_with_metadata(self):
        """Test loading a playbook with domain and group metadata"""
        yaml_content = """
name: Gateway Playbook
version: "1.0"
domain: gateway
group: maintenance
verified: true
steps:
  - id: step1
    name: Step
    type: utility.log
    parameters:
      message: "Test"
"""
        playbook = PlaybookLoader.load_from_string(yaml_content)

        assert playbook.metadata.get("domain") == "gateway"
        assert playbook.metadata.get("group") == "maintenance"
        assert playbook.metadata.get("verified") is True


class TestPlaybookLoaderValidation:
    """Test playbook validation"""

    def test_missing_name_raises_error(self):
        """Test that missing 'name' field raises validation error"""
        yaml_content = """
version: "1.0"
steps:
  - id: step1
    name: Step
    type: utility.log
"""
        with pytest.raises(PlaybookValidationError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "name" in str(exc_info.value).lower()

    def test_missing_version_raises_error(self):
        """Test that missing 'version' field raises validation error"""
        yaml_content = """
name: Test
steps:
  - id: step1
    name: Step
    type: utility.log
"""
        with pytest.raises(PlaybookValidationError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "version" in str(exc_info.value).lower()

    def test_missing_steps_raises_error(self):
        """Test that missing 'steps' field raises validation error"""
        yaml_content = """
name: Test
version: "1.0"
"""
        with pytest.raises(PlaybookValidationError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "steps" in str(exc_info.value).lower()

    def test_empty_steps_raises_error(self):
        """Test that empty steps list raises validation error"""
        yaml_content = """
name: Test
version: "1.0"
steps: []
"""
        with pytest.raises(PlaybookValidationError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "at least one step" in str(exc_info.value).lower()

    def test_duplicate_step_ids_raises_error(self):
        """Test that duplicate step IDs raise validation error"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
    name: First
    type: utility.log
  - id: step1
    name: Duplicate
    type: utility.log
"""
        with pytest.raises(PlaybookValidationError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "unique" in str(exc_info.value).lower()

    def test_invalid_step_type_raises_error(self):
        """Test that invalid step type raises validation error"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
    name: Step
    type: invalid.type
"""
        with pytest.raises(PlaybookValidationError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "invalid step type" in str(exc_info.value).lower()

    def test_invalid_parameter_type_raises_error(self):
        """Test that invalid parameter type raises validation error"""
        yaml_content = """
name: Test
version: "1.0"
parameters:
  - name: param1
    type: invalid_type
steps:
  - id: step1
    name: Step
    type: utility.log
"""
        with pytest.raises(PlaybookValidationError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "invalid parameter type" in str(exc_info.value).lower()


class TestYAMLParseErrors:
    """Test YAML parsing error handling with line numbers"""

    def test_yaml_syntax_error_includes_line_number(self):
        """Test that YAML syntax errors include line number"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
    name: Step
    type: utility.log
    parameters:
      message: "Missing closing quote
"""
        with pytest.raises(YAMLParseError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        # Verify line number is captured
        assert exc_info.value.line_number is not None

    def test_yaml_indentation_error(self):
        """Test that YAML indentation errors are caught"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
   name: Bad Indent
    type: utility.log
"""
        with pytest.raises(YAMLParseError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        assert "recovery" in str(exc_info.value).lower()

    def test_file_not_found_error(self, tmp_path):
        """Test that file not found error is handled"""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(PlaybookLoadError) as exc_info:
            PlaybookLoader.load_from_file(nonexistent)

        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.file_path == str(nonexistent)

    def test_yaml_error_includes_recovery_hint(self):
        """Test that YAML errors include recovery hints"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
    name: Step
    type: utility.log
    parameters:
      message: @invalid
"""
        with pytest.raises(YAMLParseError) as exc_info:
            PlaybookLoader.load_from_string(yaml_content)

        # Should include helpful recovery hints
        error_str = str(exc_info.value)
        assert "recovery" in error_str.lower() or "💡" in error_str


class TestPlaybookStepParsing:
    """Test step parsing with various configurations"""

    def test_step_with_on_failure(self):
        """Test parsing step with on_failure configuration"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
    name: Step
    type: utility.log
    on_failure: continue
    parameters:
      message: "Test"
"""
        playbook = PlaybookLoader.load_from_string(yaml_content)

        from ignition_toolkit.playbook.models import OnFailureAction

        assert playbook.steps[0].on_failure == OnFailureAction.CONTINUE

    def test_step_with_timeout_and_retry(self):
        """Test parsing step with timeout and retry configuration"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
    name: Step
    type: utility.log
    timeout: 60
    retry_count: 3
    retry_delay: 10
    parameters:
      message: "Test"
"""
        playbook = PlaybookLoader.load_from_string(yaml_content)

        assert playbook.steps[0].timeout == 60
        assert playbook.steps[0].retry_count == 3
        assert playbook.steps[0].retry_delay == 10

    def test_step_default_values(self):
        """Test that steps have correct default values"""
        yaml_content = """
name: Test
version: "1.0"
steps:
  - id: step1
    name: Step
    type: utility.log
"""
        playbook = PlaybookLoader.load_from_string(yaml_content)

        from ignition_toolkit.playbook.models import OnFailureAction

        assert playbook.steps[0].timeout == 300  # Default timeout
        assert playbook.steps[0].retry_count == 0  # Default no retries
        assert playbook.steps[0].on_failure == OnFailureAction.ABORT


class TestPlaybookSerialization:
    """Test playbook serialization (save to file)"""

    def test_save_and_reload_playbook(self, tmp_path):
        """Test that a playbook can be saved and reloaded"""
        yaml_content = """
name: Roundtrip Test
version: "2.0"
description: Test save and reload
parameters:
  - name: param1
    type: string
    required: true
steps:
  - id: step1
    name: Step One
    type: utility.log
    parameters:
      message: "Hello"
"""
        original = PlaybookLoader.load_from_string(yaml_content)

        # Save to file
        output_file = tmp_path / "saved_playbook.yaml"
        PlaybookLoader.save_to_file(original, output_file)

        # Reload and verify
        reloaded = PlaybookLoader.load_from_file(output_file)

        assert reloaded.name == original.name
        assert reloaded.version == original.version
        assert reloaded.description == original.description
        assert len(reloaded.parameters) == len(original.parameters)
        assert len(reloaded.steps) == len(original.steps)
        assert reloaded.steps[0].id == original.steps[0].id
