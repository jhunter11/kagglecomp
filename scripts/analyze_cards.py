from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data
from ptcg_strategy.modeling import cluster_attackers
from ptcg_strategy.synergy_graph import build_synergy_graph, top_synergy_nodes


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Pokemon TCG card features and writeup artifacts.")
    parser.add_argument("--csv", default="EN_Card_Data.csv", help="Card CSV path")
    parser.add_argument("--out", default="outputs", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_card_data(args.csv)
    features = card_level_features(raw)
    features_path = out_dir / "card_features.csv"
    features.to_csv(features_path, index=False)

    clusters = cluster_attackers(features)
    clusters_path = out_dir / "attacker_clusters.csv"
    clusters.to_csv(clusters_path, index=False)

    graph = build_synergy_graph(features)
    synergy = top_synergy_nodes(graph)
    synergy_path = out_dir / "synergy_top_nodes.csv"
    synergy.to_csv(synergy_path, index=False)

    try:
        import matplotlib.pyplot as plt

        pokemon = features[features["is_pokemon"]].copy()
        fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
        pokemon["type"].fillna("Unknown").value_counts().head(12).plot(kind="bar", ax=ax, color="#4c78a8")
        ax.set_title("Pokemon Type Counts")
        ax.set_xlabel("Type")
        ax.set_ylabel("Cards")
        fig.savefig(out_dir / "pokemon_type_counts.png", dpi=160)
        plt.close(fig)

        dpe = pokemon[pokemon["max_damage_per_energy"] > 0]["max_damage_per_energy"]
        fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
        ax.hist(dpe, bins=30, color="#f58518", edgecolor="white")
        ax.set_title("Max Damage per Energy")
        ax.set_xlabel("Damage per energy")
        ax.set_ylabel("Pokemon")
        fig.savefig(out_dir / "damage_per_energy_hist.png", dpi=160)
        plt.close(fig)
    except Exception as exc:
        print(f"Figure generation skipped: {exc}")

    print(f"Wrote {len(features)} card features to {features_path}")
    print(f"Wrote attacker clusters to {clusters_path}")
    print(f"Wrote graph centrality table to {synergy_path}")


if __name__ == "__main__":
    main()
