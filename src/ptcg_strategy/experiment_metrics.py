from __future__ import annotations

from collections import Counter
from math import sqrt
from typing import Iterable

import pandas as pd


def wilson_interval(wins: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial win rate."""
    if total <= 0:
        return 0.0, 0.0
    phat = wins / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    margin = z * sqrt((phat * (1 - phat) + z * z / (4 * total)) / total) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def herfindahl_share(values: Iterable[object]) -> float:
    """Concentration index in [0, 1], where 1 means all mass is one value."""
    counts = Counter(v for v in values if pd.notna(v))
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return sum((count / total) ** 2 for count in counts.values())


def summarize_matches(rows: pd.DataFrame) -> pd.DataFrame:
    """Summarize match-level logs with confidence intervals."""
    if rows.empty:
        return pd.DataFrame()

    group_cols = [col for col in ["agent", "opponent", "deck"] if col in rows.columns]
    summaries = []
    for key, group in rows.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        base = dict(zip(group_cols, key))
        wins = int(group["win"].sum())
        total = int(len(group))
        lo, hi = wilson_interval(wins, total)
        base.update(
            games=total,
            wins=wins,
            losses=int((group["win"] == 0).sum()),
            win_rate=wins / total if total else 0.0,
            win_rate_ci_low=lo,
            win_rate_ci_high=hi,
            avg_turns=float(group["turns"].mean()) if "turns" in group else 0.0,
        )
        summaries.append(base)
    return pd.DataFrame(summaries).sort_values("win_rate", ascending=False)


def summarize_action_diversity(rows: pd.DataFrame) -> dict:
    """Measure whether an agent is leaning on one action/attack too heavily."""
    if rows.empty:
        return {
            "decision_count": 0,
            "attack_share": 0.0,
            "top_action_share": 0.0,
            "action_hhi": 0.0,
            "top_attack_share": 0.0,
            "attack_hhi": 0.0,
            "distinct_attack_ids": 0,
            "distinct_contexts": 0,
        }

    selected_type = rows.get("selected_type", pd.Series(dtype=object)).dropna()
    attack_ids = rows.loc[rows.get("selected_type", pd.Series(dtype=object)) == "ATTACK", "attack_id"].dropna()
    action_counts = Counter(selected_type)
    attack_counts = Counter(attack_ids)
    total = len(selected_type)
    attack_total = sum(attack_counts.values())

    return {
        "decision_count": int(total),
        "attack_share": action_counts.get("ATTACK", 0) / total if total else 0.0,
        "top_action_share": max(action_counts.values()) / total if action_counts else 0.0,
        "action_hhi": herfindahl_share(selected_type),
        "top_attack_share": max(attack_counts.values()) / attack_total if attack_counts else 0.0,
        "attack_hhi": herfindahl_share(attack_ids),
        "distinct_attack_ids": len(attack_counts),
        "distinct_contexts": int(rows.get("context", pd.Series(dtype=object)).nunique()),
    }


def summarize_card_usage(decisions: pd.DataFrame, matches: pd.DataFrame | None = None) -> pd.DataFrame:
    """Summarize selected card usage and attach game outcomes when available."""
    if decisions.empty or "selected_card_id" not in decisions:
        return pd.DataFrame(
            columns=[
                "selected_card_id",
                "selected_card_name",
                "selected_type",
                "context",
                "uses",
                "games",
                "use_share",
                "win_rate_when_used",
            ]
        )

    data = decisions.copy()
    data = data[data["selected_card_id"].notna()]
    if data.empty:
        return pd.DataFrame()

    if matches is not None and not matches.empty and "game" in matches:
        outcome_cols = [col for col in ["game", "win"] if col in matches.columns]
        data = data.merge(matches[outcome_cols].drop_duplicates("game"), on="game", how="left")

    total_uses = len(data)
    group_cols = ["selected_card_id", "selected_card_name", "selected_type", "context"]
    rows = []
    for key, group in data.groupby(group_cols, dropna=False):
        item = dict(zip(group_cols, key))
        games = int(group["game"].nunique()) if "game" in group else 0
        item.update(
            uses=int(len(group)),
            games=games,
            use_share=len(group) / total_uses if total_uses else 0.0,
            win_rate_when_used=float(group["win"].mean()) if "win" in group and group["win"].notna().any() else 0.0,
        )
        rows.append(item)

    return pd.DataFrame(rows).sort_values(["uses", "games"], ascending=False).reset_index(drop=True)


def flag_usage_anomalies(
    decisions: pd.DataFrame,
    matches: pd.DataFrame | None = None,
    *,
    max_card_share: float = 0.45,
    max_attack_share: float = 0.80,
    max_action_hhi: float = 0.55,
    max_card_hhi: float = 0.35,
    min_distinct_selected_cards: int = 6,
) -> pd.DataFrame:
    """Flag usage patterns that look too concentrated or brittle."""
    flags: list[dict] = []
    if decisions.empty:
        return pd.DataFrame([{"severity": "warn", "check": "no_decisions", "value": 0, "threshold": 1}])

    diversity = summarize_action_diversity(decisions)
    if diversity["top_attack_share"] > max_attack_share:
        flags.append(
            {
                "severity": "fail",
                "check": "top_attack_share",
                "value": diversity["top_attack_share"],
                "threshold": max_attack_share,
                "message": "One attack accounts for too large a share of attacks.",
            }
        )
    if diversity["action_hhi"] > max_action_hhi:
        flags.append(
            {
                "severity": "warn",
                "check": "action_hhi",
                "value": diversity["action_hhi"],
                "threshold": max_action_hhi,
                "message": "Action choices are highly concentrated.",
            }
        )

    selected_cards = decisions.get("selected_card_id", pd.Series(dtype=object)).dropna()
    distinct_cards = int(selected_cards.nunique())
    card_hhi = herfindahl_share(selected_cards)
    card_counts = Counter(selected_cards)
    top_card_share = max(card_counts.values()) / sum(card_counts.values()) if card_counts else 0.0

    if distinct_cards < min_distinct_selected_cards:
        flags.append(
            {
                "severity": "warn",
                "check": "distinct_selected_cards",
                "value": distinct_cards,
                "threshold": min_distinct_selected_cards,
                "message": "Too few distinct cards are being selected across decisions.",
            }
        )
    if top_card_share > max_card_share:
        flags.append(
            {
                "severity": "warn",
                "check": "top_card_share",
                "value": top_card_share,
                "threshold": max_card_share,
                "message": "One card dominates selected-card usage.",
            }
        )
    if card_hhi > max_card_hhi:
        flags.append(
            {
                "severity": "warn",
                "check": "card_hhi",
                "value": card_hhi,
                "threshold": max_card_hhi,
                "message": "Selected-card usage is highly concentrated.",
            }
        )

    if matches is not None and not matches.empty and len(matches) >= 20:
        summary = summarize_matches(matches)
        if not summary.empty:
            worst_low = float(summary["win_rate_ci_low"].min())
            if worst_low > 0.90:
                flags.append(
                    {
                        "severity": "review",
                        "check": "very_high_lower_bound",
                        "value": worst_low,
                        "threshold": 0.90,
                        "message": "Win-rate lower confidence bound is very high; inspect for exploit-like behavior.",
                    }
                )

    if not flags:
        flags.append(
            {
                "severity": "pass",
                "check": "usage_concentration",
                "value": 0,
                "threshold": 0,
                "message": "No configured concentration anomaly was detected.",
            }
        )
    return pd.DataFrame(flags)


def deck_role_concentration(deck_cards: pd.DataFrame) -> dict:
    """Static proxy for whether a deck is overly dependent on one attacker."""
    weighted = deck_cards.loc[deck_cards.index.repeat(deck_cards["quantity"].astype(int))].copy()
    attackers = weighted[(weighted.get("is_pokemon", False)) & (weighted.get("max_damage", 0) > 0)]
    attacker_counts = Counter(attackers["card_name"]) if not attackers.empty else Counter()
    total_attackers = sum(attacker_counts.values())
    top_attacker = attacker_counts.most_common(1)[0] if attacker_counts else ("", 0)
    return {
        "attacker_cards": int(total_attackers),
        "distinct_attackers": len(attacker_counts),
        "top_attacker": top_attacker[0],
        "top_attacker_count": int(top_attacker[1]),
        "top_attacker_share": top_attacker[1] / total_attackers if total_attackers else 0.0,
        "attacker_hhi": herfindahl_share(attackers["card_name"]) if not attackers.empty else 0.0,
    }
