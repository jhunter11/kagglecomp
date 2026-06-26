# Autonomous Iteration Architecture — PTCG Agent

Goal: iterate the competition agent **as fast as possible with minimal human
interaction**, and spend the scarce moves (submissions, the writeup) at the right
time. This is the agent/sub-agent design that does that.

## 0. The gate (everything below is inert without it)
`cg`, the Kalshi-environments PTCG simulator, is **not installed locally**
(`import cg` fails). It is the *gradient*: no `cg` → no self-play → no VERIFY →
no autonomous loop. **Step 0 is getting `cg` running locally.** Path: (a) the
recipe from the 89%-WR notebook (it ran games locally — reportedly after compiling
a native `libstdc++` dep), or (b) a Kaggle API token + accepted Simulation rules →
download `sample_submission/cg`. Until then we build infra against the existing
mock, but cannot truly iterate.

## 1. Deployment — a portable compute hub (Mac dev · Windows overnight · VPS scale)
The repo **is** the hub: agent code, the loop, the champion, and the experiment
ledger. Hosts coordinate over **git** (the workhorse pushes the new champion +
ledger; the brain pulls). The OpenClaw runtime (orchestrator, cron, sub-agents,
memory) is reused, repointed from the Kalshi tree to `kagglecomp/` with a new skill set.

- **Windows desktop — the self-play workhorse (best near-term).** `cg` ships a native
  Windows `cg.dll`, so battles run **natively — no Docker, no emulation, full speed.**
  Leave the inner loop (`mutate → self-play → verify → keep`) running overnight; it
  commits the new champion + ledger. A GPU here is also the ideal **VibeThinker** host.
- **Mac — dev + brain.** The OpenClaw **Strategist** runs here: pulls results, picks
  levers, does the Opus passover, manages submissions. `cg` on the Mac only via Docker
  (amd64-emulated, slow) — for quick checks, not the grind.
- **VPS — scale-up (optional).** A Linux box sized to a **multiple of the competition
  spec (2 vCPU / 12 GiB each)** runs many parallel games natively (`libcg.so`). Reach
  for it only if Windows-overnight isn't enough throughput.

**Submission policy: AUTO.** The loop auto-submits the verified-best challenger (gated
by `verify_gate` + an Opus passover), ≤5/day, and notifies after. (Flip to
confirm-first anytime.)

## 2. Two tiers, two speeds (where speed + low-human come from)
- **Tier 1 — Strategist** (Opus, low cadence, judgment). The "play the right cards"
  brain: reads leaderboard + champion + governor verdict; picks the next *lever*;
  manages the **5-submissions/day budget** (2 active max) — submit only the
  verified-best challenger, bank the rest; handles plateaus (structural rethink);
  drafts the Strategy-track writeup. Runs a few times/day or on milestones.
- **Tier 2 — Iterator** (local, high cadence, ~free, **unattended**). The inner loop
  `DEVELOP → CHECK → VERIFY → TAKEAWAYS`, cron'd every few minutes. VibeThinker-local
  codegen + CPU self-play = no Claude-cap burn, dozens of iterations/day, no human.

## 3. Sub-agent fan-out (the autoresearch tournament)
Each inner cycle fans out for parallelism:
- **N Mutator sub-agents** (parallel codegen) — each proposes ONE candidate along a
  different lever: attack-weights / energy-weights / deck-swap / lookahead-depth.
  Cheap, parallel (VibeThinker or Sonnet).
- **Verifier** (deterministic harness, *not* an LLM) — runs each candidate vs the
  **champion + an opponent panel** (random, greedy, mirror, archetypes) on `cg`,
  returns win-rate + Wilson CI. Parallel across CPU cores. The executed gate.
- **Governor** (deterministic + occasional Opus) — dedup, keep-if-better (lower CI
  bound beats champion), plateau detection (kill dead levers), champion promotion.

Many mutators → parallel verification → keep verified winners. Free local compute
is what lets this run hot.

## 3.5 Compute tiering — run hot locally, ration the frontier
Use the cheapest tier that suffices; the **climb must not depend on frontier usage**
(the Max limit may shrink after this month — design for scarcity).

| Tier | Cost | Does |
|---|---|---|
| **Deterministic** | free, unlimited | self-play verify, legality, metrics, the governor's keep/iterate/plateau decisions, dedup, packaging — most of the loop. No LLM. |
| **VibeThinker-3B (local)** | free, unlimited, parallel | the codegen grunt work: mutate scoring fns, propose deck swaps, write the lookahead, refactor. Many in parallel. |
| **Sonnet** | cheap frontier | optional mid-tier: summarize a batch, draft a hypothesis. |
| **Opus** | scarce frontier | ONLY genuine judgment + the **final passover**: pick the lever, break a plateau, submit/strategy calls, the writeup. |

**Honest tweak to the split:** VibeThinker is a verifiable-code specialist — give it
code-with-a-checker (self-play is the checker), **not** open-ended strategy. Most
"deciding" should be the governor's **deterministic rules** (free + reliable), not an
LLM at all. Frontier judgment is Opus, and rare.

**The passover pattern (your idea):** VibeThinker generates → the deterministic
verifier *proves* a candidate beats the champion → only THEN does Opus do a final
passover (sanity-check the code, check for cheese / over-reliance, OK-to-submit). So
Opus touches only the handful of verified winners, never every candidate.

**Graceful degradation:** the core (mutate → verify → keep) is 100% local. If frontier
access drops, the loop keeps iterating and improving on local compute; only the
strategic-direction + passover cadence slows. The climb never stalls on a usage cap.

## 4. Skills: keep / change / drop / build
**DROP — Kalshi-business, irrelevant to a game-AI comp:** `idea-generation`,
`idea-validation`, `pain-discovery/evidence/scoring`, `market-validation`,
`money-loop`, `economics-check`, `growth-loop`, `delivery-loop`, `strategy-factory`,
`strategy-maintenance`, `validation-test-design`, `planning-loop`, `stage-router`.

**KEEP / RETARGET — generic loop + infra:** `cycle-sense` → "sense: rank, champion
WR, submission budget"; `cycle-reflection` → "log experiment to the graph";
`operator-brain` → the Tier-1 Strategist; `review-gate` → adversarial check *before*
spending a daily submission; `graphify` + `obsidian` → memory graph;
`modeling-deep-dive`, `skill-token-refactor`, `voice-prompt-optimizer` → keep.

**BUILD — PTCG-specific (the new core):**
- `selfplay` — run K games(A,B) on `cg`, alternate seats → win-rate + Wilson CI + crash/timeout.
- `agent-mutate` — champion scoring code + its WR → an improved variant (DEVELOP; VibeThinker).
- `deck-optimize` — 1–2 card neighbor search over the 60-card deck.
- `verify-gate` — keep-if-better executed gate (VERIFY).
- `legality-check` — rules + anti-over-reliance pre-kill (CHECK; reuse existing `validate_submission.py` + `deck_analysis`).
- `submit-manager` — 5/day budget, submit verified-best, poll leaderboard, track active subs.

## 5. Minimal human interaction — the escalation contract
The loop runs unattended and pings the human ONLY for: (1) the one-time `cg` unblock;
(2) a hard plateau needing a structural idea the governor can't break; (3) a
submission/strategy judgment call; (4) Kaggle account actions (auth, accept rules).
Everything else — mutate, verify, promote, log — is autonomous.

## 6. Play the right cards (timing)
- Iterate **locally** (unlimited, free); spend the **5 daily submissions** only on
  verified improvements — never on noise. 89% was vs *random* (weak); verify vs a
  strong panel so the gradient is real.
- Deadlines: entry **Sep 6**, final **Sep 13** (~11 weeks). Front-load local iteration
  now; the submission cadence is the slow climb.
- Two tracks: Simulation (leaderboard) + **Strategy ($240k, judged on writeup +
  leaderboard)**. The experiment graph the loop produces *is* the writeup material —
  so autonomous iteration directly feeds the prize track.

## 7. Build sequence
0. **Unblock `cg`** (gate).
1. Repoint runtime at `kagglecomp`; install the new skills; drop the business skills.
2. `selfplay` + `verify-gate`; **re-baseline the champion vs a real opponent panel**.
3. `agent-mutate` (VibeThinker) + the inner loop; cron it.
4. Tier-1 Strategist + `submit-manager`.
5. Let it run; human only on the escalation contract.

**Buildable now, before `cg` (against the existing mock):** the skill set,
`selfplay`/`verify-gate`/`agent-mutate`/`submit-manager` scaffolding, the
experiment-graph memory — then swap the mock for real `cg`.
