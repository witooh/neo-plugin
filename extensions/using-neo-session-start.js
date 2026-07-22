const fs = require("node:fs");
const path = require("node:path");

const usingNeoPath = path.resolve(__dirname, "../skills/using-neo/SKILL.md");

function loadSessionContext(projectDir) {
	const usingNeo = fs.readFileSync(usingNeoPath, "utf8");
	let context = `neo loaded. Route every task through the using-neo single entry point.\n\n${usingNeo}`;
	const steeringIndex = path.join(projectDir, ".kiro", "steering", "INDEX.md");

	if (fs.existsSync(steeringIndex)) {
		context += `\n\nProject steering is available. Read and follow .kiro/steering/INDEX.md now, including every file it marks with inclusion: always.\n\n${fs.readFileSync(steeringIndex, "utf8")}`;
	}

	return context;
}

module.exports = function usingNeoSessionStart(pi) {
	let sessionContext;

	pi.on("session_start", (_event, ctx) => {
		try {
			sessionContext = loadSessionContext(ctx.cwd);
		} catch (error) {
			sessionContext = undefined;
			const reason = error instanceof Error ? error.message : String(error);
			ctx.ui.notify(
				`neo: unable to load using-neo session context: ${reason}`,
				"warning",
			);
		}
	});

	pi.on("before_agent_start", (event) => {
		if (!sessionContext) return undefined;

		return {
			systemPrompt: `${event.systemPrompt}\n\n${sessionContext}`,
		};
	});
};
