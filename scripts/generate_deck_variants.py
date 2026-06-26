from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data
from ptcg_strategy.deck_analysis import analyze_deck, format_summary
from ptcg_strategy.deck_variants import DECK_VARIANTS, expanded_deck
from ptcg_strategy.experiment_metrics import deck_role_concentration


def write_deck(path: Path, deck: list[int]) -> None:
    path.write_text("\n".join(str(card_id) for card_id in deck) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate fixed-deck agent variants for experiments.")
    parser.add_argument("--csv", default="EN_Card_Data.csv")
    parser.add_argument("--base-agent", default="agents/lucario/main.py")
    parser.add_argument("--agents-dir", default="agents")
    parser.add_argument("--out", default="outputs/deck_variant_summary.csv")
    args = parser.parse_args()

    features = card_level_features(load_card_data(args.csv))
    base_agent = Path(args.base_agent)
    if not base_agent.exists():
        raise FileNotFoundError(base_agent)

    rows = []
    for name, counts in DECK_VARIANTS.items():
        agent_dir = Path(args.agents_dir) / name
        agent_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base_agent, agent_dir / "main.py")
        deck = expanded_deck(counts)
        write_deck(agent_dir / "deck.csv", deck)

        summary, cards = analyze_deck(deck, features)
        role = deck_role_concentration(cards.merge(features, on="card_id", how="left", suffixes=("", "_feature")))
        row = {"variant": name, **summary, **role}
        rows.append(row)
        print(f"\n## {name}")
        print(format_summary(summary))
        print(
            f"Attackers: {role['distinct_attackers']} distinct; "
            f"top attacker {role['top_attacker']} share {role['top_attacker_share']:.1%}"
        )

    import pandas as pd

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
