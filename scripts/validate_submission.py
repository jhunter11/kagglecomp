from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.card_features import card_level_features, load_card_data
from ptcg_strategy.deck_analysis import analyze_deck, format_summary, load_deck_ids


def _safe_extract(tar: tarfile.TarFile, target: Path) -> None:
    root = target.resolve()
    for member in tar.getmembers():
        destination = (target / member.name).resolve()
        if root != destination and root not in destination.parents:
            raise ValueError(f"Unsafe tar member path: {member.name}")
    tar.extractall(target)


def _load_agent(main_py: Path):
    spec = importlib.util.spec_from_file_location("submission_main", main_py)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {main_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "agent"):
        raise AttributeError("main.py does not define agent(obs_dict)")
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a PTCG Kaggle submission bundle.")
    parser.add_argument("--submission", default="outputs/submission.tar.gz")
    parser.add_argument("--csv", default="EN_Card_Data.csv")
    parser.add_argument("--require-cg", action="store_true", help="Fail if cg/ is not present in the archive")
    args = parser.parse_args()

    submission = Path(args.submission)
    if not submission.exists():
        raise FileNotFoundError(submission)

    with tarfile.open(submission, "r:gz") as tar:
        names = tar.getnames()
        has_main = "main.py" in names
        has_deck = "deck.csv" in names
        nested_required_files = [name for name in names if name.endswith("/main.py") or name.endswith("/deck.csv")]
        has_cg = any(name == "cg" or name.startswith("cg/") for name in names)

        print(f"Archive: {submission}")
        print(f"Top-level main.py: {has_main}")
        print(f"Top-level deck.csv: {has_deck}")
        print(f"Contains cg/: {has_cg}")
        if nested_required_files:
            print(f"Nested main/deck files also present: {nested_required_files}")

        if not has_main or not has_deck:
            raise AssertionError("Submission must contain top-level main.py and deck.csv")
        if args.require_cg and not has_cg:
            raise AssertionError("cg/ package is required by this validation mode")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _safe_extract(tar, tmp_path)
            deck_ids = load_deck_ids(tmp_path / "deck.csv")
            features = card_level_features(load_card_data(args.csv))
            summary, _ = analyze_deck(deck_ids, features)
            print(format_summary(summary))
            if not summary["legal_basic_checks"]:
                raise AssertionError("Deck failed basic legality checks")

            sys.path.insert(0, str(tmp_path))
            old_cwd = Path.cwd()
            os.chdir(tmp_path)
            module = _load_agent(tmp_path / "main.py")
            init_deck = module.agent(None)
            os.chdir(old_cwd)
            print(f"agent(None) deck length: {len(init_deck)}")
            if len(init_deck) != 60:
                raise AssertionError("agent(None) must return 60 card IDs")

            os.chdir(tmp_path)
            mock_decision = module.agent(
                {"select": {"type": "MAIN", "context": "", "option": ["PLAY", "END"], "maxCount": 1, "minCount": 1}}
            )
            os.chdir(old_cwd)
            print(f"mock decision: {mock_decision}")
            if not isinstance(mock_decision, list) or not mock_decision:
                raise AssertionError("agent(obs) must return a non-empty list of option indices")

    if not has_cg:
        print("WARNING: cg/ is absent. Add it when packaging inside Kaggle if the runtime does not provide cg.")
    print("Submission validation completed.")


if __name__ == "__main__":
    main()
