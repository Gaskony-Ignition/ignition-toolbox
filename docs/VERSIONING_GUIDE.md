# Versioning Guide

## Single Version Scheme

Ignition Toolbox uses a **single version number** tracked in two places:

| File | Example |
|------|---------|
| `package.json` | `"version": "1.5.4"` |
| `frontend/package.json` | `"version": "1.5.4"` |

These two files must always match. This version is what users see in the app, in GitHub Releases, and in auto-update notifications.

### Backend Version

The backend `pyproject.toml` has its own `version` field, but this is **internal only** and not user-facing. It does not need to match the Electron app version. Do not reference the backend version in user-facing documentation.

## Semantic Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH    (e.g. 1.5.0)
```

| Increment | When |
|-----------|------|
| **MAJOR** | Breaking changes to playbook syntax, API, or database schema |
| **MINOR** | New features (step types, pages, endpoints) that are backwards compatible |
| **PATCH** | Bug fixes, performance improvements, documentation |

## Release Process

1. **Update version** in `package.json` and `frontend/package.json`
2. **Commit** the version bump
3. **Tag and push:**
   ```bash
   git tag v1.5.1
   git push origin v1.5.1
   ```
4. **GitHub Actions** (`build-windows.yml`) automatically:
   - Builds on a `windows-latest` runner
   - Packages with PyInstaller + electron-builder
   - Creates a GitHub Release with the installer
   - Existing users receive an auto-update notification

You can also trigger builds manually from the GitHub Actions UI (workflow_dispatch).

## Version Bump Checklist

- [ ] Update `package.json` version
- [ ] Update `frontend/package.json` version
- [ ] Commit changes
- [ ] Create git tag (`git tag v1.X.Y`)
- [ ] Push tag (`git push origin v1.X.Y`)
- [ ] Verify GitHub Actions build succeeds

---

**Current Version**: 1.5.4
**Last Updated**: 2026-02-06
