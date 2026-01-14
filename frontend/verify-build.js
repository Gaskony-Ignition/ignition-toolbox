#!/usr/bin/env node
/**
 * Verify that index.html references match actual built files
 * This prevents 404 errors from mismatched content hashes
 */

import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';

const distDir = 'dist';
const assetsDir = join(distDir, 'assets');

// Read index.html
const indexHtml = readFileSync(join(distDir, 'index.html'), 'utf-8');

// Get all JS and CSS files in assets
const assetFiles = readdirSync(assetsDir);
const jsFiles = assetFiles.filter(f => f.endsWith('.js'));
const cssFiles = assetFiles.filter(f => f.endsWith('.css'));

console.log('\n=== Build Verification ===');
console.log('Built JS files:', jsFiles);
console.log('Built CSS files:', cssFiles);

// Extract references from index.html
const jsMatches = indexHtml.match(/\/assets\/index-[a-zA-Z0-9]+\.js/g) || [];
const cssMatches = indexHtml.match(/\/assets\/index-[a-zA-Z0-9]+\.css/g) || [];

console.log('\nReferenced in index.html:');
console.log('JS:', jsMatches.map(m => m.replace('/assets/', '')));
console.log('CSS:', cssMatches.map(m => m.replace('/assets/', '')));

// Verify all references exist
let errors = 0;

for (const jsRef of jsMatches) {
  const filename = jsRef.replace('/assets/', '');
  if (!jsFiles.includes(filename)) {
    console.error(`❌ ERROR: ${filename} referenced but not found!`);
    errors++;
  } else {
    console.log(`✓ ${filename} exists`);
  }
}

for (const cssRef of cssMatches) {
  const filename = cssRef.replace('/assets/', '');
  if (!cssFiles.includes(filename)) {
    console.error(`❌ ERROR: ${filename} referenced but not found!`);
    errors++;
  } else {
    console.log(`✓ ${filename} exists`);
  }
}

if (errors > 0) {
  console.error(`\n❌ Build verification FAILED with ${errors} error(s)`);
  process.exit(1);
} else {
  console.log('\n✅ Build verification PASSED - all references valid');
}
