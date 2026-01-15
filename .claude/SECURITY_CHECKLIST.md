# Security Checklist - Ignition Automation Toolkit

**Project**: Ignition Automation Toolkit
**Security Level**: Medium (Development/Testing Environment)
**Last Audit**: 2025-10-22

---

## ⚡ Quick Scan (Every Commit)

Run before every commit:

```bash
# 1. Check for hardcoded credentials
grep -r "password.*=.*['\"]" --exclude-dir=.git --exclude=".env" --exclude="env.example" ignition_toolkit/

# 2. Verify .env not staged
git status --porcelain | grep "\.env$" && echo "❌ .env file staged - REMOVE IT!"

# 3. Check for dangerous patterns
grep -r "eval(\|exec(" ignition_toolkit/

# 4. Verify encryption key not staged
git status --porcelain | grep "encryption.key" && echo "❌ Encryption key staged - REMOVE IT!"

# 5. Check for TODO security items
grep -r "TODO.*security\|FIXME.*security" ignition_toolkit/

echo "✅ Quick security scan complete"
```

### Input Validation
- [ ] Gateway API inputs validated (URLs, project names, tag paths)
- [ ] File paths validated (no path traversal)
- [ ] Playbook YAML validated before execution
- [ ] Parameter types checked

### Authentication/Authorization
- [ ] No hardcoded Gateway credentials in code
- [ ] All passwords in credential vault or `.env`
- [ ] `.env` file in `.gitignore`
- [ ] `~/.ignition-toolkit/` in `.gitignore`
- [ ] No credentials in logs or error messages

### Data Protection
- [ ] Credentials encrypted with Fernet at rest
- [ ] No sensitive data in logs
- [ ] Error messages don't expose system details
- [ ] Playbook exports don't contain actual credentials

---

## 🔒 Credential Security

### Fernet Encryption
- ✅ Credentials encrypted at rest
- ✅ Encryption key stored in `~/.ignition-toolkit/encryption.key`
- ✅ Key permissions: 0600 (owner read/write only)
- ✅ Credentials file permissions: 0600

### Playbook Security
- [ ] Playbook exports replace credentials with references
- [ ] Exported JSON contains `{{ credential.xxx }}` not actual passwords
- [ ] Import validates credential references exist
- [ ] No credentials in playbook YAML files

### API Security
- [ ] FastAPI authentication implemented (future)
- [ ] WebSocket connections authenticated (future)
- [ ] Rate limiting configured (future)

---

## 🧪 Code Security Patterns

### Never Use:
- ❌ `eval()` - Code injection risk
- ❌ `exec()` - Code injection risk
- ❌ `pickle.loads()` on untrusted data
- ❌ `subprocess.shell=True` with user input
- ❌ String concatenation for SQL queries

### Always Use:
- ✅ Parameterized queries (SQLAlchemy ORM)
- ✅ `Path()` for file operations (prevents traversal)
- ✅ Type validation (Pydantic models)
- ✅ `secrets` module for random tokens
- ✅ `httpx` with timeout parameters

### Example - Safe File Operations:
```python
from pathlib import Path

# Good ✅
def load_playbook(name: str) -> Path:
    playbook_path = Path("./playbooks") / f"{name}.yaml"
    if not playbook_path.resolve().is_relative_to(Path("./playbooks").resolve()):
        raise ValueError("Invalid playbook path")
    return playbook_path

# Bad ❌
def load_playbook(name: str) -> str:
    return f"./playbooks/{name}.yaml"  # Path traversal possible!
```

---

## 🏭 Ignition-Specific Security

### Gateway Security
- [ ] Gateway admin password not default (admin/password)
- [ ] Gateway URL validated (http/https)
- [ ] Session cookies properly managed
- [ ] Re-authentication on 401 responses
- [ ] Timeout configured for all requests

### Module Operations
- [ ] Module files validated (.modl extension)
- [ ] File size limits enforced (prevent DoS)
- [ ] Upload timeout configured
- [ ] Module installation tracked and logged

### Tag Operations (Future)
- [ ] Tag paths validated (no SQL injection via tags)
- [ ] Tag values sanitized
- [ ] Write operations logged
- [ ] Read/write permissions checked

### Project Operations
- [ ] Project names validated (alphanumeric + dash/underscore)
- [ ] Export operations logged
- [ ] Import validates structure

---

## 🔍 Full Security Review (Weekly)

### Dependency Security
```bash
# Python vulnerability scan
pip-audit

# Check outdated packages
pip list --outdated

# Review new dependencies
git diff pyproject.toml
```

### Access Control
- [ ] Credential vault accessible only to owner
- [ ] Database file permissions appropriate (data/*.db)
- [ ] No unnecessary file permissions
- [ ] Logs don't contain credentials

### Logging Security
- [ ] Passwords never logged
- [ ] API keys never logged
- [ ] Error messages don't expose internals
- [ ] Debug logging disabled in production

---

## 🚨 Security Incident Response

If vulnerability discovered:

### 1. STOP
- Halt current development
- Don't commit vulnerable code
- Document issue privately

### 2. ASSESS Severity

**Critical:**
- Remote code execution
- Credential exposure in repository
- Authentication bypass

**High:**
- Privilege escalation
- Sensitive data exposure in logs
- SQL injection vulnerabilities

**Medium:**
- Information disclosure
- Missing input validation
- Weak encryption

**Low:**
- Verbose error messages
- Missing security headers

### 3. FIX Immediately (Critical/High)
- Implement fix in separate branch
- Test thoroughly
- Document in PROGRESS.md

### 4. DOCUMENT
- Update PROGRESS.md
- Note affected versions
- Create git tag for security release

---

## 🛡️ Security Best Practices

### Never Do:
- ❌ Store passwords in plain text
- ❌ Commit `.env` or `encryption.key` to git
- ❌ Use default credentials
- ❌ Trust user input without validation
- ❌ Log sensitive information
- ❌ Hardcode API endpoints or credentials

### Always Do:
- ✅ Use environment variables for config
- ✅ Validate and sanitize all inputs
- ✅ Use parameterized queries
- ✅ Encrypt credentials at rest
- ✅ Keep dependencies updated
- ✅ Implement least privilege
- ✅ Regular security audits

---

## 📋 Pre-Deployment Checklist

Before deploying to a new machine:

- [ ] `.env.example` copied to `.env` and configured
- [ ] `ignition-toolkit init` run to create credential vault
- [ ] Default credentials changed
- [ ] File permissions verified
- [ ] Security scan passed
- [ ] All tests passing

---

## 🔐 Credential Vault Security

### Storage Location:
- `~/.ignition-toolkit/credentials.json` - Encrypted credentials
- `~/.ignition-toolkit/encryption.key` - Fernet key (0600 permissions)

### Encryption:
- **Algorithm**: Fernet (symmetric encryption)
- **Key Generation**: `cryptography.fernet.Fernet.generate_key()`
- **Key Storage**: Local file, not in git
- **Backup**: User responsible for key backup

### Security Measures:
- ✅ Double encryption: JSON encrypted, then passwords re-encrypted
- ✅ File permissions: 0600 (owner only)
- ✅ Key rotation: Planned for future (not v1.0)
- ✅ Loss of key = loss of credentials (by design)

---

## 📊 Security Audit Log

| Date | Issue | Severity | Status | Fix Version |
|------|-------|----------|--------|-------------|
| 2025-10-22 | Project initialized | Info | - | 1.0.0 |

---

**Next Security Audit**: 2025-11-22 (monthly)
**Security Contact**: nigelgwork@users.noreply.github.com
**Report Issues**: GitHub Issues (for non-critical) or email (for critical)
