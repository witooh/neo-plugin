#!/usr/bin/env node
/** Validate Pi package discovery and using-neo session context injection. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const extensionRelativePath = "./extensions/using-neo-session-start.js";
const extensionPath = path.join(root, extensionRelativePath);

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

assert.deepEqual(
	packageManifest.pi?.extensions,
	[extensionRelativePath],
	"package.json must load the using-neo session-start extension",
);

const projectExtensions = path.join(root, ".pi", "extensions");
assert.equal(
	fs.lstatSync(projectExtensions).isSymbolicLink(),
	true,
	".pi/extensions must be a symlink for project-local discovery",
);
assert.equal(
	fs.readlinkSync(projectExtensions),
	"../extensions",
	".pi/extensions must point to the package extension directory",
);

const registerExtension = require(extensionPath);
assert.equal(
	typeof registerExtension,
	"function",
	"Pi extension must export a factory function",
);

const handlers = new Map();
registerExtension({
	on(eventName, handler) {
		handlers.set(eventName, handler);
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

const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "neo-pi-hook-"));
process.on("exit", () => fs.rmSync(tempRoot, { recursive: true, force: true }));

async function injectedSystemPrompt(projectDir) {
	await sessionStart(
		{ reason: "startup" },
		{
			cwd: projectDir,
			ui: { notify() {} },
		},
	);

	const result = await beforeAgentStart({ systemPrompt: "BASE_SYSTEM_PROMPT" });
	assert.equal(
		typeof result?.systemPrompt,
		"string",
		"hook must return a system prompt",
	);
	return result.systemPrompt;
}

(async () => {
	const withoutIndex = path.join(tempRoot, "without-index");
	const withIndex = path.join(tempRoot, "with-index");
	fs.mkdirSync(withoutIndex, { recursive: true });
	fs.mkdirSync(path.join(withIndex, ".kiro", "steering"), { recursive: true });
	fs.writeFileSync(
		path.join(withIndex, ".kiro", "steering", "INDEX.md"),
		"STEERING_INDEX_SENTINEL\n",
	);

	const basePrompt = await injectedSystemPrompt(withoutIndex);
	assert.ok(
		basePrompt.startsWith("BASE_SYSTEM_PROMPT"),
		"hook must preserve the existing system prompt",
	);
	assert.ok(
		basePrompt.includes("neo loaded."),
		"hook must include the startup preface",
	);
	assert.ok(
		basePrompt.includes("# Using Neo"),
		"hook must inject the using-neo skill body",
	);
	assert.ok(
		basePrompt.includes("## Intent table") && basePrompt.includes("## Gates"),
		"hook must inject the routing contract (intent table + gates)",
	);
	assert.ok(
		!basePrompt.includes("Read and follow .kiro/steering/INDEX.md"),
		"hook must not mention a missing steering index",
	);

	const promptWithIndex = await injectedSystemPrompt(withIndex);
	assert.ok(
		promptWithIndex.includes("Read and follow .kiro/steering/INDEX.md"),
		"hook must include the steering instruction when INDEX.md exists",
	);
	assert.ok(
		promptWithIndex.includes("STEERING_INDEX_SENTINEL"),
		"hook must include the steering index contents",
	);

	const repeatedPrompt = await beforeAgentStart({ systemPrompt: "NEXT_TURN" });
	assert.ok(
		repeatedPrompt.systemPrompt.includes("# Using Neo"),
		"using-neo context must remain injected on later turns",
	);

	process.stdout.write("Pi package and using-neo session hook OK\n");
})().catch((error) => {
	const reason = error instanceof Error ? error.stack : String(error);
	process.stderr.write(`${reason}\n`);
	process.exit(1);
});
