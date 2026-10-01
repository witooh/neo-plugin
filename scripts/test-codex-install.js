#!/usr/bin/env node
/** Install in an isolated Codex home, then check the host loads every neo skill. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const readline = require("node:readline");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "..");
const testDir = fs.mkdtempSync(path.join(os.tmpdir(), "neo-codex-install-"));
const codexHome = path.join(testDir, "codex-home");
fs.mkdirSync(codexHome);
const env = { ...process.env, CODEX_HOME: codexHome };

function codex(...args) {
	const result = spawnSync("codex", args, {
		cwd: testDir, env, encoding: "utf8", timeout: 60_000,
	});
	assert.ifError(result.error);
	assert.equal(result.status, 0, `codex ${args.join(" ")} failed:\n${result.stderr}\n${result.stdout}`);
	return JSON.parse(result.stdout);
}

async function listSkills() {
	const server = spawn("codex", ["app-server", "--listen", "stdio://"], {
		cwd: testDir, env, stdio: ["pipe", "pipe", "pipe"],
	});
	const lines = readline.createInterface({ input: server.stdout });
	const pending = new Map();
	let stderr = "";
	server.stderr.on("data", (chunk) => { stderr += chunk; });
	function rejectPending(error) {
		for (const request of pending.values()) request.reject(error);
		pending.clear();
	}
	server.on("error", rejectPending);
	server.on("exit", (code) => rejectPending(new Error(`Codex app-server exited (${code}): ${stderr}`)));
	lines.on("line", (line) => {
		let message;
		try { message = JSON.parse(line); }
		catch (error) { rejectPending(error); return; }
		const request = pending.get(message.id);
		if (!request) return;
		pending.delete(message.id);
		if (message.error) request.reject(new Error(JSON.stringify(message.error)));
		else request.resolve(message.result);
	});
	function request(id, method, params) {
		return new Promise((resolve, reject) => {
			const timer = setTimeout(() => {
				pending.delete(id);
				reject(new Error(`Timed out waiting for ${method}: ${stderr}`));
			}, 20_000);
			pending.set(id, {
				resolve: (value) => { clearTimeout(timer); resolve(value); },
				reject: (error) => { clearTimeout(timer); reject(error); },
			});
			server.stdin.write(`${JSON.stringify({ id, method, params })}\n`);
		});
	}
	try {
		await request(1, "initialize", { clientInfo: { name: "neo-install-test", version: "1.0.0" } });
		server.stdin.write(`${JSON.stringify({ method: "initialized" })}\n`);
		return await request(2, "skills/list", { cwds: [testDir], forceReload: true });
	} finally {
		lines.close();
		if (server.exitCode === null) {
			const exited = new Promise((resolve) => server.once("exit", resolve));
			server.kill();
			await exited;
		}
	}
}

async function main() {
	try {
		const marketplace = codex("plugin", "marketplace", "add", root, "--json");
		assert.equal(marketplace.marketplaceName, "neo");
		const installed = codex("plugin", "add", "neo@neo", "--json");
		assert.equal(installed.pluginId, "neo@neo");
		assert.equal(installed.version, JSON.parse(fs.readFileSync(path.join(root, "plugin.json"), "utf8")).version);
		const listed = codex("plugin", "list", "--marketplace", "neo", "--json");
		const plugin = listed.installed.find((entry) => entry.pluginId === "neo@neo");
		assert.ok(plugin?.installed && plugin.enabled, "neo must be installed and enabled");

		const loaded = await listSkills();
		const installedRoot = fs.realpathSync(installed.installedPath);
		const entries = loaded.data.flatMap((entry) => entry.skills);
		const errors = loaded.data.flatMap((entry) => entry.errors)
			.filter((error) => error.path.startsWith(installedRoot + path.sep));
		assert.deepEqual(errors, [], "Installed neo skills must have no loader errors");
		const skills = entries.filter((skill) => skill.pluginId === "neo@neo");
		const expected = fs.readdirSync(path.join(root, "skills"), { withFileTypes: true })
			.filter((entry) => entry.isDirectory()).map((entry) => `neo:${entry.name}`).sort();
		assert.deepEqual(skills.map((skill) => skill.name).sort(), expected, "Codex must discover every domain skill and exclude maintainer skills");
		for (const skill of skills) {
			assert.equal(skill.enabled, true, `${skill.name} must be enabled`);
			assert.ok(skill.path.startsWith(path.join(installedRoot, "skills") + path.sep), "Skill must load from the installed plugin cache");
		}
		codex("plugin", "remove", "neo@neo", "--json");
		console.log(`PASSED — Codex installed neo@${installed.version} and loaded all ${skills.length} domain skills`);
	} finally {
		fs.rmSync(testDir, { recursive: true, force: true });
	}
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
