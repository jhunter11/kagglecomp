from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.experiment_metrics import flag_usage_anomalies, summarize_card_usage, wilson_interval


class ExperimentMetricTests(unittest.TestCase):
    def test_wilson_interval_bounds(self):
        low, high = wilson_interval(8, 10)
        self.assertGreaterEqual(low, 0)
        self.assertLessEqual(high, 1)
        self.assertLess(low, high)

    def test_usage_summary_and_flags(self):
        decisions = pd.DataFrame(
            {
                "game": [0, 0, 1, 1, 2, 2],
                "selected_card_id": [678, 678, 678, 678, 678, 674],
                "selected_card_name": ["Mega Lucario ex"] * 5 + ["Hariyama"],
                "selected_type": ["ATTACK", "ATTACK", "ATTACK", "ATTACK", "ATTACK", "PLAY"],
                "context": ["MAIN"] * 6,
                "attack_id": [1, 1, 1, 1, 1, None],
            }
        )
        matches = pd.DataFrame({"game": [0, 1, 2], "win": [1, 1, 0], "turns": [4, 5, 7]})
        usage = summarize_card_usage(decisions, matches)
        flags = flag_usage_anomalies(decisions, matches)
        self.assertFalse(usage.empty)
        self.assertIn("top_attack_share", set(flags["check"]))


if __name__ == "__main__":
    unittest.main()
