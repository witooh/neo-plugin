#!/usr/bin/env node
/**
 * Runtime skill test runner.
 *
 * Runs a case prompt through `pi` headless with only the neo plugin loaded,
 * against a throwaway copy of a fixture project, then asserts what the agent
 * actually did from the JSONL transcript.
 *
 *   node tests/runtime/run.mjs [--case <id>] [--repeat <n>] [--keep]
 */
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../..");
const grokExt =
	process.env.PI_GROK_EXT ??
	path.join(
		os.homedir(),
		".pi/agent/npm/node_modules/pi-grok-cli/src/index.ts",
	);

const args = process.argv.slice(2);
const flag = (name, fallback) => {
	const i = args.indexOf(`--${name}`);
	return i === -1 ? fallback : args[i + 1];
};
const only = flag("case");
const onlyGroup = flag("group");
const onlySkill = flag("skill");
const repeat = Number(flag("repeat", "1"));
const keep = args.includes("--keep");
const listOnly = args.includes("--list");

function runCase(caseDef, runIndex) {
	const workdir = fs.mkdtempSync(
		path.join(os.tmpdir(), `neo-eval-${caseDef.id}-`),
	);
	fs.cpSync(path.join(here, "fixtures", caseDef.fixture), workdir, {
		recursive: true,
	});
	const git = (...a) =>
		execFileSync("git", a, { cwd: workdir, encoding: "utf8" });
	git("init", "-q");
	git("add", "-A");
	git(
		"-c",
		"user.email=eval@neo",
		"-c",
		"user.name=eval",
		"commit",
		"-qm",
		"fixture",
	);
	if (caseDef.setup)
		execFileSync("bash", ["-c", caseDef.setup], { cwd: workdir });
	const baseSha = git("rev-parse", "HEAD").trim();

	// Recording stubs live outside the workdir so they never show up as changes.
	const stubDir = fs.mkdtempSync(path.join(os.tmpdir(), "neo-eval-bin-"));
	const callLog = path.join(stubDir, "calls.log");
	for (const name of caseDef.stubs ?? []) {
		const dest = path.join(stubDir, name);
		fs.copyFileSync(path.join(here, "stubs", name), dest);
		fs.chmodSync(dest, 0o755);
	}

	const started = Date.now();
	const res = spawnSync(
		"pi",
		[
			"-p",
			"--mode",
			"json",
			"--provider",
			"grok-cli",
			"--model",
			"grok-4.5",
			"--thinking",
			"high",
			"--no-session",
			"-ne",
			"-e",
			grokExt,
			"-e",
			path.join(repoRoot, "extensions/using-neo-session-start.js"),
			"-ns",
			"--skill",
			path.join(repoRoot, "skills"),
			caseDef.prompt,
		],
		{
			cwd: workdir,
			encoding: "utf8",
			maxBuffer: 256 * 1024 * 1024,
			env: {
				...process.env,
				PATH: `${stubDir}:${process.env.PATH}`,
				EVAL_CALL_LOG: callLog,
			},
		},
	);

	const events = res.stdout
		.split("\n")
		.filter(Boolean)
		.map((line) => {
			try {
				return JSON.parse(line);
			} catch {
				return null;
			}
		})
		.filter(Boolean);

	const trace = events
		.filter((e) => e.type === "tool_execution_start")
		.map((e) => ({
			tool: e.toolName,
			path: e.args?.path ?? "",
			command: e.args?.command ?? "",
		}));
	const cost = events
		.filter((e) => e.type === "turn_end")
		.reduce((sum, e) => sum + (e.message?.usage?.cost?.total ?? 0), 0);

	// Working-tree truth: the agent may write through bash (heredoc, python) which
	// never shows up as a write/edit tool call.
	// ...and it may commit its own work, which empties `git status`.
	const changed = [
		...new Set([
			...git("status", "--porcelain", "-uall")
				.split("\n")
				.filter(Boolean)
				.map((l) =>
					l
						.slice(3)
						.replace(/^.* -> /, "")
						.replace(/^"|"$/g, ""),
				),
			...git("diff", "--name-only", baseSha, "HEAD")
				.split("\n")
				.filter(Boolean),
		]),
	];

	const answer = events
		.filter((e) => e.type === "turn_end")
		.flatMap((e) => e.message?.content ?? [])
		.filter((c) => c.type === "text")
		.map((c) => c.text)
		.join("\n");

	const calls = fs.existsSync(callLog)
		? fs.readFileSync(callLog, "utf8").split("\n").filter(Boolean)
		: [];

	const results = assert(
		caseDef.expect,
		trace,
		workdir,
		changed,
		calls,
		answer,
	);
	for (const cmd of caseDef.expect.postCommand ?? []) {
		const out = spawnSync("bash", ["-c", cmd], {
			cwd: workdir,
			encoding: "utf8",
		});
		results.push({
			name: `post:${cmd.slice(0, 40)}`,
			ok: out.status === 0,
			detail:
				out.status === 0
					? "exit 0"
					: `exit ${out.status}: ${(out.stderr || out.stdout).trim().split("\n")[0]?.slice(0, 70)}`,
		});
	}
	const report = {
		case: caseDef.id,
		run: runIndex,
		workdir,
		durationSec: Math.round((Date.now() - started) / 1000),
		costUsd: Number(cost.toFixed(3)),
		toolCalls: trace.length,
		results,
		trace,
		stderr: res.stderr?.slice(-2000) ?? "",
	};

	const outDir = path.join(here, "reports", caseDef.id);
	fs.mkdirSync(outDir, { recursive: true });
	fs.writeFileSync(
		path.join(outDir, `run-${runIndex}.json`),
		JSON.stringify(report, null, 2),
	);
	fs.writeFileSync(path.join(outDir, `run-${runIndex}.jsonl`), res.stdout);
	if (!keep) fs.rmSync(workdir, { recursive: true, force: true });
	return report;
}

const isProdGo = (p) => p.endsWith(".go") && !p.endsWith("_test.go");

function assert(expect, trace, workdir, changed, calls, answer) {
	const out = [];
	const root = fs.realpathSync(workdir);
	const rel = (p) => path.relative(root, path.resolve(root, p));
	const edited = trace.filter((t) => t.tool === "edit" || t.tool === "write");
	const check = (name, ok, detail) => out.push({ name, ok, detail });

	if (expect.skillsLoaded) {
		for (const skill of expect.skillsLoaded) {
			const hit = trace.find(
				(t) =>
					t.tool === "read" && t.path.includes(`/skills/${skill}/SKILL.md`),
			);
			check(`skill:${skill}`, Boolean(hit), hit ? "loaded" : "never read");
		}
	}
	if (expect.redBeforeGreen) {
		const firstTest = edited.findIndex((t) => t.path.endsWith("_test.go"));
		const firstProd = edited.findIndex((t) => isProdGo(t.path));
		check(
			"redBeforeGreen",
			firstTest !== -1 && (firstProd === -1 || firstTest < firstProd),
			firstTest === -1
				? "no test file written"
				: `test@${firstTest} prod@${firstProd}`,
		);
	}
	if (expect.fixApplied) {
		const hit = edited.some((t) => isProdGo(t.path));
		check(
			"fixApplied",
			hit,
			hit ? "production file edited" : "no production edit",
		);
	}
	if (expect.filesWritten) {
		for (const pattern of expect.filesWritten) {
			const hit = changed.find((f) => new RegExp(pattern).test(f));
			check(`wrote:${pattern}`, Boolean(hit), hit ?? "never written");
		}
	}
	if (expect.filesNotWritten) {
		for (const pattern of expect.filesNotWritten) {
			const hit = changed.find((f) => new RegExp(pattern).test(f));
			check(`notWrote:${pattern}`, !hit, hit ? `wrote ${hit}` : "untouched");
		}
	}
	if (expect.writeOrder) {
		for (const [before, after] of expect.writeOrder) {
			const i = edited.findIndex((t) => new RegExp(before).test(rel(t.path)));
			const j = edited.findIndex((t) => new RegExp(after).test(rel(t.path)));
			check(
				`order:${before}<${after}`,
				i !== -1 && (j === -1 || i < j),
				`${before}@${i} ${after}@${j}`,
			);
		}
	}
	if (expect.ranCommand) {
		for (const pattern of expect.ranCommand) {
			const hit = trace.find(
				(t) => t.tool === "bash" && new RegExp(pattern).test(t.command),
			);
			check(
				`ran:${pattern}`,
				Boolean(hit),
				hit ? hit.command.slice(0, 60) : "never ran",
			);
		}
	}
	if (expect.outputContains) {
		for (const pattern of expect.outputContains) {
			const hit = answer.match(new RegExp(pattern, "i"));
			check(
				`says:${pattern}`,
				Boolean(hit),
				hit ? `"${hit[0].slice(0, 50)}"` : "not in the report",
			);
		}
	}
	if (expect.cliCalled) {
		for (const pattern of expect.cliCalled) {
			const hit = calls.find((c) => new RegExp(pattern).test(c));
			check(
				`cli:${pattern}`,
				Boolean(hit),
				hit?.slice(0, 70) ?? "never called",
			);
		}
	}
	if (expect.cliNotCalled) {
		for (const pattern of expect.cliNotCalled) {
			const hit = calls.find((c) => new RegExp(pattern).test(c));
			check(
				`noCli:${pattern}`,
				!hit,
				hit ? `called ${hit.slice(0, 60)}` : "not called",
			);
		}
	}
	if (expect.sandbox) {
		const escaped = edited.filter(
			(t) => !path.resolve(t.path).startsWith(root),
		);
		check(
			"sandbox",
			escaped.length === 0,
			escaped.length
				? `wrote outside: ${escaped[0].path}`
				: "all writes inside fixture",
		);
	}
	if (expect.noGitWrites) {
		const hit = trace.find(
			(t) =>
				t.tool === "bash" &&
				/\bgit\s+(commit|push|reset|rebase|merge|switch|checkout)\b|\bgit\s+branch\s+[^-\s]/.test(
					t.command,
				),
		);
		check(
			"noGitWrites",
			!hit,
			hit ? hit.command.slice(0, 60) : "no git side effects",
		);
	}
	return out;
}

const caseDir = path.join(here, "cases");
const allCases = fs
	.readdirSync(caseDir, { withFileTypes: true })
	.filter((d) => d.isDirectory())
	.flatMap((group) =>
		fs
			.readdirSync(path.join(caseDir, group.name))
			.filter((f) => f.endsWith(".json"))
			.map((f) => ({
				group: group.name,
				...JSON.parse(
					fs.readFileSync(path.join(caseDir, group.name, f), "utf8"),
				),
			})),
	);
const cases = allCases.filter(
	(c) =>
		(!only || c.id === only) &&
		(!onlyGroup || c.group === onlyGroup) &&
		(!onlySkill || (c.skills ?? []).includes(onlySkill)),
);

if (listOnly) {
	const covered = new Set(allCases.flatMap((c) => c.skills ?? []));
	const installed = fs.readdirSync(path.join(repoRoot, "skills"));
	for (const group of [...new Set(cases.map((c) => c.group))]) {
		console.log(`\n${group}/`);
		for (const c of cases.filter((x) => x.group === group))
			console.log(`  ${c.id.padEnd(22)} ${(c.skills ?? []).join(", ")}`);
	}
	console.log(
		`\ncovered ${covered.size}/${installed.length} skills — missing: ${installed.filter((s) => !covered.has(s)).join(", ")}`,
	);
	process.exit(0);
}

let failed = 0;
for (const caseDef of cases) {
	for (let i = 1; i <= repeat; i++) {
		const r = runCase(caseDef, i);
		const bad = r.results.filter((x) => !x.ok);
		failed += bad.length ? 1 : 0;
		console.log(
			`\n${bad.length ? "FAIL" : "PASS"}  ${r.case} run ${i}/${repeat}  ` +
				`(${r.toolCalls} tools, ${r.durationSec}s, $${r.costUsd})`,
		);
		for (const x of r.results)
			console.log(`  ${x.ok ? "✓" : "✗"} ${x.name} — ${x.detail}`);
	}
}
console.log(`\n${failed ? `${failed} failing run(s)` : "all runs passed"}`);
process.exit(failed ? 1 : 0);
