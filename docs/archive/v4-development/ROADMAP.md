# Ignition Automation Toolkit - Roadmap

> Future development plans and feature priorities

**Current Version:** 5.1.0
**Status:** Production Ready - All 8 Core Phases Complete ✅
**Last Updated:** 2025-11-21

---

## 🎯 Project Status Overview

**Completed:** All 8 foundational phases (100%)

- ✅ Phase 1: Foundation (packaging, credentials, database, CLI)
- ✅ Phase 2: Gateway Client (async REST API)
- ✅ Phase 3: Playbook Engine (YAML execution, 15+ step types)
- ✅ Phase 4: Import/Export (JSON sharing)
- ✅ Phase 5: API & Frontend (FastAPI + React 19)
- ✅ Phase 6: Browser Automation (Playwright)
- ✅ Phase 7: AI Scaffolding (Anthropic SDK integration)
- ✅ Phase 8: Testing & Documentation (46+ tests)

**Recent Major Features (v1.0-v3.0):**
- ✅ Live browser streaming at 2 FPS
- ✅ Interactive browser view with click detection
- ✅ AI chat interface for debugging paused executions
- ✅ Skip backward capability
- ✅ Debug mode with step-by-step execution
- ✅ WebSocket stability fixes
- ✅ browser.verify step type
- ✅ Nested playbook execution (playbook.run)
- ✅ Delete playbook functionality
- ✅ Claude Code integration Phase 1 - Manual Launch
- ✅ CI/CD pipeline (local testing)
- ✅ Complete documentation review and cleanup

---

## 🚀 Near-Term Priorities (v3.1 - v3.3)

### v3.1: UX Enhancements (Next Release)

**Goal:** Improve playbook creation and editing workflow

**Features:**
1. **One-Click Playbook Duplication** (High Priority)
   - Duplicate button in playbook list
   - Auto-rename with "(Copy)" suffix
   - Preserve all parameters and steps
   - Status: Design phase

2. **YAML Playbook Editor** (High Priority)
   - Dedicated editor page with syntax highlighting
   - Real-time validation
   - Parameter auto-completion
   - Line numbers and error markers
   - Status: Research phase

3. **Improved Error Messages** (Medium Priority)
   - Clearer step failure descriptions
   - Suggestions for common fixes
   - Links to documentation
   - Status: Planning

**Timeline:** 2-3 weeks
**Effort:** ~40 hours

---

### v3.2: Visual Regression Testing (Future)

**Goal:** Add screenshot comparison for automated UI validation

**Features:**
1. **Screenshot Baseline Management**
   - Capture and store baseline screenshots
   - Per-environment baselines (dev/staging/prod)
   - Web UI for baseline review

2. **Visual Comparison Engine**
   - Pixel-by-pixel comparison
   - Configurable difference threshold
   - Highlight changed regions
   - Support for dynamic content masks

3. **Regression Test Reports**
   - Side-by-side diff viewer
   - Approve/reject workflow
   - Historical trend tracking

**Dependencies:**
- Existing screenshot capture (✅ Complete)
- Image comparison library (research needed)
- Storage for baseline images

**Timeline:** 4-6 weeks
**Effort:** ~80 hours
**Status:** Design phase

---

### v3.3: Claude Code Integration Phase 2 (In Progress)

**Goal:** Embed Claude Code terminal in web UI for seamless AI assistance

**Features:**
1. **Embedded Terminal Component**
   - xterm.js integration in React
   - WebSocket connection to Claude Code PTY
   - Resizable terminal panel

2. **Context-Aware Launch**
   - Auto-inject execution context when launching
   - Pre-populate with playbook file path
   - Include recent error messages

3. **Workflow Integration**
   - "Ask Claude Code" button on failed steps
   - Terminal persists across navigation
   - Save/restore terminal sessions

**Status:** Design complete (see docs/CLAUDE_CODE_PHASE2_PLAN.md)
**Timeline:** 2-3 weeks
**Effort:** ~50 hours

---

## 🔮 Long-Term Vision (v4.0+)

### Performance & Scalability

**Parallel Execution**
- Run multiple playbooks concurrently
- Parallel step execution within playbooks
- Queue management for resource-intensive operations

**Caching & Optimization**
- Gateway response caching
- Lazy-load browser contexts
- Optimized WebSocket message batching

### Collaboration Features

**Multi-User Support**
- User authentication and authorization
- Role-based access control (viewer/editor/admin)
- Shared playbook libraries

**Team Coordination**
- Execution scheduling and queuing
- Conflict resolution for concurrent edits
- Audit logs for all operations

### Enterprise Features

**Ignition Designer Automation**
- Designer Launcher automation
- Project comparison and diff
- Component library management

**Advanced Gateway Operations**
- Database query steps
- System.* function wrappers
- Alarm configuration automation
- Tag import/export at scale

**Reporting & Analytics**
- Execution trend analysis
- Performance benchmarking
- Resource utilization tracking
- Compliance reporting

### AI Enhancements

**AI-Powered Test Generation**
- Generate playbooks from natural language descriptions
- Suggest test cases based on Gateway configuration
- Auto-generate assertions from screenshots

**Intelligent Debugging**
- Root cause analysis for failures
- Suggested fixes for common errors
- Predictive failure detection

---

## 📋 Feature Requests Backlog

### User-Requested Features

**Medium Priority:**
- [ ] Custom step types (plugin system)
- [ ] Environment variables in playbooks
- [ ] Playbook versioning and rollback
- [ ] Export executions as PDF reports
- [ ] Email notifications for execution results
- [ ] Slack/Teams integration
- [ ] Docker Compose for full stack deployment

**Low Priority:**
- [ ] Mobile-responsive UI
- [ ] Dark/light theme toggle
- [ ] Playbook templates marketplace
- [ ] Integration with Ignition Exchange
- [ ] GraphQL API (in addition to REST)

---

## 🛠️ Technical Debt & Refactoring

### Code Quality

**Identified Areas:**
- [ ] Reduce Ruff linting warnings (45 remaining, mostly E501 line length)
- [ ] Improve MyPy type coverage (201 type errors, non-blocking)
- [ ] Refactor large API routers (executions.py >400 lines)
- [ ] Consolidate duplicate Pydantic models

### Testing

**Gaps:**
- [ ] Integration tests for full playbook workflows
- [ ] End-to-end tests with real Ignition Gateway
- [ ] Performance/load testing
- [ ] Browser automation test coverage

### Documentation

**Completed (v3.0):**
- ✅ Version consistency across all docs
- ✅ Obsolete file cleanup
- ✅ Archive historical implementation notes
- ✅ Create NEW_DEVELOPER_START_HERE.md
- ✅ CI/CD setup documentation
- ✅ Pre-release workflow guide

**Remaining:**
- [ ] API endpoint documentation (OpenAPI/Swagger)
- [ ] Video tutorials for common workflows
- [ ] Troubleshooting guide expansion

---

## 📊 Success Metrics

### Adoption Metrics
- **Active Users:** Track number of unique users per month
- **Playbook Library Growth:** Count of shared playbooks
- **Execution Volume:** Total playbook runs per week

### Quality Metrics
- **Test Coverage:** Target 80% (currently ~60%)
- **Bug Resolution Time:** Average <48 hours
- **Documentation Completeness:** All features documented

### Performance Metrics
- **Execution Speed:** Average playbook runtime <2 minutes
- **UI Responsiveness:** Page load <1 second
- **WebSocket Latency:** <100ms for real-time updates

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Proposing new features
- Reporting bugs
- Submitting pull requests
- Code review process

---

## 📞 Feedback & Support

**Feature Requests:**
- Create an issue with the `feature-request` label
- Describe the use case and expected behavior
- Include mockups or examples if possible

**Questions:**
- Check [docs/](docs/) for existing documentation
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions
- See [.claude/CLAUDE.md](.claude/CLAUDE.md) for development guide

---

**Last Reviewed:** 2025-10-28
**Next Review:** On each major version bump
**Maintainer:** Nigel G
