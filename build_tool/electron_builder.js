/**
 * electron_builder.js — Standalone Electron build script
 *
 * Usage:
 *   node electron_builder.js
 *   node electron_builder.js --portable
 *   node electron_builder.js --help
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs   = require('fs');
const os   = require('os');

const ROOT_DIR     = path.resolve(__dirname, '..');
const ELECTRON_DIR = __dirname;

function log(msg)  { console.log(`\x1b[36m[BUILD]\x1b[0m ${msg}`); }
function ok(msg)   { console.log(`\x1b[32m[OK   ]\x1b[0m ${msg}`); }
function warn(msg) { console.log(`\x1b[33m[WARN ]\x1b[0m ${msg}`); }
function err(msg)  { console.error(`\x1b[31m[ERR  ]\x1b[0m ${msg}`); }

function run(cmd, cwd = ELECTRON_DIR) {
  log(`> ${cmd}`);
  execSync(cmd, { cwd, stdio: 'inherit', shell: true });
}

function checkNode() {
  try {
    const v = execSync('node --version').toString().trim();
    log(`Node.js: ${v}`);
    return true;
  } catch {
    err('Node.js not found. Download from https://nodejs.org');
    return false;
  }
}

function checkNpm() {
  try {
    const v = execSync('npm --version').toString().trim();
    log(`npm: ${v}`);
    return true;
  } catch {
    err('npm not found.');
    return false;
  }
}

function checkServerExe() {
  const serverExe = path.join(ELECTRON_DIR, 'resources', 'server.exe');
  if (fs.existsSync(serverExe)) {
    const size = (fs.statSync(serverExe).size / 1024 / 1024).toFixed(1);
    ok(`server.exe found (${size} MB)`);
    return true;
  }
  warn('server.exe not found. Run the web exe build first:');
  warn('  python build_tool/builder_cli.py --target web');
  return false;
}

function installDeps() {
  const nodeModules = path.join(ELECTRON_DIR, 'node_modules');
  if (!fs.existsSync(nodeModules)) {
    log('Installing Node.js dependencies...');
    run('npm install');
  } else {
    log('node_modules already exists. Skipping npm install.');
  }
}

function buildElectron(args = []) {
  let cmd = 'npx electron-builder --win';
  if (args.includes('--portable')) {
    cmd += ' --win portable';
    log('Mode: Portable EXE');
  } else if (args.includes('--installer')) {
    cmd += ' --win nsis';
    log('Mode: NSIS Installer');
  } else {
    log('Mode: Both NSIS Installer + Portable');
  }

  run(cmd);
}

function printOutputs() {
  const distDir = path.join(ROOT_DIR, 'dist_electron');
  if (!fs.existsSync(distDir)) return;
  const files = fs.readdirSync(distDir)
    .filter(f => f.endsWith('.exe') || f.endsWith('.msi'))
    .map(f => {
      const fp   = path.join(distDir, f);
      const size = (fs.statSync(fp).size / 1024 / 1024).toFixed(1);
      return `  ${f} (${size} MB)`;
    });
  if (files.length) {
    ok('Output files:');
    files.forEach(f => console.log(`\x1b[32m${f}\x1b[0m`));
  }
}

function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help')) {
    console.log(`
EveryThingDownloader — Electron Builder Script

Usage:
  node electron_builder.js [options]

Options:
  --portable    Build Portable EXE only (no installation required)
  --installer   Build NSIS Installer only
  --help        Show this help message

Default: builds both Installer and Portable.
    `);
    return;
  }

  console.log('\n' + '═'.repeat(52));
  console.log('  EveryThingDownloader — Electron Build');
  console.log('═'.repeat(52) + '\n');

  if (!checkNode() || !checkNpm()) process.exit(1);

  log('Checking server.exe...');
  const hasServer = checkServerExe();
  if (!hasServer && !args.includes('--no-server-check')) {
    err('Stopping: server.exe is required to build. Add --no-server-check to skip.');
    process.exit(1);
  }

  installDeps();

  log('Starting electron-builder...');
  try {
    buildElectron(args);
    console.log('\n' + '═'.repeat(52));
    ok('Build completed!');
    printOutputs();
    console.log('═'.repeat(52) + '\n');
  } catch (e) {
    err('Build failed: ' + e.message);
    process.exit(1);
  }
}

main();
