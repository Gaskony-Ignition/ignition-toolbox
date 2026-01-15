# V3.0.0 REFACTOR - ARCHITECTURAL DECISIONS LOG

**Purpose:** Record all architectural decisions made during the V3.0.0 refactor to maintain context and rationale.

---

## Decision Template

```markdown
## AD-XXX: [Decision Title]
**Date:** YYYY-MM-DD
**Status:** Proposed / Accepted / Superseded / Deprecated
**Context:** [What is the issue we're seeing that is motivating this decision?]
**Decision:** [What is the change we're actually proposing/doing?]
**Consequences:** [What becomes easier or more difficult to do because of this change?]
**Alternatives Considered:** [What other options were evaluated?]
```

---

## AD-001: Docker Compose for Process Management
**Date:** 2025-10-27
**Status:** ✅ Accepted
**Supersedes:** ADR-003 (No Docker)

**Context:**
- Server repeatedly fails to start from different directories
- Zombie processes accumulate (8+ background tasks in one session)
- Hardcoded paths cause failures when working directory changes
- User frustration: "PLEASE PLEASE figure out way to fix this issue. Every single time now you say its good and its not"
- No reliable health checks or process cleanup

**Decision:**
Use Docker Compose for both development and production deployments with three profiles:
1. **default** (production): Backend only with SQLite
2. **dev**: Backend + frontend-dev container with hot reload
3. **postgres**: Backend + PostgreSQL for production option

**Consequences:**
✅ **Easier:**
- Consistent startup from any directory
- Automatic health checks and restart policies
- Clean shutdown (no zombie processes)
- Environment isolation
- Deployment to production servers

❌ **More Difficult:**
- Initial setup complexity (Dockerfile, docker-compose.yml)
- Learning curve for users unfamiliar with Docker
- Debugging inside containers

**Alternatives Considered:**
1. **Supervisor** - Python-based process manager
   - Pros: Native Python, simple config
   - Cons: Still allows zombie processes, no health checks
2. **systemd** - Linux service manager
   - Pros: Native to Linux, robust
   - Cons: Requires root, complex for development
3. **Keep shell scripts** - Current approach
   - Pros: No new dependencies
   - Cons: Proven unreliable, caused all current issues

**Rationale:** Docker Compose solves ALL current startup issues and provides production-ready deployment.

---

## AD-002: PostgreSQL as Optional Database
**Date:** 2025-10-27
**Status:** ✅ Accepted

**Context:**
- Current SQLite works for development but may not scale for production
- User wants PostgreSQL option for production deployments
- Must maintain simplicity for local development

**Decision:**
- **Default:** SQLite for development and simple deployments
- **Optional:** PostgreSQL via `docker-compose --profile postgres up`
- Database backend selected via environment variable: `DATABASE_URL`

**Consequences:**
✅ **Easier:**
- Production-ready scaling option
- Multi-user support
- Better concurrent access

❌ **More Difficult:**
- Two database backends to test
- Schema migrations must work for both
- More complex configuration

**Alternatives Considered:**
1. **PostgreSQL only** - Single database
   - Pros: One codebase
   - Cons: Overkill for local dev, requires Docker always
2. **SQLite only** - Keep current
   - Pros: Simplicity
   - Cons: Not production-ready for scale
3. **MySQL** - Alternative production DB
   - Pros: Also production-ready
   - Cons: Less compatible with SQLite schemas

**Rationale:** SQLite + optional PostgreSQL balances simplicity and production readiness.

---

## AD-003: Plugin Architecture for Step Types
**Date:** 2025-10-27
**Status:** ✅ Accepted

**Context:**
- Current step types are hardcoded in `step_executor.py`
- Users cannot add custom step types without modifying core code
- 21 step types spread across Gateway, Perspective, and Utility categories
- User goal: "eventually... we can work on building & adjusting playbooks without having to modify the core project code"

**Decision:**
Implement entry point-based plugin architecture:
- Base class: `StepPlugin` with `step_type` and `execute()` method
- Registration via `pyproject.toml` entry points
- Plugin loader discovers and registers all plugins at startup
- Core plugins shipped with toolkit, custom plugins installable via pip

**Consequences:**
✅ **Easier:**
- Users can create custom step types
- Core code remains stable
- Plugins can be versioned independently
- Third-party plugins possible

❌ **More Difficult:**
- More complex architecture
- Plugin discovery overhead
- Backward compatibility for old playbook format

**Alternatives Considered:**
1. **Keep hardcoded** - Current approach
   - Pros: Simple, direct
   - Cons: Requires core modifications, not extensible
2. **Config-based registration** - YAML defines step types
   - Pros: No code changes for new types
   - Cons: Limited to predefined patterns, not flexible
3. **Importlib dynamic loading** - Import by string path
   - Pros: Flexible
   - Cons: Security risk, no standardization

**Rationale:** Entry points are Python's standard plugin mechanism, secure and maintainable.

---

## AD-004: API Versioning (/api/v1/*)
**Date:** 2025-10-27
**Status:** ✅ Accepted

**Context:**
- Current API has no versioning: `/api/playbooks`, `/api/executions`, etc.
- Future changes would break existing clients (frontend, CLI, integrations)
- V3.0.0 is a major refactor with potential breaking changes

**Decision:**
Implement URL path versioning:
- Move all endpoints from `/api/*` to `/api/v1/*`
- Add redirects for backward compatibility (temporary)
- Document deprecation policy
- Frontend updated to use `/api/v1/`

**Consequences:**
✅ **Easier:**
- Future breaking changes don't affect existing clients
- Clear communication of API evolution
- Multiple API versions can coexist

❌ **More Difficult:**
- URL changes require frontend updates
- More routes to maintain during transition
- Must document version differences

**Alternatives Considered:**
1. **Header versioning** - `Accept: application/vnd.ignition.v1+json`
   - Pros: URLs stay clean
   - Cons: Harder to test, not browser-friendly
2. **Query parameter** - `/api/playbooks?version=1`
   - Pros: Flexible
   - Cons: Easy to forget, not standard
3. **Subdomain** - `v1.api.ignition-toolkit.com`
   - Pros: Complete isolation
   - Cons: Overkill for this project, DNS complexity

**Rationale:** URL path versioning is RESTful, explicit, and easiest to understand.

---

## AD-005: Version 3.0.0 (Major Version Bump)
**Date:** 2025-10-27
**Status:** ✅ Accepted

**Context:**
- Current version: v2.4.0
- Massive refactor planned: Docker, plugins, code split, API versioning
- Semantic versioning: MAJOR.MINOR.PATCH
- Breaking changes warrant major version bump

**Decision:**
Bump version to v3.0.0 to signal major architectural changes.

**Breaking Changes:**
- Docker Compose replaces shell scripts
- Plugin architecture changes step type format
- API versioning changes URLs
- Config structure changes (centralized .env)
- Code structure changes (app.py split)

**Consequences:**
✅ **Easier:**
- Clear signal to users that this is a major change
- Expectations set for migration effort
- Fresh start for documentation

❌ **More Difficult:**
- Users must migrate from v2.x to v3.x
- Must document migration path
- Must maintain v2.x for a period

**Alternatives Considered:**
1. **v2.5.0** - Minor version bump
   - Pros: Less scary
   - Cons: Doesn't signal breaking changes
2. **v3.0.0-beta** - Beta release first
   - Pros: Testing period
   - Cons: Delays release, user confusion
3. **v4.0.0** - Skip v3
   - Pros: Even clearer break
   - Cons: Unnecessary, v3 is appropriate

**Rationale:** Semantic versioning dictates major version for breaking changes.

---

## AD-006: Archive Old Step Format Immediately
**Date:** 2025-10-27
**Status:** ✅ Accepted

**Context:**
- Old hardcoded step format exists in current codebase
- Plugin architecture requires new format
- User requested: "Archive it immediately"

**Decision:**
- Create migration tool: `ignition-toolkit migrate-playbooks`
- Auto-convert old format → new plugin format
- Create backups before conversion
- Deprecation warnings for old format (not errors)
- Remove old format code in v4.0.0

**Consequences:**
✅ **Easier:**
- Clean codebase for plugin architecture
- Users guided to new format
- Migration tool reduces manual work

❌ **More Difficult:**
- Must maintain both formats temporarily
- Migration tool complexity
- Testing migration for all step types

**Alternatives Considered:**
1. **Keep both formats** - Maintain forever
   - Pros: No migration needed
   - Cons: Technical debt, confusing for users
2. **Breaking change** - Remove old format immediately
   - Pros: Clean break
   - Cons: User playbooks break without warning
3. **Manual migration** - Let users convert manually
   - Pros: Simple for us
   - Cons: Error-prone, user frustration

**Rationale:** Migration tool balances clean codebase with user-friendly transition.

---

## AD-007: Makefile for Unified Commands
**Date:** 2025-10-27
**Status:** ✅ Accepted

**Context:**
- Current approach: Shell scripts (`start_server.sh`, `stop_server.sh`, etc.)
- User must remember different commands for different tasks
- No standardized interface for common operations

**Decision:**
Create Makefile with 20+ commands:
- `make install` - Setup environment
- `make start` - Start server (Docker or local)
- `make stop` - Stop all processes
- `make test` - Run test suite
- `make lint` - Code quality checks
- `make build` - Build Docker images
- And more...

**Consequences:**
✅ **Easier:**
- Single entry point for all operations
- Self-documenting (`make help`)
- Cross-platform (works on Linux, macOS, WSL)
- Consistent interface

❌ **More Difficult:**
- Must maintain Makefile
- Users must have `make` installed
- Windows users need WSL or make alternative

**Alternatives Considered:**
1. **Keep shell scripts** - Current approach
   - Pros: No new dependencies
   - Cons: Inconsistent, hard to remember
2. **Python CLI only** - `ignition-toolkit start`, etc.
   - Pros: Python-native
   - Cons: Must install package first
3. **npm scripts** - package.json scripts
   - Pros: Familiar to JS devs
   - Cons: Requires Node.js, not standard for Python

**Rationale:** Makefiles are industry standard for Python projects, proven pattern.

---

## Future Decisions

### Pending Decisions (to be documented as made):
- Lock file strategy (pip-compile vs poetry vs pipenv)
- Logging format (JSON vs text for production)
- JWT token expiration policy
- Rate limiting thresholds
- Monitoring/metrics collection approach
- Frontend container build strategy
- Database migration tool (Alembic vs raw SQL)

### Questions to Answer:
- Should we support Python 3.9 or require 3.10+?
- Should we add GraphQL API alongside REST?
- Should we create official Docker Hub images?
- Should we publish to PyPI?

---

**Last Updated:** 2025-10-27 (Session 1)
**Next Review:** After Phase 1 completion
