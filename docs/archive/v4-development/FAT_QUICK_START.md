# FAT Testing - Quick Start Guide

**Get started with automated Factory Acceptance Testing in 5 minutes**

---

## Prerequisites

1. ✅ Ignition Gateway running (with Perspective module)
2. ✅ Ignition Automation Toolkit server running (`ignition-toolkit serve`)
3. ✅ Perspective project deployed and accessible
4. ⚠️ (Optional) Anthropic API key for AI-assisted testing

---

## Step 1: Basic FAT Test (No AI Required)

### Using the Frontend UI

1. **Navigate to Playbooks**
   - Open http://localhost:9000 in browser
   - Click "Playbooks" in sidebar

2. **Open Basic FAT Playbook**
   - Find `perspective/fat_basic_test.yaml`
   - Click to view details

3. **Configure Parameters**
   ```
   perspective_url: http://localhost:8088/data/perspective/client/YourProjectName
   project_name: My Dashboard v1.0
   ```

4. **Run Playbook**
   - Click "Run Playbook" button
   - Watch live execution with browser streaming (2 FPS)
   - Monitor progress: Discover → Test → Report

5. **View Results**
   - Check execution log for summary
   - Open report at `./data/reports/fat_report_YYYYMMDD_HHMMSS.html`

### Expected Execution Time
- 10-20 components: ~2-3 minutes
- 50-100 components: ~5-10 minutes
- 100+ components: ~10-20 minutes

---

## Step 2: Comprehensive FAT Test (AI-Assisted)

### Setup AI Integration

1. **Get Anthropic API Key**
   - Visit https://console.anthropic.com
   - Create API key
   - Copy key

2. **Configure Environment**
   ```bash
   # Option 1: Environment variable
   export ANTHROPIC_API_KEY="sk-ant-..."

   # Option 2: .env file
   echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
   ```

3. **Restart Toolkit Server**
   ```bash
   # Stop current server
   # Restart with:
   ignition-toolkit serve
   ```

### Run Comprehensive FAT

1. **Open Comprehensive Playbook**
   - Open `perspective/fat_comprehensive_test.yaml`

2. **Configure Parameters**
   ```
   perspective_url: http://localhost:8088/data/perspective/client/Production
   project_name: Production Dashboard v2.1
   tester_name: John Doe
   client_name: ACME Manufacturing
   test_mode: comprehensive  # or "smoke" or "critical_path"
   enable_visual_verification: true  # Requires AI
   ```

3. **Run and Monitor**
   - Click "Run Playbook"
   - Watch AI analysis steps (Step 6-7)
   - View intelligent test plan generation
   - Monitor test execution with screenshots
   - See visual consistency verification

4. **Review FAT Report**
   - Professional HTML report generated
   - Located at `./reports/FAT_Production Dashboard v2.1_TIMESTAMP.html`
   - Includes:
     - Executive summary with pass rate
     - Component test matrix
     - Visual consistency analysis
     - Screenshots for each test
     - Client-ready presentation

---

## Step 3: Understanding the Workflow

### Discovery Phase
```yaml
# Step 1: Navigate to page
type: browser.navigate

# Step 2: Discover interactive components
type: perspective.discover_page
# Finds: buttons, inputs, links, dropdowns, toggles
# Output: Component inventory with selectors

# Step 3: Extract metadata
type: perspective.extract_component_metadata
# Enriches: Labels, tooltips, Perspective paths
```

### Analysis Phase (AI-Assisted)
```yaml
# Step 4: AI page analysis
type: ai.analyze_page_structure
# Analyzes: Screenshot + component list
# Predicts: Expected behavior for each component

# Step 5: Generate test plan
type: ai.generate_test_cases
# Generates: Structured test manifest
# Fallback: Rule-based if AI unavailable
```

### Execution Phase
```yaml
# Step 6: Execute tests
type: perspective.execute_test_manifest
# For each component:
#   1. Perform action (click, fill, etc.)
#   2. Capture screenshot
#   3. Verify no errors
#   4. Return to baseline
```

### Reporting Phase
```yaml
# Step 7: Generate report
type: fat.generate_report
# Creates: Professional HTML report
# Includes: Test results, screenshots, metadata

# Step 8: Export report
type: fat.export_report
# Exports: To specified location (HTML/PDF)
```

---

## Step 4: Customizing for Your Project

### Exclude System Elements

```yaml
- id: discover
  type: perspective.discover_page
  parameters:
    selector: "body"
    exclude_selectors:
      - ".ia_header__logo"           # Ignition logo
      - "[data-test-ignore='true']"  # Custom ignore
      - ".system-navigation"         # Your system elements
```

### Filter Component Types

```yaml
# Only test buttons and links (smoke test)
- id: discover
  type: perspective.discover_page
  parameters:
    types:
      - button
      - link
```

### Custom Visual Guidelines

```yaml
- id: visual_check
  type: ai.verify_visual_consistency
  parameters:
    guidelines:
      - "All buttons use company blue (#003366)"
      - "Font size minimum 14px"
      - "Contrast ratio meets WCAG AA"
      - "Logo placement top-left corner"
```

### Test Mode Selection

```yaml
# Comprehensive: Test everything
test_mode: comprehensive

# Smoke: Critical functionality only
test_mode: smoke

# Critical Path: Main user workflows
test_mode: critical_path
```

---

## Step 5: Troubleshooting

### Component Discovery Issues

**Problem:** Components not discovered
```yaml
# Solution 1: Broaden selector
selector: "body"  # Instead of specific container

# Solution 2: Include all types
types: []  # Empty = discover all

# Solution 3: Remove excludes
exclude_selectors: []
```

**Problem:** Wrong components discovered
```yaml
# Solution: Be more specific with excludes
exclude_selectors:
  - ".navigation-menu"
  - "[role='presentation']"
  - ".backdrop"
```

### Test Execution Issues

**Problem:** Tests fail due to slow page
```yaml
# Solution: Increase timeout
- id: execute_tests
  timeout: 600  # 10 minutes
```

**Problem:** Navigation breaks tests
```yaml
# Solution: Ensure baseline return is enabled
parameters:
  return_to_baseline: true
  baseline_url: "{{ parameter.perspective_url }}"
```

### AI Issues

**Problem:** AI steps fail
```yaml
# Solution 1: Check API key is set
# Solution 2: Set on_failure: continue
- id: ai_step
  on_failure: continue  # Gracefully skip

# Solution 3: Use basic mode (no AI)
# Just run fat_basic_test.yaml
```

**Problem:** AI responses not helpful
```yaml
# Solution: Add more context
parameters:
  context: |
    Production line monitoring dashboard
    Shows 4 production lines with status
    Includes alarms, trends, and controls
```

---

## Step 6: Best Practices

### 1. Start Small
- Begin with `fat_basic_test.yaml`
- Test on simple pages first
- Gradually increase complexity

### 2. Iterate on Excludes
- First run will find many components
- Review component list
- Add excludes for unwanted elements
- Re-run for cleaner results

### 3. Use Test Modes Effectively
- **Development:** Use `smoke` mode (fast)
- **Pre-release:** Use `comprehensive` mode
- **Critical:** Use `critical_path` mode

### 4. Organize Reports
```bash
# Create project-specific directories
mkdir -p ./reports/production-dashboard
mkdir -p ./reports/operator-hmi

# Export with organized names
output_path: "./reports/production-dashboard/FAT_v1.0.html"
```

### 5. Document Findings
- Save failed test screenshots
- Note recurring issues
- Track visual consistency violations
- Share reports with team/client

---

## Step 7: Example Workflows

### Smoke Test Workflow
```yaml
# Quick daily smoke test
name: "Daily Smoke Test"
steps:
  - Navigate
  - Discover (buttons only)
  - Generate tests (smoke mode)
  - Execute tests
  - Report
# Runtime: ~2 minutes for 20 components
```

### Pre-Release FAT Workflow
```yaml
# Comprehensive pre-release test
name: "v2.0 Release FAT"
steps:
  - Navigate
  - Screenshot baseline
  - Discover (all types)
  - AI analysis
  - Generate comprehensive tests
  - Execute tests
  - Visual verification
  - Generate professional report
  - Export to ./releases/
# Runtime: ~15 minutes for 100 components
```

### Regression Test Workflow
```yaml
# Compare against baseline
name: "Regression Test"
steps:
  - Navigate
  - Discover components
  - Compare with previous run
  - Test changed components only
  - Report differences
# (Future enhancement - not yet implemented)
```

---

## 📊 Understanding the Report

### Executive Summary Section
- **Pass Rate:** Overall success percentage
- **Total Tests:** All components tested
- **Passed/Failed/Skipped:** Breakdown of results

### Test Results Table
- **Green rows:** Passed tests
- **Red rows:** Failed tests
- **Screenshot column:** Click to view test screenshot

### Visual Consistency Section (if enabled)
- **Passed Guidelines:** ✓ in green
- **Failed Guidelines:** ✗ in red
- **Warnings:** ⚠ in yellow

### Using Report for Client Review
1. Export to client-facing directory
2. Include in release documentation
3. Attach to change requests
4. Archive for compliance/audit

---

## 🎯 Next Steps

1. ✅ Run basic FAT test on your Perspective project
2. ✅ Review generated component list
3. ✅ Customize excludes and types
4. ✅ Run comprehensive test with AI (optional)
5. ✅ Review professional FAT report
6. ✅ Iterate and refine for your needs

---

## 📞 Need Help?

- **Documentation:** See `/docs/FAT_PROTOTYPE_README.md`
- **Playbook Syntax:** See `/docs/playbook_syntax.md`
- **Issues:** Check execution logs for errors
- **Questions:** Review `PROJECT_GOALS.md` for design decisions

---

**Happy Testing! 🚀**

