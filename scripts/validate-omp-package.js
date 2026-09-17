#!/usr/bin/env node
/** Validate omp package discovery and Agent Plugins 1.0 manifest. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

const packageManifest = JSON.parse(
	fs.readFileSync(path.join(root, "package.json"), "utf8"),
);

assert.ok(
	packageManifest.omp != null && typeof packageManifest.omp === "object",
	"package.json must have an omp key",
);
const ompExtensions = packageManifest.omp.extensions;
if (ompExtensions != null) {
	const listed = Array.isArray(ompExtensions) ? ompExtensions : [ompExtensions];
	assert.ok(
		!listed.some((entry) => String(entry).includes("using-neo")),
		"package.json must not list a using-neo omp extension",
	);
}

const AGENT_PLUGIN_SCHEMA =
	"https://agent-plugins.org/schemas/1.0.0/plugin.schema.json";
const AGENT_PLUGIN_FIELDS = new Set([
	"$schema",
	"name",
	"version",
	"description",
	"author",
	"homepage",
	"repository",
	"license",
	"keywords",
	"extensions",
]);
const agentPluginManifest = JSON.parse(
	fs.readFileSync(path.join(root, "plugin.json"), "utf8"),
);
assert.equal(
	agentPluginManifest.$schema,
	AGENT_PLUGIN_SCHEMA,
	"root plugin.json must target Agent Plugins 1.0.0",
);
assert.equal(
	agentPluginManifest.name,
	"neo",
	"root plugin.json name must be neo",
);
assert.equal(
	agentPluginManifest.version,
	packageManifest.version,
	"root plugin.json version must match package.json",
);
for (const key of Object.keys(agentPluginManifest)) {
	assert.ok(
		AGENT_PLUGIN_FIELDS.has(key),
		`root plugin.json has unknown Agent Plugins field "${key}"`,
	);
}
assert.ok(
	fs.existsSync(path.join(root, ".omp-plugin", "marketplace.json")),
	".omp-plugin/marketplace.json must ship as the preferred omp catalog",
);
assert.ok(
	packageManifest.keywords?.includes("omp-package"),
	"package.json keywords must include omp-package",
);

process.stdout.write("omp package OK\n");
