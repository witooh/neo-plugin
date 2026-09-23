#!/usr/bin/env node
/** Validate the Cursor plugin import: GitHub Add reads .cursor-plugin/marketplace.json. */

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

assert.equal(
	fs.existsSync(path.join(root, "cursor.sh")),
	false,
	"cursor.sh must stay deleted — Cursor installs this repo as a plugin",
);

const claudePlugin = readJson(".claude-plugin/plugin.json");
const cursorPlugin = readJson(".cursor-plugin/plugin.json");
const marketplace = readJson(".cursor-plugin/marketplace.json");

assert.equal(cursorPlugin.name, "neo", ".cursor-plugin/plugin.json name must be neo");
assert.equal(
	cursorPlugin.version,
	claudePlugin.version,
	".cursor-plugin/plugin.json version must match .claude-plugin/plugin.json",
);
assert.equal(
	cursorPlugin.skills,
	"./skills",
	".cursor-plugin/plugin.json must load repo-root skills/ and not a forked copy",
);
for (const forbidden of ["hooks", "agents", "commands", "rules", "mcpServers"]) {
	assert.equal(
		cursorPlugin[forbidden],
		undefined,
		`.cursor-plugin/plugin.json must not ship ${forbidden}`,
	);
}

assert.equal(marketplace.name, "neo", "Cursor marketplace name must be neo");
assert.equal(
	marketplace.metadata?.description,
	claudePlugin.description,
	"Cursor marketplace description must match the plugin description",
);
assert.ok(Array.isArray(marketplace.plugins), "marketplace.plugins must be an array");
assert.equal(marketplace.plugins.length, 1, "marketplace must list exactly one plugin");

const listed = marketplace.plugins[0];
assert.equal(listed.name, "neo", "marketplace plugin name must be neo");
assert.equal(
	listed.source,
	"./",
	"marketplace source must be the repo root so skills/ is discovered without a fork",
);
assert.ok(!("version" in listed), "marketplace plugin entry must not carry a version field");

const skillsDir = path.join(root, "skills");
const skillNames = fs
	.readdirSync(skillsDir, { withFileTypes: true })
	.filter((entry) => entry.isDirectory())
	.map((entry) => entry.name);
assert.ok(skillNames.includes("markitdown"), "skills/markitdown must exist for the plugin");
assert.equal(
	skillNames.includes("ship"),
	false,
	"maintainer skill ship must not be inside the Cursor plugin skills/",
);
for (const name of skillNames) {
	assert.equal(
		fs.existsSync(path.join(skillsDir, name, "SKILL.md")),
		true,
		`skills/${name} must contain SKILL.md`,
	);
}

console.log(
	`PASSED — Cursor plugin neo@${cursorPlugin.version} lists ${skillNames.length} skills from ./skills`,
);
