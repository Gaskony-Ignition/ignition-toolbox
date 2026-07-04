---
name: security-checking
description: Security checklist and quick scan for the Ignition Toolbox — credentials, input validation, subprocess, and file handling. Load for any security-related work and before commits that touch those areas.
user-invocable: true
---

# Toolbox Security Checking

Condensed and updated from the former SECURITY_CHECKLIST.md.

## Quick scan (before commit)

```bash
cd /home/nigel/ignition/ignition-toolbox

# Hardcoded credentials in backend code
grep -rn "password.*=.*['\"]" --include="*.py" backend/ignition_toolkit/ | grep -v test | grep -v "password: str"

# eval/exec/pickle/shell=True (should return nothing new)
grep -rn "eval(\|exec(\|pickle.loads\|shell=True" --include="*.py" backend/ignition_toolkit/

# Secrets staged for commit (should be empty)
git status --porcelain | grep -E "\.env$|encryption\.key|credentials\.json"
```

## Non-negotiables

- Credentials live in the **Fernet-encrypted vault**
  (`~/.ignition-toolkit/credentials.json` + `encryption.key`, both 0600) or
  `.env` — never in code, playbooks, exports, or logs. Playbook exports must
  contain `{{ credential.xxx }}` references, not values.
- **Losing `encryption.key` = losing all credentials (by design).** It is
  local-only and unrecoverable — see `/home/nigel/ignition/TRANSFER.md` before
  any machine move.
- Never: `eval()`, `exec()`, `pickle.loads()` on untrusted data,
  `subprocess(shell=True)` with user input, string-built SQL.
- Always: SQLAlchemy parameterised queries, `Path()` +
  `resolve().is_relative_to()` for user-supplied paths, Pydantic validation,
  `secrets` for tokens, `httpx` with timeouts.

## Implemented controls (don't regress)

- API key authentication + RBAC + audit logging (`ignition_toolkit/auth/`) —
  the old checklist called these "future"; they shipped in Phase 6.2.
- Gateway client: session cookie management, re-auth on 401, request timeouts.
- Module upload: `.modl` extension + size validation, upload timeout.
- Electron: context isolation on, IPC channels validated in `preload.ts`.

## Ignition-specific checks

- Gateway URLs validated (http/https only); project names alphanumeric + dash/
  underscore; tag paths validated before write; write operations logged.

## Periodic (when touching dependencies)

```bash
cd backend && pip-audit          # Python CVE scan
npm audit --omit=dev             # Electron/frontend scan
```

## Severity triage

Critical (fix before anything else): RCE, credential exposure in repo, auth
bypass. High: privilege escalation, secrets in logs, SQL injection.
Medium: missing validation, info disclosure. Low: verbose errors, headers.
