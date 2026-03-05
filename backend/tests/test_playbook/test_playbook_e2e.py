"""
End-to-end playbook validation tests.

Validates every playbook YAML across the full pipeline:
1. YAML loads correctly via PlaybookLoader
2. Every step's parameters match what the handler actually reads
3. Variable/parameter references point to something that exists
4. Nested playbook paths resolve to existing files
5. Selector syntax avoids known anti-patterns
6. Step-level vs parameter-level properties are not confused

These tests catch the class of bugs that caused repeated fixes to
gateway_restart (v3.0→v3.3) and module_uninstall (v4.0→v4.1).
"""

from pathlib import Path

import pytest
import yaml

from ignition_toolkit.playbook.loader import PlaybookLoader
from ignition_toolkit.playbook.models import StepType
from ignition_toolkit.playbook.step_type_registry import (
    get_step_definition,
    get_all_definitions,
)

# Directories containing playbooks
LIBRARY_DIR = Path(__file__).parent.parent.parent.parent / "library"
BACKEND_PLAYBOOKS_DIR = Path(__file__).parent.parent.parent / "playbooks"
BUNDLED_PLAYBOOKS_DIR = (
    Path(__file__).parent.parent.parent / "ignition_toolkit" / "playbooks"
)

# All playbook directories to scan
PLAYBOOK_DIRS = [LIBRARY_DIR, BACKEND_PLAYBOOKS_DIR]
# Add bundled dir only if it exists (may not in all setups)
if BUNDLED_PLAYBOOKS_DIR.is_dir():
    PLAYBOOK_DIRS.append(BUNDLED_PLAYBOOKS_DIR)

# Parameter names that handlers actually read (from browser_executor.py, etc.)
# This is the ground truth — derived from reading the handler source code.
HANDLER_PARAMS = {
    "browser.navigate": {"url", "wait_until"},
    "browser.click": {"selector", "timeout", "force"},
    "browser.fill": {"selector", "value", "timeout"},
    "browser.file_upload": {"selector", "file_path", "timeout"},
    "browser.screenshot": {"name", "full_page"},
    "browser.wait": {"selector", "timeout"},
    "browser.verify": {"selector", "exists", "timeout"},
    "browser.verify_text": {"selector", "text", "match", "timeout"},
    "browser.verify_attribute": {"selector", "attribute", "value", "timeout"},
    "browser.verify_state": {"selector", "state", "timeout"},
    "browser.get_text": {"selector", "variable_name", "timeout"},
    "browser.keyboard": {"key"},
    "gateway.login": {"credential"},
    "gateway.logout": set(),
    "gateway.ping": set(),
    "gateway.get_info": set(),
    "gateway.get_health": set(),
    "gateway.list_modules": set(),
    "gateway.upload_module": {"file"},
    "gateway.wait_for_module_installation": {"module_name", "timeout"},
    "gateway.list_projects": set(),
    "gateway.get_project": {"project_name"},
    "gateway.restart": {"wait_for_ready", "timeout"},
    "gateway.wait_for_ready": {"timeout"},
    "designer.launch": {"launcher_file"},
    "designer.launch_shortcut": {
        "designer_shortcut", "project_name", "gateway_credential",
        "username", "password", "timeout",
    },
    "designer.login": {"username", "password", "timeout"},
    "designer.open_project": {"project_name", "timeout"},
    "designer.close": set(),
    "designer.screenshot": {"name"},
    "designer.wait": {"timeout"},
    "playbook.run": {"playbook"},  # handler reads "playbook", NOT "playbook_path"
    "utility.sleep": {"seconds"},
    "utility.log": {"message", "level"},
    "utility.set_variable": {"name", "value"},
    "utility.python": {"script"},
    "perspective.discover_page": {"selector", "types", "exclude_selectors"},
    "perspective.extract_component_metadata": {"components"},
    "perspective.execute_test_manifest": {
        "manifest", "capture_screenshots", "on_failure",
        "return_to_baseline", "baseline_url",
    },
    "perspective.verify_navigation": {"expected_url_pattern", "expected_title_pattern", "timeout"},
    "perspective.verify_dock_opened": {"dock_selector", "timeout"},
    "perspective.verify_with_ai": {
        "prompt", "ai_api_key", "selector", "confidence_threshold", "ai_model",
    },
    "fat.generate_report": {"test_results", "title", "include_screenshots"},
    "fat.export_report": {"report", "output_path", "format"},
}

# Known parameter aliases that are WRONG (common mistakes)
WRONG_PARAM_ALIASES = {
    "browser.navigate": {"wait_for": "wait_until"},
    "browser.screenshot": {"path": "name"},
    "browser.verify": {"state": "use browser.verify_state instead", "condition": "exists"},
}

# Step-level properties that should NOT be inside parameters dict
STEP_LEVEL_PROPERTIES = {"retry_count", "retry_delay", "on_failure", "timeout"}

# For playbook.run steps, these are passed as nested playbook parameters, not handler params
PLAYBOOK_RUN_PASS_THROUGH = True  # playbook.run passes all extra params to child


def collect_all_playbooks() -> list[tuple[Path, str]]:
    """Collect all YAML playbook files with a label."""
    playbooks = []
    for base_dir in PLAYBOOK_DIRS:
        if not base_dir.is_dir():
            continue
        for yaml_file in sorted(base_dir.rglob("*.yaml")):
            label = f"{base_dir.name}/{yaml_file.relative_to(base_dir)}"
            playbooks.append((yaml_file, label))
    return playbooks


def collect_all_library_playbooks() -> list[tuple[Path, str]]:
    """Collect playbook files from library/ only."""
    playbooks = []
    if not LIBRARY_DIR.is_dir():
        return playbooks
    for yaml_file in sorted(LIBRARY_DIR.rglob("*.yaml")):
        label = f"library/{yaml_file.relative_to(LIBRARY_DIR)}"
        playbooks.append((yaml_file, label))
    return playbooks


ALL_PLAYBOOKS = collect_all_playbooks()
LIBRARY_PLAYBOOKS = collect_all_library_playbooks()


# =============================================================================
# Test 1: Every playbook loads through the full PlaybookLoader pipeline
# =============================================================================

class TestPlaybookLoaderE2E:
    """Verify every YAML loads via PlaybookLoader without error."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_playbook_loads_via_loader(self, yaml_path: Path, label: str):
        """PlaybookLoader.load_from_file succeeds for every playbook."""
        playbook = PlaybookLoader.load_from_file(yaml_path)
        assert playbook.name, f"{label}: playbook name is empty"
        assert playbook.steps, f"{label}: playbook has no steps"


# =============================================================================
# Test 2: Step parameters match what handlers actually read
# =============================================================================

class TestStepParameterContracts:
    """Verify every step passes parameters the handler actually reads."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_no_wrong_parameter_aliases(self, yaml_path: Path, label: str):
        """Catch common parameter name mistakes (wait_for→wait_until, path→name, etc.)."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            step_type = step.get("type", "")
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            wrong_aliases = WRONG_PARAM_ALIASES.get(step_type, {})
            for wrong_name, correct_name in wrong_aliases.items():
                if wrong_name in params:
                    failures.append(
                        f"  {step.get('id', f'step[{i}]')}: "
                        f"'{step_type}' uses '{wrong_name}' but handler reads "
                        f"'{correct_name}' — parameter is silently ignored"
                    )

        assert not failures, (
            f"{label}: {len(failures)} wrong parameter name(s):\n"
            + "\n".join(failures)
        )

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_no_unknown_parameters(self, yaml_path: Path, label: str):
        """Every parameter passed to a step is recognized by the handler."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            step_type = step.get("type", "")
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            known_params = HANDLER_PARAMS.get(step_type)
            if known_params is None:
                continue  # Unknown step type — caught by other tests

            # playbook.run passes extra params to nested playbook, so skip those
            if step_type == "playbook.run":
                continue

            for param_name in params:
                if param_name not in known_params:
                    failures.append(
                        f"  {step.get('id', f'step[{i}]')}: "
                        f"'{step_type}' receives unknown param '{param_name}' "
                        f"(handler reads: {sorted(known_params)})"
                    )

        assert not failures, (
            f"{label}: {len(failures)} unknown parameter(s):\n"
            + "\n".join(failures)
        )

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_required_parameters_present(self, yaml_path: Path, label: str):
        """Every step provides all required parameters for its type."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            step_type_str = step.get("type", "")
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                params = {}

            try:
                step_type_enum = StepType(step_type_str)
            except ValueError:
                continue  # Caught by other tests

            defn = get_step_definition(step_type_enum)
            if defn is None:
                continue

            for param_def in defn.parameters:
                if not param_def.required:
                    continue
                # playbook.run: 'playbook_path' in registry but 'playbook' in handler
                if step_type_str == "playbook.run" and param_def.name == "playbook_path":
                    if "playbook" not in params:
                        failures.append(
                            f"  {step.get('id', f'step[{i}]')}: "
                            f"'{step_type_str}' missing required 'playbook'"
                        )
                    continue

                if param_def.name not in params:
                    failures.append(
                        f"  {step.get('id', f'step[{i}]')}: "
                        f"'{step_type_str}' missing required param '{param_def.name}'"
                    )

        assert not failures, (
            f"{label}: {len(failures)} missing required parameter(s):\n"
            + "\n".join(failures)
        )


# =============================================================================
# Test 3: Step-level properties are not confused with parameters
# =============================================================================

class TestStepStructure:
    """Verify step-level properties are at the right level."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_step_properties_not_in_parameters(self, yaml_path: Path, label: str):
        """retry_count, retry_delay should be at step level, not inside parameters."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            # These should never be inside parameters (except for specific step types
            # that legitimately use "timeout" as a handler parameter)
            step_type = step.get("type", "")
            for prop in ["retry_count", "retry_delay"]:
                if prop in params:
                    failures.append(
                        f"  {step.get('id', f'step[{i}]')}: "
                        f"'{prop}' is inside 'parameters' but should be at step level"
                    )

        assert not failures, (
            f"{label}: {len(failures)} misplaced step property(ies):\n"
            + "\n".join(failures)
        )

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_on_failure_and_timeout_at_step_level_not_parameter_level(
        self, yaml_path: Path, label: str
    ):
        """on_failure must be at step level, not inside parameters dict.

        timeout can be at either level depending on context:
          - Step level: overall step timeout (seconds, used by engine)
          - Parameter level: handler-specific timeout (ms for browser ops)
        But on_failure is ONLY a step-level property.
        """
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            if "on_failure" in params:
                failures.append(
                    f"  {step.get('id', f'step[{i}]')}: "
                    f"'on_failure' is inside 'parameters' but should be at step level"
                )

        assert not failures, (
            f"{label}: {len(failures)} misplaced property(ies):\n"
            + "\n".join(failures)
        )


# =============================================================================
# Test 4: Variable and parameter references
# =============================================================================

class TestReferenceIntegrity:
    """Verify that variable/parameter references can be resolved."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_parameter_references_point_to_declared_parameters(
        self, yaml_path: Path, label: str
    ):
        """{{ parameter.X }} references must match a declared parameter name."""
        import re

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        declared_params = set()
        for p in data.get("parameters", []):
            if isinstance(p, dict):
                declared_params.add(p.get("name", ""))

        failures = []
        param_ref_pattern = re.compile(r"\{\{\s*parameter\.(\w+)\s*\}\}")

        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            for key, value in params.items():
                if not isinstance(value, str):
                    continue
                for match in param_ref_pattern.finditer(value):
                    ref_name = match.group(1)
                    if ref_name not in declared_params:
                        failures.append(
                            f"  {step.get('id', f'step[{i}]')}.{key}: "
                            f"references '{{{{ parameter.{ref_name} }}}}' "
                            f"but no parameter '{ref_name}' is declared"
                        )

        assert not failures, (
            f"{label}: {len(failures)} unresolvable parameter reference(s):\n"
            + "\n".join(failures)
        )

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_variable_references_set_before_use(self, yaml_path: Path, label: str):
        """{{ variable.X }} references must be set by a prior step."""
        import re

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        var_ref_pattern = re.compile(r"\{\{\s*variable\.(\w+)\s*\}\}")
        set_var_pattern = re.compile(r"set_variable\(\s*['\"](\w+)['\"]")

        set_variables = set()
        failures = []

        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            step_type = step.get("type", "")
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            # Check for variable references in this step's parameters
            for key, value in params.items():
                if not isinstance(value, str):
                    continue
                for match in var_ref_pattern.finditer(value):
                    ref_name = match.group(1)
                    if ref_name not in set_variables:
                        failures.append(
                            f"  {step.get('id', f'step[{i}]')}.{key}: "
                            f"references '{{{{ variable.{ref_name} }}}}' "
                            f"but no prior step sets variable '{ref_name}'"
                        )

            # Track variables set by utility.set_variable steps
            if step_type == "utility.set_variable":
                var_name = params.get("name")
                if var_name:
                    set_variables.add(var_name)

            # Track variables set by utility.python set_variable() calls
            if step_type == "utility.python":
                script = params.get("script", "")
                if isinstance(script, str):
                    for match in set_var_pattern.finditer(script):
                        set_variables.add(match.group(1))

        assert not failures, (
            f"{label}: {len(failures)} variable reference(s) used before set:\n"
            + "\n".join(failures)
        )


# =============================================================================
# Test 5: Nested playbook references resolve to existing files
# =============================================================================

class TestNestedPlaybookPaths:
    """Verify playbook.run references point to real files."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_nested_playbook_paths_exist(self, yaml_path: Path, label: str):
        """Every playbook.run step references a playbook that exists."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            if step.get("type") != "playbook.run":
                continue

            params = step.get("parameters", {})
            playbook_ref = params.get("playbook", "")
            if not playbook_ref or "{{" in playbook_ref:
                continue  # Dynamic reference, can't validate statically

            # Check if the referenced playbook exists in any known directory
            found = False
            for base_dir in [LIBRARY_DIR, BACKEND_PLAYBOOKS_DIR]:
                if not base_dir.is_dir():
                    continue
                candidate = base_dir / playbook_ref
                if candidate.exists():
                    found = True
                    break

            if not found:
                failures.append(
                    f"  {step.get('id', f'step[{i}]')}: "
                    f"references '{playbook_ref}' but file not found in "
                    f"library/ or backend/playbooks/"
                )

        assert not failures, (
            f"{label}: {len(failures)} missing nested playbook(s):\n"
            + "\n".join(failures)
        )

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_nested_playbook_receives_required_parameters(
        self, yaml_path: Path, label: str
    ):
        """playbook.run steps pass all required parameters to the nested playbook."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            if step.get("type") != "playbook.run":
                continue

            params = step.get("parameters", {})
            playbook_ref = params.get("playbook", "")
            if not playbook_ref or "{{" in playbook_ref:
                continue

            # Load the nested playbook
            nested_path = None
            for base_dir in [LIBRARY_DIR, BACKEND_PLAYBOOKS_DIR]:
                if not base_dir.is_dir():
                    continue
                candidate = base_dir / playbook_ref
                if candidate.exists():
                    nested_path = candidate
                    break

            if nested_path is None:
                continue  # Caught by test above

            with open(nested_path, encoding="utf-8") as f2:
                nested_data = yaml.safe_load(f2)

            # Check required parameters
            provided_params = set(params.keys()) - {"playbook"}
            for nested_param in nested_data.get("parameters", []):
                if not isinstance(nested_param, dict):
                    continue
                if nested_param.get("required", True) and nested_param.get("default") is None:
                    param_name = nested_param.get("name", "")
                    if param_name not in provided_params:
                        failures.append(
                            f"  {step.get('id', f'step[{i}]')}: "
                            f"calls '{playbook_ref}' but doesn't pass required "
                            f"parameter '{param_name}'"
                        )

        assert not failures, (
            f"{label}: {len(failures)} missing nested playbook parameter(s):\n"
            + "\n".join(failures)
        )


# =============================================================================
# Test 6: Selector syntax validation
# =============================================================================

class TestSelectorSyntax:
    """Validate CSS selectors don't use known anti-patterns."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_no_text_prefix_with_comma_selectors(self, yaml_path: Path, label: str):
        """Never mix text= prefix with comma-separated CSS selectors.

        BAD:  'text=I understand the risks, input[type="checkbox"]'
        GOOD: ':text("I understand the risks"), input[type="checkbox"]'
        """
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            for key in ("selector", "dock_selector"):
                selector = params.get(key, "")
                if not isinstance(selector, str):
                    continue

                # Check for text= prefix followed by comma (indicating mixed syntax)
                if selector.startswith("text=") and "," in selector:
                    failures.append(
                        f"  {step.get('id', f'step[{i}]')}.{key}: "
                        f"mixes 'text=' prefix with comma selector — "
                        f"Playwright treats entire string as text match. "
                        f"Use :has-text() or :text() CSS pseudo-classes instead. "
                        f"Selector: {selector!r}"
                    )

        assert not failures, (
            f"{label}: {len(failures)} invalid selector(s):\n"
            + "\n".join(failures)
        )


# =============================================================================
# Test 7: Unique step IDs within each playbook
# =============================================================================

class TestUniqueStepIds:
    """Verify step IDs are unique within each playbook."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_unique_step_ids(self, yaml_path: Path, label: str):
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        step_ids = []
        for step in data.get("steps", []):
            if isinstance(step, dict):
                step_ids.append(step.get("id", ""))

        duplicates = [sid for sid in step_ids if step_ids.count(sid) > 1]
        assert not duplicates, (
            f"{label}: duplicate step IDs: {sorted(set(duplicates))}"
        )


# =============================================================================
# Test 8: Library and backend playbook copies are in sync
# =============================================================================

class TestLibraryBackendSync:
    """Verify library/ and backend/playbooks/ copies match."""

    def test_library_playbooks_have_backend_copy(self):
        """Every gateway library playbook should have a matching backend copy.

        Perspective playbooks are library-only (distributed via online library),
        so only gateway/ and designer/ playbooks need backend copies.
        """
        if not LIBRARY_DIR.is_dir() or not BACKEND_PLAYBOOKS_DIR.is_dir():
            pytest.skip("library/ or backend/playbooks/ not found")

        # Only gateway/ and designer/ playbooks must be bundled
        BUNDLED_DOMAINS = {"gateway", "designer"}

        missing = []
        for yaml_file in sorted(LIBRARY_DIR.rglob("*.yaml")):
            rel_path = yaml_file.relative_to(LIBRARY_DIR)
            domain = rel_path.parts[0] if rel_path.parts else ""
            if domain not in BUNDLED_DOMAINS:
                continue
            backend_copy = BACKEND_PLAYBOOKS_DIR / rel_path
            if not backend_copy.exists():
                missing.append(str(rel_path))

        assert not missing, (
            f"{len(missing)} library playbook(s) have no backend copy:\n"
            + "\n".join(f"  {m}" for m in missing)
        )

    def test_library_and_backend_versions_match(self):
        """Library and backend copies should have the same version."""
        if not LIBRARY_DIR.is_dir() or not BACKEND_PLAYBOOKS_DIR.is_dir():
            pytest.skip("library/ or backend/playbooks/ not found")

        mismatches = []
        for yaml_file in sorted(LIBRARY_DIR.rglob("*.yaml")):
            rel_path = yaml_file.relative_to(LIBRARY_DIR)
            backend_copy = BACKEND_PLAYBOOKS_DIR / rel_path
            if not backend_copy.exists():
                continue

            with open(yaml_file, encoding="utf-8") as f:
                lib_data = yaml.safe_load(f)
            with open(backend_copy, encoding="utf-8") as f:
                backend_data = yaml.safe_load(f)

            lib_version = str(lib_data.get("version", ""))
            backend_version = str(backend_data.get("version", ""))
            if lib_version != backend_version:
                mismatches.append(
                    f"  {rel_path}: library={lib_version}, backend={backend_version}"
                )

        assert not mismatches, (
            f"{len(mismatches)} version mismatch(es):\n" + "\n".join(mismatches)
        )


# =============================================================================
# Test 9: Step type correctness (verify vs verify_state)
# =============================================================================

class TestStepTypeCorrectness:
    """Verify steps use the right step type for their parameters."""

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_verify_with_state_should_be_verify_state(
        self, yaml_path: Path, label: str
    ):
        """browser.verify steps using 'state' param should be browser.verify_state."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            step_type = step.get("type", "")
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            if step_type == "browser.verify" and "state" in params:
                failures.append(
                    f"  {step.get('id', f'step[{i}]')}: "
                    f"uses 'browser.verify' with 'state' param — "
                    f"should be 'browser.verify_state' "
                    f"(browser.verify only supports 'exists' boolean)"
                )

        assert not failures, (
            f"{label}: {len(failures)} wrong step type(s):\n"
            + "\n".join(failures)
        )

    @pytest.mark.parametrize(
        "yaml_path,label",
        ALL_PLAYBOOKS,
        ids=[label for _, label in ALL_PLAYBOOKS],
    )
    def test_browser_wait_does_not_use_state_param(
        self, yaml_path: Path, label: str
    ):
        """browser.wait only reads selector and timeout, not state."""
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        failures = []
        for i, step in enumerate(data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            if step.get("type") != "browser.wait":
                continue
            params = step.get("parameters", {})
            if not isinstance(params, dict):
                continue

            if "state" in params:
                failures.append(
                    f"  {step.get('id', f'step[{i}]')}: "
                    f"'browser.wait' has 'state' param but handler ignores it — "
                    f"browser.wait only reads 'selector' and 'timeout'"
                )

        assert not failures, (
            f"{label}: {len(failures)} invalid browser.wait param(s):\n"
            + "\n".join(failures)
        )
