#!/usr/bin/env node
/** Validate Codex plugin identity, marketplace discovery, and shared skills. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

function readJson(rel) {
	const full = path.join(root, rel);
	assert.equal(fs.existsSync(full), true, `${rel} must exist`);
	try {
		return JSON.parse(fs.readFileSync(full, "utf8"));
	} catch (error) {
		const reason = error instanceof Error ? error.message : String(error);
		assert.fail(`${rel} must be valid JSON: ${reason}`);
	}
}

const claudePlugin = readJson(".claude-plugin/plugin.json");
const rootPlugin = readJson("plugin.json");
const codexPlugin = readJson(".codex-plugin/plugin.json");
const marketplace = readJson(".agents/plugins/marketplace.json");

for (const field of ["name", "version", "description", "author", "homepage", "repository", "license"]) {
	assert.deepEqual(codexPlugin[field], claudePlugin[field], `Codex ${field} must match the canonical plugin`);
	assert.deepEqual(rootPlugin[field], claudePlugin[field], `Root plugin ${field} must match the canonical plugin`);
}
assert.equal(rootPlugin.$schema, "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json");
assert.equal(rootPlugin.extensions?.["com.openai"], undefined, "Codex settings must come from .codex-plugin/plugin.json; an inline overlay would replace it");
assert.equal(codexPlugin.skills, "./skills/", "Codex must load the shared repo-root skills/");
assert.equal(codexPlugin.interface?.displayName, "neo");
assert.ok(codexPlugin.interface?.shortDescription?.length > 0, "Codex listing must have a short description");
for (const forbidden of ["$schema", "hooks", "agents", "commands", "mcpServers", "apps"]) {
	assert.equal(codexPlugin[forbidden], undefined, `Codex compatibility manifest must not declare ${forbidden}`);
}

assert.equal(marketplace.name, "neo");
assert.equal(marketplace.interface?.displayName, "neo");
assert.ok(Array.isArray(marketplace.plugins), "marketplace.plugins must be an array");
assert.equal(marketplace.plugins.length, 1, "Codex marketplace must list exactly one plugin");
assert.equal(marketplace.version, undefined, "Marketplace must not carry a version");
const listed = marketplace.plugins[0];
assert.equal(listed.name, "neo");
assert.deepEqual(listed.source, { source: "local", path: "./" }, "Marketplace source must be its repo root, including in a Git snapshot");
assert.deepEqual(listed.policy, { installation: "AVAILABLE", authentication: "ON_INSTALL" });
assert.equal(listed.category, "Developer Tools");
assert.equal(listed.version, undefined, "Marketplace entries must not carry a version");

const skillsDir = path.join(root, "skills");
const skillNames = fs.readdirSync(skillsDir, { withFileTypes: true })
	.filter((entry) => entry.isDirectory()).map((entry) => entry.name);
assert.ok(skillNames.includes("markitdown"));
assert.equal(skillNames.includes("ship"), false, "Maintainer ship skill must stay outside the installed skills/");
for (const name of skillNames) {
	assert.equal(fs.existsSync(path.join(skillsDir, name, "SKILL.md")), true, `skills/${name} must contain SKILL.md`);
}

console.log(`PASSED — Codex plugin neo@${codexPlugin.version} lists ${skillNames.length} skills from ./skills/`);
