# Migration Guide: v4.x → v5.0

**Target Version:** 5.0.0
**Migration Date:** 2025-11-19
**Migration Tool:** `scripts/migrate-to-v5.py`

---

## Overview

Version 5.0 introduces a **plugin architecture** for playbooks, transforming the toolkit from a monolithic structure to a modular, extensible system. This is a **major architectural change** that requires migration.

### Key Changes

1. **✂️ AI Features Removed** (temporarily)
   - All AI step types removed from the toolkit
   - AI features will return in a future release as an optional plugin
   - Playbooks using AI steps will fail to load

2. **📦 Playbook Library Introduced**
   - Browse and install playbooks from a central repository
   - Update checking for installed playbooks
   - Checksum verification for secure downloads
   - GitHub Releases as the distribution mechanism

3. **🏗️ Directory Restructure**
   - **Before:** All playbooks in `playbooks/`
   - **After:**
     - Built-in (6 base): `ignition_toolkit/playbooks/gateway/`
     - User-installed: `~/.ignition-toolkit/playbooks/`
   - Priority: User playbooks override built-in playbooks

4. **📋 Playbook Registry**
   - New registry tracks all installed playbooks
   - Location: `~/.ignition-toolkit/registry.json`
   - Tracks version, source, checksum, verification status

5. **🔐 Enhanced Security**
   - SHA256 checksum verification for all downloads
   - Verified playbook badges in UI
   - Protected base playbooks (cannot be uninstalled)

---

## Pre-Migration Checklist

Before migrating to v5.0, ensure:

- [ ] **Backup your data:**
  ```bash
  # Backup playbooks directory
  cp -r playbooks playbooks.backup.$(date +%Y%m%d)

  # Backup user data
  cp -r ~/.ignition-toolkit ~/.ignition-toolkit.backup.$(date +%Y%m%d)
  ```

- [ ] **Export custom playbooks:**
  - Go to Playbooks page
  - Click Export on each custom playbook
  - Save JSON files to a safe location

- [ ] **Document your setup:**
  - List of installed playbooks
  - Custom configurations
  - Saved credentials (these are preserved)

- [ ] **Check for AI playbooks:**
  ```bash
  # Search for AI step types
  grep -r "ai\." playbooks/ --include="*.yaml"
  ```
  - If found, these playbooks will fail after migration
  - Remove or comment out AI steps before migrating

- [ ] **Git commit (if using version control):**
  ```bash
  git add .
  git commit -m "Pre-v5.0 migration snapshot"
  ```

---

## Migration Steps

### Step 1: Update the Toolkit

```bash
cd /git/ignition-playground

# Pull latest changes
git fetch origin
git checkout master
git pull origin master

# Update dependencies (if needed)
pip install -e .
```

### Step 2: Run Migration Script (Dry Run)

First, test the migration without making changes:

```bash
python scripts/migrate-to-v5.py --dry-run
```

**Review the output:**
- Number of base playbooks found (should be 6)
- Number of user playbooks to migrate
- Any errors or warnings

**Expected output:**
```
Base playbooks found: 6
User playbooks migrated: X
Backup files skipped: Y
Errors: 0
```

### Step 3: Run Migration (Live)

If the dry run looks good, run the actual migration:

```bash
python scripts/migrate-to-v5.py
```

**What happens:**
1. 6 base playbooks are registered as "built-in"
2. All other playbooks are copied to `~/.ignition-toolkit/playbooks/`
3. All playbooks are registered in the registry
4. Old `playbooks/` directory remains (for backup)

### Step 4: Verify Migration

```bash
# Check registry contents
python -c "
from ignition_toolkit.playbook.registry import PlaybookRegistry
registry = PlaybookRegistry()
registry.load()
print(f'Installed playbooks: {len(registry.installed)}')
for pb in registry.get_installed_playbooks():
    print(f'  {pb.playbook_path} (v{pb.version}) [{pb.source}]')
"

# Check user playbooks directory
ls -la ~/.ignition-toolkit/playbooks/
```

### Step 5: Test Playbook Loading

```bash
# Start the server
ignition-toolkit serve

# In another terminal, check API
curl http://localhost:9000/api/playbooks
```

**In the UI:**
1. Navigate to Playbooks page
2. Verify all playbooks appear
3. Check that base playbooks show "built-in" badge
4. Try executing a simple playbook (e.g., Gateway Login)

### Step 6: Clean Up (Optional)

After verifying everything works:

```bash
# Remove old playbooks directory
python scripts/migrate-to-v5.py --clean
```

This creates a timestamped backup before removing the old directory.

---

## What Gets Migrated

### ✅ Automatically Migrated

- **Playbook YAML files** → Copied to new locations
- **Playbook metadata** → Registered in registry
- **Directory structure** → Recreated under `~/.ignition-toolkit/`
- **Execution history** → Preserved (stored separately in database)
- **Credentials** → Preserved (stored in credential vault)
- **Saved configurations** → Preserved (localStorage in UI)

### ❌ Not Migrated

- **AI step types** → Removed (playbooks with AI steps will fail)
- **Backup files** → Skipped (files with `.backup.` in name)
- **Old playbooks directory** → Left intact (for safety)
- **Custom modifications to built-in playbooks** → Overwritten by clean built-ins

---

## Troubleshooting

### Migration Fails with "Playbook already exists"

**Cause:** You've run the migration multiple times.

**Solution:**
```bash
# Clear the registry
rm ~/.ignition-toolkit/registry.json

# Clear user playbooks
rm -rf ~/.ignition-toolkit/playbooks/

# Re-run migration
python scripts/migrate-to-v5.py
```

### Playbooks Not Appearing in UI

**Symptoms:** UI shows empty playbook list.

**Diagnosis:**
```bash
# Check if playbooks exist
ls ~/.ignition-toolkit/playbooks/

# Check if registry exists
cat ~/.ignition-toolkit/registry.json

# Check server logs
tail -f logs/server.log
```

**Solutions:**
1. Re-run migration if playbooks are missing
2. Rebuild frontend if UI is stale: `cd frontend && npm run build`
3. Clear browser cache and reload

### Error Loading Playbook with AI Steps

**Symptom:** "Invalid step type 'ai.xxx'" error

**Cause:** AI features were removed in v5.0.

**Solution:**
1. Remove AI playbooks:
   ```bash
   # Find AI playbooks
   grep -r "type: ai\." ~/.ignition-toolkit/playbooks/ --include="*.yaml"

   # Remove them
   rm path/to/ai_playbook.yaml
   ```

2. Or comment out AI steps in the YAML:
   ```yaml
   # - id: ai_step
   #   type: ai.analyze_page_structure
   #   ...
   ```

### Registry Corruption

**Symptom:** JSON parse errors when loading registry.

**Solution:**
```bash
# Backup corrupted registry
mv ~/.ignition-toolkit/registry.json ~/.ignition-toolkit/registry.json.corrupted

# Re-run migration to rebuild
python scripts/migrate-to-v5.py
```

---

## Rolling Back

If you need to roll back to v4.x:

### Step 1: Restore Backup

```bash
# Restore playbooks directory
rm -rf playbooks
cp -r playbooks.backup.YYYYMMDD playbooks

# Restore user data
rm -rf ~/.ignition-toolkit
cp -r ~/.ignition-toolkit.backup.YYYYMMDD ~/.ignition-toolkit
```

### Step 2: Checkout v4.x

```bash
git checkout v4.1.1  # Or your previous version
pip install -e .
```

### Step 3: Restart Server

```bash
ignition-toolkit serve
```

---

## Breaking Changes

### 1. AI Features Removed

**Before (v4.x):**
```yaml
- id: analyze_page
  type: ai.analyze_page_structure
  parameters:
    url: "{{ url }}"
```

**After (v5.0):**
```
ERROR: Invalid step type 'ai.analyze_page_structure'
```

**Migration Path:** Remove AI steps or wait for AI plugin in future release.

### 2. Playbook Path Changes

**Before (v4.x):**
- All playbooks in `playbooks/`
- Hardcoded path: `playbooks/gateway/module_upgrade.yaml`

**After (v5.0):**
- Built-in: `ignition_toolkit/playbooks/gateway/`
- User: `~/.ignition-toolkit/playbooks/`
- Dynamic resolution with priority

**Migration Path:** Use `get_all_playbook_dirs()` instead of hardcoded paths.

### 3. Playbook Source Tracking

**Before (v4.x):**
- No tracking of playbook source
- All playbooks treated equally

**After (v5.0):**
- Source field: `built-in`, `user-installed`, `user-created`, `imported`
- Built-in playbooks protected from deletion

**Migration Path:** No action needed (automatic during migration).

### 4. Registry Required

**Before (v4.x):**
- No registry file
- Playbooks scanned on every startup

**After (v5.0):**
- Registry file required: `~/.ignition-toolkit/registry.json`
- Faster startup (no directory scanning)

**Migration Path:** Run migration script to create registry.

---

## New Features in v5.0

### 1. Playbook Library UI

**Access:** Playbooks page → "Browse Library" button

**Features:**
- Browse 24+ playbooks from central repository
- Filter by domain (Gateway/Perspective/Designer)
- Search by name/description/author/tags
- One-click installation with checksum verification
- Verified badge for trusted playbooks

### 2. Update Checking

**Access:** Playbooks page → "Updates" button (with badge)

**Features:**
- Automatic check every 5 minutes
- Visual indicators for major vs minor updates
- Release notes display
- One-click updates
- Update statistics dashboard

### 3. Playbook Management API

**New Endpoints:**
```
GET  /api/playbooks/browse
POST /api/playbooks/install
DELETE /api/playbooks/{path}/uninstall
POST /api/playbooks/{path}/update
GET  /api/playbooks/updates
GET  /api/playbooks/updates/{path}
GET  /api/playbooks/updates/stats
```

### 4. Enhanced Security

- SHA256 checksum verification for all downloads
- Verified playbook badges
- Protected built-in playbooks
- Source tracking for audit trail

---

## Post-Migration Tasks

After successfully migrating:

### 1. Browse the Library

Explore available playbooks:
1. Click "Browse Library"
2. Install playbooks you need
3. Remove old duplicates if desired

### 2. Check for Updates

Update your playbooks:
1. Click "Updates" button
2. Review available updates
3. Install updates selectively or all at once

### 3. Clean Up Old Files

Remove unnecessary files:
```bash
# Remove old playbooks directory (after verifying migration)
python scripts/migrate-to-v5.py --clean

# Remove old backups
rm -rf playbooks.backup.*
rm -rf ~/.ignition-toolkit.backup.*
```

### 4. Update Documentation

If you have custom documentation:
- Update references to playbook paths
- Document your installed playbooks
- Note any customizations

### 5. Test Critical Workflows

Test your most important use cases:
- Gateway module upgrades
- Perspective testing
- Designer automation
- Custom playbooks

---

## FAQ

**Q: Will my execution history be preserved?**
A: Yes, execution history is stored separately in the database and is not affected.

**Q: Will my credentials be preserved?**
A: Yes, credentials are stored in the credential vault and are not affected.

**Q: Can I keep using the old playbooks directory?**
A: The old directory is left intact for backup, but the toolkit will only load from the new locations.

**Q: What if I have custom modifications to built-in playbooks?**
A: Export them before migration, then re-import after migration. Built-in playbooks are reset to clean versions.

**Q: Can I roll back after migration?**
A: Yes, if you have backups. See "Rolling Back" section above.

**Q: Will future updates require migration?**
A: Minor updates (5.x) won't require migration. Major updates (6.0+) may require migration scripts.

**Q: What happened to AI features?**
A: Temporarily removed to streamline the toolkit. AI features will return as an optional plugin in a future release.

**Q: Can I contribute playbooks to the repository?**
A: Yes! Fork the repo, add your playbook, and submit a pull request.

---

## Getting Help

If you encounter issues during migration:

1. **Check the logs:**
   ```bash
   tail -f logs/server.log
   ```

2. **Run diagnostics:**
   ```bash
   python -c "from ignition_toolkit.core.paths import validate_paths; print(validate_paths())"
   ```

3. **Ask for help:**
   - GitHub Issues: https://github.com/nigelgwork/ignition-playground/issues
   - Include migration script output
   - Include error messages from logs

---

## See Also

- [Playbook Library Guide](PLAYBOOK_LIBRARY.md)
- [Getting Started Guide](getting_started.md)
- [CHANGELOG](../CHANGELOG.md)
- [Architecture Documentation](../ARCHITECTURE.md)
