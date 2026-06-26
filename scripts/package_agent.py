from __future__ import annotations

import argparse
import tarfile
from pathlib import Path
import glob
import os
import sys


DEFAULT_CG_PATTERNS = [
    "cg",
    "agents/lucario/cg",
    "/kaggle/input/competitions/pokemon-tcg-ai-battle/sample_submission/cg",
    "/kaggle/input/**/sample_submission/cg",
    "/kaggle/input/**/cg-lib/cg",
    "/kaggle/input/**/cg",
]


def _find_cg_dir(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.exists() and path.is_dir() else None

    for pattern in DEFAULT_CG_PATTERNS:
        matches = glob.glob(pattern, recursive=True)
        for match in matches:
            path = Path(match)
            if path.is_dir() and (path / "api.py").exists():
                return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Package a Kaggle agent directory.")
    parser.add_argument("--agent-dir", default="agents/lucario", help="Directory containing main.py and deck.csv")
    parser.add_argument("--out", default="outputs/submission.tar.gz", help="Output tar.gz path")
    parser.add_argument("--cg-dir", default=None, help="Optional path to competition cg package")
    parser.add_argument("--require-cg", action="store_true", help="Fail if cg package cannot be found")
    args = parser.parse_args()

    agent_dir = Path(args.agent_dir)
    main_py = agent_dir / "main.py"
    deck_csv = agent_dir / "deck.csv"
    if not main_py.exists():
        raise FileNotFoundError(main_py)
    if not deck_csv.exists():
        raise FileNotFoundError(deck_csv)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cg_dir = _find_cg_dir(args.cg_dir)
    if args.require_cg and cg_dir is None:
        raise FileNotFoundError("Could not find cg package. Pass --cg-dir or run on Kaggle with sample_submission input.")

    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(main_py, arcname="main.py")
        tar.add(deck_csv, arcname="deck.csv")
        if cg_dir is not None:
            tar.add(cg_dir, arcname="cg")
    print(f"Wrote {out_path}")
    if cg_dir is not None:
        print(f"Included cg package from {cg_dir}")
    else:
        print("WARNING: cg package not found; archive contains only main.py and deck.csv.", file=sys.stderr)


if __name__ == "__main__":
    main()
