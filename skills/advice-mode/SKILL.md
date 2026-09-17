---
name: advice-mode
description: "Pick the omp session mode for this task: plan, vibe, goal, or none."
disable-model-invocation: true
---

# Advice Mode

Recommend **one** omp session mode for the user's stated task, then stop. Do not start the work. Do not switch modes: the human types the slash command.

The four answers:

| Pick | Command the human types | What it does |
| --- | --- | --- |
| none | stay in this session; type nothing | Default coding session. Full toolset. One conversation does the work. |
| plan | `/plan` then the task | Read-only until a plan is approved. Then execute that plan. |
| vibe | `/vibe` then the task | This session becomes a director (`read` only). Persistent `fast`/`good` workers do the edits. |
| goal | `/goal <objective>` or `/guided-goal` | Autonomous loop on one pinned objective until verified done or a stop condition fires. |

Plan, vibe, and goal are mutually exclusive. Never recommend two. Never recommend stacking with a mode already on.

## Steps

1. **Task.** Use the user's message after `/advice-mode` as the task. If there is no task, ask one question: what do they want done. Stop for the answer. Do not interview beyond that.

2. **Classify.** Walk the first-match tree below. Stop at the first yes.

3. **Reply.** Thai, scannable, this shape:

   Mode: none | plan | vibe | goal
   Command: (อยู่ session นี้) | /plan | /vibe | /goal … | /guided-goal
   Why: <one sentence, the matching rule>
   Next: type the Command. This skill does not start the work.

If the session is already in a different mode than the pick, first line of Next: exit that mode (`/plan`, `/vibe`, or `/goal` toggles off) then type the Command. Plan paused: `/plan` again to fully exit before another mode.

Done when the reply names exactly one of the four and a Command the human can type.

## First-match tree

Walk in order. First yes wins.

1. **none** if any of:
   - Question, lookup, explanation, review of already-written text, or grilling/interview.
   - One clear change the current session can finish: a known file, a known bug with a tight loop, a small edit, a single CLI action.
   - Design still too foggy to pin success criteria and not yet a multi-file build (sharpen with grilling first; that is none, not plan).

2. **goal** if all of:
   - Success is binary and checkable without judgement: tests pass, command exits 0, score ≥ N, file exists with property X.
   - The user wants the agent to keep going across turns without re-prompting until that check passes.
   - Scope can be bounded (allowed paths / denylist) and a stop condition exists (attempt cap, escalate on ambiguity).
   Command: `/guided-goal` when any of the five fields is missing (success criteria, verification command, attempt cap, boundaries, stop conditions). `/goal <objective>` only when all five are already in the user's message.

3. **vibe** if all of:
   - The work splits into **two or more independent workstreams** that can run concurrently (not a linear pipeline where B needs A's result).
   - Directing workers beats doing it in one conversation (high volume, mechanical fan-out, parallel scouts).
   Command: `/vibe`.

4. **plan** if any of:
   - Multi-file or cross-cutting change where writes should wait for a frozen execution spec.
   - Open design choices that must be settled in a reviewable plan before editing.
   - Irreversible or high-blast-radius work (migrate, delete, schema, production cutover).
   Command: `/plan`.

5. **none** (fallback). Default session. Modes add ceremony; they have not earned it.

## Do not confuse

- Foggy tracker work: pick mode none.
- **loop** (`/loop`) is not one of the four answers. Do not recommend it.
- **prewalk** is a model handoff, not a session mode. Do not recommend it.
