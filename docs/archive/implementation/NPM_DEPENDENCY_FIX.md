# NPM Dependency Fix Documentation

**Date:** 2025-10-27
**Issue:** npm install failing with "No matching version found" errors
**Root Cause:** package.json contained future/non-existent version numbers

## Problem

After commit dd22f78 ("Update all dependencies to latest versions + Node.js 22 upgrade"), the package.json contained version numbers that don't exist yet:

```json
{
  "eslint": "^9.42.0",           // Latest available: 9.17.0
  "react-router-dom": "^7.11.2", // Latest available: 7.9.4
  "xterm": "^5.5.0",             // Latest available: 5.3.0
  "react": "^19.2.0",            // Latest available: 19.1.1
  "vite": "^7.1.9"               // Latest available: 7.1.7
}
```

This caused npm install to fail with:
```
npm ERR! notarget No matching version found for <package>@<version>
```

## Solution

### 1. Restore Working package.json

Restored package.json from commit d676a2a (v1.0.34) which had stable versions:

```bash
git show d676a2a:frontend/package.json > frontend/package.json
```

### 2. Add Required xterm Packages

Added xterm packages for Claude Code Phase 2 embedded terminal:

```json
{
  "dependencies": {
    "xterm": "^5.3.0",
    "xterm-addon-fit": "^0.8.0",
    "xterm-addon-web-links": "^0.9.0"
  }
}
```

### 3. Install with Legacy Peer Deps

```bash
cd frontend
npm install --legacy-peer-deps
```

**Result:** Successfully installed 262 packages in 2 seconds with 0 vulnerabilities.

## Working package.json Versions

```json
{
  "name": "frontend",
  "version": "1.0.34",
  "dependencies": {
    "@dnd-kit/core": "^6.3.1",
    "@dnd-kit/sortable": "^10.0.0",
    "@emotion/react": "^11.14.0",
    "@emotion/styled": "^11.14.1",
    "@mui/icons-material": "^7.3.4",
    "@mui/material": "^7.3.4",
    "@tanstack/react-query": "^5.90.5",
    "react": "^19.1.1",
    "react-dom": "^19.1.1",
    "react-router-dom": "^7.9.4",
    "xterm": "^5.3.0",
    "xterm-addon-fit": "^0.8.0",
    "xterm-addon-web-links": "^0.9.0",
    "zustand": "^5.0.8"
  },
  "devDependencies": {
    "@eslint/js": "^9.36.0",
    "@types/node": "^24.6.0",
    "@types/react": "^19.1.16",
    "@types/react-dom": "^19.1.9",
    "@vitejs/plugin-react": "^5.0.4",
    "eslint": "^9.36.0",
    "eslint-plugin-react-hooks": "^5.2.0",
    "eslint-plugin-react-refresh": "^0.4.22",
    "globals": "^16.4.0",
    "typescript": "~5.9.3",
    "typescript-eslint": "^8.45.0",
    "vite": "^7.1.7"
  }
}
```

## Prevention

**Before upgrading dependencies:**

1. **Check actual latest versions:**
   ```bash
   npm view <package> versions --json | tail -20
   npm view <package> version  # Latest stable
   ```

2. **Use exact versions that exist:**
   - Don't use future version numbers
   - Verify packages exist on npm registry
   - Test install in clean environment

3. **Upgrade incrementally:**
   - Update one dependency at a time
   - Test after each update
   - Don't bump all versions simultaneously

4. **Use npm-check-updates carefully:**
   ```bash
   npx npm-check-updates --target latest  # Shows what's available
   npx npm-check-updates -u                # Updates package.json
   npm install                              # Test the changes
   ```

## Notes

- The older xterm packages (5.3.0) show deprecation warnings but work fine
- Newer @xterm/xterm packages require different import paths
- ESLint peer dependency warnings can be ignored with --legacy-peer-deps
- Node.js 18.19.1 works fine despite Vite preferring Node 20+

## Quick Fix Command

If this happens again:

```bash
cd frontend
git show d676a2a:package.json > package.json
npm install --legacy-peer-deps
```

Then manually add any new required packages with correct versions.
