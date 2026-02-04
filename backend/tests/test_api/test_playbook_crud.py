"""
Tests for playbook CRUD API endpoints

Tests list, get, update, and delete operations for playbooks.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create test client with mocked dependencies"""
    # Mock the database and other dependencies before importing app
    with patch('ignition_toolkit.storage.get_database') as mock_db:
        mock_db.return_value = MagicMock()

        from ignition_toolkit.api.app import app
        client = TestClient(app)
        yield client


@pytest.fixture
def sample_playbook_yaml():
    """Sample playbook YAML content"""
    return """
name: Test Playbook
version: "1.0"
description: A test playbook for API testing
domain: gateway
steps:
  - id: step1
    name: First Step
    type: utility.log
    parameters:
      message: "Hello from test"
"""


@pytest.fixture
def temp_playbooks_dir(tmp_path):
    """Create a temporary playbooks directory with sample playbooks"""
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()

    # Create gateway subdirectory
    gateway_dir = playbooks_dir / "gateway"
    gateway_dir.mkdir()

    # Create sample playbook
    sample = gateway_dir / "test_playbook.yaml"
    sample.write_text("""
name: Test Playbook
version: "1.0"
description: A test playbook
domain: gateway
steps:
  - id: step1
    name: Log Message
    type: utility.log
    parameters:
      message: "Test"
""")

    # Create another playbook
    another = gateway_dir / "another_playbook.yaml"
    another.write_text("""
name: Another Playbook
version: "2.0"
description: Another test playbook
domain: gateway
steps:
  - id: step1
    name: Sleep
    type: utility.sleep
    parameters:
      seconds: 1
""")

    return playbooks_dir


class TestPlaybookMetadataValidation:
    """Test Pydantic validation for playbook metadata requests"""

    def test_valid_metadata_update(self):
        """Test valid metadata update request"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest

        request = PlaybookMetadataUpdateRequest(
            playbook_path="gateway/test.yaml",
            name="New Name",
            description="New description"
        )

        assert request.name == "New Name"
        assert request.description == "New description"

    def test_name_too_long_raises_error(self):
        """Test that overly long names are rejected"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PlaybookMetadataUpdateRequest(
                playbook_path="test.yaml",
                name="x" * 300  # Over 200 char limit
            )

        assert "too long" in str(exc_info.value).lower()

    def test_name_with_dangerous_chars_raises_error(self):
        """Test that dangerous characters in name are rejected"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest
        from pydantic import ValidationError

        dangerous_names = [
            "Test<script>",
            "Test'name",
            'Test"name',
            "Test`name",
            "Test{name}",
            "Test$name",
            "Test|name",
            "Test&name",
            "Test;name",
        ]

        for name in dangerous_names:
            with pytest.raises(ValidationError):
                PlaybookMetadataUpdateRequest(
                    playbook_path="test.yaml",
                    name=name
                )

    def test_description_too_long_raises_error(self):
        """Test that overly long descriptions are rejected"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            PlaybookMetadataUpdateRequest(
                playbook_path="test.yaml",
                description="x" * 3000  # Over 2000 char limit
            )

        assert "too long" in str(exc_info.value).lower()

    def test_description_with_xss_patterns_raises_error(self):
        """Test that XSS patterns in description are rejected"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest
        from pydantic import ValidationError

        dangerous_descriptions = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            '<img onerror="alert(1)">',
            '<div onload="alert(1)">',
            "<?php echo 'xss'; ?>",
        ]

        for desc in dangerous_descriptions:
            with pytest.raises(ValidationError):
                PlaybookMetadataUpdateRequest(
                    playbook_path="test.yaml",
                    description=desc
                )

    def test_empty_path_raises_error(self):
        """Test that empty playbook path is rejected"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PlaybookMetadataUpdateRequest(
                playbook_path="",
                name="Test"
            )

    def test_whitespace_is_trimmed(self):
        """Test that whitespace is trimmed from inputs"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookMetadataUpdateRequest

        request = PlaybookMetadataUpdateRequest(
            playbook_path="  gateway/test.yaml  ",
            name="  Trimmed Name  ",
            description="  Trimmed Description  "
        )

        assert request.playbook_path == "gateway/test.yaml"
        assert request.name == "Trimmed Name"
        assert request.description == "Trimmed Description"


class TestPlaybookPathValidation:
    """Test playbook path validation for security"""

    def test_directory_traversal_rejected(self, temp_playbooks_dir):
        """Test that directory traversal attempts are rejected"""
        from ignition_toolkit.api.routers.playbook_crud import validate_playbook_path
        from fastapi import HTTPException

        with patch('ignition_toolkit.core.paths.get_playbooks_dir', return_value=temp_playbooks_dir):
            # These should all raise HTTPException
            dangerous_paths = [
                "../etc/passwd",
                "gateway/../../../etc/passwd",
                "..\\windows\\system32",
                "gateway/..\\..\\..\\etc\\passwd",
            ]

            for path in dangerous_paths:
                with pytest.raises(HTTPException) as exc_info:
                    validate_playbook_path(path)
                assert exc_info.value.status_code in [400, 404]

    def test_absolute_path_rejected(self, temp_playbooks_dir):
        """Test that absolute paths are rejected"""
        from ignition_toolkit.api.routers.playbook_crud import validate_playbook_path
        from fastapi import HTTPException

        with patch('ignition_toolkit.core.paths.get_playbooks_dir', return_value=temp_playbooks_dir):
            with pytest.raises(HTTPException):
                validate_playbook_path("/etc/passwd")

    def test_valid_relative_path_accepted(self, temp_playbooks_dir):
        """Test that valid relative paths are accepted"""
        from ignition_toolkit.core.validation import PathValidator

        # Use PathValidator directly with explicit base_dir
        result = PathValidator.validate_playbook_path(
            "gateway/test_playbook.yaml",
            base_dir=temp_playbooks_dir,
            must_exist=True
        )
        assert result.exists()
        assert result.name == "test_playbook.yaml"


class TestStepEditRequest:
    """Test step edit request validation"""

    def test_valid_step_edit_request(self):
        """Test valid step edit request"""
        from ignition_toolkit.api.routers.playbook_crud import StepEditRequest

        request = StepEditRequest(
            playbook_path="gateway/test.yaml",
            step_id="step1",
            new_parameters={"message": "Updated message", "level": "info"}
        )

        assert request.playbook_path == "gateway/test.yaml"
        assert request.step_id == "step1"
        assert request.new_parameters["message"] == "Updated message"

    def test_empty_parameters_allowed(self):
        """Test that empty parameters dict is allowed"""
        from ignition_toolkit.api.routers.playbook_crud import StepEditRequest

        request = StepEditRequest(
            playbook_path="gateway/test.yaml",
            step_id="step1",
            new_parameters={}
        )

        assert request.new_parameters == {}

    def test_complex_parameters(self):
        """Test step edit with complex nested parameters"""
        from ignition_toolkit.api.routers.playbook_crud import StepEditRequest

        request = StepEditRequest(
            playbook_path="gateway/test.yaml",
            step_id="step1",
            new_parameters={
                "selector": {
                    "type": "css",
                    "value": "#my-button"
                },
                "timeout": 30,
                "options": ["option1", "option2"]
            }
        )

        assert request.new_parameters["selector"]["type"] == "css"
        assert request.new_parameters["timeout"] == 30


class TestPlaybookUpdateRequest:
    """Test playbook update request validation"""

    def test_valid_update_request(self, sample_playbook_yaml):
        """Test valid playbook update request"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookUpdateRequest

        request = PlaybookUpdateRequest(
            playbook_path="gateway/test.yaml",
            yaml_content=sample_playbook_yaml
        )

        assert request.playbook_path == "gateway/test.yaml"
        assert "name: Test Playbook" in request.yaml_content

    def test_empty_yaml_content_allowed(self):
        """Test that empty YAML content is allowed at request level"""
        from ignition_toolkit.api.routers.playbook_crud import PlaybookUpdateRequest

        # Pydantic allows empty string, validation happens at endpoint level
        request = PlaybookUpdateRequest(
            playbook_path="gateway/test.yaml",
            yaml_content=""
        )

        assert request.yaml_content == ""
