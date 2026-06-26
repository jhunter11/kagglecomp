from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data
from ptcg_strategy.deck_analysis import analyze_deck, format_summary, load_deck_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a Pokemon TCG deck list by card id.")
    parser.add_argument("--deck", default="agents/lucario/deck.csv", help="Deck file")
    parser.add_argument("--csv", default="EN_Card_Data.csv", help="Card CSV path")
    parser.add_argument("--out", default=None, help="Optional card-level deck report CSV")
    args = parser.parse_args()

    deck_ids = load_deck_ids(args.deck)
    features = card_level_features(load_card_data(args.csv))
    summary, cards = analyze_deck(deck_ids, features)

    print(format_summary(summary))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cards.to_csv(out_path, index=False)
        print(f"Wrote deck card report to {out_path}")


if __name__ == "__main__":
    main()
