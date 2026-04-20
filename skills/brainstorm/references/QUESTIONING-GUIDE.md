# Questioning Guide

Detailed patterns for each discovery phase across all three modes. Read this file when executing the brainstorm workflow to understand the intent, techniques, and examples for each phase.

**Important:** Always use `AskUserQuestion` (Claude Code), `ask_user` (Copilot), or plain text with numbered options (Kiro) — never embed questions in unstructured text output. See SKILL.md's **AskUserQuestion Usage** section for the Claude Code call schema.

---

## Prompt Mode Phases

### Phase 2 — Goal

**Intent:** Establish a clear, measurable end-state so every subsequent question narrows toward it.

**Key questions (pick the most relevant, ask ONE at a time):**
- What is the single most important outcome you want?
- How would you know this succeeded? What does "done" look like?
- Who benefits from this and how?

**Prefer structured options when the answer space is predictable:**
- "Which matters more to you?" → Speed / Quality / Cost efficiency
- "What does success look like?" → Revenue target / User growth / Personal learning

**Techniques:**
- If the goal is vague ("I want to make money"), ask what "enough" looks like in concrete terms.
- If the goal is a feeling ("I want to feel secure"), translate to observable indicators: "What would need to be true for you to feel secure?"
- Reflect back the goal in one sentence and confirm before moving on.

**Exit criteria:** You can state the goal in one sentence with at least one measurable indicator.

---

### Phase 3 — Direction

**Intent:** Eliminate unsuitable paths WITHOUT requiring domain knowledge from the user.

**Key questions (pick the most relevant, ask ONE at a time):**
- What must absolutely NOT happen? (deal-breakers, hard constraints)
- What level of risk are you comfortable with?
- Have you tried anything before that didn't work?

**Techniques:**
- Frame questions in everyday language: "Would you be okay losing 30% temporarily?" not "What's your max drawdown tolerance?"
- Use the user's own words — avoid introducing jargon.
- Each constraint eliminates branches. Summarize which directions are now ruled out.

**Proposing approaches:** After collecting constraints, propose 2–3 viable approaches:
- Lead with your recommended option and explain why
- Include trade-offs for each (what you gain vs. what you give up)
- Frame as structured options with recommended first: Option A (Recommended) / Option B / Option C — each with a description explaining trade-offs

**Exit criteria:** At least 2 constraints that meaningfully narrow the solution space, AND the user has selected from proposed approaches.

---

### Phase 4 — Reference (optional)

**Intent:** Ground the work in existing knowledge — skip if not needed.

**When to include this phase:**
- Design/style requests (landing pages, UIs, branding)
- Requests where "in the style of X" would meaningfully improve the output
- When the user seems unsure about what good looks like

**When to skip:**
- Technical problems with clear solution spaces
- The user already mentioned references in their prompt
- Straightforward requests where references wouldn't change the output

**If included (1 question max):**
- Ask if they have examples. If yes, ask what they like about them.
- If no, and references would genuinely help, use `WebSearch` to find 2–3 relevant ones.
- If search returns poor or no results, inform the user and ask: proceed without references, or try different search terms?

---

### Phase 5 — Context

**Intent:** Surface real-world constraints the user often forgets to mention.

**Key questions (pick the most relevant, 1–2 max):**
- How much time can you realistically invest?
- What skills or tools do you already have?
- Who else is involved? Do you need buy-in?
- What's your current environment? (tech stack, team size)

**Techniques:**
- Ask about reality, not aspirations: "How many hours per week do you actually have free?" not "How much time would you ideally spend?"
- If context contradicts the goal, flag it gently.
- Combine related questions when natural: "What's your tech stack and team size?" is fine as one question.

**Exit criteria:** Enough practical constraints to distinguish "theoretically possible" from "actually feasible."

---

### Phase 6 — Criteria

**Intent:** Define what "better" means BEFORE producing output.

**Key question (usually just 1):**
- If you had to pick the top 2–3 things that matter most in the result, what are they?

**Techniques:**
- Force-rank if more than 3 criteria: "If you could only optimize for one, which would it be?"
- Make criteria specific: "easy to use" → "a beginner can follow it in under 10 minutes"

**Exit criteria:** 2–3 ranked, specific criteria.

---

## Explore Mode Phases

### Quick Goal (Phase 1)

**Intent:** Understand motivation and general direction in a single question.

**Example questions (ask via tool with structured options):**
- "What draws you to this?" → options: Learning / Solving a problem / Earning money / Building portfolio
- "What kind of result would make you feel this was time well spent?" → options: Working product / New skill learned / Revenue generated

**Techniques:**
- This replaces the separate Goal + Direction phases. One good question here is worth three mediocre ones.
- The answer tells you both what they want AND what kind of person they are.

### Constraints (Phase 2)

**Intent:** Set boundaries quickly so generated ideas are realistic.

**Combine into 1–2 questions:**
- "Any hard limits I should know? Like budget, time, or skills?" (open-ended is fine here — you need their unique situation)
- Or use structured options if predictable: "How much time do you have?" → A few hours/week / Part-time / Full-time

### Generate (Phase 3)

**Intent:** Produce a diverse set of concrete, actionable ideas.

**Structure ideas as:**
- 5–8 ideas organized by 2–3 themes
- Each idea: name, one-sentence description, why it fits their constraints, one challenge
- Highlight 1–2 "top picks" based on what you learned

**Don't just list ideas — organize them** so the user can scan and react. Use themes like "Quick wins", "Ambitious but rewarding", "Safe bets".

### Narrow (Phase 4)

**Intent:** Let the user react and choose next steps.

Ask: "Which of these resonate? I can go deeper on any of them, generate more in a specific direction, or you can take it from here."

---

## Focused Mode Phases

### Acknowledge Context (Phase 1)

**Intent:** Show the user you've absorbed their context. This builds trust and prevents redundant questions.

**Template:** "Here's what I understand: [bullet list of key facts from their prompt]. Is this accurate, and is there anything else I should know?"

This serves double duty: confirms understanding AND invites additional context in a single turn.

### Fill Gaps (Phase 2)

**Intent:** Only ask about unknowns that would change your recommendations.

**Before asking, consider:** "If I didn't know this, would my recommendations be wrong or just slightly less tailored?" Only ask if the answer is "wrong."

**Common useful unknowns:**
- Priority: cost vs. speed vs. quality
- Hard constraints not mentioned (deadlines, team size, approval needed)
- What they've already tried

**It's OK to ask zero questions** if the prompt is detailed enough. Go straight to strategies.

### Strategize (Phase 3)

**Intent:** Give actionable recommendations, not theory.

**Structure:**
- Start with quick wins (high impact, low effort)
- Then medium-term improvements
- Each item: what to do, estimated impact, effort, risks
- End with a clear "start here" recommendation and action plan

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Harmful | What to Do Instead |
|---|---|---|
| Asking multiple questions at once | Overwhelms user, gets shallow answers | Ask ONE question, wait, then follow up |
| Using open-ended when choices exist | Higher cognitive load, slower answers | Offer 2–4 concrete options |
| Introducing jargon the user didn't use | Makes non-experts feel lost | Mirror the user's vocabulary |
| Running all 7 phases for every request | Wastes time on casual brainstorms | Triage first, adapt depth |
| Always outputting "Improved Prompt" | Wrong format for idea/strategy requests | Match output to what user actually wants |
| Asking about things already in the prompt | Wastes time, frustrates user | Acknowledge context explicitly |
| Treating "I don't know" as a dead end | Misses opportunity for AI to help | Offer options or search for references |

---

## Phase Transition Signals

Move to the next phase when:
- The current phase's exit criteria are met
- OR the user explicitly wants to move on
- OR 2 questions in the current phase get "I don't know" / "doesn't matter" responses

Before transitioning, briefly summarize what was established (1 sentence, not a paragraph).
