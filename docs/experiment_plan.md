# Experiment Plan

## Rules Guardrails

- Treat each packaged submission as one fixed deck. We can generate many deck
  variants for testing, but do not switch decks between games inside a single
  submission.
- Keep `main.py` and `deck.csv` at the top level of the tarball.
- Bundle `cg/` when building on Kaggle if the runtime does not provide it.
- Use only competition data, public Kaggle discussion/code, and code we can
  document and reproduce.

## Anti-Overreliance Criteria

We should reject a candidate if repeated official simulations show:

- One attack id is more than 80% of all attacks and win rate falls sharply in
  matchups that block or resist that attacker.
- Fewer than two meaningful attackers are used across wins.
- The deck has a high static attacker concentration and more than 25% mulligan
  probability.
- The agent cannot win when the primary active attacker is knocked out first.

## Candidate Decks

- `lucario_resilient`: current balanced Lucario/Hariyama/Solrock-Lunatone plan.
- `lucario_anti_wall`: more Makuhita/Hariyama and Marshadow for wall matchups.
- `lucario_consistency`: more Basics and draw/synergy to reduce dead starts.
- `lucario_power`: more damage pressure and gust effects, higher dependency risk.

## First Simulation Battery

Run on Kaggle or any environment where `cg` imports:

```powershell
python scripts/generate_deck_variants.py --csv EN_Card_Data.csv
python scripts/audit_deck_usage_static.py --agents-dir agents --pattern "lucario_*"
python scripts/simulate_openings.py --agents-dir agents --pattern "lucario_*" --trials 20000
python scripts/run_official_simulations.py --agent agents/lucario_resilient --opponent first --games 100
python scripts/run_official_simulations.py --agent agents/lucario_resilient --opponent random --games 100
python scripts/analyze_simulation_logs.py --matches outputs/simulations/lucario_resilient_vs_first_matches.csv --decisions outputs/simulations/lucario_resilient_vs_first_decisions.csv --agent lucario_resilient
```

Then repeat for each candidate and promote only the deck with strong win-rate,
low failure variance, and reasonable action/attack diversity.
