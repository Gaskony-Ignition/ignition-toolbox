# Ways of Working - Ignition Automation Toolkit

**Team**: Nigel G + Claude Code
**Project**: Ignition Automation Toolkit
**Start Date**: October 2025

---

## 🎯 Project Philosophy

### Core Principles:
1. **Walk Before We Run** - Gateway automation first, Designer/Perspective later
2. **Simplicity Over Complexity** - No Docker, native Python, SQLite
3. **Security First** - SCADA systems require heightened security awareness
4. **Modular Design** - Each step can be AI-assisted in future
5. **Documentation Driven** - Update docs with code, not after
6. **Type Safety** - Type hints, dataclasses, Pydantic models everywhere

### Decision-Making:
- **Functionality > Polish** - Get it working, then make it pretty
- **User Experience** - CLI should be intuitive, UI should be clean
- **Transferability** - Must work on any Linux/WSL2 machine with minimal setup

---

## 📅 Development Workflow

### Phase-Based Development:
We work in distinct phases (see PLAN.md):
1. Foundation ✅
2. Gateway Client ✅
3. Playbook Engine 🚧
4. Import/Export
5. Frontend Migration
6. Browser Automation
7. AI Scaffolding
8. Testing & Docs

**Rule**: Complete one phase before moving to next. No jumping ahead.

### Daily Workflow:
1. **Review PROGRESS.md** - Check current status
2. **Update todo list** - Mark in_progress, complete immediately when done
3. **Write code** - Focus on current phase
4. **Test manually** - Quick verification
5. **Commit frequently** - Atomic commits with descriptive messages
6. **Update PROGRESS.md** - Document what's working

### Code Review (Self):
Before committing:
- [ ] Run security quick scan
- [ ] Type hints on all functions
- [ ] Docstrings on public methods
- [ ] No TODOs in committed code (or documented in PROGRESS.md)
- [ ] Tests passing (when we have them)

---

## 🔧 Code Standards

### Python Style:
- **Formatter**: Black (line length 100)
- **Linter**: Ruff
- **Type Checker**: mypy (when configured)
- **Imports**: Sorted with isort

### Naming Conventions:
```python
# Classes: PascalCase
class GatewayClient:
    pass

# Functions/methods: snake_case
async def upload_module(self, file_path: Path) -> str:
    pass

# Constants: UPPER_SNAKE_CASE
API_TIMEOUT = 30.0

# Private: _leading_underscore
def _ensure_authenticated(self):
    pass
```

### File Structure:
```python
"""
Module docstring

Brief description of what this module does.
"""

# Standard library imports
import asyncio
from pathlib import Path
from typing import Optional

# Third-party imports
import httpx
from sqlalchemy import Column

# Local imports
from ignition_toolkit.gateway.models import Module
from ignition_toolkit.credentials import CredentialVault

# Module-level constants
TIMEOUT = 30.0

# Module-level logger
logger = logging.getLogger(__name__)

# Classes and functions
class MyClass:
    pass
```

---

## 📝 Documentation Standards

### README Files:
- **README.md** - Project overview, quick start, examples
- **PLAN.md** - Detailed implementation roadmap
- **PROGRESS.md** - Current status, what's working, what's next
- **CLAUDE.md** - Guide for Claude Code AI assistant

### Code Documentation:
```python
def upload_module(self, module_file_path: Path) -> str:
    """
    Upload a module file (.modl) to Gateway

    This method uploads a .modl file to the Gateway and waits for
    acknowledgment. The module will need to be installed separately.

    Args:
        module_file_path: Path to .modl file to upload

    Returns:
        Module ID or name returned by Gateway

    Raises:
        ModuleInstallationError: If upload fails
        FileNotFoundError: If module file doesn't exist

    Example:
        >>> client = GatewayClient("http://localhost:8088")
        >>> await client.login("admin", "password")
        >>> module_id = await client.upload_module(Path("perspective.modl"))
        >>> print(f"Uploaded: {module_id}")
    """
    pass
```

### Inline Comments:
```python
# Good ✅ - Explains WHY
# Wait extra 10 seconds for module initialization (Ignition 8.3 quirk)
await asyncio.sleep(10)

# Bad ❌ - Explains WHAT (obvious from code)
# Sleep for 10 seconds
await asyncio.sleep(10)
```

---

## 🧪 Testing Strategy

### Test Levels:
1. **Unit Tests** - Individual functions/methods
2. **Integration Tests** - Multiple components together
3. **E2E Tests** - Full workflows (future)

### Test Structure:
```python
def test_credential_vault_save_and_retrieve():
    """Test saving and retrieving credentials"""
    # Arrange
    vault = CredentialVault()
    credential = Credential(name="test", username="admin", password="secret")

    # Act
    vault.save_credential(credential)
    retrieved = vault.get_credential("test")

    # Assert
    assert retrieved is not None
    assert retrieved.username == "admin"
    assert retrieved.password == "secret"  # Decrypted
```

### Manual Testing:
Before each phase completion:
1. Test CLI commands work
2. Test main functionality end-to-end
3. Document in PROGRESS.md

---

## 🔒 Security Practices

### Every Commit:
1. Run security quick scan (see SECURITY_CHECKLIST.md)
2. Verify no credentials in code
3. Check .env not staged
4. Validate .gitignore is working

### Every Phase:
1. Review code for security issues
2. Update SECURITY_CHECKLIST.md if needed
3. Document security considerations in PROGRESS.md

### Production Deployment:
- Change all default credentials
- Enable HTTPS/SSL
- Review SECURITY_CHECKLIST.md fully
- Audit logging enabled

---

## 📊 Progress Tracking

### Todo List:
- **in_progress**: Currently working on (only ONE at a time)
- **pending**: Not started yet
- **completed**: Done and verified

### Update Frequency:
- **Start of task**: Mark as in_progress
- **End of task**: Mark as completed immediately
- **Don't batch**: Mark completed as soon as done

### PROGRESS.md:
Update after each significant milestone:
- What's working now
- What's next
- Known issues
- Testing status

---

## 🔄 Git Workflow

### Commit Messages:
```
Brief summary (imperative mood, <50 chars)

Detailed explanation:
- What changed and why
- Key features added or modified
- Related issues or tickets

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Commit Frequency:
- After completing a logical unit of work
- After adding a new feature/method
- After fixing a bug
- Before switching contexts

### Push Frequency:
- After completing a phase
- End of development sessions
- When tests pass
- Before major refactoring

---

## 🎯 Quality Gates

### Before Marking Phase Complete:
- [ ] All planned features working
- [ ] Manual testing done
- [ ] Security quick scan passed
- [ ] PROGRESS.md updated
- [ ] Todo list updated
- [ ] Code committed and pushed
- [ ] Ready for next phase

### Before Release (v1.0):
- [ ] All phases complete
- [ ] Full test suite passing
- [ ] Documentation complete
- [ ] Security audit passed
- [ ] Tested on fresh machine
- [ ] Example playbooks working

---

## 💡 Problem-Solving Approach

### When Stuck:
1. **Review documentation** - PLAN.md, PROGRESS.md, code comments
2. **Check old project** - See if solution exists in ignition-auto-test
3. **Simplify** - Can we make this simpler?
4. **Ask user** - Clarify requirements if ambiguous
5. **Document** - Note the issue and solution in PROGRESS.md

### When Design Changes:
1. **Update PLAN.md** - Document the change
2. **Update PROGRESS.md** - Note why changed
3. **Update CLAUDE.md** - Revise guidance if needed
4. **Commit separately** - Don't mix design changes with features

---

## 🎨 User Experience Principles

### CLI Design:
- **Intuitive**: Commands should be obvious
- **Helpful**: Error messages guide user to solution
- **Consistent**: Similar commands have similar syntax
- **Colorful**: Use Rich library for pretty output

### Example:
```bash
# Good ✅
$ ignition-toolkit credential add gateway_admin
Username: admin
Password: ***
✅ Credential 'gateway_admin' saved successfully
   Use in playbooks: {{ credential.gateway_admin }}

# Bad ❌
$ ignition-toolkit cred add gw_admin
username? admin
password? password
Saved.
```

---

## 📚 Knowledge Sharing

### When Learning Something New:
1. Document in code comments
2. Add to PROGRESS.md if significant
3. Consider adding to CLAUDE.md for future reference

### When Finding a Quirk:
1. Document in code with comment
2. Add to PROGRESS.md "Known Issues"
3. Consider adding workaround example

---

## 🚀 Release Strategy

### Version Numbers (Semantic Versioning):
- **MAJOR** (X.0.0): Breaking changes, architecture changes
- **MINOR** (1.X.0): New features, new capabilities
- **PATCH** (1.0.X): Bug fixes, docs, minor updates

### Release Checklist:
- [ ] All phases complete
- [ ] Tests passing
- [ ] Documentation up to date
- [ ] Security audit passed
- [ ] Example playbooks tested
- [ ] VERSION.md updated
- [ ] Git tag created
- [ ] README.md updated

---

**Last Updated**: 2025-10-22
**Next Review**: Monthly or when process needs adjustment
**Status**: Phase 2 Complete, Phase 3 Next
