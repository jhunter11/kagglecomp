from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data, parse_damage, parse_energy_cost


class CardFeatureTests(unittest.TestCase):
    def test_parsers(self):
        self.assertEqual(parse_damage("270"), (270.0, "static"))
        self.assertEqual(parse_damage("20x")[0], 20.0)
        self.assertEqual(parse_energy_cost("{F}\u25cf"), (2, 1, 1))

    def test_feature_build_has_lucario(self):
        raw = load_card_data(Path(__file__).resolve().parents[1] / "EN_Card_Data.csv")
        features = card_level_features(raw)
        lucario = features[features["card_id"] == 678].iloc[0]
        self.assertGreaterEqual(lucario["max_damage"], 270)
        self.assertTrue(bool(lucario["is_pokemon"]))


if __name__ == "__main__":
    unittest.main()
