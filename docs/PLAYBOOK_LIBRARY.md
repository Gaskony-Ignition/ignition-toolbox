# Playbook Library - User Guide

**Version:** 5.1.0
**Last Updated:** 2025-11-21

## Overview

The Playbook Library is a plugin architecture that allows you to browse, install, update, and manage playbooks from a central repository. Instead of bundling all playbooks with the toolkit, you can now install only the playbooks you need.

## Key Concepts

### Playbook Sources

There are three types of playbooks in v5.0:

1. **Built-in Playbooks** (6 base playbooks)
   - Bundled with the toolkit installation
   - Located in `ignition_toolkit/playbooks/gateway/`
   - Cannot be uninstalled (they're part of the core toolkit)
   - Include:
     - Gateway Login
     - Gateway Backup
     - Module Install
     - Module Uninstall
     - Module Upgrade
     - Gateway Restart

2. **User-Installed Playbooks**
   - Downloaded from the central repository
   - Located in `~/.ignition-toolkit/playbooks/`
   - Can be installed, updated, and uninstalled
   - Verified by the repository maintainer

3. **User-Created Playbooks**
   - Your own custom playbooks
   - Located in `~/.ignition-toolkit/playbooks/`
   - Marked as "user-created" in the registry
   - Not available in the repository

### Playbook Registry

The registry tracks all installed playbooks:
- **Location:** `~/.ignition-toolkit/registry.json`
- **Tracks:** Installed playbooks, available playbooks (cached)
- **Metadata:** Version, source, checksum, verification status

### Priority Order

When multiple playbooks have the same path:
1. User-installed playbooks (highest priority)
2. Built-in playbooks (fallback)

This allows you to override built-in playbooks by installing a newer version.

---

## Using the Playbook Library

### Browse Available Playbooks

1. Navigate to the **Playbooks** page
2. Click **"Browse Library"** button (store icon)
3. The Playbook Library dialog opens showing:
   - All available playbooks from the repository
   - Filter by domain (Gateway/Perspective/Designer)
   - Search by name, description, author, or tags
   - Verified badge for verified playbooks
   - Version numbers and file sizes

### Install a Playbook

1. In the Playbook Library dialog, find the playbook you want
2. Click the **"Install"** button
3. The playbook is:
   - Downloaded from GitHub Releases
   - Checksum verified (SHA256)
   - Installed to `~/.ignition-toolkit/playbooks/`
   - Registered in the registry
4. Refresh the playbook list to see the new playbook

**Example:**
```bash
# Install via CLI (alternative)
python -m ignition_toolkit.playbook.installer install gateway/module_upgrade
```

### Check for Updates

1. Navigate to the **Playbooks** page
2. Click **"Updates"** button (update icon)
3. The Updates dialog shows:
   - Playbooks with available updates
   - Current version vs latest version
   - Release notes for each update
   - Major vs minor update badges
4. Click **"Update"** to install the latest version

**Automatic Check:**
- Updates are checked every 5 minutes automatically
- A red badge shows the number of available updates

### Uninstall a Playbook

**Via UI:**
1. Navigate to the Playbooks page
2. Find the playbook you want to remove
3. Click the delete icon on the playbook card
4. Confirm the deletion

**Via CLI:**
```bash
python -m ignition_toolkit.playbook.installer uninstall gateway/module_upgrade
```

**Note:** Built-in playbooks cannot be uninstalled (they're part of the core toolkit).

---

## Advanced Usage

### Manual Playbook Installation

If you have a playbook YAML file:

1. Navigate to Playbooks page
2. Click **"Import"** button
3. Select the YAML file
4. The playbook is:
   - Validated for correct syntax
   - Installed to the appropriate domain directory
   - Registered as "imported"

### Update a Specific Playbook

```bash
python -m ignition_toolkit.playbook.installer update gateway/module_upgrade
```

### View Registry Contents

```python
from ignition_toolkit.playbook.registry import PlaybookRegistry

registry = PlaybookRegistry()
registry.load()

# List installed playbooks
for pb in registry.get_installed_playbooks():
    print(f"{pb.playbook_path} (v{pb.version}) - {pb.source}")

# List available playbooks (cached)
for pb in registry.get_available_playbooks():
    print(f"{pb.playbook_path} (v{pb.version})")

# Check for updates
updates = registry.check_for_updates()
for path, (current, latest) in updates.items():
    print(f"{path}: {current} → {latest}")
```

---

## Playbook Verification

### Verified Playbooks

Playbooks in the central repository may be marked as **verified**:
- ✅ **Verified**: Tested and approved by the repository maintainer
- 🔒 **Verified By**: Shows who verified the playbook
- 📅 **Verified At**: Date of verification

### Checksum Verification

All playbook installations verify the SHA256 checksum:
- Ensures the downloaded file matches the repository
- Protects against corrupted or tampered downloads
- Can be disabled with `verify_checksum=False` (not recommended)

---

## Repository Structure

The central repository uses GitHub Releases:

### Repository URL
```
https://github.com/nigelgwork/ignition-playground
```

### Playbooks Index
```
https://github.com/nigelgwork/ignition-playground/releases/latest/download/playbooks-index.json
```

### Index Format
```json
{
  "version": "1.0",
  "last_updated": "2025-11-19T00:00:00Z",
  "playbooks": {
    "gateway/module_upgrade": {
      "version": "4.0",
      "domain": "gateway",
      "verified": true,
      "verified_by": "Nigel G",
      "description": "Upgrade an existing module",
      "download_url": "https://github.com/.../module_upgrade.yaml",
      "checksum": "sha256:abc123...",
      "size_bytes": 4303,
      "author": "Nigel G",
      "tags": ["gateway", "module", "upgrade"],
      "dependencies": [],
      "release_notes": "Fixed boolean slider for unsigned modules"
    }
  }
}
```

---

## Troubleshooting

### Playbook Not Found in Repository

**Symptom:** "Playbook not found in repository" error

**Solution:**
1. Refresh the library: Click the refresh icon in the Library dialog
2. Check if the playbook path is correct
3. Verify internet connection
4. Check GitHub availability

### Checksum Verification Failed

**Symptom:** "Checksum verification failed" error

**Solution:**
1. Retry the installation (may be a network error)
2. Clear the cache and try again
3. Report to repository maintainer if problem persists

### Playbook Already Installed

**Symptom:** "Playbook already installed" error

**Solution:**
1. Uninstall the old version first
2. Or use the "Update" button instead
3. Or force reinstall: `installer.uninstall(..., force=True)` then install

### Cannot Uninstall Built-in Playbook

**Symptom:** "Cannot uninstall built-in playbook" error

**Explanation:** The 6 base playbooks are part of the core toolkit and cannot be removed.

**Workaround:** Install a newer version with the same path to override it.

---

## Best Practices

### 1. Keep Playbooks Updated
- Check for updates regularly (every few weeks)
- Major updates may include breaking changes
- Read release notes before updating

### 2. Verify Downloaded Playbooks
- Always keep checksum verification enabled
- Only install playbooks from trusted sources
- Check the "verified" badge

### 3. Backup Custom Playbooks
- Export your custom playbooks: Click Export on playbook card
- Save the JSON file to a safe location
- Import on other machines or after reinstall

### 4. Use Playbook Groups
- Organize related playbooks with the `group` field
- Groups appear as nested accordions in the UI
- Example: `group: "Gateway (Base Playbooks)"`

### 5. Test After Migration
- After upgrading to v5.0, test all critical playbooks
- Verify credentials still work
- Check execution history is preserved

---

## Migration from v4.x to v5.0

See [MIGRATION_V5.md](MIGRATION_V5.md) for detailed migration instructions.

**Quick Migration:**
```bash
# Automatic migration
python scripts/migrate-to-v5.py

# With cleanup (removes old playbooks directory)
python scripts/migrate-to-v5.py --clean
```

---

## API Reference

### Browse Available Playbooks
```
GET /api/playbooks/browse?force_refresh=false
```

### Install Playbook
```
POST /api/playbooks/install
{
  "playbook_path": "gateway/module_upgrade",
  "version": "latest",
  "verify_checksum": true
}
```

### Uninstall Playbook
```
DELETE /api/playbooks/{playbook_path}/uninstall?force=false
```

### Update Playbook
```
POST /api/playbooks/{playbook_path}/update
```

### Check for Updates
```
GET /api/playbooks/updates?force_refresh=false
```

### Get Update for Specific Playbook
```
GET /api/playbooks/updates/{playbook_path}
```

### Get Update Statistics
```
GET /api/playbooks/updates/stats
```

---

## FAQ

**Q: Where are my custom playbooks stored?**
A: User-created and installed playbooks are in `~/.ignition-toolkit/playbooks/`

**Q: Can I share my custom playbooks?**
A: Yes! Export them using the Export button, then share the JSON file.

**Q: What happens if I delete the registry file?**
A: The registry will be rebuilt next time the app starts. You may need to re-register playbooks.

**Q: Can I use playbooks offline?**
A: Yes, once installed. Browsing and installing new playbooks requires internet.

**Q: How do I contribute playbooks to the repository?**
A: Fork the repository, add your playbook to the appropriate directory, and submit a pull request.

**Q: What's the difference between "user-installed" and "user-created"?**
A: "user-installed" = downloaded from repository, "user-created" = you wrote it yourself.

---

## See Also

- [Migration Guide (v5.0)](MIGRATION_V5.md)
- [Playbook Syntax Reference](playbook_syntax.md)
- [Getting Started Guide](getting_started.md)
- [Architecture Documentation](../ARCHITECTURE.md)
