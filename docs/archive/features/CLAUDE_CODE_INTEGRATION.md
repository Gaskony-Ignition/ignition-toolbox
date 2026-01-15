# Claude Code Integration

**Version:** 2.2.0+ (Phase 1 - Manual Launch)

## Overview

The Claude Code integration feature allows you to debug paused playbook executions using Claude Code CLI with full context and file editing capabilities.

When a playbook execution is paused (due to error or manual pause), you can click the **Claude Code** button to generate a pre-configured command that opens Claude Code with:
- The playbook YAML file opened for editing
- Full execution context (current step, error messages, parameters)
- Helpful system prompt guiding Claude on how to fix the issue

## How It Works

### 1. User Flow

1. **Execution Pauses**: A playbook execution pauses due to an error or manual pause
2. **Click "Claude Code" Button**: On the execution detail page, click the blue "Claude Code" button
3. **Dialog Opens**: A dialog displays:
   - Playbook file path
   - Pre-generated Claude Code command
   - Execution context (step results, parameters, errors)
4. **Copy Command**: Click "Copy Command" to copy to clipboard
5. **Run in Terminal**: Paste and run the command in your terminal
6. **Claude Code Opens**: Claude Code starts with the playbook file and debugging context
7. **Debug and Fix**: Work with Claude to identify and fix the issue
8. **Apply Changes**: Claude Code can edit the playbook YAML with your approval
9. **Resume Execution**: Go back to the UI and click "Resume" to retry with the fixed playbook

### 2. Technical Details

#### Backend Endpoint

**POST /api/ai/claude-code-session**

Request:
```json
{
  "execution_id": "abc123"
}
```

Response:
```json
{
  "command": "claude-code -p \"/path/to/playbook.yaml\" -m \"...context...\"",
  "playbook_path": "/git/ignition-playground/playbooks/examples/gateway_login.yaml",
  "execution_id": "abc123",
  "context_message": "# Playbook Execution Debug Session\n\n**Execution ID:** abc123\n..."
}
```

The endpoint:
1. Looks up the active execution from `active_engines`
2. Finds the playbook YAML file by name
3. Builds a context message with:
   - Execution ID, playbook name, status
   - Current step number
   - Step results (success/error for each step)
   - Parameters (with sensitive values masked)
4. Generates a Claude Code command with:
   - `-p` flag pointing to playbook file path
   - `-m` flag containing execution context + system prompt
5. Returns the command, file path, and formatted context

#### Frontend Components

**ClaudeCodeDialog.tsx:**
- Dialog component showing the Claude Code command
- Copy-to-clipboard functionality
- Displays playbook path, command, and execution context
- Loads session data via API call when dialog opens

**ExecutionControls.tsx:**
- Added "Claude Code" button (appears when paused or in debug mode)
- Button triggers `onClaudeCode` callback to open dialog

**ExecutionDetail.tsx:**
- Manages ClaudeCodeDialog state
- Passes `executionId` to dialog

#### API Client

**frontend/src/api/client.ts:**
```typescript
getClaudeCodeSession: (executionId: string) =>
  fetchJSON<{
    command: string;
    playbook_path: string;
    execution_id: string;
    context_message: string;
  }>('/api/ai/claude-code-session', {
    method: 'POST',
    body: JSON.stringify({ execution_id: executionId }),
  }),
```

## Usage Example

### Scenario: Fixing a Selector Error

1. **Playbook fails** at Step 5 with error: `Element not found: #login-button`
2. **Click "Claude Code"** button
3. **Dialog shows:**
   ```bash
   claude-code -p "/git/ignition-playground/playbooks/examples/gateway_login.yaml" -m "# Playbook Execution Debug Session

   **Execution ID:** e7f3a9b1
   **Playbook:** Gateway Login Test
   **Status:** paused
   **Current Step:** 5

   ## Step Results:
   ✅ **Step 1:** Navigate to Gateway login page
   ✅ **Step 2:** Wait for login form
   ✅ **Step 3:** Fill username field
   ✅ **Step 4:** Fill password field
   ❌ **Step 5:** Click login button
      Error: Element not found: #login-button

   You are debugging a paused Ignition Automation Toolkit playbook execution..."
   ```

4. **Copy and run the command**
5. **Claude Code session starts**, Claude analyzes:
   - Step 5 uses selector `#login-button`
   - Suggests checking DOM for actual selector
   - Proposes trying `.login-button` or `button[type="submit"]`

6. **With your approval**, Claude edits the playbook:
   ```yaml
   - id: click_login
     type: browser.click
     parameters:
       selector: "button[type='submit']"  # ← Changed from #login-button
   ```

7. **Resume execution** in UI - playbook now succeeds!

## Requirements

- **Claude Code must be installed** and accessible via `claude-code` command
- **Execution must be active** (running or paused) - completed/failed executions won't have active engines
- **Playbook file must exist** in the `playbooks/` directory

## Limitations (Phase 1)

This is Phase 1 (Simple Approach) with these limitations:

- **Manual workflow**: User must copy/paste command into their own terminal
- **No hot-reload**: Changes to playbook don't automatically reload in the UI
- **No embedded terminal**: Must use external terminal application
- **File path must be accessible**: Claude Code needs filesystem access to the playbook path

## Future Enhancements (Phase 2)

Phase 2 (Advanced Approach) would include:

- **Embedded terminal**: xterm.js terminal built into the UI
- **WebSocket proxy**: Seamless integration with Claude Code process
- **Live reload**: Playbook changes automatically refresh in UI
- **One-click launch**: No manual copy/paste required
- **Progress indicators**: See Claude Code activity in real-time

Estimated effort: 6-8 additional hours

## Troubleshooting

### "Execution not found or not active"

**Cause:** Execution has completed, failed, or been cancelled
**Solution:** This feature only works for running/paused executions

### "Playbook file not found for 'XYZ'"

**Cause:** Playbook YAML file has been moved/deleted
**Solution:** Ensure the playbook still exists in `playbooks/` directory

### "command not found: claude-code"

**Cause:** Claude Code CLI is not installed
**Solution:** Install Claude Code from https://claude.com/claude-code

### Changes don't take effect

**Cause:** Playbook changes aren't auto-reloaded
**Solution:** After editing, you may need to stop and restart the execution (future enhancement will add hot-reload)

## Architecture Notes

### Why Manual Launch (Phase 1)?

Phase 1 provides immediate value with minimal complexity:
- ✅ No WebSocket management needed
- ✅ No terminal emulation required
- ✅ No process lifecycle management
- ✅ Works immediately if Claude Code is installed
- ✅ 2-3 hours implementation vs 6-8 hours for Phase 2

### Security Considerations

1. **Credentials are masked** in the context message (any parameter containing "password", "token", "key", "secret")
2. **Only active executions** can be debugged (prevents accessing completed execution data indefinitely)
3. **File paths are validated** to ensure they're in the playbooks/ directory
4. **Shell escaping**: Context message properly escapes quotes and `$` for shell safety

### Why Not Just Use AI Assist Dialog?

The AI Assist Dialog is great for chat-based debugging, but Claude Code offers:
- **Direct file editing**: Can modify the playbook YAML directly
- **Multi-file awareness**: Can read related docs (playbook_syntax.md, etc.)
- **Terminal access**: Can run commands if needed
- **Richer context**: Full-screen interface vs chat box
- **Better for complex fixes**: Multi-step changes, refactoring, etc.

Both tools complement each other:
- **AI Assist**: Quick questions, understanding errors, suggestions
- **Claude Code**: Implementing fixes, refactoring, complex debugging

## Related Documentation

- [Playbook Syntax Reference](/docs/playbook_syntax.md) - Full YAML syntax guide
- [Getting Started](/docs/getting_started.md) - Installation and setup
- [Execution Controls](/docs/EXECUTION_CONTROLS.md) - All execution control features

---

**Last Updated:** 2025-10-27
**Status:** Production Ready (Phase 1)
**Version:** 2.2.0+
