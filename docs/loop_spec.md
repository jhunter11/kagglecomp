# The PTCG Research Loop (custom)

A competition-specific loop. Based on the operator's shape
(consider → research → develop → check-rules → takeaways → repeat) with one
critical addition — an **executed-metric VERIFY gate** — and a two-speed
structure so judgment-tokens aren't spent on every micro-iteration.

## Why VERIFY is non-negotiable
"Check against rules" proves a candidate is *legal*; it does not prove it *wins
more*. A legal deck can lose. Every prior failure (Kalshi flat hill, the
phantom-edge settlement bugs) came from trusting a claimed improvement instead of
an executed one. So a candidate is only "better" when **self-play vs the current
champion shows a Wilson-CI-significant win-rate gain** — measured by running games,
never asserted. That measured win-rate IS the gradient we climb.

## Two speeds
- **OUTER loop (slow, judgment, Opus):** CONSIDER → RESEARCH. Picks *which lever*
  to pull next and forms a testable hypothesis. Runs a few times a day.
- **INNER loop (fast, ~free):** DEVELOP → CHECK → VERIFY → TAKEAWAYS on each
  candidate. Code-gen (local VibeThinker) + deterministic validators + local
  self-play (CPU). Runs many times per outer cycle, off the Claude cap.

## The six phases

### 1. CONSIDER  *(orient — pick the lever)*  · Opus · cheap
- **In:** champion state, the iteration ledger, governor verdict, open takeaways.
- **Do:** choose the highest-leverage lever for the next batch:
  (a) heuristic weights (~40 magic numbers in `agents/*/main.py`
  `score_attack/score_play_option/score_card_choice`),
  (b) deck composition (1–2 card neighbor swaps),
  (c) structure (a 1-ply lookahead wrapper over legal moves — biggest lever).
- **Out:** a target lever + a budget (how many candidates this batch).

### 2. RESEARCH  *(hypothesis)*  · Opus/Sonnet · medium
- **In:** the chosen lever, `EN_Card_Data.csv`, synergy graph, opponent meta,
  public Kaggle discussion.
- **Do:** form ONE falsifiable hypothesis ("raising the lethal bonus will not help
  because X already dominates"; "swapping a Dusk Ball for a 3rd Carmine raises
  turn-2 Lucario access without raising mulligan risk").
- **Out:** a written hypothesis + expected direction of win-rate change.

### 3. DEVELOP  *(implement)*  · **VibeThinker-3B (local)** / Sonnet · ~free
- **In:** the hypothesis + the current champion code/deck.
- **Do:** emit the concrete change — rewritten scoring function, a new `deck.csv`,
  or the lookahead wrapper. This is the code-with-a-checker task VibeThinker is
  built for; self-play (phase 5) is the checker.
- **Out:** a candidate agent dir (`agents/<candidate>/`).

### 4. CHECK  *(rules + sandbox pre-gate)*  · deterministic Python · free
- **In:** the candidate.
- **Do:** fast kill before spending sim compute. Reuse existing validators:
  `ptcg_strategy.deck_analysis` (60-card legality, copy limits, ACE-Spec ≤1),
  `validate_submission.py` (loads, returns a legal move, tarball format),
  sandbox fit (≤197 MB, imports clean, no GPU), and the **anti-over-reliance
  criteria** in `docs/experiment_plan.md` (no single attack >80%, ≥2 real
  attackers, mulligan <25%, survives primary-attacker KO).
- **Out:** PASS → phase 5, or KILL with a reason (logged).
- **Note — this gate is dual-purpose:** the anti-over-reliance checks aren't just
  compliance, they're *literally* part of the judged Model Score
  (70%: "consistency under repeated matches", "avoids over-reliance on initial
  states/matchups"). Passing CHECK is optimizing the prize metric directly.

### 5. VERIFY  *(executed measurement — THE gate)*  · `cg` self-play · ~free (CPU)
- **In:** the candidate + the champion + a fixed **opponent panel**
  (baseline `first`, `random`, mirror variants, archetype decks — NOT just random,
  or the gradient is fake).
- **Do:** run N games candidate-vs-panel and candidate-vs-champion, alternating
  seat order. Compute win-rate + Wilson CI (`experiment_metrics.wilson_interval`)
  and the champion delta. **Promote only if the lower CI bound beats the champion.**
- **Out:** measured win-rate, CI, promote/reject. Append to the iteration ledger.

### 6. TAKEAWAYS  *(reflect + govern)*  · Haiku/Sonnet + deterministic · cheap
- **In:** the VERIFY result + the original hypothesis.
- **Do:** write one Obsidian experiment note (`memory/experiments/exp-NNN.md`:
  parent version, change, hypothesis, win-rate before→after, verdict) linked to
  its parent → the search-tree of agent-space. Feed the `research_governor`:
  `KEEP_ITERATING` (lever still improving) / `BLOCKED_PLATEAU` (lever exhausted →
  back to CONSIDER with a different lever) / `DEPLOY` (new champion). If promoted,
  update the champion pointer + package a fresh submission tarball.
- **Out:** governor verdict → drives the next CONSIDER.

## Champion ledger
`registry.json`: the current champion (version, code/deck hash, measured win-rate
vs panel, ancestry) + every challenger's verdict. Always hold the best *verified*
agent; never regress.

## Execution dependency
Phases 4–6 are built and ready to wire (validators exist; governor/metrics fork
from the harness). **Phase 5 requires the local `cg` simulator**, which is the one
open blocker (see `docs/loop_integration.md`). No `cg` → no VERIFY → no gradient.
