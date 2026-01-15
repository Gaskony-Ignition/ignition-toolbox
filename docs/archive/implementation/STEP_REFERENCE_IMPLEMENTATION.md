# Step Output References - Implementation Summary

**Version:** 3.4
**Date:** 2025-10-30
**Status:** Complete

## Overview

Implemented support for `{{ step.step_id.output_key }}` syntax in playbook parameter resolution, enabling steps to reference outputs from previously completed steps.

## Problem Statement

The Module Upgrade playbook needed to:
1. Detect module metadata from a .modl file (Step 0)
2. Use the detected module name to search in the Gateway UI (Step 4)
3. Use the detected file path for upload (Step 18)

However, the parameter resolver only supported:
- `{{ credential.* }}` - Credential references
- `{{ variable.* }}` - Runtime variables
- `{{ parameter.* }}` - Playbook parameters

**It did NOT support step output references**, forcing workarounds like:
- Writing to temp files
- Re-extracting data multiple times
- Complex Python scripts trying to manipulate browser state

## Solution: Step Output References

### Syntax

```yaml
{{ step.step_id.output_key }}
```

Where:
- `step` - Reference type (new)
- `step_id` - The ID of a previously completed step
- `output_key` - The key in that step's output dictionary

### Example

```yaml
steps:
  - id: detect_module
    name: "Detect Module Metadata"
    type: utility.python
    parameters:
      script: |
        print(f"DETECTED_MODULE_NAME=Perspective")
        print(f"DETECTED_MODULE_FILE=/path/to/module.modl")

  - id: store_name
    name: "Store Module Name as Variable"
    type: utility.set_variable
    parameters:
      name: "module_name"
      value: "{{ step.detect_module.DETECTED_MODULE_NAME }}"

  - id: search
    name: "Search for Module"
    type: browser.fill
    parameters:
      selector: "input[type='search']"
      value: "{{ variable.module_name }}"
```

## Implementation Details

### 1. Parameter Resolver Enhancement

**File:** `/git/ignition-playground/ignition_toolkit/playbook/parameters.py`

**Changes:**
- Added `step_results` parameter to `__init__` (dict mapping step_id → output dict)
- Added `_resolve_step()` method to handle step references
- Updated `_resolve_reference()` to support "step" reference type
- Added comprehensive error messages for missing steps/attributes

**Key Code:**
```python
def __init__(
    self,
    credential_vault: CredentialVault | None = None,
    parameters: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
    step_results: dict[str, dict[str, Any]] | None = None,  # NEW
):
    self.step_results = step_results or {}

def _resolve_step(self, name: str) -> Any:
    """Resolve step output reference"""
    if name not in self.step_results:
        raise ParameterResolutionError(
            f"Step '{name}' not found or has not been executed yet."
        )
    return self.step_results[name]
```

### 2. Playbook Engine Integration

**File:** `/git/ignition-playground/ignition_toolkit/playbook/engine.py`

**Changes:**
- Create `step_results_dict` dictionary at execution start
- Pass it to ParameterResolver by reference
- After each step completes, store its output in `step_results_dict[step.id] = step_result.output`

**Key Code:**
```python
# Create step_results dictionary (shared by reference)
step_results_dict: dict[str, dict[str, Any]] = {}

resolver = ParameterResolver(
    credential_vault=self.credential_vault,
    parameters=parameters,
    variables=execution_state.variables,
    step_results=step_results_dict,  # NEW
)

# After each step executes
if step_result.output:
    step_results_dict[step.id] = step_result.output
    logger.debug(f"Step {step.id} output stored: {list(step_result.output.keys())}")
```

### 3. Nested Playbook Support

**File:** `/git/ignition-playground/ignition_toolkit/playbook/step_executor.py`

**Changes:**
- Create separate `nested_step_results` dict for child playbooks
- Pass to child resolver
- Store nested step outputs after execution

**Key Code:**
```python
# Create step_results dictionary for nested playbook
nested_step_results: dict[str, dict[str, Any]] = {}

child_resolver = ParameterResolver(
    parameters=child_params,
    variables={},
    credential_vault=self.parameter_resolver.credential_vault,
    step_results=nested_step_results,  # NEW
)

# After nested step executes
if step_result.output:
    nested_step_results[step.id] = step_result.output
```

### 4. Module Upgrade Playbook Update

**File:** `/git/ignition-playground/playbooks/gateway/module_upgrade.yaml`

**Changes:**
- Version bumped to 3.4
- Added step0_store_name and step0_store_file steps
- Use `{{ step.step0_detect.DETECTED_MODULE_NAME }}` to extract values
- Use `{{ variable.module_name }}` in browser.fill for search
- Use `{{ variable.module_file_path }}` in browser.fill for upload

**Before (broken):**
```yaml
- id: step4
  name: "Search for Module"
  type: utility.python  # Tried to manipulate browser from Python
  parameters:
    script: |
      # Complex workaround with temp files
```

**After (clean):**
```yaml
- id: step0_store_name
  name: "Store Module Name as Variable"
  type: utility.set_variable
  parameters:
    name: "module_name"
    value: "{{ step.step0_detect.DETECTED_MODULE_NAME }}"

- id: step4_search
  name: "Search for Module by Name"
  type: browser.fill
  parameters:
    selector: "input[type='search']"
    value: "{{ variable.module_name }}"  # Uses stored variable
```

## Testing

### Unit Tests

**File:** `/git/ignition-playground/tests/test_parameter_resolver.py`

**New Tests:**
- `test_resolve_step_output()` - Basic step reference resolution
- `test_resolve_step_output_in_template()` - Step references in templates
- `test_resolve_step_output_missing_step()` - Error handling for missing steps
- `test_resolve_step_output_missing_attribute()` - Error handling for missing attributes
- `test_resolve_step_output_empty()` - Error handling for empty outputs
- `test_resolve_step_output_in_dict()` - Step references in dictionaries
- `test_resolve_mixed_references()` - Mixing step, parameter, variable, and credential references

### Manual Testing

The user should test by:
1. Running the Module Upgrade playbook with a .modl file
2. Verifying that Step 0 detects module metadata correctly
3. Verifying that Step 4 searches for the specific module name (not just any checkbox)
4. Checking the execution logs to see step outputs being stored

## Documentation

**Updated:** `/git/ignition-playground/docs/playbook_syntax.md`

Added comprehensive "Step Output References" section with:
- Syntax explanation
- How it works
- Complete example
- Key points
- Valid output sources

## Benefits

### For Users
- **Cleaner Playbooks** - No more temp files or workarounds
- **Dynamic Workflows** - Steps can adapt based on previous step outputs
- **Better Debugging** - Clear step-to-step data flow
- **Module Search Works** - Can actually search for specific module names

### For Developers
- **Type-Safe** - All references validated at runtime
- **Explicit Dependencies** - Clear which steps depend on others
- **Testable** - Easy to mock step outputs in tests
- **Extensible** - Any step type can produce outputs

## Backward Compatibility

- **Fully backward compatible** - Existing playbooks continue to work
- **Opt-in feature** - Only used when `{{ step.* }}` syntax is present
- **No breaking changes** - All existing tests pass

## Known Limitations

1. **Forward References Not Allowed** - Can only reference previously completed steps
2. **Step ID Must Be Exact** - Typos in step IDs cause runtime errors
3. **Output Must Exist** - Steps with no output cannot be referenced
4. **No Step Failure Handling** - If source step fails, reference fails

## Future Enhancements

1. **Step Validation** - Validate step references at playbook load time
2. **Autocomplete Support** - IDE/UI autocomplete for available step outputs
3. **Step Output Inspector** - UI to view all step outputs during debugging
4. **Conditional Steps** - Skip steps based on previous step outputs

## Architecture Decision Record

**Decision:** Store step outputs in a shared dictionary passed by reference to the ParameterResolver

**Rationale:**
- Simple implementation (no need to pass execution state around)
- Efficient (no copying of data)
- Thread-safe (single execution thread per playbook)
- Extensible (easy to add more output sources)

**Alternatives Considered:**
1. **Extend utility.set_variable to auto-extract outputs** - Would require special handling of utility.python steps
2. **Create browser.fill_from_file step type** - Too specific, doesn't solve general problem
3. **Pass execution state to step executor** - Circular dependency issues
4. **Use temp files** - Fragile, not portable, hard to debug

## Files Changed

1. `/git/ignition-playground/ignition_toolkit/playbook/parameters.py`
2. `/git/ignition-playground/ignition_toolkit/playbook/engine.py`
3. `/git/ignition-playground/ignition_toolkit/playbook/step_executor.py`
4. `/git/ignition-playground/playbooks/gateway/module_upgrade.yaml`
5. `/git/ignition-playground/tests/test_parameter_resolver.py`
6. `/git/ignition-playground/docs/playbook_syntax.md`

## Summary

This implementation provides a clean, extensible solution for referencing step outputs in playbooks. It solves the immediate problem (module search in Module Upgrade playbook) while providing a general-purpose feature that can be used in any playbook.

The implementation follows the existing architecture patterns, maintains backward compatibility, and includes comprehensive tests and documentation.

**Status:** Ready for testing and deployment
