#!/usr/bin/env node
/**
 * Sync version from root package.json to all version-bearing files.
 *
 * Files updated:
 *   - package.json
 *   - frontend/package.json
 *   - backend/ignition_toolkit/__init__.py
 *   - backend/pyproject.toml
 *
 * Usage:
 *   node scripts/sync-version.js          # sync current version
 *   node scripts/sync-version.js 3.0.2    # set specific version
 */

const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD

const rootPkgPath      = path.join(root, 'package.json');
const frontendPkgPath  = path.join(root, 'frontend', 'package.json');
const initPyPath       = path.join(root, 'backend', 'ignition_toolkit', '__init__.py');
const pyprojectPath    = path.join(root, 'backend', 'pyproject.toml');

// ── Determine target version ────────────────────────────────────────────────
// Read version from package.json via regex to avoid JSON roundtrip issues
const rootPkgContent = fs.readFileSync(rootPkgPath, 'utf8');
const versionMatch = rootPkgContent.match(/"version":\s*"([^"]+)"/);
const currentVersion = versionMatch ? versionMatch[1] : '0.0.0';
const newVersion = process.argv[2] || currentVersion;

// ── Helper ───────────────────────────────────────────────────────────────────
// Uses regex replacement to update files in place, preserving all existing
// content exactly as-is. This avoids JSON.parse/JSON.stringify roundtrip
// which can corrupt package.json by dropping fields.
function replaceInFile(filePath, replacements) {
  if (!fs.existsSync(filePath)) {
    console.warn(`  (skipped ${path.relative(root, filePath)} - file not found)`);
    return;
  }
  let content = fs.readFileSync(filePath, 'utf8');
  let changed = false;
  for (const [pattern, replacement] of replacements) {
    const next = content.replace(pattern, replacement);
    if (next !== content) { content = next; changed = true; }
  }
  if (changed) {
    fs.writeFileSync(filePath, content);
    console.log(`  ${path.relative(root, filePath)} -> ${newVersion}`);
  } else {
    console.log(`  ${path.relative(root, filePath)} already at ${newVersion}`);
  }
}

// ── package.json ─────────────────────────────────────────────────────────────
replaceInFile(rootPkgPath, [
  [/"version": "[^"]+"/, `"version": "${newVersion}"`],
]);

// ── frontend/package.json ─────────────────────────────────────────────────────
replaceInFile(frontendPkgPath, [
  [/"version": "[^"]+"/, `"version": "${newVersion}"`],
]);

// ── backend/__init__.py ───────────────────────────────────────────────────────
replaceInFile(initPyPath, [
  [/__version__ = "[^"]+".*$/m, `__version__ = "${newVersion}"  # Updated: ${today}`],
]);

// ── backend/pyproject.toml ────────────────────────────────────────────────────
replaceInFile(pyprojectPath, [
  [/^version = "[^"]+".*$/m, `version = "${newVersion}"  # Updated: ${today}`],
]);

console.log(`\nVersion synced to ${newVersion} (${today})`);
