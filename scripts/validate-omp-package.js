#!/usr/bin/env node
/** Validate omp package discovery and using-neo-only system-prompt injection. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const extensionRelativePath = "./extensions/using-neo-session-start.mjs";
const extensionPath = path.join(root, extensionRelativePath);

const packageManifest = JSON.parse(
	fs.readFileSync(path.join(root, "package.json"), "utf8"),
);

assert.deepEqual(
	packageManifest.omp?.extensions,
	[extensionRelativePath],
	"package.json must load the omp session-start extension",
);

for (const agentName of ["fresh-eyes", "neo-builder", "neo-author", "neo-e2e"]) {
	const agentPath = path.join(root, "agents", `${agentName}.md`);
	assert.ok(
		fs.existsSync(agentPath),
		`agents/${agentName}.md must ship with the plugin`,
	);
}

const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "neo-omp-ext-"));
process.on("exit", () => fs.rmSync(tempRoot, { recursive: true, force: true }));

(async () => {
	const module = await import(`file://${extensionPath}`);
	const registerExtension = module.default;
	assert.equal(
		typeof registerExtension,
		"function",
		"omp extension must default-export a factory function",
	);

	const handlers = new Map();
	registerExtension({
		on(event, handler) {
			handlers.set(event, handler);
		},
	});

	const sessionStart = handlers.get("session_start");
	const beforeAgentStart = handlers.get("before_agent_start");
	assert.equal(
		typeof sessionStart,
		"function",
		"extension must register session_start",
	);
	assert.equal(
		typeof beforeAgentStart,
		"function",
		"extension must register before_agent_start",
	);

	const projectDir = path.join(tempRoot, "project");
	fs.mkdirSync(path.join(projectDir, ".kiro", "steering"), { recursive: true });
	fs.writeFileSync(
		path.join(projectDir, ".kiro", "steering", "INDEX.md"),
		"STEERING_INDEX_SENTINEL\n",
	);

	await sessionStart(
		{ reason: "startup" },
		{ cwd: projectDir, ui: { notify() {} } },
	);

	// omp >= 14.7 hands `before_agent_start` an ordered block array and takes one back.
	const result = await beforeAgentStart({
		systemPrompt: ["BASE_BLOCK_0", "BASE_BLOCK_1"],
	});
	assert.ok(
		Array.isArray(result?.systemPrompt),
		"extension must return the system prompt as a block array",
	);
	assert.deepEqual(
		result.systemPrompt.slice(0, 2),
		["BASE_BLOCK_0", "BASE_BLOCK_1"],
		"extension must preserve existing system-prompt blocks verbatim",
	);
	assert.equal(
		result.systemPrompt.length,
		3,
		"extension must append exactly one block",
	);

	const injected = result.systemPrompt[2];
	assert.ok(
		injected.includes("neo loaded."),
		"injected block must include the startup preface",
	);
	assert.ok(
		injected.includes("# Using Neo"),
		"injected block must include the using-neo skill body",
	);
	assert.ok(
		injected.includes("## Intent table") && injected.includes("## Gates"),
		"injected block must include the routing contract (intent table + gates)",
	);
	assert.ok(
		!injected.includes("STEERING_INDEX_SENTINEL"),
		"extension must not inject steering index contents",
	);

	const repeated = await beforeAgentStart({ systemPrompt: ["NEXT_TURN"] });
	assert.ok(
		repeated.systemPrompt.at(-1).includes("# Using Neo"),
		"using-neo context must remain injected on later turns",
	);

	process.stdout.write("omp package and using-neo session extension OK\n");
})().catch((error) => {
	const reason = error instanceof Error ? error.stack : String(error);
	process.stderr.write(`${reason}\n`);
	process.exit(1);
});
