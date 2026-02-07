# Ignition Toolbox - Project Goals

**Version:** 1.5.4
**Last Updated:** 2026-02-06
**Status:** Production Ready (All Phases Complete)

---

## 📋 Table of Contents

1. [Problem Statement](#problem-statement)
2. [Solution Overview](#solution-overview)
3. [Target Users](#target-users)
4. [Core Use Cases](#core-use-cases)
5. [Must-Have Features](#must-have-features)
6. [Key Principles](#key-principles)
7. [What This Is NOT](#what-this-is-not)
8. [Decision-Making Framework](#decision-making-framework)
9. [Documentation Hierarchy](#documentation-hierarchy)

---

## Problem Statement

Ignition SCADA acceptance testing currently suffers from four critical problems:

### 1. **Repeatability Problem**
Gateway operations (module upgrades, trial resets, project deployments, health checks) and Perspective UI testing are performed manually or with throwaway scripts. This leads to:
- Inconsistent test execution
- Human error in manual testing
- Lost knowledge when scripts aren't saved
- No standardized test procedures across teams

### 2. **Visual Verification Problem**
When testing Perspective web applications or Gateway operations, testers need to **SEE** what's happening to verify correctness:
- Blind script execution misses visual UI bugs
- No way to verify UX issues programmatically
- Can't pause and inspect state during execution
- No visual confirmation that operations succeeded

### 3. **Playbook Management Problem**
Test engineers need a library of reusable test patterns, not programming from scratch:
- Writing tests from scratch is time-consuming
- Similar tests (login flows, navigation, form validation) are rewritten repeatedly
- No easy way to duplicate and modify existing tests
- Difficult to share test procedures across teams

### 4. **AI-Assisted Testing Gap**
Some acceptance testing steps require intelligent decision-making that humans OR AI can perform:
- "Does this Perspective page look correct?" (visual regression)
- "Is the data displayed reasonable?" (intelligent assertions)
- "Why did this step fail?" (error analysis)
- Creating new tests from natural language descriptions

---

## Solution Overview

**Ignition Toolbox is a visual acceptance testing platform for Ignition SCADA with domain-separated playbook libraries, real-time visual feedback, and optional AI-assisted test creation and verification.**

### Core Capabilities

1. **Domain-Specific Playbook Libraries**
   - Gateway playbooks: REST API operations (upload modules, restart, health checks)
   - Perspective playbooks: Browser automation (UI testing with Playwright)
   - Designer playbooks (future): Designer automation (complex, non-web)

2. **Visual Real-Time Execution**
   - Step-by-step progress tracking
   - Live visual feedback (embedded browser for Perspective tests)
   - Pause/Resume/Skip controls during execution
   - Execution history and audit logs

3. **Modular Playbook Management**
   - Browse organized playbook library (categorized by domain)
   - Duplicate existing playbooks as starting point
   - Edit playbooks with AI assistance or manually
   - Import/Export for team collaboration
   - Secure credential management (Fernet encryption)

4. **AI-Injectable Intelligence**
   - AI-assisted playbook creation from natural language
   - AI-assisted playbook editing ("add a step to verify logout")
   - AI-injectable verification steps (visual regression, intelligent assertions)
   - Optional enhancement - playbooks work without AI

---

## Target Users

### Primary User: **Test Automation Engineer**
**Profile:**
- Responsible for acceptance testing of Ignition applications
- Needs repeatable test procedures for regression testing
- Tests both Gateway operations and Perspective UI
- May not be a programmer but understands YAML
- Works in teams and shares test procedures

**Primary Workflow:**
1. Browse existing playbook library
2. Find similar test (e.g., login flow)
3. Duplicate and modify for specific project
4. Execute with visual feedback to verify correctness
5. Save to library for future regression testing
6. Export and share with team

### Secondary User: **DevOps Engineer**
**Profile:**
- Automates Gateway deployments and upgrades
- Needs reliable, repeatable Gateway operations
- Requires audit trail of operations
- Values security (encrypted credentials)

**Primary Workflow:**
1. Use existing Gateway playbooks (module upload, restart, backup)
2. Execute with monitoring to verify success
3. Review execution history for troubleshooting
4. Adapt playbooks for specific environments

### Tertiary User: **Integration Specialist**
**Profile:**
- Builds and maintains Ignition projects
- Tests complex Perspective applications
- Needs to verify UI behavior after changes
- May use AI to create tests from descriptions

**Primary Workflow:**
1. Describe test in natural language to AI
2. AI generates playbook
3. Review and refine generated playbook
4. Execute with visual feedback
5. Save successful tests to library

---

## Core Use Cases

### Use Case 1: Gateway Module Upgrade Acceptance Test
**Scenario:** Test that a new Gateway module can be uploaded and activated successfully

**Playbook Type:** Gateway (domain-specific)

**Steps:**
1. Login to Gateway
2. Upload .modl file
3. Verify module appears in module list
4. Restart Gateway
5. Wait for Gateway to be ready
6. Verify module is in "running" state

**Visual Feedback:** Progress indicators, API response previews

**Reusability:** Duplicate and change module file parameter for different modules

---

### Use Case 2: Perspective Login Flow Acceptance Test
**Scenario:** Test that users can log into a Perspective application and navigate to dashboard

**Playbook Type:** Perspective (domain-specific)

**Steps:**
1. Navigate to Perspective session URL
2. Fill username field
3. Fill password field
4. Click login button
5. Verify dashboard page loads
6. Verify user widget shows correct username
7. Take screenshot for visual regression

**Visual Feedback:** Embedded browser showing live Perspective session (user SEES login happening)

**Reusability:** Duplicate and modify selectors for different Perspective projects

---

### Use Case 3: Perspective Form Validation Test
**Scenario:** Test that form validation works correctly on a Perspective page

**Playbook Type:** Perspective (domain-specific)

**Steps:**
1. Navigate to form page
2. Click submit button (without filling fields)
3. Verify error messages appear
4. Fill required fields
5. Click submit button
6. Verify success message or navigation
7. AI-injectable step: "Does this form look correct?" (visual verification)

**Visual Feedback:** Embedded browser showing form interactions

**Reusability:** Duplicate and modify for different forms

---

### Use Case 4: AI-Assisted Test Creation
**Scenario:** Test engineer needs to create a new test but doesn't want to write YAML from scratch

**Workflow:**
1. Describe test in natural language: "Create a test that verifies the dashboard chart loads and shows production data"
2. AI generates playbook with appropriate steps
3. Review generated playbook
4. Execute with visual feedback to verify
5. Refine if needed (AI-assisted editing: "also verify the legend appears")
6. Save to library

**Visual Feedback:** Embedded browser showing chart rendering

**Reusability:** Generated playbook becomes template for similar tests

---

### Use Case 5: Sequential Test Execution (Domain Separation in Practice)
**Scenario:** Test end-to-end deployment and functionality

**Workflow:**
1. Run "upload_project.yml" (Gateway playbook) - Upload new Perspective project
2. Wait for completion
3. Run "test_dashboard.yml" (Perspective playbook) - Verify new dashboard works
4. Review combined execution history

**Note:** These are TWO separate playbooks, run sequentially - NOT one playbook mixing Gateway and Perspective steps

**Why Separate:** Clearer organization, easier troubleshooting, reusable components

---

## Must-Have Features

### Priority 1: Core Execution (Production Ready ✅)

1. **Playbook Execution Engine**
   - YAML-based playbook definitions
   - Step-by-step execution with state management
   - Pause/Resume/Skip controls
   - Error handling and retry logic
   - Status: ✅ Complete

2. **Visual Real-Time Feedback**
   - Step progress tracking with WebSocket updates
   - Embedded browser view for Perspective tests (✅ Implemented v1.0.4)
   - Live browser streaming at 2 FPS with interactive click detection
   - Visual operation indicators for Gateway tests
   - Status: ✅ Complete

3. **Domain-Specific Step Types**
   - Gateway steps: login, upload_module, restart, health_check, etc.
   - Perspective steps: navigate, click, fill_input, verify_element, screenshot
   - Utility steps: wait, log, assert
   - Status: ✅ Complete

4. **Secure Credential Management**
   - Fernet-encrypted credential vault
   - Credential references in playbooks (never plaintext passwords)
   - UI for credential CRUD operations
   - Status: ✅ Complete

5. **Execution History & Auditing**
   - SQLite database for execution logs
   - Step-by-step result tracking
   - Execution replay and analysis
   - Status: ✅ Complete

### Priority 2: Playbook Management (Complete ✅)

6. **Playbook Library Organization**
   - Domain-based categorization (Gateway/Perspective/Designer)
   - Playbook cards with metadata (version, steps, parameters)
   - Enable/Disable toggle for experimental playbooks
   - Status: ✅ Complete

7. **Playbook Configuration**
   - Parameter input with credential selection
   - Save configurations for reuse
   - Configuration preview on playbook cards
   - Status: ✅ Complete

8. **Playbook Import/Export**
   - Export playbooks as JSON (credentials stripped)
   - Import playbooks from colleagues
   - Safe sharing across environments
   - Status: ✅ Complete

9. **Playbook Duplication**
   - One-click duplicate existing playbook
   - Create starting point for modifications
   - Status: ✅ Complete (v1.4.66)

10. **Playbook Editor**
    - YAML editor with syntax highlighting
    - Form-based editor for non-technical users
    - Preview changes before saving
    - Status: ✅ Complete (v1.4.68 YAML editor, v1.4.75 form editor)

### Priority 3: AI Integration (Implemented ✅)

11. **AI-Assisted Playbook Creation**
    - Natural language to playbook generation
    - Chat interface for test description
    - Status: ✅ Implemented v1.0.26 (AIAssistDialog component)

12. **AI-Assisted Playbook Editing**
    - "Modify this playbook to also test logout"
    - Intelligent step suggestions
    - Status: ✅ Implemented v1.0.26 (AI dialog with execution context)

13. **AI-Injectable Verification Steps**
    - perspective.verify_with_ai step type
    - AI-powered visual verification with confidence scoring
    - Intelligent assertions
    - Status: ✅ Complete (v1.4.75)

### Priority 4: Enhanced Visual Feedback (Implemented ✅)

14. **Embedded Playwright Browser View** ⭐ CRITICAL
    - Live browser embedded in UI during Perspective test execution
    - User SEES the test happening in real-time
    - Pause to inspect current state
    - Interactive click detection with coordinate display
    - Status: ✅ Implemented v1.0.4 (live streaming) + v1.0.26 (interactive)

15. **Visual Regression Testing**
    - Screenshot capture and comparison
    - Highlight visual differences
    - AI-assisted visual verification
    - Status: ❌ Removed (was implemented in v1.4.75, removed in v1.5.2 - use AI verification instead)

---

## Key Principles

These principles guide ALL feature decisions and implementation work:

### Principle 1: **Domain Separation**

**Playbooks stay domain-specific: Gateway OR Perspective OR Designer (never mixed)**

**Rationale:**
- Simpler execution model
- Clearer organization and troubleshooting
- Easier to maintain and share
- Reduces complexity

**Implementation:**
```
playbooks/
├── gateway/              # Gateway-only playbooks
│   ├── reset_trial.yml
│   ├── upload_module.yml
│   └── backup.yml
├── perspective/          # Perspective-only playbooks
│   ├── test_login.yml
│   ├── test_dashboard.yml
│   └── test_forms.yml
└── designer/             # Designer-only playbooks (future)
    └── (TBD)
```

**Anti-Pattern (DO NOT DO):**
```yaml
# ❌ WRONG - mixing domains in one playbook
steps:
  - type: gateway.restart       # Gateway domain
  - type: perspective.navigate  # Perspective domain (different domain!)
```

**Correct Pattern:**
```yaml
# ✅ CORRECT - Run playbooks sequentially if needed

# Playbook 1: gateway_deploy.yml (Gateway domain only)
steps:
  - type: gateway.upload_project
  - type: gateway.restart

# Playbook 2: perspective_verify.yml (Perspective domain only)
steps:
  - type: perspective.navigate
  - type: perspective.verify_element
```

Users execute: `gateway_deploy.yml` → wait for completion → `perspective_verify.yml`

---

### Principle 2: **Visual Feedback is Required, Not Optional**

**Users must SEE what's happening during test execution, especially for Perspective tests**

**Rationale:**
- Acceptance testing requires visual verification
- Blind execution misses UX issues
- Real-time feedback enables pause-and-inspect workflow
- Builds confidence in test results

**Implementation:**
- Perspective tests: Embedded Playwright browser showing live session
- Gateway tests: Visual progress indicators and API response previews
- All tests: Step-by-step progress with real-time status updates

**Current State:**
- ✅ Step progress tracking (done)
- ✅ Embedded browser view (done, v1.0.4)

---

### Principle 3: **Modular Playbook Library Over Programming**

**Users duplicate and modify existing playbooks - they don't write from scratch**

**Rationale:**
- Test engineers need patterns, not programming
- Duplicating is faster than creating from scratch
- Encourages standardization and best practices
- Lowers barrier to entry

**User Workflow:**
1. Browse playbook library
2. Find similar test
3. Click "Duplicate"
4. Modify copy for specific needs
5. Execute and verify
6. Save to library

**Implementation Requirements:**
- Easy-to-browse playbook library ✅ (done)
- One-click duplication ✅ (done, v1.4.66)
- YAML editor with AI assistance ✅ (done, v1.4.68)
- Form-based editor for non-technical users ✅ (done, v1.4.75)

---

### Principle 4: **AI is Injectable and Optional**

**AI assists where helpful but is never required for playbook execution**

**Rationale:**
- AI speeds up test creation and editing
- AI enables intelligent verification
- But not all users have AI access
- Core functionality must work without AI

**AI Integration Points:**
1. **Playbook Creation:** "Create a test that verifies login flow" → generates playbook
2. **Playbook Editing:** "Add a step to verify logout button" → modifies playbook
3. **Verification Steps:** `perspective.verify_with_ai` uses AI for visual regression
4. **Error Analysis:** AI suggests fixes when steps fail

**Implementation:**
- AI module with Claude integration ✅ (done)
- AI chat interface ✅ (done, v1.0.26)
- AI-injectable steps ✅ (done, v1.4.75)

---

### Principle 5: **Secure by Default**

**Credentials never appear in playbooks, always encrypted at rest**

**Rationale:**
- Playbooks must be shareable without exposing secrets
- Compliance requirements (audit trail without passwords)
- Security best practice

**Implementation:**
- Fernet-encrypted credential vault ✅
- Credential references in playbooks (`{{ credential.gateway_admin }}`) ✅
- Export strips credentials, includes only references ✅
- UI credential management ✅

---

## What This Is NOT

Understanding boundaries helps evaluate feature requests:

### ❌ NOT a Replacement for Ignition's Built-In Scripting

**If you need:**
- Real-time Gateway event handling
- Tag change scripts
- Message handlers
- Alarm pipeline notifications

**Use:** Ignition's built-in scripting (Python/Jython in Gateway)

**This tool is for:** Administrative operations and acceptance testing, not runtime logic

---

### ❌ NOT a General-Purpose Automation Framework

**If you need:**
- AWS/Azure/GCP automation
- Kubernetes orchestration
- Generic infrastructure management

**Use:** Ansible, Terraform, or cloud-native tools

**This tool is for:** Ignition-specific acceptance testing (Gateway, Perspective, Designer)

---

### ❌ NOT a Designer Replacement

**If you need:**
- Create or modify Perspective views
- Edit Vision windows
- Configure UDTs or tags
- Design HMI screens

**Use:** Ignition Designer

**This tool is for:** Testing Designer projects, not creating them

---

### ❌ NOT a Monitoring/Alerting System

**If you need:**
- 24/7 health monitoring
- Alert notifications
- Performance dashboards
- Uptime tracking

**Use:** Nagios, Grafana, Prometheus, or Ignition's built-in alarming

**This tool is for:** On-demand acceptance testing, not continuous monitoring

---

### ❌ NOT Headless-Only Testing

**If you think:**
- "Visual feedback is optional"
- "Headless execution is faster"
- "I just need API testing"

**Understand:** Visual verification is a CORE REQUIREMENT for Perspective acceptance testing. Headless mode may be added as an option later, but visual mode is primary.

---

## Decision-Making Framework

Use these questions to evaluate ANY feature request, bug fix, or design decision:

### Question 1: Does this help users manage playbooks (create/edit/duplicate/organize)?
- **YES** → High priority (core value proposition)
- **NO** → Consider other questions

**Examples:**
- ✅ "Add playbook duplication button" → YES (high priority)
- ✅ "Add YAML editor" → YES (high priority)
- ❌ "Add Gateway tag browsing" → NO (not playbook management)

---

### Question 2: Does this maintain domain separation (Gateway OR Perspective OR Designer, not mixed)?
- **YES** → Consider it
- **NO** → REJECT IT (violates core principle)

**Examples:**
- ✅ "Add more Gateway step types" → YES (stays in Gateway domain)
- ✅ "Add Perspective form validation steps" → YES (stays in Perspective domain)
- ❌ "Allow calling Perspective steps from Gateway playbooks" → NO (mixes domains)

---

### Question 3: Does this provide or enhance visual feedback during execution?
- **YES** → High priority (core requirement)
- **NO** → Still valid if it's non-visual domain (pure Gateway API)

**Examples:**
- ✅ "Add embedded browser view for Perspective tests" → YES (critical feature)
- ✅ "Add screenshot comparison" → YES (visual regression)
- ✅ "Add Gateway health check step" → Still valid (non-visual but useful)

---

### Question 4: Does this support optional AI assistance?
- **YES** → Consider it (valuable enhancement)
- **NO** → Still valid if manual operation is sufficient

**Examples:**
- ✅ "Add AI chat for playbook creation" → YES (speeds up workflow)
- ✅ "Add AI visual regression step" → YES (intelligent verification)
- ✅ "Add manual YAML editor" → Still valid (AI is optional)

---

### Question 5: Does this keep playbooks reusable and shareable?
- **YES** → Consider it
- **NO** → Might still be valid for one-off operations

**Examples:**
- ✅ "Improve import/export" → YES (team collaboration)
- ✅ "Add playbook templates" → YES (starting points)
- ❌ "Add hardcoded Gateway URLs in playbooks" → NO (not reusable)

---

### Decision Matrix Examples

#### Example 1: "Should we add drag-and-drop for playbook import?"
- Q1 (Playbook management): **YES** - Makes import easier
- Q2 (Domain separation): **N/A** - Doesn't affect domain model
- Q3 (Visual feedback): **N/A** - Import operation, not execution
- Q4 (AI assistance): **NO** - Manual operation
- Q5 (Reusability): **YES** - Easier sharing workflow

**DECISION:** ✅ ACCEPT - Improves playbook management and sharing

---

#### Example 2: "Should we allow Gateway steps in Perspective playbooks?"
- Q1 (Playbook management): **MAYBE** - Could be convenient
- Q2 (Domain separation): **NO** - Violates domain separation principle
- Q3 (Visual feedback): **N/A**
- Q4 (AI assistance): **N/A**
- Q5 (Reusability): **NO** - Makes playbooks more complex

**DECISION:** ❌ REJECT - Violates core principle (domain separation)

**Alternative:** Run two playbooks sequentially (Gateway playbook → Perspective playbook)

---

#### Example 3: "Should we add embedded browser view for Perspective tests?"
- Q1 (Playbook management): **YES** - Helps verify tests work correctly
- Q2 (Domain separation): **YES** - Perspective-specific feature
- Q3 (Visual feedback): **YES** - Core requirement for acceptance testing
- Q4 (AI assistance): **NO** - Manual visual verification
- Q5 (Reusability): **YES** - Confirms playbooks work as expected

**DECISION:** ✅ STRONGLY ACCEPT - Aligns with all criteria, CRITICAL FEATURE

---

#### Example 4: "Should we add Ansible integration?"
- Q1 (Playbook management): **NO** - Different kind of playbook
- Q2 (Domain separation): **NO** - Outside Ignition domains
- Q3 (Visual feedback): **NO** - No visual execution
- Q4 (AI assistance): **NO**
- Q5 (Reusability): **MAYBE** - But Ansible has its own reusability

**DECISION:** ❌ REJECT - Out of scope, use Ansible directly if needed

---

## Documentation Hierarchy

To prevent future confusion, this is the single source of truth for project goals:

### **Tier 1: Definitive References (Update Rarely)**

1. **PROJECT_GOALS.md** (THIS FILE)
   - What problem this solves
   - Who uses it and when
   - Core features and priorities
   - Non-goals and limitations
   - Decision-making framework
   - **Update when:** Core mission changes (very rare)

2. **ARCHITECTURE.md**
   - Design decisions (ADRs)
   - Why SQLite? Why YAML? Why domain separation?
   - Technical rationale
   - **Update when:** Major architectural changes

---

### **Tier 2: Current State (Update Each Release)**

3. **README.md**
   - Quick start guide
   - Current version
   - Installation instructions
   - Links to deeper docs
   - **Update when:** Each release (version number, features)

4. **package.json** + **frontend/package.json**
   - Single source of truth for version number
   - **Update when:** Each release (required)

---

### **Tier 3: Guides and References (Update as Needed)**

6. **/docs/ directory**
   - **DEVELOPER_GUIDE.md** - Installation and development setup
   - **PLAYBOOK_LIBRARY.md** - Playbook library management
   - **PLAYBOOK_BEST_PRACTICES.md** - Best practices for playbook creation
   - **playbook_syntax.md** - YAML reference
   - **TROUBLESHOOTING.md** - Common issues
   - **API_GUIDE.md** - REST API and WebSocket reference
   - **VERSIONING_GUIDE.md** - Version scheme and release process
   - **CANCELLATION_PATTERN.md** - Cancellation pattern for developers
   - **Update when:** Features added, bugs found, user feedback

7. **.claude/CLAUDE.md**
   - Development guidance for Claude Code
   - Code patterns and best practices
   - References PROJECT_GOALS.md for context
   - **Update when:** Code patterns change, new modules added

---

### **Update Policy**

**What to update for each release:**

1. **package.json** - Bump version number
2. **frontend/package.json** - Bump version number (must match package.json)
3. **README.md** - Update version number, add new features if major
4. Create git tag and push to trigger GitHub Actions build

**What NOT to create:**
- ❌ Session summary files (PROGRESS_STATUS.md, IMPLEMENTATION_COMPLETE.md, etc.)
- ❌ Temporary TODO files (use GitHub Issues or project management tool)
- ❌ Duplicate version tracking (one source of truth: package.json)

**Where to track work:**
- ✅ Git commits with descriptive messages
- ✅ GitHub Issues for bugs and feature requests
- ✅ ROADMAP_PHASES.md for development history

---

## Summary

**This project solves acceptance testing for Ignition SCADA by providing:**

1. **Domain-separated playbook libraries** (Gateway OR Perspective OR Designer)
2. **Visual real-time execution feedback** (see tests happening)
3. **Modular playbook management** (duplicate and modify, not write from scratch)
4. **Optional AI assistance** (speeds up creation and enables intelligent verification)
5. **Secure credential management** (never expose passwords)
6. **Execution history and auditing** (compliance and troubleshooting)

**Guiding principles:**
- Domain separation (no mixing)
- Visual feedback required
- Playbook library over programming
- AI injectable and optional
- Secure by default

**Use the Decision-Making Framework to evaluate every feature request.**

---

**Last Updated:** 2026-02-06
**Maintainer:** Nigel G
**Status:** Production Ready (v1.5.4)

**Next Steps:** See [ROADMAP_PHASES.md](/ROADMAP_PHASES.md) for development history.
