import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const usingNeoPath = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	"../skills/using-neo/SKILL.md",
);

function loadSessionContext() {
	const usingNeo = fs.readFileSync(usingNeoPath, "utf8");
	return `neo loaded. Route every task through the using-neo single entry point.\n\n${usingNeo}`;
}

/** omp channel: ESM factory, and `before_agent_start` carries `systemPrompt` as an ordered block array. */
export default function usingNeoSessionStart(pi) {
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

		const blocks = Array.isArray(event.systemPrompt)
			? event.systemPrompt
			: event.systemPrompt
				? [event.systemPrompt]
				: [];

		return { systemPrompt: [...blocks, sessionContext] };
	});
}
