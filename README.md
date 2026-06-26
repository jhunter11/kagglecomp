# Pokemon TCG AI Battle Challenge Code Scaffold

This folder now has a small reproducible code path around the local competition
materials.

## Skill Plan

- `data-pipeline`: load the Kaggle card CSVs, normalize columns, parse attacks,
  and write derived features without touching the original data.
- `scikit-learn`: cluster and rank attacker profiles from structured card
  features. This is useful for archetype discovery and Strategy writeup evidence.
- `networkx`: build an evolution/support graph so deck choices can be explained
  as connected card systems rather than one-off card picks.
- `statistical-analysis`: use deck and simulation summaries with confidence
  intervals/effect sizes before making claims in the Strategy writeup.
- `stable-baselines3`: keep PPO/RL as an experiment track only after a Gymnasium
  wrapper exists. The local notebooks strongly suggest the first competitive
  path should be a fast heuristic agent.
- `matplotlib`: generate writeup-ready figures from the feature and deck reports.

## Recommended First Path

The local notebooks and notes point to a practical ordering:

1. Build evidence from `EN_Card_Data.csv`.
2. Evaluate a Lucario-style deck for legality, mulligan risk, role balance, and
   attacker efficiency.
3. Submit a crash-resistant heuristic agent first.
4. Treat PPO/MCTS as research branches once the heuristic baseline is measurable.

## Commands

```powershell
python scripts/analyze_cards.py --csv EN_Card_Data.csv --out outputs
python scripts/generate_deck_variants.py --csv EN_Card_Data.csv
python scripts/audit_deck_usage_static.py --agents-dir agents --pattern "lucario_*"
python scripts/simulate_openings.py --agents-dir agents --pattern "lucario_*" --trials 20000
python scripts/evaluate_deck.py --deck agents/lucario/deck.csv --csv EN_Card_Data.csv --out outputs/lucario_deck_report.csv
python scripts/package_agent.py --agent-dir agents/lucario --out outputs/submission.tar.gz
python scripts/validate_submission.py --submission outputs/submission.tar.gz --csv EN_Card_Data.csv
python -m unittest discover -s tests
```

The Kaggle agent bundle is `outputs/submission.tar.gz` after packaging.

On Kaggle, the packager will include the competition `cg/` package if it can find
it under the sample submission input. The local copy of this folder only contains
the Strategy data files, so local validation may warn that `cg/` is absent.

## Official Simulation

This local folder does not include the Kaggle `cg` simulator package. Once the
Simulation competition input is attached in Kaggle, run:

```powershell
python scripts/run_official_simulations.py --agent agents/lucario_resilient --opponent first --games 100
python scripts/run_official_simulations.py --agent agents/lucario_resilient --opponent random --games 100
python scripts/analyze_simulation_logs.py --matches outputs/simulations/lucario_resilient_vs_first_matches.csv --decisions outputs/simulations/lucario_resilient_vs_first_decisions.csv --agent lucario_resilient
```

See [docs/experiment_plan.md](docs/experiment_plan.md) for the anti-overreliance
criteria and deck promotion process.
