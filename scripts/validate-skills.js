#!/usr/bin/env node
/**
 * Lean validator for neo skills.
 *   1. Every skills/<dir>/SKILL.md has YAML frontmatter with name (matching the
 *      directory) and a non-empty description ≤ 1024 characters.
 *   2. No file in skills/, hooks/, extensions/, AGENTS.md, or README.md
 *      references a removed (dead) skill name.
 */
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const skillsDir = path.join(root, "skills");
const errors = [];

const DEAD_SKILLS = [
	"api-and-interface-design",
	"browser-testing-with-devtools",
	"ci-cd-and-automation",
	"code-review-and-quality",
	"code-simplification",
	"context-engineering",
	"debugging-and-error-recovery",
	"deprecation-and-migration",
	"documentation-and-adrs",
	"doubt-driven-development",
	"frontend-ui-engineering",
	"git-workflow-and-versioning",
	"idea-refine",
	"incremental-implementation",
	"interview-me",
	"observability-and-instrumentation",
	"performance-optimization",
	"planning-and-task-breakdown",
	"security-and-hardening",
	"shipping-and-launch",
	"source-driven-development",
	"spec-driven-development",
	"test-driven-development",
	"sync-upstream",
];

function parseFrontmatter(text) {
	const match = text.match(/^---\n([\s\S]*?)\n---/);
	if (!match) return null;
	const out = {};
	const lines = match[1].split("\n");
	for (let i = 0; i < lines.length; i++) {
		const keyMatch = lines[i].match(/^([a-zA-Z_-]+):\s*(.*)$/);
		if (!keyMatch) continue;
		const [, key, inline] = keyMatch;
		const parts = [];
		if (inline && !/^[>|][+-]?$/.test(inline)) parts.push(inline.trim());
		while (
			i + 1 < lines.length &&
			(/^\s+\S/.test(lines[i + 1]) || lines[i + 1] === "")
		) {
			i++;
			if (lines[i].trim()) parts.push(lines[i].trim());
		}
		out[key] = parts
			.join(" ")
			.replace(/^["']|["']$/g, "")
			.trim();
	}
	return out;
}

/**
 * The parser above is forgiving; a real YAML loader is not. A plain (unquoted,
 * non-block) value containing ": " reads as a nested mapping and makes the
 * whole skill unloadable — which this validator used to report as PASSED.
 */
function unloadableFrontmatter(text) {
	const match = text.match(/^---\n([\s\S]*?)\n---/);
	if (!match) return null;
	for (const line of match[1].split("\n")) {
		const keyMatch = line.match(/^([a-zA-Z_-]+): +(\S.*)$/);
		if (!keyMatch) continue;
		const [, key, value] = keyMatch;
		if (/^[>|]|^["']/.test(value)) continue;
		if (/: /.test(value))
			return `${key}: plain value contains ": " — YAML reads it as a nested mapping (quote it or use ">-")`;
	}
	return null;
}

for (const dir of fs.readdirSync(skillsDir)) {
	const skillPath = path.join(skillsDir, dir, "SKILL.md");
	if (!fs.existsSync(skillPath)) {
		errors.push(`${dir}: missing SKILL.md`);
		continue;
	}
	const raw = fs.readFileSync(skillPath, "utf8");
	const unloadable = unloadableFrontmatter(raw);
	if (unloadable) errors.push(`${dir}: ${unloadable}`);
	const fm = parseFrontmatter(raw);
	if (!fm) {
		errors.push(`${dir}: missing YAML frontmatter`);
		continue;
	}
	if (fm.name !== dir)
		errors.push(
			`${dir}: frontmatter name "${fm.name}" does not match directory`,
		);
	if (!fm.description) errors.push(`${dir}: missing description`);
	else if (fm.description.length > 1024)
		errors.push(
			`${dir}: description ${fm.description.length} chars (max 1024)`,
		);
}

function scanFile(filePath) {
	const rel = path.relative(root, filePath);
	const lines = fs.readFileSync(filePath, "utf8").split("\n");
	lines.forEach((line, i) => {
		for (const dead of DEAD_SKILLS) {
			if (new RegExp(`(^|[^a-z0-9-])${dead}([^a-z0-9-]|$)`).test(line)) {
				errors.push(`${rel}:${i + 1}: references removed skill "${dead}"`);
			}
		}
	});
}

function walk(dir) {
	for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
		const full = path.join(dir, entry.name);
		if (entry.isSymbolicLink()) continue;
		if (entry.isDirectory()) walk(full);
		else if (/\.(md|sh|js|json|ya?ml|toml)$/.test(entry.name)) scanFile(full);
	}
}

walk(skillsDir);
walk(path.join(root, "hooks"));
if (fs.existsSync(path.join(root, "extensions")))
	walk(path.join(root, "extensions"));
for (const f of ["AGENTS.md", "README.md"]) {
	const p = path.join(root, f);
	if (fs.existsSync(p)) scanFile(p);
}

if (errors.length) {
	console.error(`FAILED — ${errors.length} error(s):`);
	for (const e of errors) console.error(`  ${e}`);
	process.exit(1);
}
console.log(
	`PASSED — ${fs.readdirSync(skillsDir).length} skills validated, no dead references.`,
);
