from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.experiment_metrics import (
    flag_usage_anomalies,
    summarize_action_diversity,
    summarize_card_usage,
    summarize_matches,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize official simulation match and decision logs.")
    parser.add_argument("--matches", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--out-dir", default="outputs/simulations")
    parser.add_argument("--agent", default=None, help="Optional acting_agent filter for decision logs")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    matches = pd.read_csv(args.matches)
    decisions = pd.read_csv(args.decisions)
    if args.agent and "acting_agent" in decisions.columns:
        decisions = decisions[decisions["acting_agent"] == args.agent].copy()

    match_summary = summarize_matches(matches)
    diversity = summarize_action_diversity(decisions)
    diversity_df = pd.DataFrame([diversity])
    card_usage = summarize_card_usage(decisions, matches)
    anomaly_flags = flag_usage_anomalies(decisions, matches)

    match_out = out_dir / "match_summary.csv"
    diversity_out = out_dir / "action_diversity_summary.csv"
    card_usage_out = out_dir / "card_usage_summary.csv"
    anomaly_out = out_dir / "usage_anomaly_flags.csv"
    match_summary.to_csv(match_out, index=False)
    diversity_df.to_csv(diversity_out, index=False)
    card_usage.to_csv(card_usage_out, index=False)
    anomaly_flags.to_csv(anomaly_out, index=False)

    print(match_summary.to_string(index=False))
    print(diversity_df.to_string(index=False))
    if not card_usage.empty:
        print(card_usage.head(20).to_string(index=False))
    print(anomaly_flags.to_string(index=False))
    print(f"Wrote {match_out}")
    print(f"Wrote {diversity_out}")
    print(f"Wrote {card_usage_out}")
    print(f"Wrote {anomaly_out}")


if __name__ == "__main__":
    main()
