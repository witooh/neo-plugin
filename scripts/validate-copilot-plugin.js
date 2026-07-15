#!/usr/bin/env node
/**
 * Validate the GitHub Copilot plugin adapter, marketplace entry, and hook.
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');

function fail(message) {
  throw new Error(message);
}

function assert(condition, message) {
  if (!condition) fail(message);
}

function readJson(relativePath) {
  const absolutePath = path.join(ROOT, relativePath);
  assert(fs.existsSync(absolutePath), `missing ${relativePath}`);

  try {
    return JSON.parse(fs.readFileSync(absolutePath, 'utf8'));
  } catch (error) {
    fail(`${relativePath} is not valid JSON: ${error.message}`);
  }
}

function normalizeComponentPath(componentPath) {
  return componentPath.replace(/^\.\//, '').replace(/\/$/, '');
}

function frontmatterValue(content, key) {
  const frontmatter = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!frontmatter) return undefined;

  const value = frontmatter[1].match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
  return value?.[1].trim().replace(/^['"]|['"]$/g, '');
}

function validateHookCommand(command, shell, args) {
  const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'neo-copilot-hook-'));
  const withoutIndex = path.join(temporaryRoot, 'without-index');
  const withIndex = path.join(temporaryRoot, 'with-index');
  fs.mkdirSync(withoutIndex);
  fs.mkdirSync(path.join(withIndex, '.kiro', 'steering'), { recursive: true });
  fs.writeFileSync(
    path.join(withIndex, '.kiro', 'steering', 'INDEX.md'),
    'STEERING_INDEX_SENTINEL\n',
  );

  function runHook(cwd) {
    const output = execFileSync(shell, [...args, command], {
      cwd: ROOT,
      encoding: 'utf8',
      input: JSON.stringify({ cwd }),
    });
    return JSON.parse(output);
  }

  let payload;
  let payloadWithIndex;
  try {
    payload = runHook(withoutIndex);
    payloadWithIndex = runHook(withIndex);
  } finally {
    fs.rmSync(temporaryRoot, { recursive: true, force: true });
  }

  assert(
    typeof payload.additionalContext === 'string',
    `${shell} sessionStart hook must output additionalContext`,
  );
  assert(
    payload.additionalContext.includes('using-neo'),
    `${shell} sessionStart hook must route through using-neo`,
  );
  assert(
    !payload.additionalContext.includes('STEERING_INDEX_SENTINEL'),
    `${shell} sessionStart hook must ignore absent steering INDEX.md`,
  );
  assert(
    !payload.additionalContext.includes('Read and follow .kiro/steering/INDEX.md'),
    `${shell} sessionStart hook must not mention absent steering INDEX.md`,
  );
  assert(
    payloadWithIndex.additionalContext.includes(
      'Read and follow .kiro/steering/INDEX.md',
    ),
    `${shell} sessionStart hook must instruct the session to read steering INDEX.md`,
  );
  assert(
    payloadWithIndex.additionalContext.includes('STEERING_INDEX_SENTINEL'),
    `${shell} sessionStart hook must include steering INDEX.md content`,
  );
}

function main() {
  const manifest = readJson('.plugin/plugin.json');
  const claudeManifest = readJson('.claude-plugin/plugin.json');

  assert(manifest.name === 'neo', 'Copilot plugin name must be neo');
  assert(
    manifest.version === claudeManifest.version,
    'Copilot and Claude plugin versions must stay in sync',
  );
  assert(
    normalizeComponentPath(manifest.skills) === 'skills',
    'Copilot plugin must reuse the canonical skills directory',
  );
  assert(
    normalizeComponentPath(manifest.hooks) === '.plugin/hooks.json',
    'Copilot plugin must select its Copilot-specific hooks file',
  );

  const expectedAgents = fs
    .readdirSync(path.join(ROOT, 'agents'))
    .filter((file) => file.endsWith('.md'))
    .sort()
    .map((file) => `agents/${file}`);
  const declaredAgents = (manifest.agents || [])
    .map(normalizeComponentPath)
    .sort();

  assert(
    JSON.stringify(declaredAgents) === JSON.stringify(expectedAgents),
    'Copilot plugin must declare every canonical agent',
  );

  for (const agentPath of declaredAgents) {
    const absoluteAgentPath = path.join(ROOT, agentPath);
    assert(fs.existsSync(absoluteAgentPath), `missing ${agentPath}`);

    const content = fs.readFileSync(absoluteAgentPath, 'utf8');
    const agentName = path.basename(agentPath, '.md');
    assert(
      frontmatterValue(content, 'name') === agentName,
      `${agentPath} must declare name: ${agentName}`,
    );
    assert(
      frontmatterValue(content, 'description'),
      `${agentPath} must declare a description for Copilot inference`,
    );
  }

  const hooks = readJson('.plugin/hooks.json');
  assert(hooks.version === 1, 'Copilot hooks schema version must be 1');

  const sessionStart = hooks.hooks?.sessionStart;
  assert(
    Array.isArray(sessionStart) && sessionStart.length === 1,
    'Copilot hooks must define one sessionStart hook',
  );

  const hook = sessionStart[0];
  assert(hook.type === 'command', 'sessionStart hook must be a command hook');
  assert(typeof hook.bash === 'string', 'sessionStart hook must support bash');
  assert(
    typeof hook.powershell === 'string',
    'sessionStart hook must support PowerShell',
  );
  validateHookCommand(hook.bash, 'bash', ['-c']);

  const pwsh = spawnSync('pwsh', ['-NoProfile', '-Command', '$PSVersionTable.PSVersion'], {
    stdio: 'ignore',
  });
  if (!pwsh.error && pwsh.status === 0) {
    validateHookCommand(hook.powershell, 'pwsh', ['-NoProfile', '-Command']);
  }

  const marketplace = readJson('.github/plugin/marketplace.json');
  assert(marketplace.name === 'neo', 'Copilot marketplace name must be neo');
  assert(
    marketplace.metadata?.version === manifest.version,
    'marketplace metadata version must match manifest',
  );
  assert(
    Array.isArray(marketplace.plugins) && marketplace.plugins.length === 1,
    'Copilot marketplace must publish exactly one plugin',
  );

  const entry = marketplace.plugins[0];
  assert(entry.name === manifest.name, 'marketplace plugin name must match manifest');
  assert(
    entry.version === manifest.version,
    'marketplace plugin version must match manifest',
  );
  assert(entry.source === '.', 'marketplace plugin source must be the repo root');

  console.log(
    `Copilot plugin OK (${declaredAgents.length} agents, shared skills, sessionStart hook)`,
  );
}

try {
  main();
} catch (error) {
  console.error(`Copilot plugin validation failed: ${error.message}`);
  process.exit(1);
}
