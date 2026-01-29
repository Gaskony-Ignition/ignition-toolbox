"""
Playbook exporter - Export/import playbooks as JSON

Handles exporting playbooks to JSON format for sharing, with credential references
stripped for security.
"""

import json
import re
from typing import Any

from ignition_toolkit.playbook.exceptions import PlaybookLoadError
from ignition_toolkit.playbook.loader import PlaybookLoader
from ignition_toolkit.playbook.models import Playbook


class PlaybookExporter:
    """
    Export and import playbooks as JSON

    Example:
        exporter = PlaybookExporter()

        # Export playbook (strips credentials)
        json_data = exporter.export(playbook)

        # Import playbook
        playbook = exporter.import_from_json(json_data)
    """

    # Pattern to detect credential references
    CREDENTIAL_PATTERN = re.compile(r"\{\{\s*credential\.\w+.*?\}\}")

    @staticmethod
    def export(playbook: Playbook, strip_credentials: bool = True) -> str:
        """
        Export playbook to JSON

        Args:
            playbook: Playbook to export
            strip_credentials: Strip credential values for security

        Returns:
            JSON string
        """
        # Convert to dict using loader serialization
        data = PlaybookLoader._serialize_playbook(playbook)

        # Strip credentials if requested
        if strip_credentials:
            data = PlaybookExporter._strip_credentials(data)

        # Add export metadata
        data["_export_metadata"] = {
            "version": "1.0",
            "exported_by": "Ignition Automation Toolkit",
            "credentials_stripped": strip_credentials,
        }

        return json.dumps(data, indent=2)

    @staticmethod
    def import_from_json(json_data: str) -> Playbook:
        """
        Import playbook from JSON

        Args:
            json_data: JSON string

        Returns:
            Playbook object

        Raises:
            PlaybookLoadError: If JSON is invalid
        """
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise PlaybookLoadError(f"Invalid JSON: {e}")

        # Remove export metadata if present
        if "_export_metadata" in data:
            del data["_export_metadata"]

        # Parse using loader
        return PlaybookLoader._parse_playbook(data)

    @staticmethod
    def _strip_credentials(data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively strip credential values from data structure

        Replaces actual credential values with references.

        Args:
            data: Data structure to process

        Returns:
            Processed data with credentials stripped
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Check if this is a parameter with type credential
                if key == "type" and value == "credential":
                    result[key] = value
                elif key == "default" and isinstance(data.get("type"), str):
                    # Don't include default values for credential parameters
                    if data.get("type") == "credential":
                        continue
                    else:
                        result[key] = PlaybookExporter._strip_credentials(value)
                else:
                    result[key] = PlaybookExporter._strip_credentials(value)
            return result

        elif isinstance(data, list):
            return [PlaybookExporter._strip_credentials(item) for item in data]

        elif isinstance(data, str):
            # Check if string contains credential reference - keep as-is
            if PlaybookExporter.CREDENTIAL_PATTERN.search(data):
                return data
            # Otherwise return as-is (could be any string)
            return data

        else:
            # Primitive values (int, float, bool, None)
            return data

    @staticmethod
    def export_to_file(playbook: Playbook, file_path: str, strip_credentials: bool = True) -> None:
        """
        Export playbook to JSON file

        Args:
            playbook: Playbook to export
            file_path: Output file path
            strip_credentials: Strip credential values
        """
        json_data = PlaybookExporter.export(playbook, strip_credentials)
        with open(file_path, "w", encoding='utf-8') as f:
            f.write(json_data)

    @staticmethod
    def import_from_file(file_path: str) -> Playbook:
        """
        Import playbook from JSON file

        Args:
            file_path: JSON file path

        Returns:
            Playbook object

        Raises:
            PlaybookLoadError: If file cannot be read
        """
        try:
            with open(file_path, encoding='utf-8') as f:
                json_data = f.read()
        except Exception as e:
            raise PlaybookLoadError(f"Error reading file: {e}")

        return PlaybookExporter.import_from_json(json_data)
