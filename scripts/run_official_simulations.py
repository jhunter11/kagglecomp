from __future__ import annotations

import argparse
import csv
import importlib.util
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_strategy.deck_analysis import load_deck_ids


def enum_name(value) -> str:
    if value is None:
        return ""
    return str(getattr(value, "name", value)).split(".")[-1]


def card_id(card) -> int | None:
    return getattr(card, "id", getattr(card, "cardId", None))


def safe_list(value) -> list:
    return list(value) if value else []


def build_card_table() -> dict[int, str]:
    try:
        from cg.api import all_card_data

        table = {}
        for card in all_card_data():
            cid = getattr(card, "cardId", getattr(card, "id", None))
            name = getattr(card, "name", getattr(card, "cardName", ""))
            if cid is not None:
                table[int(cid)] = str(name)
        return table
    except Exception:
        return {}


CARD_NAMES: dict[int, str] = {}


def card_name(cid: int | None) -> str:
    if cid is None:
        return ""
    return CARD_NAMES.get(int(cid), "")


def get_player(state, index: int):
    players = safe_list(getattr(state, "players", []))
    if 0 <= index < len(players):
        return players[index]
    return None


def get_card(obs, area, index, player_index):
    if index is None:
        return None
    state = getattr(obs, "current", None)
    if state is None:
        return None
    area_name = enum_name(area)
    player = get_player(state, int(player_index or 0))
    if area_name == "STADIUM":
        cards = safe_list(getattr(state, "stadium", []))
    elif area_name == "LOOKING":
        cards = safe_list(getattr(state, "looking", []))
    elif player is None:
        return None
    elif area_name == "HAND":
        cards = safe_list(getattr(player, "hand", []))
    elif area_name == "DISCARD":
        cards = safe_list(getattr(player, "discard", []))
    elif area_name == "ACTIVE":
        cards = safe_list(getattr(player, "active", []))
    elif area_name == "BENCH":
        cards = safe_list(getattr(player, "bench", []))
    else:
        return None
    return cards[index] if 0 <= index < len(cards) else None


def zone_ids(player, zone: str) -> str:
    cards = safe_list(getattr(player, zone, []))
    ids = [str(card_id(card)) for card in cards if card_id(card) is not None]
    return ";".join(ids)


class BuiltinAgent:
    def __init__(self, name: str, deck: list[int], seed: int = 42):
        self.name = name
        self.deck = deck
        self.rng = random.Random(seed)

    def agent(self, obs_dict):
        if obs_dict is None:
            return list(self.deck)
        try:
            from cg.api import to_observation_class

            obs = to_observation_class(obs_dict)
            select = getattr(obs, "select", None)
            if select is None:
                return list(self.deck)
            options = list(getattr(select, "option", []) or [])
            max_count = max(1, int(getattr(select, "maxCount", 1) or 1))
            if self.name == "random":
                idx = list(range(len(options)))
                self.rng.shuffle(idx)
                return idx[:max_count] or [0]
            return list(range(min(max_count, len(options)))) or [0]
        except Exception:
            return [0]


def load_agent(agent_dir: Path):
    main_py = agent_dir / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(main_py)
    spec = importlib.util.spec_from_file_location(f"agent_{agent_dir.name}", main_py)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {main_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_option_info(obs_dict, choice: list[int], acting_agent: str) -> dict:
    from cg.api import to_observation_class

    obs = to_observation_class(obs_dict)
    select = getattr(obs, "select", None)
    state = getattr(obs, "current", None)
    if select is None:
        return {}
    options = list(getattr(select, "option", []) or [])
    selected_index = choice[0] if choice else None
    selected = options[selected_index] if selected_index is not None and 0 <= selected_index < len(options) else None
    player_index = int(getattr(state, "yourIndex", 0) or 0) if state is not None else 0
    player = get_player(state, player_index) if state is not None else None
    opponent = get_player(state, 1 - player_index) if state is not None else None
    active = safe_list(getattr(player, "active", []))[0] if player and safe_list(getattr(player, "active", [])) else None
    opponent_active = (
        safe_list(getattr(opponent, "active", []))[0] if opponent and safe_list(getattr(opponent, "active", [])) else None
    )

    selected_type = enum_name(getattr(selected, "type", ""))
    selected_card = None
    selected_area = enum_name(getattr(selected, "area", ""))
    selected_in_play_area = enum_name(getattr(selected, "inPlayArea", ""))
    if selected_type == "PLAY":
        selected_card = get_card(obs, "HAND", getattr(selected, "index", None), player_index)
        selected_area = "HAND"
    elif selected_type == "CARD":
        selected_card = get_card(
            obs,
            getattr(selected, "area", None),
            getattr(selected, "index", None),
            getattr(selected, "playerIndex", player_index),
        )
    elif selected_type in {"ATTACH", "EVOLVE"}:
        selected_card = get_card(
            obs,
            getattr(selected, "inPlayArea", None),
            getattr(selected, "inPlayIndex", None),
            player_index,
        )
    elif selected_type in {"ABILITY", "RETREAT"}:
        selected_card = get_card(
            obs,
            getattr(selected, "inPlayArea", None),
            getattr(selected, "inPlayIndex", None),
            player_index,
        )

    selected_cid = card_id(selected_card)
    active_cid = card_id(active)
    opponent_active_cid = card_id(opponent_active)
    return {
        "acting_agent": acting_agent,
        "turn": getattr(state, "turn", None),
        "player": player_index,
        "result": getattr(state, "result", None),
        "select_type": enum_name(getattr(select, "type", "")),
        "context": enum_name(getattr(select, "context", "")),
        "option_count": len(options),
        "selected_index": selected_index,
        "selected_type": selected_type,
        "selected_area": selected_area,
        "selected_in_play_area": selected_in_play_area,
        "selected_card_id": selected_cid,
        "selected_card_name": card_name(selected_cid),
        "attack_id": getattr(selected, "attackId", None),
        "active_card_id": active_cid,
        "active_card_name": card_name(active_cid),
        "opponent_active_card_id": opponent_active_cid,
        "opponent_active_card_name": card_name(opponent_active_cid),
        "hand_ids": zone_ids(player, "hand") if player is not None else "",
        "active_ids": zone_ids(player, "active") if player is not None else "",
        "bench_ids": zone_ids(player, "bench") if player is not None else "",
        "discard_ids": zone_ids(player, "discard") if player is not None else "",
        "opponent_active_ids": zone_ids(opponent, "active") if opponent is not None else "",
        "opponent_bench_ids": zone_ids(opponent, "bench") if opponent is not None else "",
        "my_prizes_left": len(safe_list(getattr(player, "prize", []))) if player is not None else None,
        "opponent_prizes_left": len(safe_list(getattr(opponent, "prize", []))) if opponent is not None else None,
    }


def run_game(
    agent0,
    agent1,
    deck0: list[int],
    deck1: list[int],
    agent_names: list[str],
    max_steps: int,
    game_id: int,
    writer,
) -> dict:
    from cg.api import to_observation_class
    from cg.game import battle_finish, battle_select, battle_start

    obs_dict, _ = battle_start(list(deck0), list(deck1))
    agents = [agent0, agent1]
    started = time.perf_counter()
    final = {"game": game_id, "result": None, "turns": 0, "steps": 0, "duration_s": 0.0}
    try:
        for step in range(max_steps):
            obs = to_observation_class(obs_dict)
            state = getattr(obs, "current", None)
            if state is not None and getattr(state, "result", -1) != -1:
                final.update(result=getattr(state, "result", None), turns=getattr(state, "turn", 0), steps=step)
                break
            if getattr(obs, "select", None) is None:
                final.update(result=getattr(state, "result", None) if state is not None else None, steps=step)
                break
            player = int(getattr(state, "yourIndex", 0) or 0)
            choice = agents[player].agent(obs_dict)
            row = selected_option_info(obs_dict, choice, agent_names[player])
            row.update(game=game_id, step=step)
            writer.writerow(row)
            obs_dict = battle_select(choice)
        else:
            final.update(result="max_steps", steps=max_steps)
    finally:
        final["duration_s"] = time.perf_counter() - started
        battle_finish()
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="Run official cg.game simulations on Kaggle or a local cg install.")
    parser.add_argument("--agent", default="agents/lucario")
    parser.add_argument("--opponent", default="first", help="Agent dir, 'first', or 'random'")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=800)
    parser.add_argument("--out-dir", default="outputs/simulations")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    try:
        import cg.api  # noqa: F401
        import cg.game  # noqa: F401
    except Exception as exc:
        raise SystemExit(
            "Official cg simulator is not importable here. Run this in a Kaggle notebook with the "
            "Simulation competition input, or package/copy sample_submission/cg first.\n"
            f"Import error: {exc}"
        )

    global CARD_NAMES
    CARD_NAMES = build_card_table()

    agent_dir = Path(args.agent)
    agent0 = load_agent(agent_dir)
    deck0 = load_deck_ids(agent_dir / "deck.csv")

    if args.opponent in {"first", "random"}:
        deck1 = list(deck0)
        agent1 = BuiltinAgent(args.opponent, deck1, seed=args.seed)
        opponent_name = args.opponent
    else:
        opponent_dir = Path(args.opponent)
        agent1 = load_agent(opponent_dir)
        deck1 = load_deck_ids(opponent_dir / "deck.csv")
        opponent_name = opponent_dir.name

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    decisions_path = out_dir / f"{agent_dir.name}_vs_{opponent_name}_decisions.csv"
    matches_path = out_dir / f"{agent_dir.name}_vs_{opponent_name}_matches.csv"

    fieldnames = [
        "game",
        "step",
        "acting_agent",
        "turn",
        "player",
        "result",
        "select_type",
        "context",
        "option_count",
        "selected_index",
        "selected_type",
        "selected_area",
        "selected_in_play_area",
        "selected_card_id",
        "selected_card_name",
        "attack_id",
        "active_card_id",
        "active_card_name",
        "opponent_active_card_id",
        "opponent_active_card_name",
        "hand_ids",
        "active_ids",
        "bench_ids",
        "discard_ids",
        "opponent_active_ids",
        "opponent_bench_ids",
        "my_prizes_left",
        "opponent_prizes_left",
    ]
    matches = []
    random.seed(args.seed)
    with decisions_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for game in range(args.games):
            if game % 2 == 0:
                final = run_game(
                    agent0,
                    agent1,
                    deck0,
                    deck1,
                    [agent_dir.name, opponent_name],
                    args.max_steps,
                    game,
                    writer,
                )
                agent_is_player = 0
            else:
                final = run_game(
                    agent1,
                    agent0,
                    deck1,
                    deck0,
                    [opponent_name, agent_dir.name],
                    args.max_steps,
                    game,
                    writer,
                )
                agent_is_player = 1
            result = final.get("result")
            matches.append(
                {
                    "game": game,
                    "agent": agent_dir.name,
                    "opponent": opponent_name,
                    "deck": agent_dir.name,
                    "agent_player": agent_is_player,
                    "result": result,
                    "win": int(result == agent_is_player),
                    "turns": final.get("turns", 0),
                    "steps": final.get("steps", 0),
                    "duration_s": final.get("duration_s", 0.0),
                }
            )

    import pandas as pd

    pd.DataFrame(matches).to_csv(matches_path, index=False)
    print(f"Wrote {matches_path}")
    print(f"Wrote {decisions_path}")


if __name__ == "__main__":
    main()
