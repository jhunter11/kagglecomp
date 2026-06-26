from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data
from ptcg_strategy.deck_analysis import analyze_deck, load_deck_ids
from ptcg_strategy.experiment_metrics import deck_role_concentration


def main() -> None:
    parser = argparse.ArgumentParser(description="Static card usage and concentration audit for fixed-deck agents.")
    parser.add_argument("--agents-dir", default="agents")
    parser.add_argument("--pattern", default="lucario_*")
    parser.add_argument("--csv", default="EN_Card_Data.csv")
    parser.add_argument("--out", default="outputs/static_usage_audit.csv")
    args = parser.parse_args()

    features = card_level_features(load_card_data(args.csv))
    rows = []
    card_rows = []
    for agent_dir in sorted(Path(args.agents_dir).glob(args.pattern)):
        deck_path = agent_dir / "deck.csv"
        if not deck_path.exists():
            continue
        deck = load_deck_ids(deck_path)
        summary, cards = analyze_deck(deck, features)
        enriched = cards.merge(features, on="card_id", how="left", suffixes=("", "_feature"))
        role = deck_role_concentration(enriched)
        rows.append({"variant": agent_dir.name, **summary, **role})
        detail = enriched.copy()
        detail.insert(0, "variant", agent_dir.name)
        card_rows.append(detail)

    summary_df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_path, index=False)
    cards_path = out_path.with_name(out_path.stem + "_cards.csv")
    if card_rows:
        pd.concat(card_rows, ignore_index=True).to_csv(cards_path, index=False)

    print(summary_df.to_string(index=False))
    print(f"Wrote {out_path}")
    print(f"Wrote {cards_path}")


if __name__ == "__main__":
    main()
