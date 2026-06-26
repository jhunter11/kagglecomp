# Autonomous Research-Loop Integration Plan

How we wrap a self-improving research loop around the existing PTCG codebase.
This repo is the **canonical home** (the portfolio artifact). The loop layer is
added here under `loop/`, `codegen/`, `memory/`. Forked, Kalshi-free, no money path.

## What already exists (the domain layer — strong)

- **A real submission agent** (`agents/lucario/main.py`, 398 lines): heuristic
  move-scorer matching the cabt interface `agent(obs_dict) -> [option indices]`,
  with a crash-proof try/except fallback (the right first competitive path given
  the 197 MB / 2 vCPU / no-GPU submission sandbox — RL/MCTS are research branches).
- **5 deck variants** (Mega-Lucario archetype) + a `ptcg_strategy` package:
  card features, deck legality/mulligan, k-means archetype clustering,
  PageRank synergy graph, Wilson-CI experiment metrics.
- **A manual, linear pipeline** (`scripts/`): generate variants → simulate (official
  `cg` engine) → analyze logs (win-rate + Wilson CI) → static audit → package → validate.
- **Measured signal:** 89.4 % (8,938/10,000) vs a random-action mirror. That proves
  the agent isn't broken — but random is a weak opponent; it is a ceiling, not a rank.
- Tests, anti-over-reliance criteria (`docs/experiment_plan.md`), submission tarballs.

## What the loop adds (the gap)

The `scripts/` ARE a primitive generate→simulate→evaluate chain — but it's manual,
linear, and open: no automated keep-if-better, no champion/challenger with
significance testing, no neighbor-search over decks or heuristic weights, no
self-improving feedback. The loop closes it:

- **`loop/research_governor.py`** (forked) — keep-if-better / plateau-stop over an
  iteration ledger. The metric is **self-play win-rate vs the current champion**.
- **`loop/verify_gate.py`** (new) — a candidate is "better" ONLY if it runs inside
  the sandbox AND beats the champion by a Wilson-CI-significant win-rate margin over
  N games. Decided by executed games, never by a model's claim. (Reuses
  `ptcg_strategy.experiment_metrics.wilson_interval`.) This is the anti-phantom-edge rule.
- **`loop/orchestrator.py` + `sprint.py`** (forked) — pick the next highest-leverage
  experiment; fan out candidate evaluations in parallel.
- **Champion/challenger ladder** — always hold the best *verified* agent; promote only on a verified gain.

## Search space (where the gradient is)

1. **Heuristic weights** — the ~40 magic numbers in `score_attack/score_play_option/
   score_card_choice` (attack base 1800, lethal +8000, attach scores…). Tunable
   against self-play win-rate.
2. **Deck composition** — automate `generate_deck_variants` into a 1–2 card neighbor
   search instead of 5 hand-built variants.
3. **Structure** — a 1-ply expectiminimax / lookahead wrapper over legal moves
   (bigger lever than weight-tuning). This is the highest-value VibeThinker target.

**Opponent panel matters:** 89 % vs random is uninformative for ranking. The gate
must score vs a panel — `first`/baseline opponents, mirror (our variants vs each
other), and ideally public archetype agents — or the gradient is fake.

## Leverage (the four)

- **VibeThinker-3B** (`codegen/`) — dev-time code-improver, NOT the in-match agent
  (the sandbox forbids a 3B at inference). It rewrites the heuristic scoring
  functions / proposes the lookahead wrapper; **self-play win-rate is its checker.**
  Perfect code-with-a-checker task; runs local (~6 GB) → ~free iteration off the Claude cap.
- **Obsidian memory graph** (`memory/`) — one linked note per iteration (parent
  version, change, win-rate before→after, verdict) → a navigable search-tree of agent-space.
- **`/verify` principle** — embodied in `verify_gate.py`: run it, measure it, or it didn't improve.
- **Obsidian skills** — run-sims / profile / package / read-cabt-API as lean linked notes.

## Why this fits the Strategy track specifically

This repo targets the **Strategy Category** ($240 k; 8 finalists × $30 k). Scoring is
**70 % Model Score / 20 % Deck Score / 10 % Report**, and Model Score explicitly rewards:
clearly articulated approach, originality/soundness, **consistency under repeated
matches**, and **avoiding over-reliance on specific initial states/matchups** — plus
Simulation-track performance. An autonomous loop that tests hypotheses, runs
thousands of significance-tested matches, and logs every ablation **is** that
evidence; the experiment graph becomes the writeup. Deadlines: entry **Sep 6**,
final submission **Sep 13 2026**, judging → Oct 11. ~11 weeks. (Strategy entry
requires a Simulation-track entry too.)

## CRITICAL PATH — the one blocker

The local `cg` simulator is the gradient. It is **not in the repo and not on PyPI** —
it ships inside the Kaggle Simulation competition input
(`/kaggle/input/.../sample_submission/cg`, per `scripts/package_agent.py`). The 89 %
notebook ran it locally (reportedly after compiling a native `libstdc++` dep), so a
working local recipe exists. Until `cg` runs locally on this machine, the loop has
nothing to execute. **First task: restore local `cg` self-play** (download via Kaggle
API with accepted Simulation rules, replicate the native-lib fix), prove
`run_official_simulations.py` runs N games and emits a win-rate, then build
`verify_gate.py` on top.
