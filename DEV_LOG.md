# Development Log

Record of each step of building this project with an AI coding agent
(Claude Code), following the prompt sequence in the assignment guide.
For each step: the prompt used (short), what was built, test results, and
problems found + fixes.

---

## Step 1 — Prompt 1: Rescope the TODO

**Prompt (short):** "Read SPECIFICATION.md and TODO.md. Revise TODO.md into a
phased plan covering only engine, words, Flask API, browser client, testing,
docs/deploy config, cloud deployment. Keep out-of-scope phases at the bottom.
Keep the spec's REST API. No code yet."

**What was done:**
- Rewrote `TODO.md` into 7 in-scope phases, each with a task checklist and
  completion criteria.
- Moved terminal client, bots, evaluation mode, scoring, leaderboard,
  anti-cheating safeguards, logging/replay, and optional future phases into
  an "Out of Scope for This Assignment" section (kept, not deleted).
- `SPECIFICATION.md` untouched.

**Problems found:**
- The original `TODO.md` had **every** checkbox already checked (`[x]`) even
  though the repo contained no code. Leaving it like that would make the
  TODO meaningless as a progress tracker. Fix: all in-scope items reset to
  `[ ]` and are checked off only after verification; a note explains why.
- The original `TODO.md` referred to the spec as
  `Hangman_Project_Specification.md`, but the file in the repo is
  `SPECIFICATION.md`. Fix: references updated in TODO.md (the spec itself
  is not modified).

**Tests:** none (no code yet).
