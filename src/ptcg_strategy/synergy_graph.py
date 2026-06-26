from __future__ import annotations

import re

import networkx as nx
import pandas as pd


def build_synergy_graph(card_features: pd.DataFrame) -> nx.DiGraph:
    """Build a card graph from evolutions and obvious typed support effects."""
    graph = nx.DiGraph()
    features = card_features.copy()

    for _, row in features.iterrows():
        graph.add_node(
            int(row["card_id"]),
            label=row["card_name"],
            stage_type=row.get("stage_type"),
            card_type=row.get("type"),
            is_pokemon=bool(row.get("is_pokemon", False)),
        )

    by_name = {
        str(row["card_name"]).strip().lower(): int(row["card_id"])
        for _, row in features.iterrows()
        if pd.notna(row.get("card_name"))
    }

    for _, row in features.iterrows():
        previous = row.get("previous_stage")
        if pd.notna(previous):
            previous_id = by_name.get(str(previous).strip().lower())
            if previous_id is not None:
                graph.add_edge(previous_id, int(row["card_id"]), relation="evolves_to", weight=3.0)

    type_to_cards: dict[str, list[int]] = {}
    for _, row in features.iterrows():
        if bool(row.get("is_pokemon", False)) or bool(row.get("is_energy", False)):
            card_type = str(row.get("type", "")).strip()
            if card_type and card_type != "nan":
                type_to_cards.setdefault(card_type, []).append(int(row["card_id"]))

    for _, row in features.iterrows():
        text = f"{row.get('text', '')} {row.get('card_name', '')}"
        mentioned_types = sorted(set(re.findall(r"\{[A-Z]\}", text)))
        if not mentioned_types:
            continue
        source = int(row["card_id"])
        for card_type in mentioned_types:
            for target in type_to_cards.get(card_type, []):
                if target != source:
                    graph.add_edge(source, target, relation="typed_support", weight=1.0)

    return graph


def top_synergy_nodes(graph: nx.DiGraph, limit: int = 20) -> pd.DataFrame:
    """Return high-centrality cards in the synergy graph."""
    if graph.number_of_nodes() == 0:
        return pd.DataFrame(columns=["card_id", "card_name", "pagerank", "in_degree", "out_degree"])

    pagerank = nx.pagerank(graph, weight="weight")
    rows = []
    for node, score in pagerank.items():
        rows.append(
            {
                "card_id": node,
                "card_name": graph.nodes[node].get("label"),
                "pagerank": score,
                "in_degree": graph.in_degree(node),
                "out_degree": graph.out_degree(node),
            }
        )
    return pd.DataFrame(rows).sort_values("pagerank", ascending=False).head(limit).reset_index(drop=True)
