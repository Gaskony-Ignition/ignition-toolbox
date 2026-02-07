#!/usr/bin/env node
/**
 * Sync version from root package.json to frontend/package.json.
 *
 * Usage:
 *   node scripts/sync-version.js          # sync current version
 *   node scripts/sync-version.js 1.6.0    # set specific version
 */

const fs = require('fs');
const path = require('path');

const rootPkgPath = path.join(__dirname, '..', 'package.json');
const frontendPkgPath = path.join(__dirname, '..', 'frontend', 'package.json');

const rootPkg = JSON.parse(fs.readFileSync(rootPkgPath, 'utf8'));

// Allow overriding version via CLI argument
const newVersion = process.argv[2] || rootPkg.version;

// Update root package.json if a new version was specified
if (process.argv[2] && rootPkg.version !== newVersion) {
  rootPkg.version = newVersion;
  fs.writeFileSync(rootPkgPath, JSON.stringify(rootPkg, null, 2) + '\n');
  console.log(`  package.json -> ${newVersion}`);
}

// Update frontend/package.json
const frontendPkg = JSON.parse(fs.readFileSync(frontendPkgPath, 'utf8'));
if (frontendPkg.version !== newVersion) {
  frontendPkg.version = newVersion;
  fs.writeFileSync(frontendPkgPath, JSON.stringify(frontendPkg, null, 2) + '\n');
  console.log(`  frontend/package.json -> ${newVersion}`);
} else {
  console.log(`  frontend/package.json already at ${newVersion}`);
}

console.log(`Version synced: ${newVersion}`);
