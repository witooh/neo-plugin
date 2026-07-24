const fs = require("node:fs");
const path = require("node:path");

const usingNeoPath = path.resolve(__dirname, "../skills/using-neo/SKILL.md");

function loadSessionContext() {
	const usingNeo = fs.readFileSync(usingNeoPath, "utf8");
	return `neo loaded. Route every task through the using-neo single entry point.\n\n${usingNeo}`;
}

module.exports = function usingNeoSessionStart(pi) {
	let sessionContext;

	pi.on("session_start", (_event, ctx) => {
		try {
			sessionContext = loadSessionContext();
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
