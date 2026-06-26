# loop/ — the autonomous iteration loop

The machinery that iterates the agent against self-play win-rate. See
`../docs/agent_architecture.md` for the full design. This dir is being built
**token-independently first** (works with no Kaggle access), then `cg` plugs in.

## Runs today (no cg, no token)
- `verify_gate.py` — the keep-if-better gate (Wilson-CI). `python loop/verify_gate.py` self-tests.
- `mutate_deck.py` — DEVELOP step (deck lever): generates legal 1-card neighbour
  decks as starter candidates. `python loop/mutate_deck.py --base agents/lucario --n 8`.

## Needs cg — ready to flip on
`cg` is native (`cg.dll` on Windows, `libcg.so` on Linux). The scripts are pure
Python and cross-platform; only the engine is native.

- **Windows desktop (primary, native, overnight):** drop `cg/` in, then
  `python scripts/run_official_simulations.py --agent agents/lucario --opponent random --games 200`.
  No Docker — `cg.dll` loads directly, full speed. This is the self-play workhorse.
- **Mac (dev only, emulated):** `bash loop/run_selfplay.sh agents/lucario random 200`
  runs it in an amd64 Linux container (`Dockerfile`) — slower; for quick checks.
- **Linux VPS (scale):** run the scripts directly; `libcg.so` loads natively.

## To get cg
`kaggle competitions download -c pokemon-tcg-ai-battle`, extract
`sample_submission/cg/` → `./cg/`. (Needs a Kaggle token + accepted Sim rules.)
Existing harness: `scripts/run_official_simulations.py` already drives `cg.game`.

## The loop (once cg is in)
`mutate_deck` / `agent-mutate` (DEVELOP) → legality CHECK → `run_selfplay` vs
champion+panel (VERIFY) → `verify_gate` keep-if-better → log → repeat. Most of it
is free local compute; Opus only does the final passover on a verified winner.
