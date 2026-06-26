from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data
from ptcg_strategy.deck_analysis import analyze_deck, load_deck_ids
from ptcg_strategy.deck_variants import DECK_VARIANTS, expanded_deck
from ptcg_strategy.experiment_metrics import deck_role_concentration


class DeckAnalysisTests(unittest.TestCase):
    def test_lucario_deck_basic_checks(self):
        root = Path(__file__).resolve().parents[1]
        deck = load_deck_ids(root / "agents" / "lucario" / "deck.csv")
        features = card_level_features(load_card_data(root / "EN_Card_Data.csv"))
        summary, cards = analyze_deck(deck, features)
        self.assertEqual(summary["deck_size"], 60)
        self.assertTrue(summary["ace_spec_ok"])
        self.assertEqual(summary["unknown_ids"], [])
        self.assertGreater(summary["basic_pokemon_count"], 0)
        self.assertFalse(cards.empty)

    def test_variant_decks_are_legal_and_diverse(self):
        root = Path(__file__).resolve().parents[1]
        features = card_level_features(load_card_data(root / "EN_Card_Data.csv"))
        for name, counts in DECK_VARIANTS.items():
            with self.subTest(name=name):
                deck = expanded_deck(counts)
                summary, cards = analyze_deck(deck, features)
                role = deck_role_concentration(cards.merge(features, on="card_id", how="left", suffixes=("", "_feature")))
                self.assertTrue(summary["legal_basic_checks"])
                self.assertLess(summary["mulligan_probability"], 0.25)
                self.assertGreaterEqual(role["distinct_attackers"], 3)


if __name__ == "__main__":
    unittest.main()
