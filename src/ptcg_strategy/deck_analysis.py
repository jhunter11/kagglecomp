from __future__ import annotations

from collections import Counter
from math import comb
from pathlib import Path
import re
from typing import Iterable

import pandas as pd


def load_deck_ids(path: str | Path) -> list[int]:
    """Load a deck file with one card id per line, tolerating simple headers."""
    ids: list[int] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("card"):
            continue
        matches = re.findall(r"\d+", stripped)
        if matches:
            ids.append(int(matches[-1]))
    return ids


def mulligan_probability(deck_size: int, basic_pokemon_count: int, hand_size: int = 7) -> float:
    """Exact probability of opening a hand with zero Basic Pokemon."""
    if deck_size <= 0 or basic_pokemon_count <= 0:
        return 1.0
    if deck_size < hand_size:
        raise ValueError("Deck size must be at least the opening hand size")
    non_basics = deck_size - basic_pokemon_count
    if non_basics < hand_size:
        return 0.0
    return comb(non_basics, hand_size) / comb(deck_size, hand_size)


def _is_unlimited_basic_energy(row: pd.Series) -> bool:
    name = str(row.get("card_name", ""))
    stage = str(row.get("stage_type", ""))
    return "Basic" in stage and "Energy" in stage and "Energy" in name


def analyze_deck(deck_ids: Iterable[int], card_features: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Analyze legality, composition, and consistency for a 60-card deck."""
    ids = list(deck_ids)
    counts = Counter(ids)
    features = card_features.set_index("card_id", drop=False)

    rows = []
    unknown_ids = []
    for card_id, qty in sorted(counts.items()):
        if card_id not in features.index:
            unknown_ids.append(card_id)
            rows.append({"card_id": card_id, "quantity": qty, "card_name": "<unknown>"})
            continue
        row = features.loc[card_id].to_dict()
        row["quantity"] = qty
        rows.append(row)

    cards = pd.DataFrame(rows)
    if cards.empty:
        raise ValueError("Deck is empty")

    known = cards[cards["card_name"] != "<unknown>"].copy()
    weighted = known.loc[known.index.repeat(known["quantity"].astype(int))]

    copy_limit_violations = []
    ace_spec_total = 0
    for _, row in known.iterrows():
        qty = int(row["quantity"])
        if bool(row.get("is_ace_spec", False)):
            ace_spec_total += qty
        if qty > 4 and not _is_unlimited_basic_energy(row):
            copy_limit_violations.append(f"{row['card_name']} ({qty})")

    basic_pokemon_count = int(
        weighted[(weighted.get("is_pokemon", False)) & (weighted.get("is_basic", False))].shape[0]
    )
    deck_size = len(ids)

    summary = {
        "deck_size": deck_size,
        "unique_cards": len(counts),
        "is_60_cards": deck_size == 60,
        "unknown_ids": unknown_ids,
        "copy_limit_violations": copy_limit_violations,
        "ace_spec_total": ace_spec_total,
        "ace_spec_ok": ace_spec_total <= 1,
        "pokemon_count": int(weighted.get("is_pokemon", pd.Series(dtype=bool)).sum()),
        "basic_pokemon_count": basic_pokemon_count,
        "trainer_count": int(weighted.get("is_trainer", pd.Series(dtype=bool)).sum()),
        "energy_count": int(weighted.get("is_energy", pd.Series(dtype=bool)).sum()),
        "avg_hp": float(weighted["hp"].mean()) if "hp" in weighted else 0.0,
        "max_attack_damage": float(weighted["max_damage"].max()) if "max_damage" in weighted else 0.0,
        "avg_attack_dpe": float(weighted["max_damage_per_energy"].mean())
        if "max_damage_per_energy" in weighted
        else 0.0,
        "mulligan_probability": mulligan_probability(deck_size, basic_pokemon_count),
    }
    summary["legal_basic_checks"] = (
        summary["is_60_cards"]
        and not summary["unknown_ids"]
        and not summary["copy_limit_violations"]
        and summary["ace_spec_ok"]
        and basic_pokemon_count > 0
    )

    display_cols = [
        "card_id",
        "card_name",
        "quantity",
        "stage_type",
        "rule",
        "hp",
        "type",
        "max_damage",
        "min_attack_cost",
        "max_damage_per_energy",
        "has_search",
        "has_draw",
        "has_gust",
        "has_energy_accel",
    ]
    cards = cards[[c for c in display_cols if c in cards.columns]].sort_values(
        ["stage_type", "card_name"], na_position="last"
    )
    return summary, cards.reset_index(drop=True)


def format_summary(summary: dict) -> str:
    """Format a deck summary for terminal output."""
    lines = [
        f"Deck size: {summary['deck_size']} (60-card legal: {summary['is_60_cards']})",
        f"Unique cards: {summary['unique_cards']}",
        f"Pokemon / Trainers / Energy: {summary['pokemon_count']} / {summary['trainer_count']} / {summary['energy_count']}",
        f"Basic Pokemon: {summary['basic_pokemon_count']}",
        f"Mulligan probability: {summary['mulligan_probability']:.2%}",
        f"ACE SPEC count: {summary['ace_spec_total']} (ok: {summary['ace_spec_ok']})",
        f"Copy-limit violations: {', '.join(summary['copy_limit_violations']) or 'none'}",
        f"Unknown card IDs: {summary['unknown_ids'] or 'none'}",
        f"Basic legality checks passed: {summary['legal_basic_checks']}",
    ]
    return "\n".join(lines)
