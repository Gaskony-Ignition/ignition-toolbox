#!/usr/bin/env node
/**
 * Sync version from root package.json to all version-bearing files.
 *
 * Files updated:
 *   - package.json
 *   - frontend/package.json
 *   - backend/ignition_toolkit/__init__.py
 *   - backend/pyproject.toml
 *   - .claude/CLAUDE.md  (version number, example tags, Last Updated date, Status line)
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
const claudeMdPath     = path.join(root, '.claude', 'CLAUDE.md');

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

// ── .claude/CLAUDE.md ─────────────────────────────────────────────────────────
replaceInFile(claudeMdPath, [
  // "Current Version: X.Y.Z"
  [/\*\*Current Version:\*\* \S+/, `**Current Version:** ${newVersion}`],
  // Example tag lines like "git tag v3.0.1"
  [/git tag v\d+\.\d+\.\d+/g, `git tag v${newVersion}`],
  // Example push lines like "git push origin v3.0.1"
  [/git push origin v\d+\.\d+\.\d+/g, `git push origin v${newVersion}`],
  // Last Updated date
  [/\*\*Last Updated\*\*: \d{4}-\d{2}-\d{2}/, `**Last Updated**: ${today}`],
  // Status line "Production Ready (vX.Y.Z)"
  [/Production Ready \(v\d+\.\d+\.\d+\)/, `Production Ready (v${newVersion})`],
]);

console.log(`\nVersion synced to ${newVersion} (${today})`);
