#!/usr/bin/env node
/** Validate that AGENTS.md remains the sole repository-guidance source. */

'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const claudeAdapter = fs.readFileSync(path.join(root, 'CLAUDE.md'), 'utf8');
const canonicalGuidance = fs.readFileSync(path.join(root, 'AGENTS.md'), 'utf8');

if (claudeAdapter !== '@AGENTS.md\n') {
  console.error('CLAUDE.md must contain only the @AGENTS.md import.');
  process.exit(1);
}

if (!canonicalGuidance.startsWith('# AGENTS.md\n')) {
  console.error('AGENTS.md must remain a non-empty canonical guidance document.');
  process.exit(1);
}

console.log('Agent guidance SOT OK (AGENTS.md canonical, CLAUDE.md import-only)');
