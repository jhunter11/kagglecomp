"""verify_gate — the keep-if-better gate (the VERIFY step).

A challenger replaces the champion ONLY if its win-rate beats the champion's by
a statistically significant margin (Wilson lower bound > champion point estimate).
Token-free, deterministic. The win-rates come from self-play on `cg`; this module
only decides keep/reject given the counts.
"""
from __future__ import annotations
import math
from dataclasses import dataclass


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass
class Verdict:
    promote: bool
    challenger_wr: float
    challenger_lb: float        # Wilson lower bound
    champion_wr: float
    margin: float
    reason: str


def evaluate(champ_wins: int, champ_n: int,
             chal_wins: int, chal_n: int,
             min_games: int = 200, min_margin: float = 0.0) -> Verdict:
    """Promote the challenger iff its Wilson lower bound clears the champion's
    point estimate (plus an optional safety margin) on enough games."""
    chal_wr = chal_wins / chal_n if chal_n else 0.0
    champ_wr = champ_wins / champ_n if champ_n else 0.0
    chal_lb, _ = wilson_interval(chal_wins, chal_n)
    if chal_n < min_games:
        return Verdict(False, chal_wr, chal_lb, champ_wr, chal_wr - champ_wr,
                       f"insufficient games ({chal_n}<{min_games})")
    promote = chal_lb > (champ_wr + min_margin)
    return Verdict(promote, chal_wr, chal_lb, champ_wr, chal_wr - champ_wr,
                   "challenger LB beats champion" if promote
                   else "not significantly better")


if __name__ == "__main__":
    # self-test (no cg needed)
    a = evaluate(champ_wins=100, champ_n=200, chal_wins=130, chal_n=200)
    b = evaluate(champ_wins=100, champ_n=200, chal_wins=104, chal_n=200)
    c = evaluate(champ_wins=100, champ_n=200, chal_wins=70, chal_n=100)  # too few
    assert a.promote and not b.promote and not c.promote, (a, b, c)
    print("verify_gate self-test OK:")
    for v in (a, b, c):
        print(f"  chal_wr={v.challenger_wr:.3f} lb={v.challenger_lb:.3f} "
              f"vs champ={v.champion_wr:.3f} -> promote={v.promote} ({v.reason})")
