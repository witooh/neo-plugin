#!/usr/bin/env node
/** Validate using-neo as the only lifecycle entry point. */

'use strict';

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const removedSkills = [
  'neo',
  'neo-ingest',
  'neo-spec',
  'neo-plan',
  'neo-build',
  'neo-test',
  'neo-review',
  'neo-code-simplify',
  'neo-commit',
  'neo-ship',
  'neo-webperf',
];

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function assertIncludes(content, expected, subject) {
  if (!content.includes(expected)) {
    throw new Error(`${subject} must include ${JSON.stringify(expected)}`);
  }
}

function main() {
  const router = read('skills/using-neo/SKILL.md');

  if (router.split(/\r?\n/).length > 500) {
    throw new Error('skills/using-neo/SKILL.md must stay under 500 lines');
  }

  for (const heading of [
    '## Single Entry Point',
    '## Adaptive Routing',
    '## Modes and Lifecycle Control',
  ]) {
    assertIncludes(router, heading, 'skills/using-neo/SKILL.md');
  }

  for (const reference of [
    'references/ingest-define-plan.md',
    'references/build-verify.md',
    'references/review-ship.md',
  ]) {
    assertIncludes(router, reference, 'skills/using-neo/SKILL.md');
    if (!fs.existsSync(path.join(root, 'skills/using-neo', reference))) {
      throw new Error(`missing skills/using-neo/${reference}`);
    }
  }

  const phaseContracts = {
    'skills/using-neo/references/ingest-define-plan.md': [
      '`markitdown`',
      '`AC-001`',
      '`docs/api/`',
      'vertically',
    ],
    'skills/using-neo/references/build-verify.md': [
      'RED -> GREEN',
      '`git status --porcelain`',
      '`debugging-and-error-recovery`',
      '`browser-testing-with-devtools`',
      '`e2e-playwright`',
    ],
    'skills/using-neo/references/review-ship.md': [
      'Conventions & Style',
      '`code-reviewer`',
      'AC -> evidence',
      '`e2e-playwright`',
      '`unit-only`',
      'project-wide unit line coverage',
      '80%',
      '`security-auditor`',
      '`test-engineer`',
      'rollback plan',
      '`api-spec` Update-from-code',
    ],
  };

  for (const [relativePath, markers] of Object.entries(phaseContracts)) {
    const contract = read(relativePath);
    for (const marker of markers) {
      assertIncludes(contract, marker, relativePath);
    }
  }

  for (const gate of ['commit', 'ship', 'blocker', 'high-risk']) {
    assertIncludes(router, gate, 'skills/using-neo/SKILL.md');
  }

  const decisionStopContracts = {
    'skills/using-neo/SKILL.md': [
      '### Decision stops in auto mode',
      'material decision',
      'Ask for explicit approval',
      'routine bounded fixes',
    ],
    'skills/using-neo/references/build-verify.md': [
      '### Decision stops',
      'material decision',
      'Resume only after the user decides',
    ],
    'AGENTS.md': ['decision stop'],
    'docs/command-workflow.md': ['decision stop'],
    'README.md': ['decision stop'],
  };

  for (const [relativePath, markers] of Object.entries(decisionStopContracts)) {
    const content = read(relativePath);
    for (const marker of markers) {
      assertIncludes(content, marker, relativePath);
    }
  }

  for (const skill of removedSkills) {
    const relativePath = `skills/${skill}`;
    if (fs.existsSync(path.join(root, relativePath))) {
      throw new Error(`${relativePath} must be removed`);
    }
  }

  const legacyPhase = /\bneo-(?:ingest|spec|plan|build|test|review|code-simplify|commit|ship|webperf)\b|neo-\*|neo-<phase>/;
  for (const relativePath of [
    'AGENTS.md',
    'README.md',
    'docs/agents.md',
    'docs/antigravity-setup.md',
    'docs/comparison.md',
    'docs/copilot-setup.md',
    'docs/cursor-setup.md',
    'docs/gemini-cli-setup.md',
    'docs/getting-started.md',
    'docs/opencode-setup.md',
    'docs/pi-setup.md',
    'docs/windsurf-setup.md',
    'docs/command-workflow.md',
    'skills/using-neo/SKILL.md',
  ]) {
    if (legacyPhase.test(read(relativePath))) {
      throw new Error(`${relativePath} still references a removed phase entry`);
    }
  }

  const legacyDriver = /`neo`|`\/neo`/;
  for (const relativePath of [
    'skills/init-project/SKILL.md',
    'skills/init-project/references/init-project-guide.md',
    'skills/init-project/assets/template/README.md',
    'skills/migrate-project/SKILL.md',
    'skills/migrate-project/references/migration-tracking.md',
  ]) {
    if (legacyDriver.test(read(relativePath))) {
      throw new Error(`${relativePath} still references the removed neo driver`);
    }
  }

  assertIncludes(read('README.md'), '## Single Entry Point', 'README.md');

  console.log(
    `using-neo routing OK (${removedSkills.length} legacy skills absent)`,
  );
}

try {
  main();
} catch (error) {
  console.error(`using-neo validation failed: ${error.message}`);
  process.exit(1);
}
