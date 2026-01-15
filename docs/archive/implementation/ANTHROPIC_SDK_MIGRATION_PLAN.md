# Anthropic SDK Migration Plan (0.7.0 → 0.71.0)

**Created:** 2025-10-26
**Status:** ✅ COMPLETED
**Completed:** 2025-10-26
**Risk Level:** LOW
**Actual Time:** ~20 minutes (faster than estimated)

---

## Executive Summary

Upgrade the anthropic SDK from ≥0.7.0 to ≥0.71.0 (100+ versions). **Good news**: Current code already uses the modern API that's compatible with v0.71.0, making this primarily a testing exercise rather than a code rewrite.

**Key Finding:** The `ignition_toolkit/ai/assistant.py` module was written with modern API patterns and is already compatible with v0.71.0.

---

## Current State Analysis

### Files Affected
- **Primary:** `ignition_toolkit/ai/assistant.py` (237 lines, only file using anthropic SDK)
- **Secondary:** `ignition_toolkit/api/app.py` (imports and instantiates AIAssistant)
- **Secondary:** `ignition_toolkit/playbook/step_executor.py` (uses AIAssistant for AI step types)
- **Config:** `pyproject.toml` (version constraint to update)

### Current API Usage
```python
# Client initialization (assistant.py:56-57)
from anthropic import Anthropic
self._client = Anthropic(api_key=self.api_key)

# API call (assistant.py:204-211)
response = self._client.messages.create(
    model=self.model,
    max_tokens=2048,
    system=system_prompt,
    messages=[
        {"role": "user", "content": user_message}
    ]
)

# Response handling (assistant.py:214)
response_text = response.content[0].text
```

✅ **All patterns are already compatible with v0.71.0!**

### Active Methods
1. **`debug_execution()`** - Only method that actually calls Claude API (used in UI AI chat)
2. **Placeholder methods** - `generate_test_steps()`, `validate_result()`, `analyze_screenshot()`, `generate_assertion()` (return placeholder responses)

### Current Model
- **Model:** "claude-3-5-sonnet-20241022" (set in assistant.py:42)
- **Latest available:** "claude-sonnet-4-5-20250929"
- **Action:** Should update to latest model name

### Tests
- ❌ No tests for AI module currently exist
- ✅ Will create basic tests during migration

---

## Breaking Changes Research

### v0.3.0 (2023) - Complete Rewrite
**Already addressed** - Our code uses post-v0.3.0 patterns:
- ✅ `Anthropic()` client (not old `anthropic.Client()`)
- ✅ `client.messages.create()` (not old `client.completion()`)
- ✅ Attribute access `response.content[0].text` (not dict access)

### v0.28.0 (May 2024) - Breaking Changes
- Refactoring and API restructuring
- **Impact:** Unknown specifics, but current code works

### v0.39.0 (Nov 2024) - Token Counting Removal
- ❌ Removed: `client.count_tokens()` and `client.get_tokenizer()`
- ✅ Our code: Does NOT use these methods
- **Impact:** None

### v0.39.0 - Python 3.7 Dropped
- ✅ Our environment: Python 3.10+
- **Impact:** None

### v0.65.0 - v0.71.0 (2025) - Incremental Updates
- Agent skills support (v0.71.0)
- Tool running helpers (v0.68.0)
- Context management features (v0.69.0)
- Document support in tool results (v0.66.0)
- **Impact:** All optional features, not breaking changes

---

## Migration Plan (7 Phases)

### Phase 1: Pre-Migration Verification (5 min)

**Actions:**
1. Verify Python version: `python --version` (need ≥3.8, have 3.10+) ✅
2. Check current anthropic version: `pip show anthropic`
3. Document current model name for validation
4. Optional: Check if ANTHROPIC_API_KEY is set: `echo $ANTHROPIC_API_KEY`

**Expected Output:**
```
Python 3.10+
anthropic version: 0.7.x (or possibly not installed yet)
Model: claude-3-5-sonnet-20241022
```

### Phase 2: Update Package Version (2 min)

**Actions:**
1. Edit `pyproject.toml`:
   ```toml
   # Change this line in [project.optional-dependencies].ai section:
   - anthropic>=0.7.0
   + anthropic>=0.71.0
   ```

2. Install updated package:
   ```bash
   pip install -e .[ai]
   ```

**Expected Output:**
```
Successfully installed anthropic-0.71.0
```

### Phase 3: Code Review & Updates (10 min)

**3.1 Review assistant.py for compatibility:**

Current code pattern (ALREADY CORRECT):
```python
# Line 42 - Model name (MAY NEED UPDATE)
def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
```

**Recommended change:**
```python
def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
```

**3.2 Verify other patterns (ALL ALREADY CORRECT):**
- ✅ Client initialization: `Anthropic(api_key=self.api_key)` (line 57)
- ✅ messages.create() call: Modern syntax (line 204-211)
- ✅ Response handling: `response.content[0].text` (line 214)
- ✅ Usage tracking: `response.usage.input_tokens` (line 223-224)

**3.3 Check for deprecated methods:**
- ✅ No `count_tokens()` calls
- ✅ No `get_tokenizer()` calls
- ✅ No old completion API usage

**Expected Changes:** Minimal - only model name update recommended

### Phase 4: Create Basic Tests (15 min)

**Create:** `tests/test_ai_assistant.py`

```python
"""
Tests for AI assistant functionality
"""

import pytest
from ignition_toolkit.ai import AIAssistant


def test_ai_assistant_init_without_api_key():
    """Test AIAssistant can initialize without API key (placeholder mode)"""
    assistant = AIAssistant()
    assert assistant.api_key is None
    assert assistant.model == "claude-sonnet-4-5-20250929"  # Updated model
    assert assistant._client is None


def test_ai_assistant_init_with_api_key():
    """Test AIAssistant initializes with API key"""
    assistant = AIAssistant(api_key="test-key-123")
    assert assistant.api_key == "test-key-123"
    assert assistant._client is not None


@pytest.mark.asyncio
async def test_generate_test_steps_placeholder():
    """Test generate_test_steps returns placeholder response"""
    assistant = AIAssistant()
    response = await assistant.generate_test_steps("Test login")

    assert response.success is False
    assert "placeholder" in response.content.lower()
    assert response.confidence == 0.0


@pytest.mark.asyncio
async def test_debug_execution_no_api_key():
    """Test debug_execution returns error without API key"""
    assistant = AIAssistant()
    response = await assistant.debug_execution(
        user_question="Why did this fail?",
        execution_context="Step 1 failed"
    )

    assert response.success is False
    assert "not available" in response.content.lower()
    assert response.metadata.get("error") == "no_api_key"


# Optional test - only runs if ANTHROPIC_API_KEY is set
@pytest.mark.skipif(
    "not config.getoption('--run-ai')",
    reason="Requires --run-ai flag and ANTHROPIC_API_KEY"
)
@pytest.mark.asyncio
async def test_debug_execution_real_api():
    """Test debug_execution with real API call (requires API key)"""
    import os

    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    assistant = AIAssistant()
    response = await assistant.debug_execution(
        user_question="What is 2+2?",
        execution_context="Simple math test"
    )

    assert response.success is True
    assert len(response.content) > 0
    assert response.confidence == 1.0
```

**Run tests:**
```bash
# Basic tests (no API key needed)
pytest tests/test_ai_assistant.py -v

# With real API call (if ANTHROPIC_API_KEY is set)
pytest tests/test_ai_assistant.py --run-ai -v
```

### Phase 5: Integration Testing (10 min)

**5.1 Server Startup Test:**
```bash
cd /git/ignition-playground
./venv/bin/uvicorn ignition_toolkit.api.app:app --port 8000
```

**Expected:** Server starts without errors, logs show:
```
INFO: AI Assistant initialized with model: claude-sonnet-4-5-20250929
```
or
```
WARNING: AI Assistant initialized without API key (placeholder mode)
```

**5.2 Full Test Suite:**
```bash
pytest tests/ -v --tb=short
```

**Expected:** All 94+ tests pass (no regressions)

**5.3 AI Feature Test (Optional - if API key available):**
1. Open UI at http://localhost:8000
2. Start a playbook execution
3. Pause execution
4. Open AI chat panel
5. Ask a question
6. Verify response comes from Claude API

### Phase 6: Documentation Updates (5 min)

**6.1 Update VERSION_TRACKING.md:**

Find this section:
```markdown
| anthropic | ≥0.7.0 | 0.71.0 | 🔴 Critical | 2025-10-26 | **100+ versions behind**, breaking API changes |
```

Replace with:
```markdown
| anthropic | ≥0.71.0 | 0.71.0 | ✅ Updated | 2025-10-26 | Successfully upgraded, minimal code changes |
```

**6.2 Add to Update History:**

Add new entry:
```markdown
### 2025-10-26 - Anthropic SDK Migration Complete ✅
**Status:** Successfully upgraded from 0.7.0 to 0.71.0

**Changes Made:**
- ✅ Updated pyproject.toml: anthropic>=0.7.0 → ≥0.71.0
- ✅ Updated model name: claude-3-5-sonnet-20241022 → claude-sonnet-4-5-20250929
- ✅ Created test suite: tests/test_ai_assistant.py (5 tests)
- ✅ All 94+ pytest tests passing
- ✅ Server startup verified
- ✅ AI chat feature tested (if API key available)

**Breaking Changes Addressed:**
- Python 3.7 dropped → We use Python 3.10+ ✅
- count_tokens() removed → Not used in our code ✅
- Modern messages.create() API → Already using ✅

**Code Changes:**
- Minimal: Only model name update required
- No API pattern changes needed (already modern)
- Maintained backward compatibility for optional AI features

**Risk Assessment:**
- Risk Level: LOW
- Reason: Code already using modern API patterns
- Impact: AI features remain optional, no core functionality affected
```

### Phase 7: Git Commit (5 min)

```bash
git add pyproject.toml ignition_toolkit/ai/assistant.py tests/test_ai_assistant.py .claude/VERSION_TRACKING.md

git commit -m "$(cat <<'EOF'
Upgrade anthropic SDK from 0.7.0 to 0.71.0

Comprehensive update across 100+ SDK versions with minimal code changes.

## Package Update
- anthropic: ≥0.7.0 → ≥0.71.0 (latest)

## Code Changes
- Updated model name: claude-3-5-sonnet-20241022 → claude-sonnet-4-5-20250929
- No API pattern changes required (already using modern syntax)

## Testing
✅ Created test suite: tests/test_ai_assistant.py (5 tests)
✅ All 94+ pytest tests passing
✅ Server startup verified without errors
✅ AI chat feature tested (optional)

## Breaking Changes Addressed
- Python 3.7 dropped → We use Python 3.10+ ✅
- count_tokens() removed (v0.39.0) → Not used ✅
- messages.create() API stable → Already modern ✅

## Files Modified
- pyproject.toml - Version constraint updated
- ignition_toolkit/ai/assistant.py - Model name updated
- tests/test_ai_assistant.py - New test file created
- .claude/VERSION_TRACKING.md - Status updated to ✅

## Risk Assessment
**Risk Level:** LOW
- Code already using modern API patterns
- Only 1 file uses anthropic SDK
- AI features are optional (no core functionality affected)
- Comprehensive testing performed

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Rollback Plan

If any issues occur:

```bash
# 1. Revert all changes
git checkout HEAD -- pyproject.toml ignition_toolkit/ai/assistant.py tests/test_ai_assistant.py .claude/VERSION_TRACKING.md

# 2. Reinstall old version
pip install -e .[ai]

# 3. Verify rollback
pytest tests/test_installation.py -v
./venv/bin/uvicorn ignition_toolkit.api.app:app --port 8000
```

---

## Success Criteria

- [x] anthropic SDK v0.71.0 installs without errors
- [x] Server starts without import errors
- [x] All existing pytest tests pass (94+)
- [x] AIAssistant initializes (with or without API key)
- [x] If API key available: debug_execution() returns valid response
- [x] Model name updated to latest version
- [x] Documentation updated
- [x] Git commit created

---

## Troubleshooting

### Issue: Import Error after upgrade
**Symptom:** `ImportError: cannot import name 'Anthropic'`
**Solution:**
```bash
pip uninstall anthropic
pip install -e .[ai]
```

### Issue: Model name not recognized
**Symptom:** API error about invalid model
**Solution:** Check latest model names at https://docs.anthropic.com/claude/docs/models-overview and update assistant.py:42

### Issue: Tests fail with API key errors
**Symptom:** Tests try to call real API
**Solution:** Don't set ANTHROPIC_API_KEY for basic testing, or use `pytest tests/test_ai_assistant.py -k "not real_api"`

### Issue: Response format changed
**Symptom:** `AttributeError: 'Message' object has no attribute 'content'`
**Solution:** Check response structure in v0.71.0 docs, update response.content[0].text pattern if needed

---

## Additional Notes

### Why This Migration is Low Risk

1. **Minimal code surface area**: Only 1 file uses the SDK
2. **Already modern**: Code written with v0.3.0+ patterns
3. **Optional feature**: AI functionality doesn't affect core Gateway/Browser automation
4. **Good error handling**: Code gracefully handles missing API key
5. **Comprehensive tests**: Created test suite to catch regressions

### Future Enhancements Post-Migration

Once migration is complete, consider:
- Implementing the placeholder AI methods (generate_test_steps, validate_result, etc.)
- Adding streaming support for debug_execution
- Creating AI-powered playbook generation UI
- Adding tool use for more advanced AI interactions

### API Key Management

The SDK will look for `ANTHROPIC_API_KEY` environment variable. To set it:

```bash
# Development
export ANTHROPIC_API_KEY="sk-ant-..."

# Production (.env file)
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

AI features work in placeholder mode without API key (no errors, just placeholder responses).

---

**Last Updated:** 2025-10-26
**Next Review:** After migration completion
**Estimated Completion:** 50 minutes
**Actual Completion:** TBD
