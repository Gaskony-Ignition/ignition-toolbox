#!/usr/bin/env node
/**
 * Python Bundling Script for Ignition Toolbox
 *
 * This script helps bundle a Python distribution with the Electron app
 * for standalone distribution without requiring Python to be installed.
 *
 * Usage:
 *   node scripts/bundle-python.js
 *
 * Options:
 *   --python-version <version>  Python version to bundle (default: 3.11.9)
 *   --output <path>             Output directory (default: resources/python)
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');

const PYTHON_VERSION = process.env.PYTHON_VERSION || '3.11.9';
const OUTPUT_DIR = path.join(__dirname, '..', 'resources', 'python');

// Python embed download URL for Windows
const PYTHON_EMBED_URL = `https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip`;

async function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    console.log(`Downloading ${url}...`);
    const file = fs.createWriteStream(dest);
    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        // Follow redirect
        https.get(response.headers.location, (redirectResponse) => {
          redirectResponse.pipe(file);
          file.on('finish', () => {
            file.close();
            resolve();
          });
        }).on('error', reject);
      } else {
        response.pipe(file);
        file.on('finish', () => {
          file.close();
          resolve();
        });
      }
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

async function extractZip(zipPath, destDir) {
  console.log(`Extracting ${zipPath} to ${destDir}...`);

  // Use PowerShell on Windows to extract
  if (process.platform === 'win32') {
    execSync(`powershell -command "Expand-Archive -Path '${zipPath}' -DestinationPath '${destDir}' -Force"`, { stdio: 'inherit' });
  } else {
    execSync(`unzip -o "${zipPath}" -d "${destDir}"`, { stdio: 'inherit' });
  }
}

async function installPipAndDependencies() {
  const pythonExe = path.join(OUTPUT_DIR, 'python.exe');
  const pipPath = path.join(OUTPUT_DIR, 'get-pip.py');

  // Download get-pip.py
  console.log('Downloading pip...');
  await downloadFile('https://bootstrap.pypa.io/get-pip.py', pipPath);

  // Enable site-packages by modifying python311._pth
  const pthFile = fs.readdirSync(OUTPUT_DIR).find(f => f.endsWith('._pth'));
  if (pthFile) {
    const pthPath = path.join(OUTPUT_DIR, pthFile);
    let content = fs.readFileSync(pthPath, 'utf8');
    // Uncomment import site
    content = content.replace('#import site', 'import site');
    // Add Lib/site-packages
    content += '\nLib/site-packages\n';
    fs.writeFileSync(pthPath, content);
    console.log(`Modified ${pthFile} to enable site-packages`);
  }

  // Install pip
  console.log('Installing pip...');
  execSync(`"${pythonExe}" "${pipPath}"`, { stdio: 'inherit', cwd: OUTPUT_DIR });

  // Install backend requirements
  const requirementsPath = path.join(__dirname, '..', 'backend', 'requirements.txt');
  if (fs.existsSync(requirementsPath)) {
    console.log('Installing backend requirements...');
    const pipExe = path.join(OUTPUT_DIR, 'Scripts', 'pip.exe');
    execSync(`"${pipExe}" install -r "${requirementsPath}" --no-warn-script-location`, { stdio: 'inherit' });
  }

  // Clean up
  fs.unlinkSync(pipPath);
}

async function main() {
  console.log(`Bundling Python ${PYTHON_VERSION} for Windows...`);

  // Create output directory
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  // Download Python embeddable
  const zipPath = path.join(OUTPUT_DIR, 'python-embed.zip');
  await downloadFile(PYTHON_EMBED_URL, zipPath);

  // Extract
  await extractZip(zipPath, OUTPUT_DIR);

  // Clean up zip
  fs.unlinkSync(zipPath);

  // Install pip and dependencies
  await installPipAndDependencies();

  console.log('\n✅ Python bundled successfully!');
  console.log(`   Location: ${OUTPUT_DIR}`);
  console.log('\nNote: Run "npm run dist:win" to build the distributable.');
}

// Check if running on Windows
if (process.platform !== 'win32') {
  console.log('⚠️  This script is designed for Windows.');
  console.log('   For other platforms, Python should be installed via system package manager.');
  process.exit(0);
}

main().catch((err) => {
  console.error('Error bundling Python:', err);
  process.exit(1);
});
