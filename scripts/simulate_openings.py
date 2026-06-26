from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data
from ptcg_strategy.deck_analysis import load_deck_ids


RIOLU = 677
MAKUHITA = 673
HARIYAMA = 674
LUNATONE = 675
SOLROCK = 676
MARSHADOW = 681
MEGA_LUCARIO_EX = 678
FIGHTING_ENERGY = 6
CARMINE = 1192
LILLIE = 1227
DUSK_BALL = 1102
FIGHTING_GONG = 1142
POKE_PAD = 1152
BOSS_ORDERS = 1182
SWITCH = 1123
PREMIUM_POWER_PRO = 1141

BASIC_FIGHTING_POKEMON = {RIOLU, MAKUHITA, LUNATONE, SOLROCK, MARSHADOW}
SECONDARY_ATTACKER_BASICS = {MAKUHITA, SOLROCK, MARSHADOW}
DRAW_SUPPORT = {CARMINE, LILLIE}
SEARCH_SUPPORT = {DUSK_BALL, FIGHTING_GONG, POKE_PAD}


def simulate_deck(deck: list[int], trials: int, seed: int) -> dict:
    rng = random.Random(seed)
    rows = []
    for _ in range(trials):
        shuffled = list(deck)
        rng.shuffle(shuffled)
        opening = shuffled[:7]
        by_turn2 = shuffled[:9]
        open_counts = Counter(opening)
        turn2_counts = Counter(by_turn2)
        opening_basics = sum(open_counts[cid] for cid in BASIC_FIGHTING_POKEMON)
        turn2_basic_species = len([cid for cid in BASIC_FIGHTING_POKEMON if turn2_counts[cid] > 0])

        rows.append(
            {
                "open_has_basic": opening_basics > 0,
                "open_has_riolu": open_counts[RIOLU] > 0,
                "open_has_secondary_basic": any(open_counts[cid] > 0 for cid in SECONDARY_ATTACKER_BASICS),
                "open_basic_count": opening_basics,
                "turn2_has_riolu_access": turn2_counts[RIOLU] > 0 or turn2_counts[DUSK_BALL] > 0 or turn2_counts[FIGHTING_GONG] > 0,
                "turn2_has_lucario_access": turn2_counts[MEGA_LUCARIO_EX] > 0 or turn2_counts[DUSK_BALL] > 0,
                "turn2_has_hariyama_line": (turn2_counts[MAKUHITA] > 0 and turn2_counts[HARIYAMA] > 0)
                or turn2_counts[DUSK_BALL] > 0,
                "turn2_energy_ge_1": turn2_counts[FIGHTING_ENERGY] >= 1,
                "turn2_energy_ge_2": turn2_counts[FIGHTING_ENERGY] >= 2,
                "turn2_draw_support": any(turn2_counts[cid] > 0 for cid in DRAW_SUPPORT),
                "turn2_search_support": any(turn2_counts[cid] > 0 for cid in SEARCH_SUPPORT),
                "turn2_boss_or_switch": turn2_counts[BOSS_ORDERS] > 0 or turn2_counts[SWITCH] > 0,
                "turn2_power_mod": turn2_counts[PREMIUM_POWER_PRO] > 0 or turn2_counts[FIGHTING_GONG] > 0,
                "turn2_basic_species": turn2_basic_species,
                "turn2_multi_plan": turn2_basic_species >= 2
                and any(turn2_counts[cid] > 0 for cid in DRAW_SUPPORT | SEARCH_SUPPORT),
            }
        )

    frame = pd.DataFrame(rows)
    summary = {}
    for col in frame.columns:
        if frame[col].dtype == bool:
            summary[col] = float(frame[col].mean())
        else:
            summary[f"{col}_mean"] = float(frame[col].mean())
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Monte Carlo opening-hand simulations for deck variants.")
    parser.add_argument("--agents-dir", default="agents")
    parser.add_argument("--pattern", default="lucario_*")
    parser.add_argument("--csv", default="EN_Card_Data.csv")
    parser.add_argument("--trials", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="outputs/opening_simulation_summary.csv")
    args = parser.parse_args()

    # Loading features here catches stale or invalid card ids early.
    card_level_features(load_card_data(args.csv))

    rows = []
    for agent_dir in sorted(Path(args.agents_dir).glob(args.pattern)):
        deck_path = agent_dir / "deck.csv"
        if not deck_path.exists():
            continue
        deck = load_deck_ids(deck_path)
        if len(deck) != 60:
            raise ValueError(f"{deck_path} has {len(deck)} cards")
        summary = simulate_deck(deck, args.trials, args.seed)
        summary["variant"] = agent_dir.name
        summary["trials"] = args.trials
        rows.append(summary)

    out = pd.DataFrame(rows)
    preferred_cols = ["variant", "trials"] + [col for col in out.columns if col not in {"variant", "trials"}]
    out = out[preferred_cols]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
