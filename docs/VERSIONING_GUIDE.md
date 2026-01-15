# Versioning Guide

This guide explains how to manage versions when making changes to the Ignition Automation Toolkit.

## Current Version

**Version**: 1.0.0
**Release Date**: 2025-10-22
**Tag**: v1.0.0

## Semantic Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH

Example: 1.2.3
         │ │ │
         │ │ └─ Patch version (bug fixes)
         │ └─── Minor version (new features, backwards compatible)
         └───── Major version (breaking changes)
```

## When to Increment

### MAJOR version (X.0.0)
Increment when you make **incompatible API changes**:
- Breaking changes to playbook syntax
- Removing step types or parameters
- Changing database schema incompatibly
- Major architecture changes
- Breaking CLI command changes

**Example**: 1.0.0 → 2.0.0

### MINOR version (0.X.0)
Increment when you **add functionality** in a backwards compatible manner:
- New step types
- New CLI commands
- New API endpoints
- Additional parameters (with defaults)
- New features that don't break existing functionality

**Example**: 1.0.0 → 1.1.0

### PATCH version (0.0.X)
Increment when you make **backwards compatible bug fixes**:
- Bug fixes
- Performance improvements
- Documentation updates
- Typo corrections
- Security patches

**Example**: 1.0.0 → 1.0.1

## How to Update Version

### Step 1: Update Version Numbers

Update version in these files:

1. **VERSION file**:
   ```
   1.1.0
   ```

2. **pyproject.toml**:
   ```toml
   version = "1.1.0"  # Updated: 2025-XX-XX - Description of changes
   ```

3. **ignition_toolkit/__init__.py**:
   ```python
   __version__ = "1.1.0"  # Updated: 2025-XX-XX - Description
   __build_date__ = "2025-XX-XX"
   ```

### Step 2: Update CHANGELOG.md

Add new section at the top:

```markdown
## [1.1.0] - 2025-XX-XX

### Added
- New feature X
- New step type Y

### Changed
- Improved performance of Z

### Fixed
- Bug in W

### Deprecated
- Feature V (will be removed in 2.0.0)

### Removed
- None

### Security
- None
```

### Step 3: Commit Changes

```bash
# Stage changes
git add VERSION pyproject.toml ignition_toolkit/__init__.py CHANGELOG.md

# Commit with version bump message
git commit -m "Bump version to 1.1.0

- Added: [list features]
- Changed: [list changes]
- Fixed: [list fixes]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 4: Create Git Tag

```bash
# Create annotated tag
git tag -a v1.1.0 -m "Version 1.1.0

[Brief description of release]

Major changes:
- Feature 1
- Feature 2
- Bug fix 3"

# Verify tag
git tag
git show v1.1.0
```

### Step 5: Update PROGRESS.md (Optional)

Update the status section at the top:

```markdown
**Date**: 2025-XX-XX
**Status**: Version 1.1.0 Released ✅
**Version**: 1.1.0
```

## Version History

Track all versions in CHANGELOG.md:

```markdown
## [Unreleased]
- Work in progress

## [1.1.0] - 2025-XX-XX
- Minor update

## [1.0.1] - 2025-XX-XX
- Patch update

## [1.0.0] - 2025-10-22
- Initial release
```

## Pre-release Versions

For development versions:

```
1.1.0-alpha.1  # Alpha release
1.1.0-beta.2   # Beta release
1.1.0-rc.1     # Release candidate
```

Update VERSION file:
```
1.1.0-beta.1
```

Tag:
```bash
git tag -a v1.1.0-beta.1 -m "Beta release 1 for version 1.1.0"
```

## Quick Reference Table

| Change Type | Example | Version Change |
|-------------|---------|----------------|
| Breaking API change | Remove step type | 1.0.0 → 2.0.0 |
| New feature | Add browser step | 1.0.0 → 1.1.0 |
| Bug fix | Fix parameter resolution | 1.0.0 → 1.0.1 |
| Documentation | Update guides | No version change (or 1.0.0 → 1.0.1) |
| Dependency update | Update FastAPI | 1.0.0 → 1.0.1 |

## Checklist for Version Release

- [ ] Update VERSION file
- [ ] Update pyproject.toml
- [ ] Update __init__.py
- [ ] Update CHANGELOG.md
- [ ] Run tests: `pytest tests/ -v`
- [ ] Commit changes
- [ ] Create git tag
- [ ] Update PROGRESS.md (optional)
- [ ] Test installation: `pip install -e .`
- [ ] Verify version: `ignition-toolkit --version`

## Example Workflow

### Bug Fix (Patch)

```bash
# Make fix
# Test fix

# Update version: 1.0.0 → 1.0.1
echo "1.0.1" > VERSION
# Edit pyproject.toml and __init__.py
# Update CHANGELOG.md

# Commit
git add VERSION pyproject.toml ignition_toolkit/__init__.py CHANGELOG.md
git commit -m "Fix credential vault bug - v1.0.1"

# Tag
git tag -a v1.0.1 -m "Patch: Fix credential vault bug"
```

### New Feature (Minor)

```bash
# Implement feature
# Add tests
# Update documentation

# Update version: 1.0.0 → 1.1.0
echo "1.1.0" > VERSION
# Edit pyproject.toml and __init__.py
# Update CHANGELOG.md

# Commit
git add .
git commit -m "Add new Gateway tag operations - v1.1.0"

# Tag
git tag -a v1.1.0 -m "Feature: Gateway tag operations"
```

### Breaking Change (Major)

```bash
# Implement breaking change
# Update all tests
# Update documentation
# Write migration guide

# Update version: 1.0.0 → 2.0.0
echo "2.0.0" > VERSION
# Edit pyproject.toml and __init__.py
# Update CHANGELOG.md with migration notes

# Commit
git add .
git commit -m "BREAKING: New playbook syntax - v2.0.0"

# Tag
git tag -a v2.0.0 -m "BREAKING CHANGES: See CHANGELOG for migration guide"
```

## Version Numbering Best Practices

1. **Start at 1.0.0** for first stable release ✅ (Done!)
2. **Use 0.x.x** for initial development (we skipped this)
3. **Never reuse** version numbers
4. **Always tag** releases in git
5. **Update CHANGELOG** with every release
6. **Test thoroughly** before incrementing MAJOR
7. **Document breaking changes** clearly

## Viewing Version Information

```bash
# Check current version
cat VERSION

# Check git tags
git tag -l

# See specific tag
git show v1.0.0

# Check Python version
python -c "import ignition_toolkit; print(ignition_toolkit.__version__)"

# CLI version
ignition-toolkit --version
```

---

**Current Version**: 1.0.0
**Next Version**: TBD (based on changes)
**Maintainer**: Nigel G
