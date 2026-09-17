#!/usr/bin/env node
/** Validate Pi package discovery (skills only; no session injection). */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

let packageManifest;
try {
	packageManifest = JSON.parse(
		fs.readFileSync(path.join(root, "package.json"), "utf8"),
	);
} catch (error) {
	const reason = error instanceof Error ? error.message : String(error);
	process.stderr.write(`Unable to read package.json: ${reason}\n`);
	process.exit(1);
}

assert.ok(
	Array.isArray(packageManifest.pi?.skills),
	"package.json must have pi.skills",
);
assert.ok(
	packageManifest.pi.skills.includes("./skills"),
	'package.json pi.skills must include "./skills"',
);

const piExtensions = packageManifest.pi?.extensions;
if (piExtensions != null) {
	const listed = Array.isArray(piExtensions) ? piExtensions : [piExtensions];
	assert.ok(
		!listed.some((entry) => String(entry).includes("using-neo")),
		"package.json must not list a using-neo Pi extension",
	);
}

const projectExtensions = path.join(root, ".pi", "extensions");
if (fs.existsSync(projectExtensions)) {
	assert.equal(
		fs.lstatSync(projectExtensions).isSymbolicLink(),
		true,
		".pi/extensions must be a symlink if present",
	);
}

const projectSkills = path.join(root, ".pi", "skills");
if (fs.existsSync(projectSkills)) {
	assert.equal(
		fs.lstatSync(projectSkills).isSymbolicLink(),
		true,
		".pi/skills must be a symlink",
	);
	assert.equal(
		fs.readlinkSync(projectSkills),
		"../skills",
		".pi/skills must point at ../skills",
	);
}

process.stdout.write("Pi package OK\n");
