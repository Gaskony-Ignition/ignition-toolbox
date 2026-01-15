# Feature Request: Nested Playbook Execution

**Status**: Approved - Ready for Implementation
**Target Version**: v2.2.0
**Date Requested**: 2025-10-27
**Priority**: High

## Overview

Enable verified playbooks to be used as single steps within other playbooks, creating composable, modular automation workflows.

## User Story

**As a** playbook author
**I want to** use verified playbooks as steps in other playbooks
**So that** I can build complex workflows from proven, tested building blocks without duplicating steps

## Current Behavior

- Playbooks can be marked as "Verified" via the 3-dot menu on playbook cards
- Verified status is stored in metadata and displayed with a green chip badge
- Each playbook executes independently with all steps visible
- To reuse logic, users must copy/paste steps between playbooks

## Desired Behavior

### 1. Verified Playbooks as Steps

Once a playbook is verified (e.g., "Gateway Login" with 13 steps), it should be usable as a **single step** in other playbooks:

```yaml
name: "Complete Gateway Setup"
version: "1.0"
description: "Full gateway setup using verified building blocks"

steps:
  - id: login
    name: "Login to Gateway"
    type: playbook.run  # NEW step type
    parameters:
      playbook: "examples/gateway_login.yaml"  # Path to verified playbook
      gateway_url: "{{ parameter.gateway_url }}"
      username: "{{ parameter.username }}"
      password: "{{ parameter.password }}"
    timeout: 120

  - id: upload_module
    name: "Upload Perspective Module"
    type: playbook.run
    parameters:
      playbook: "examples/module_upload.yaml"
      module_file: "{{ parameter.module_path }}"
    timeout: 300
```

### 2. Single-Step Visibility

When viewing execution of the parent playbook:
- ✅ Show nested playbook as **one step** in the execution list
- ✅ Step name comes from the parent playbook's step definition
- ✅ Overall status (pending/running/completed/failed) for the nested playbook
- ❌ **Do NOT** show all 13 individual steps from "Gateway Login"
- ✅ Optional: Click to expand and see child steps (future enhancement)

### 3. Verification Enforcement

**Safety Rule**: Only verified playbooks can be used with `playbook.run`

- Attempting to use an unverified playbook → Error at validation time
- Clear error message: "Playbook 'xyz' must be verified before it can be used as a step"
- Encourages testing and verification workflow

## Benefits

1. **Modularity**: Build complex workflows from tested components
2. **Reusability**: Share common sequences (login, module upload, etc.) across playbooks
3. **Maintainability**: Update login logic once, all parent playbooks benefit
4. **Readability**: High-level playbooks show intent, not implementation details
5. **Testing**: Verify small playbooks independently before composing

## Example Use Cases

### Use Case 1: Progressive Complexity
```
1. Create "Gateway Login" (13 steps) → Test → Verify ✓
2. Create "Module Upload" (5 steps) → Test → Verify ✓
3. Create "Gateway Setup" using both as steps (2 steps total)
   - Step 1: playbook.run gateway_login.yaml
   - Step 2: playbook.run module_upload.yaml
```

### Use Case 2: Perspective Testing Suite
```
1. Verify "Perspective Login" playbook ✓
2. Verify "Navigate Dashboard" playbook ✓
3. Verify "Test Button Click" playbook ✓
4. Create "Full Perspective Test" (uses all 3 as steps)
```

### Use Case 3: Multi-Gateway Deployment
```
1. Verify "Deploy to Single Gateway" playbook ✓
2. Create "Deploy to All Gateways" (loops, calling verified playbook for each)
```

## Technical Requirements

### 1. New Step Type
- `StepType.PLAYBOOK_RUN = "playbook.run"`
- Add to `ignition_toolkit/playbook/models.py`

### 2. Step Executor Implementation
**File**: `ignition_toolkit/playbook/step_executor.py`

```python
async def _execute_playbook_step(
    self, step_type: StepType, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a nested playbook as a single step"""

    playbook_path = params.get("playbook")

    # Load playbook
    loader = PlaybookLoader()
    nested_playbook = loader.load_from_file(playbook_path)

    # Verify that playbook is marked as verified
    metadata = metadata_store.get_metadata(playbook_path)
    if not metadata.verified:
        raise StepExecutionError(
            "playbook",
            f"Playbook '{playbook_path}' must be verified before use as a step"
        )

    # Check for circular dependencies
    if self._is_circular_dependency(playbook_path):
        raise StepExecutionError(
            "playbook",
            f"Circular dependency detected: playbook calls itself"
        )

    # Map parameters from parent to child
    child_params = self._map_parameters(params, nested_playbook.parameters)

    # Execute nested playbook
    nested_engine = PlaybookEngine(...)
    nested_state = await nested_engine.execute_playbook(
        nested_playbook,
        child_params
    )

    # Return aggregated result
    return {
        "playbook": playbook_path,
        "status": nested_state.status.value,
        "steps_executed": len(nested_state.step_results),
        "completed": nested_state.status == ExecutionStatus.COMPLETED
    }
```

### 3. Safety Checks

#### Circular Dependency Detection
```python
def _is_circular_dependency(self, playbook_path: str) -> bool:
    """Check if playbook is already in the execution stack"""
    # Track execution stack in engine context
    # Return True if playbook_path is already executing
```

#### Max Nesting Depth
```python
MAX_NESTING_DEPTH = 3  # Prevent deeply nested playbooks

def _check_nesting_depth(self) -> None:
    if self.nesting_depth > MAX_NESTING_DEPTH:
        raise StepExecutionError(
            "playbook",
            f"Maximum nesting depth ({MAX_NESTING_DEPTH}) exceeded"
        )
```

#### Verification Requirement
```python
# Already covered in _execute_playbook_step
if not metadata.verified:
    raise StepExecutionError(...)
```

### 4. Parameter Mapping

Parent playbook parameters can be passed to child:

```yaml
# Parent playbook
parameters:
  - name: gateway_url
    type: string
    required: true

steps:
  - type: playbook.run
    parameters:
      playbook: "child.yaml"
      gateway_url: "{{ parameter.gateway_url }}"  # Pass through
      username: "admin"  # Hardcoded value
```

## Documentation Updates

### 1. Playbook Syntax Reference
**File**: `docs/playbook_syntax.md`

Add section:
```markdown
### Nested Playbook Steps

Use verified playbooks as steps:

\`\`\`yaml
- id: run_login
  name: "Login using verified playbook"
  type: playbook.run
  parameters:
    playbook: "examples/gateway_login.yaml"  # Relative to playbooks/
    gateway_url: "{{ parameter.gateway_url }}"
    username: "{{ parameter.username }}"
    password: "{{ parameter.password }}"
  timeout: 120
\`\`\`

**Requirements:**
- Target playbook MUST be verified
- Prevents circular dependencies
- Max nesting depth: 3 levels
```

### 2. PROJECT_GOALS.md
Add to v2.2.0 goals:
- Nested playbook execution (`playbook.run` step type)
- Composable, modular playbook architecture

### 3. CHANGELOG.md (future v2.2.0)
```markdown
## [2.2.0] - TBD

### Added
- **Nested Playbook Execution**: Use verified playbooks as steps
  - New `playbook.run` step type
  - Verification enforcement (only verified playbooks allowed)
  - Circular dependency detection
  - Parameter mapping from parent to child
  - Max nesting depth limit (3 levels)
```

## Implementation Checklist

- [ ] Add `PLAYBOOK_RUN` to StepType enum
- [ ] Implement `_execute_playbook_step()` in step_executor.py
- [ ] Add circular dependency detection
- [ ] Add max nesting depth check
- [ ] Enforce verification requirement
- [ ] Implement parameter mapping
- [ ] Add tests for nested execution
- [ ] Add tests for circular dependency detection
- [ ] Add tests for verification enforcement
- [ ] Update playbook_syntax.md
- [ ] Update PROJECT_GOALS.md
- [ ] Create example playbooks demonstrating nesting

## Open Questions

1. **Execution History**: Should nested playbook steps be visible in execution history?
   - **Answer**: Show as single aggregated step, optionally expandable

2. **Debugging**: How to debug failed nested playbooks?
   - **Answer**: Use existing debug mode, pause at nested playbook step, inspect child steps

3. **Credentials**: How to pass credentials to nested playbooks?
   - **Answer**: Use parameter mapping with credential references

4. **Version Compatibility**: What if child playbook version changes?
   - **Answer**: Track revision in metadata, warn if child playbook updated

## Success Metrics

- ✅ Users can create verified "building block" playbooks
- ✅ Users can compose complex playbooks from verified blocks
- ✅ Execution view shows nested playbooks as single steps
- ✅ Error messages are clear for verification/circular dependency issues
- ✅ No performance degradation with nested execution

## Future Enhancements (v2.3.0+)

1. **Expandable Steps**: Click nested step to see child steps
2. **Playbook Library**: Browse and search verified playbooks
3. **Visual Playbook Builder**: Drag-and-drop verified playbooks as steps
4. **Playbook Versioning**: Pin to specific playbook versions
5. **Playbook Marketplace**: Share verified playbooks with community

---

**Implementation Timeline**:
- Design & Documentation: 1 hour (COMPLETE)
- Backend Implementation: 3-4 hours
- Testing: 1-2 hours
- Documentation Updates: 1 hour
- **Total Estimate**: ~6-8 hours

**Approved By**: User
**Assigned To**: Claude Code
**Target Completion**: v2.2.0
