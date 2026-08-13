#!/usr/bin/env node
/** Validate Grok Build native plugin + marketplace wiring. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

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
const grokPlugin = readJson(".grok-plugin/plugin.json");
const rootPlugin = readJson("plugin.json");
const marketplace = readJson(".grok-plugin/marketplace.json");

assert.equal(grokPlugin.name, "neo", ".grok-plugin/plugin.json name must be neo");
assert.equal(
	grokPlugin.version,
	claudePlugin.version,
	".grok-plugin/plugin.json version must match .claude-plugin/plugin.json",
);
assert.equal(
	rootPlugin.name,
	"neo",
	"root plugin.json name must be neo",
);
assert.equal(
	rootPlugin.version,
	claudePlugin.version,
	"root plugin.json version must match .claude-plugin/plugin.json",
);
assert.ok(
	typeof grokPlugin.description === "string" && grokPlugin.description.length > 0,
	".grok-plugin/plugin.json must have a description",
);
assert.equal(
	grokPlugin.skills,
	undefined,
	".grok-plugin/plugin.json must not override skills/ — Grok discovers ./skills by convention",
);
assert.equal(
	grokPlugin.hooks,
	undefined,
	".grok-plugin/plugin.json must not override hooks/ — keep the shared hooks/hooks.json",
);

assert.equal(marketplace.name, "neo", "marketplace name must be neo");
assert.ok(Array.isArray(marketplace.plugins), "marketplace.plugins must be an array");
assert.equal(marketplace.plugins.length, 1, "marketplace must list exactly one plugin");

const listed = marketplace.plugins[0];
assert.equal(listed.name, "neo", "marketplace plugin name must be neo");
assert.ok(!("version" in listed), "marketplace plugin entry must not carry a version field");

const source = listed.source;
assert.equal(typeof source, "object", "marketplace source must be an object");
assert.notEqual(
	source.path,
	".",
	"Grok rejects marketplace path '.': measured empty / current-directory component",
);
assert.notEqual(
	source.path,
	"./",
	"Grok rejects marketplace path './': measured empty / current-directory component",
);
assert.equal(source.source, "url", "marketplace source.source must be url");
assert.equal(
	source.url,
	"https://github.com/witooh/neo-plugin.git",
	"marketplace url must be this repo — Grok cannot list the marketplace root as a local plugin path",
);

const usingNeo = path.join(root, "skills", "using-neo", "SKILL.md");
assert.equal(fs.existsSync(usingNeo), true, "skills/using-neo/SKILL.md is the canonical router");

const hooks = readJson("hooks/hooks.json");
assert.ok(
	hooks.hooks && Array.isArray(hooks.hooks.SessionStart),
	"hooks/hooks.json must keep SessionStart for the Claude channel",
);

const setupDoc = path.join(root, "docs", "grok-setup.md");
assert.equal(fs.existsSync(setupDoc), true, "docs/grok-setup.md must exist");
const setup = fs.readFileSync(setupDoc, "utf8");
assert.ok(
	setup.includes("grok plugin marketplace add"),
	"docs/grok-setup.md must document marketplace add",
);
assert.ok(
	setup.includes("grok plugin install"),
	"docs/grok-setup.md must document plugin install",
);
assert.ok(
	setup.includes("additionalContext"),
	"docs/grok-setup.md must record the measured SessionStart injection gap",
);

const grok = spawnSync("grok", ["plugin", "validate", root], {
	encoding: "utf8",
});
if (grok.error && grok.error.code === "ENOENT") {
	process.stdout.write(
		"Grok marketplace + plugin manifest OK (grok CLI not on PATH; skipped grok plugin validate)\n",
	);
	process.exit(0);
}

assert.equal(
	grok.status,
	0,
	`grok plugin validate failed:\n${grok.stdout || ""}${grok.stderr || ""}`,
);
assert.ok(
	/Plugin manifest is valid/i.test(grok.stdout || ""),
	`grok plugin validate did not report a valid manifest:\n${grok.stdout || ""}`,
);

process.stdout.write("Grok marketplace + plugin manifest OK\n");
