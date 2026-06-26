"""mutate_deck — token-free DEVELOP step (deck lever).

Generates legal 1-card neighbour variants of a base deck by swapping one copy of
a card for one copy of another card already in the playable pool (the union of
cards across the hand-built variants). Gives the loop starter candidates to
iterate on with NO LLM and NO cg. Self-play (cg) then ranks them.

Usage: python loop/mutate_deck.py --base agents/lucario --n 8 --seed 0
"""
from __future__ import annotations
import argparse, random, shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"
OUT = ROOT / "outputs" / "loop_variants"


def read_deck(path: Path) -> list[int]:
    ids = [int(l) for l in path.read_text().splitlines() if l.strip().isdigit()]
    if len(ids) != 60:
        raise ValueError(f"{path}: expected 60 cards, got {len(ids)}")
    return ids


def playable_pool() -> tuple[set[int], set[int]]:
    """Union of card ids across all agents/*/deck.csv; plus the 'unlimited' set
    (basic energy = any id that appears >4 times in some deck)."""
    pool, unlimited = set(), set()
    for d in AGENTS.glob("*/deck.csv"):
        c = Counter(read_deck(d))
        pool |= set(c)
        unlimited |= {cid for cid, n in c.items() if n > 4}
    return pool, unlimited


def mutate(base: list[int], pool: set[int], unlimited: set[int],
           rng: random.Random) -> list[int] | None:
    c = Counter(base)
    # remove one copy of a randomly chosen present card
    drop = rng.choice([cid for cid, n in c.items() if n > 0])
    c[drop] -= 1
    # add one copy of a pool card that still has room (<=4, or unlimited)
    addable = [cid for cid in pool
               if cid in unlimited or c[cid] < 4]
    addable = [cid for cid in addable if cid != drop] or list(pool)
    add = rng.choice(addable)
    c[add] += 1
    deck = sorted(c.elements())
    return deck if len(deck) == 60 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="agents/lucario", help="base agent dir")
    ap.add_argument("--n", type=int, default=8, help="variants to generate")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    base_dir = ROOT / a.base
    base = read_deck(base_dir / "deck.csv")
    pool, unlimited = playable_pool()
    rng = random.Random(a.seed)
    OUT.mkdir(parents=True, exist_ok=True)

    made, seen = 0, {tuple(sorted(base))}
    while made < a.n:
        deck = mutate(base, pool, unlimited, rng)
        if not deck or tuple(deck) in seen:
            continue
        seen.add(tuple(deck))
        vdir = OUT / f"variant_{made:02d}"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "deck.csv").write_text("\n".join(map(str, deck)) + "\n")
        shutil.copy(base_dir / "main.py", vdir / "main.py")   # same policy, new deck
        diff = Counter(deck) - Counter(base)
        made += 1
        print(f"  variant_{made-1:02d}: +{dict(diff)} -> {vdir.relative_to(ROOT)}")
    print(f"Generated {made} legal neighbour decks under {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
