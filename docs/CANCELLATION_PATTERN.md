# Cancellation Pattern - Developer Guide

## ⚠️ CRITICAL: Why This Matters

**User complaint:** "Cancel doesn't work for running executions and keeps going backwards."

**Root cause #1:** Long-running operations don't check for cancellation, so clicking cancel has no effect until the operation completes (which can be 30+ seconds or even minutes).

**Root cause #2 (FIXED 2025-11-04):** Manual cancellation checks using `asyncio.current_task().cancelled()` interfered with the natural cancellation mechanism. The correct approach is to let `asyncio.sleep()` automatically raise `CancelledError` when `task.cancel()` is called.

**This document defines the MANDATORY pattern** that ALL step handlers MUST follow to prevent this regression.

## ✅ Proof of Fix (2025-11-04)

Tested with `playbooks/tests/test_cancellation.yaml`:
- Test 1: Cancellation latency: **251ms** ✓
- Test 2: Cancellation latency: **262ms** ✓
- Target: <500ms (0.5 seconds)
- Status: **PASSING** - Cancellation now responds within 0.5 seconds

---

## The Problem

When a user clicks "Cancel":
1. ✅ Frontend sends cancel request correctly
2. ✅ API receives and processes cancel correctly
3. ✅ ExecutionManager calls `engine.cancel()` correctly
4. ✅ StateManager sets CANCEL signal correctly
5. ❌ **BUT** the currently executing step doesn't check for cancellation and continues blocking

**Result:** User waits 30+ seconds for cancel to take effect, creating a frustrating UX.

---

## The Solution: Cancellable Utilities

All long-running operations MUST use utilities from `ignition_toolkit/playbook/cancellation.py`:

### 1. `cancellable_sleep()` - For Delays

**DO NOT USE** `asyncio.sleep()` directly in step handlers.

```python
# ❌ WRONG - Blocks for full duration, ignores cancellation
await asyncio.sleep(30)

# ✅ CORRECT - Checks for cancellation every 0.5s
from ignition_toolkit.playbook.cancellation import cancellable_sleep
await cancellable_sleep(30)
```

### 2. `cancellable_poll()` - For Polling/Waiting

**DO NOT** use while loops with `asyncio.sleep()` for polling.

```python
# ❌ WRONG - Only checks cancellation every 5 seconds
while not condition():
    await asyncio.sleep(5)

# ✅ CORRECT - Checks cancellation every poll
from ignition_toolkit.playbook.cancellation import cancellable_poll
await cancellable_poll(
    condition=lambda: element.is_visible(),
    timeout=30,
    poll_interval=1.0,
    error_message="Element not visible"
)
```

### 3. `with_cancellation_check()` - For External Operations

For operations that don't natively support cancellation (like Playwright commands):

```python
# ✅ Wrap operations that might block
from ignition_toolkit.playbook.cancellation import with_cancellation_check

result = await with_cancellation_check(
    page.click(selector, timeout=30000)
)
```

---

## Mandatory Pattern for ALL Step Handlers

Every step handler that performs ANY operation >1 second MUST:

### Pattern 1: Use Cancellable Utilities

```python
from ignition_toolkit.playbook.cancellation import cancellable_sleep, cancellable_poll

class MyStepHandler(StepHandler):
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        # Use cancellable utilities
        await cancellable_sleep(params.get("wait_time", 10))

        # Or use cancellable polling
        await cancellable_poll(
            condition=lambda: self.check_ready(),
            timeout=30,
            poll_interval=1.0
        )
```

### Pattern 2: Polling Loops (NO Manual Checks Needed!)

```python
from ignition_toolkit.playbook.cancellation import cancellable_sleep

async def wait_for_something(self):
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < timeout:
        # Do work
        if check_condition():
            return True

        # ✅ Use cancellable sleep - CancelledError raises automatically
        await cancellable_sleep(poll_interval)
```

**Important:** DO NOT use manual `asyncio.current_task().cancelled()` checks! They interfere with the natural cancellation mechanism. Just use `cancellable_sleep()` and let `CancelledError` propagate.

---

## Examples of Fixes

### Example 1: utility.sleep (FIXED ✅)

**Before:**
```python
class UtilitySleepHandler(StepHandler):
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        seconds = params.get("seconds", 1)
        await asyncio.sleep(seconds)  # ❌ Blocks, ignores cancel
        return {"slept": seconds}
```

**After:**
```python
from ignition_toolkit.playbook.cancellation import cancellable_sleep

class UtilitySleepHandler(StepHandler):
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        seconds = params.get("seconds", 1)
        await cancellable_sleep(seconds)  # ✅ Cancellable
        return {"slept": seconds}
```

### Example 2: gateway.wait_for_ready (FIXED ✅)

**Before:**
```python
async def wait_for_ready(self, timeout: int = 300) -> bool:
    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        # Check health
        if await self.get_health():
            return True
        await asyncio.sleep(poll_interval)  # ❌ Blocks
```

**After:**
```python
async def wait_for_ready(self, timeout: int = 300) -> bool:
    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        if await self.get_health():
            return True

        # ✅ Use cancellable sleep - no manual checks needed
        await cancellable_sleep(poll_interval)  # Raises CancelledError automatically
```

### Example 3: The Bug We Just Fixed (2025-11-04) ❌ → ✅

**WRONG IMPLEMENTATION (caused bug):**
```python
async def cancellable_sleep(seconds: float, check_interval: float = 0.5) -> None:
    remaining = seconds
    while remaining > 0:
        # ❌ WRONG: Manual check interferes with natural cancellation
        if asyncio.current_task().cancelled():
            logger.debug("Sleep cancelled before interval")
            raise asyncio.CancelledError()

        sleep_time = min(check_interval, remaining)
        await asyncio.sleep(sleep_time)
        remaining -= sleep_time
```

**Problem:** The manual `asyncio.current_task().cancelled()` check doesn't work reliably because `task.cancel()` only *schedules* cancellation - it doesn't immediately set the flag. The `CancelledError` is only raised at the next `await` point.

**CORRECT IMPLEMENTATION (fixed):**
```python
async def cancellable_sleep(seconds: float, check_interval: float = 0.5) -> None:
    remaining = seconds
    while remaining > 0:
        # ✅ CORRECT: Let asyncio.sleep() raise CancelledError naturally
        sleep_time = min(check_interval, remaining)
        try:
            await asyncio.sleep(sleep_time)  # Automatically raises CancelledError
        except asyncio.CancelledError:
            logger.debug(f"Sleep cancelled after {seconds - remaining:.1f}s")
            raise
        remaining -= sleep_time
```

**Key Insight:** When `task.cancel()` is called, any ongoing `await asyncio.sleep()` will automatically raise `CancelledError`. We don't need manual checks - just let the exception propagate naturally!

---

## Testing Cancellation

### Test Playbook

A test playbook is provided at `playbooks/tests/test_cancellation.yaml`:

```yaml
name: "Test Cancellation"
domain: gateway
steps:
  - id: step1
    name: "Long Sleep"
    type: utility.sleep
    parameters:
      seconds: 30  # Should be cancellable within 0.5s
```

### How to Test

1. Run the test playbook
2. Wait 2-3 seconds
3. Click "Cancel" button
4. **Expected:** Execution stops within 0.5 seconds
5. **Failure:** If it takes >2 seconds, cancellation is broken

### Automated Test (Future)

```python
async def test_cancellation_responsive():
    """Cancel should stop execution within 1 second"""
    execution_id = await start_execution("test_cancellation.yaml")
    await asyncio.sleep(2)  # Let it start

    start_cancel = time.time()
    await cancel_execution(execution_id)

    # Wait for status to update
    status = await wait_for_status(execution_id, "cancelled", timeout=2)
    cancel_duration = time.time() - start_cancel

    assert status == "cancelled", "Execution should be cancelled"
    assert cancel_duration < 1.0, f"Cancel took {cancel_duration}s (should be <1s)"
```

---

## Why This Keeps Regressing

1. **No systematic pattern** - Developers add new step types without knowing the cancellation requirement
2. **Easy to forget** - `asyncio.sleep()` works fine for short operations, easy to use it everywhere
3. **Not enforced** - No linting rules or automated tests catch violations
4. **Not documented** - This pattern wasn't written down until now

---

## Prevention Strategy

### 1. Code Review Checklist

Before merging ANY PR that adds/modifies step handlers:

- [ ] Does the step perform any operation >1 second?
- [ ] If yes, does it use `cancellable_sleep()` instead of `asyncio.sleep()`?
- [ ] If it polls/waits, does it use `cancellable_poll()` or check cancellation in loops?
- [ ] Has the developer tested cancellation manually?

### 2. Linting Rule (Future)

```python
# Add to .pylintrc or flake8 config
[pylint]
disallow-asyncio-sleep-in-handlers = true

# Ban direct use of asyncio.sleep in step handler files
```

### 3. Architecture Decision Record

**ADR-007: All step handlers MUST support responsive cancellation**

- **Status:** Accepted
- **Context:** Users expect cancel to work immediately
- **Decision:** All step handlers MUST use cancellable utilities from `playbook/cancellation.py`
- **Consequences:** Slightly more complex code, but much better UX

### 4. Documentation

- This file (CANCELLATION_PATTERN.md) is the authoritative source
- Link to this from:
  - New developer onboarding docs
  - Contributing guidelines
  - PR template checklist

---

## Step Types Requiring Updates

### ✅ Already Fixed

- `utility.sleep` - Uses `cancellable_sleep()`
- `gateway.wait_for_module_installation` - Checks cancellation in loop
- `gateway.wait_for_ready` - Checks cancellation in loop

### ⚠️ Needs Fixing (from code-fault-analyzer)

**Priority 1 (Critical - User blocks >5s):**

1. **browser.wait** - Playwright wait operations (up to 30s)
   - File: `ignition_toolkit/browser/manager.py:229`
   - Fix: Wrap with `cancellable_poll()` or add timeout parameter

2. **browser.verify** - Verification with retries (5-30s)
   - File: `ignition_toolkit/playbook/executors/browser_executor.py:81,98`
   - Fix: Check cancellation between retries

3. **designer.wait_for_window** - Wait for window (30s)
   - File: `ignition_toolkit/designer/manager.py:366`
   - Fix: Check cancellation in poll loop

**Priority 2 (Medium - User blocks 1-5s):**

4. **browser.navigate**, **browser.click**, **browser.fill** - Implicit waits
   - File: `ignition_toolkit/browser/manager.py`
   - Fix: Wrap Playwright calls with `with_cancellation_check()`

---

## Summary

**THE RULE:** If your step handler can block for >1 second, it MUST use cancellable utilities.

**THE TEST:** Can I cancel within 1 second? If not, it's broken.

**THE FIX:** Use `cancellable_sleep()`, `cancellable_poll()`, or `with_cancellation_check()` from `ignition_toolkit/playbook/cancellation.py`.

**THE PREVENTION:** Document, review, test, and enforce this pattern for ALL new code.

---

**Last Updated:** 2026-02-06
**Version:** 1.5.4
**Status:** Mandatory Pattern - DO NOT VIOLATE
