# Frontend Build Guide

## The Problem

Vite generates content-hashed filenames (e.g., `index-BTf413Oi.js`) during build. Sometimes the server serves a cached version of `index.html` that references old file hashes, causing 404 errors.

## The Solution

A multi-layered permanent fix has been implemented:

### 1. Automatic Build Verification

Every build now automatically verifies that `index.html` references match the actual built files.

```bash
npm run build   # Builds AND verifies
```

The build will FAIL if there are mismatched references, preventing broken deployments.

### 2. Rebuild Command

Use this command to ensure a clean build:

```bash
npm run rebuild   # Clean dist + build + verify
```

This removes the `dist` directory before building, ensuring no stale files.

### 3. Project-Level Script

From the project root, use:

```bash
./rebuild-frontend.sh   # One-command rebuild from anywhere
```

## When to Use Each Command

- **Regular development**: `npm run build` (automatic verification)
- **After making changes**: `npm run rebuild` (clean build)
- **From project root**: `./rebuild-frontend.sh` (convenience script)
- **Just verify current build**: `npm run verify`

## What Gets Verified

The verification script checks:
- ✅ All JS files referenced in `index.html` exist in `dist/assets/`
- ✅ All CSS files referenced in `index.html` exist in `dist/assets/`
- ❌ Fails build if any references are missing

## Troubleshooting

### Build verification fails
```bash
cd frontend
npm run rebuild
```

### Server serves old version
The server reads files from disk on each request, so changes are immediate. If you see old content:
1. Verify the build: `npm run verify`
2. Check the actual files: `ls -la dist/assets/`
3. Check `dist/index.html` references

### 404 errors on assets
This should never happen with the new verification system. If it does:
```bash
cd frontend
rm -rf dist
npm run build
```

The build will fail if there are any mismatches.

## How It Works

1. **Build**: TypeScript compiles → Vite bundles → generates hashed filenames
2. **Verify**: Script reads `index.html` and checks all referenced files exist
3. **Fail Fast**: If any references are missing, build fails with clear error

This ensures broken builds never make it to production.
