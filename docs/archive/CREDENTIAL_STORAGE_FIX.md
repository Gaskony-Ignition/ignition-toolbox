# Credential Storage Location Fix

**Date:** 2025-10-25
**Issue:** Multiple credential storage locations causing data loss between sessions
**Status:** ✅ FIXED

## Problem

### Root Cause
The application was using `Path.home()` to determine where to store credentials and data. However, the `HOME` environment variable changes between Claude Code sessions:

- Session 1: `HOME=/root/.config/claude-work`
- Session 2: `HOME=/root/.config/claude-personal`
- Session 3: `HOME=/root` (default)

This caused credentials to be stored in different locations:
```
/root/.config/claude-work/.ignition-toolkit/
/root/.config/claude-personal/.ignition-toolkit/
/root/.ignition-toolkit/
```

**Result:** Users would lose access to their credentials when the HOME variable changed.

###Impact
- Gateway credentials (username/password) stored in different locations
- AI credentials (API keys) in different databases
- Playbook metadata scattered across directories
- Confusing user experience ("Where did my credentials go?")

## Solution

### 1. Created Centralized Config Module (`ignition_toolkit/config.py`)

**New function:** `get_toolkit_data_dir()`

**Priority order:**
1. `IGNITION_TOOLKIT_DATA` environment variable (override)
2. Project directory: `/git/ignition-playground/data/.ignition-toolkit`
3. Fallback: `/root/.ignition-toolkit` (actual root, not $HOME)

**Benefits:**
- ✅ Consistent location regardless of HOME variable
- ✅ Project-relative storage (keeps data with code)
- ✅ Environment variable override for custom setups
- ✅ No dependence on changing environment variables

### 2. Automatic Migration

**New function:** `migrate_credentials_if_needed()`

**Behavior:**
- Checks old locations for existing credentials
- If found, automatically copies to new location
- Only migrates once (doesn't overwrite existing data)
- Logs migration activity for transparency

**Old locations checked:**
```python
[
    Path("/root/.config/claude-work/.ignition-toolkit"),
    Path("/root/.config/claude-personal/.ignition-toolkit"),
    Path.home() / ".ignition-toolkit",  # Wherever HOME points
]
```

**Files migrated:**
- `credentials.json` (encrypted Gateway credentials)
- `encryption.key` (Fernet encryption key)
- `ignition_toolkit.db` (AI credentials, execution history)
- `playbook_metadata.json` (playbook verification status)

### 3. Updated All Modules

**Files modified:**
1. `ignition_toolkit/credentials/vault.py` - Uses `get_toolkit_data_dir()` instead of `Path.home()`
2. `ignition_toolkit/credentials/encryption.py` - Consistent key location
3. `ignition_toolkit/storage/database.py` - Database in same location as credentials

**Before:**
```python
vault_path = Path.home() / ".ignition-toolkit"  # WRONG!
```

**After:**
```python
vault_path = get_toolkit_data_dir()  # Consistent location
migrate_credentials_if_needed()      # Auto-migrate old data
```

## New Storage Location

**All data now stored in:**
```
/git/ignition-playground/data/.ignition-toolkit/
├── credentials.json          # Gateway credentials (encrypted)
├── encryption.key            # Fernet key (600 permissions)
├── ignition_toolkit.db       # AI credentials, execution history
└── playbook_metadata.json    # Playbook verification status
```

**Benefits:**
- ✅ Single, consistent location
- ✅ Survives environment variable changes
- ✅ Easy to backup (all in one place)
- ✅ Easy to version control exclusion (already in .gitignore)
- ✅ Portable with project

## Environment Variable Override

For advanced users or deployment scenarios:

```bash
export IGNITION_TOOLKIT_DATA=/custom/path/.ignition-toolkit
```

This allows:
- Custom storage locations
- Shared credentials across multiple project copies
- Docker volume mounts
- Network storage

## Testing

**Migration tested successfully:**
```
$ rm -rf /git/ignition-playground/data/.ignition-toolkit
$ python3 -c "from ignition_toolkit.credentials import CredentialVault; CredentialVault()"

INFO:ignition_toolkit.config:Found credentials in old location: /root/.config/claude-personal/.ignition-toolkit
INFO:ignition_toolkit.config:Migrating to new location: /git/ignition-playground/data/.ignition-toolkit
INFO:ignition_toolkit.config:✓ Migration complete
```

**Verification:**
```bash
$ curl http://localhost:5000/api/credentials
[{"name":"localgateway","username":"admin","gateway_url":"http://localhost:9088"}]
```

## Breaking Changes

**None.** The automatic migration ensures existing users don't lose data.

## Future Improvements

1. Add migration status to health check endpoint
2. Add CLI command to show current data location
3. Add CLI command to manually trigger migration
4. Add warning if old locations still contain data after migration

## Lessons Learned

1. **Never use `Path.home()` in application code** - it's environment-dependent
2. **Use project-relative paths** or explicit configuration
3. **Always provide migration path** when changing storage locations
4. **Log migration activities** for debugging and transparency
5. **Test with different environment variables** to catch this type of issue

## Related Files

- `ignition_toolkit/config.py` - New config module
- `ignition_toolkit/credentials/vault.py` - Updated to use config
- `ignition_toolkit/credentials/encryption.py` - Updated to use config
- `ignition_toolkit/storage/database.py` - Updated to use config

## References

- [PEP 518](https://peps.python.org/pep-0518/) - Project configuration
- [Cryptography Fernet](https://cryptography.io/en/latest/fernet/) - Encryption
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM

---

**Status:** Production ready ✅
**Version:** 1.0.31+
**Confidence:** High 🎯
