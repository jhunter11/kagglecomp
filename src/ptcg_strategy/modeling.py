from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


ATTACKER_FEATURES = [
    "hp",
    "retreat",
    "attack_count",
    "max_damage",
    "max_damage_per_energy",
    "min_attack_cost",
    "has_draw",
    "has_search",
    "has_gust",
    "has_energy_accel",
    "has_damage_boost",
]


def cluster_attackers(card_features: pd.DataFrame, n_clusters: int = 6, random_state: int = 42) -> pd.DataFrame:
    """Cluster Pokemon attacker profiles for archetype discovery."""
    candidates = card_features[
        (card_features["is_pokemon"]) & ((card_features["attack_count"] > 0) | (card_features["max_damage"] > 0))
    ].copy()
    if candidates.empty:
        raise ValueError("No attacker candidates found")

    features = candidates[ATTACKER_FEATURES].copy()
    for col in features.columns:
        features[col] = pd.to_numeric(features[col], errors="coerce").fillna(0)

    n_clusters = max(1, min(n_clusters, len(candidates)))
    scaled = StandardScaler().fit_transform(features)
    labels = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20).fit_predict(scaled)

    out = candidates[
        [
            "card_id",
            "card_name",
            "stage_type",
            "type",
            "hp",
            "max_damage",
            "max_damage_per_energy",
            "min_attack_cost",
            "has_energy_accel",
            "has_gust",
            "has_search",
        ]
    ].copy()
    out["cluster"] = labels
    out["attacker_score"] = (
        out["max_damage"].fillna(0)
        + 0.20 * out["hp"].fillna(0)
        + 15.0 * out["max_damage_per_energy"].fillna(0)
        - 8.0 * out["min_attack_cost"].fillna(0)
        + 35.0 * out["has_energy_accel"].astype(float)
        + 20.0 * out["has_gust"].astype(float)
        + 12.0 * out["has_search"].astype(float)
    )
    return out.sort_values(["attacker_score", "max_damage"], ascending=False).reset_index(drop=True)
