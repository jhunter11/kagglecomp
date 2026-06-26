from __future__ import annotations

from collections import Counter
from pathlib import Path


DECK = [
    678, 678, 678, 678,
    677, 677, 677, 677,
    674, 674,
    673, 673,
    675, 675,
    676, 676, 676,
    1159,
    1182, 1182,
    1192, 1192, 1192, 1192,
    1227, 1227, 1227, 1227,
    1102, 1102, 1102, 1102,
    1141, 1141, 1141, 1141,
    1142, 1142, 1142, 1142,
    1152, 1152, 1152, 1152,
    1123, 1123,
    1252, 1252,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
]
assert len(DECK) == 60


RIOLU = 677
MAKUHITA = 673
HARIYAMA = 674
LUNATONE = 675
SOLROCK = 676
MEGA_LUCARIO_EX = 678
FIGHTING_ENERGY = 6
HERO_CAPE = 1159
BOSS_ORDERS = 1182
CARMINE = 1192
LILLIE = 1227
DUSK_BALL = 1102
PREMIUM_POWER_PRO = 1141
FIGHTING_GONG = 1142
POKE_PAD = 1152
SWITCH = 1123
GRAVITY_MOUNTAIN = 1252

KEY_ATTACKERS = {MEGA_LUCARIO_EX, HARIYAMA, SOLROCK}
KEY_BASICS = {RIOLU, MAKUHITA, LUNATONE, SOLROCK}
SEARCH_AND_DRAW = {CARMINE, LILLIE, DUSK_BALL, FIGHTING_GONG, POKE_PAD}


try:
    from cg.api import all_attack, all_card_data, to_observation_class
except Exception:
    def all_card_data():
        return []

    def all_attack():
        return []

    class _MockObservation:
        def __init__(self, select=None):
            self.select = select
            self.current = None
            self.logs = []

    class _MockSelect:
        def __init__(self, options):
            self.option = options
            self.maxCount = 1
            self.minCount = 1
            self.context = ""
            self.type = "MAIN"

    class _MockOption:
        def __init__(self, option_type):
            self.type = option_type

    def to_observation_class(obs_dict):
        if not obs_dict or "select" not in obs_dict:
            return _MockObservation()
        select = obs_dict["select"]
        options = [_MockOption(value) for value in select.get("option", [])]
        mock_select = _MockSelect(options)
        mock_select.maxCount = select.get("maxCount", 1)
        mock_select.minCount = select.get("minCount", 1)
        mock_select.context = select.get("context", "")
        mock_select.type = select.get("type", "MAIN")
        return _MockObservation(mock_select)


CARD_TABLE = {getattr(card, "cardId", getattr(card, "id", None)): card for card in all_card_data()}
CARD_TABLE = {card_id: card for card_id, card in CARD_TABLE.items() if card_id is not None}
ATTACK_TABLE = {getattr(attack, "attackId", None): attack for attack in all_attack()}
ATTACK_TABLE = {attack_id: attack for attack_id, attack in ATTACK_TABLE.items() if attack_id is not None}


def _deck_from_file() -> list[int]:
    for path in [Path("deck.csv"), Path("/kaggle_simulations/agent/deck.csv")]:
        if path.exists():
            ids = []
            for line in path.read_text().splitlines():
                line = line.strip()
                if line and line.isdigit():
                    ids.append(int(line))
            if len(ids) == 60:
                return ids
    return list(DECK)


def enum_name(value) -> str:
    if value is None:
        return ""
    return str(getattr(value, "name", value)).split(".")[-1]


def card_id(card) -> int | None:
    return getattr(card, "id", getattr(card, "cardId", None))


def safe_list(value) -> list:
    return list(value) if value else []


def get_player(state, index):
    players = safe_list(getattr(state, "players", []))
    if 0 <= index < len(players):
        return players[index]
    return None


def get_card(obs, area, index, player_index):
    state = getattr(obs, "current", None)
    if state is None or index is None:
        return None

    area_name = enum_name(area)
    player = get_player(state, player_index)
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


def in_play_cards(player) -> list:
    if player is None:
        return []
    return [card for card in safe_list(getattr(player, "active", [])) + safe_list(getattr(player, "bench", [])) if card]


def energies(card) -> list:
    return safe_list(getattr(card, "energies", []))


def hp_left(card) -> int:
    return int(getattr(card, "hp", getattr(card, "maxHp", 0)) or 0)


def card_data(card_or_id):
    cid = card_or_id if isinstance(card_or_id, int) else card_id(card_or_id)
    return CARD_TABLE.get(cid)


def prize_value(pokemon) -> int:
    data = card_data(pokemon)
    if data is None:
        return 1
    if bool(getattr(data, "megaEx", False)):
        return 3
    if bool(getattr(data, "ex", False)):
        return 2
    return 1


def effective_damage(base_damage: int, target) -> int:
    data = card_data(target)
    damage = int(base_damage or 0)
    if data is not None:
        weakness = enum_name(getattr(data, "weakness", ""))
        resistance = enum_name(getattr(data, "resistance", ""))
        if weakness == "FIGHTING":
            damage *= 2
        elif resistance == "FIGHTING":
            damage -= 30
    return max(0, damage)


def target_score(pokemon) -> int:
    if pokemon is None or hp_left(pokemon) <= 0:
        return 0
    data = card_data(pokemon)
    score = 1000 * prize_value(pokemon)
    score += 150 * len(energies(pokemon))
    score += max(0, 360 - hp_left(pokemon))
    if data is not None:
        if bool(getattr(data, "stage2", False)):
            score += 250
        elif bool(getattr(data, "stage1", False)):
            score += 130
        if enum_name(getattr(data, "weakness", "")) == "FIGHTING":
            score += 350
    return score


def attach_target_score(card, active_card=None) -> int:
    cid = card_id(card)
    score = 0
    if cid == MEGA_LUCARIO_EX:
        score += 1600
    elif cid == RIOLU:
        score += 1000
    elif cid == HARIYAMA:
        score += 850
    elif cid == MAKUHITA:
        score += 650
    elif cid == SOLROCK:
        score += 450 if len(energies(card)) == 0 else 50
    elif cid == LUNATONE:
        score -= 200
    else:
        score += 100
    if active_card is not None and card is active_card:
        score += 400
    if len(energies(card)) >= 3:
        score -= 600
    return score


def hand_and_field_counts(player) -> tuple[Counter, Counter]:
    hand_counts = Counter(card_id(card) for card in safe_list(getattr(player, "hand", [])))
    field_counts = Counter(card_id(card) for card in in_play_cards(player))
    return hand_counts, field_counts


def score_card_choice(card, context: str, my_player, op_player, active_card) -> int:
    cid = card_id(card)
    if cid is None:
        return 0

    hand_counts, field_counts = hand_and_field_counts(my_player)
    if context == "SETUP_ACTIVE_POKEMON":
        if cid == RIOLU:
            return 1000
        if cid == MAKUHITA:
            return 550
        if cid == SOLROCK:
            return 500
        if cid == LUNATONE:
            return 450
        return 50

    if context == "SETUP_BENCH_POKEMON":
        if cid in KEY_BASICS:
            return 900 - 120 * field_counts[cid]
        return 80

    if context in {"DAMAGE", "DAMAGE_COUNTER", "DAMAGE_COUNTER_ANY"}:
        return target_score(card)

    if context in {"TO_ACTIVE", "SWITCH"}:
        return attach_target_score(card, active_card) + hp_left(card)

    if context in {"ATTACH_FROM", "ATTACH_TO"}:
        return attach_target_score(card, active_card)

    if context == "TO_HAND":
        priority = {
            MEGA_LUCARIO_EX: 1400,
            RIOLU: 1200,
            FIGHTING_ENERGY: 950,
            FIGHTING_GONG: 900,
            DUSK_BALL: 850,
            BOSS_ORDERS: 825,
            HARIYAMA: 760,
            MAKUHITA: 725,
            CARMINE: 700,
            LILLIE: 680,
            HERO_CAPE: 620,
            GRAVITY_MOUNTAIN: 550,
        }
        score = priority.get(cid, 100)
        if cid == MEGA_LUCARIO_EX and field_counts[RIOLU] == 0:
            score -= 550
        if cid == RIOLU and field_counts[RIOLU] >= 2:
            score -= 350
        if cid == FIGHTING_ENERGY and hand_counts[FIGHTING_ENERGY] >= 3:
            score -= 250
        return score

    if context == "DISCARD":
        if cid == FIGHTING_ENERGY:
            return 800
        if hand_counts[cid] > 1 and cid not in {MEGA_LUCARIO_EX, RIOLU}:
            return 500
        if cid in {LUNATONE, SOLROCK} and field_counts[cid] > 0:
            return 420
        if cid in KEY_ATTACKERS or cid in KEY_BASICS:
            return -500
        return 100

    if context == "HEAL":
        return max(0, 400 - hp_left(card))

    return 20


def score_play_option(card, my_player, active_card) -> int:
    cid = card_id(card)
    if cid is None:
        return 0
    hand_counts, field_counts = hand_and_field_counts(my_player)

    if cid == RIOLU:
        return 3600 if field_counts[RIOLU] < 2 else 900
    if cid == MAKUHITA:
        return 2400 if field_counts[MAKUHITA] < 1 else 500
    if cid in {LUNATONE, SOLROCK}:
        pair_id = SOLROCK if cid == LUNATONE else LUNATONE
        return 2300 + (500 if field_counts[pair_id] else 0)
    if cid == MEGA_LUCARIO_EX:
        return 3200
    if cid == HARIYAMA:
        return 2500
    if cid == FIGHTING_ENERGY:
        return 50
    if cid == BOSS_ORDERS:
        return 2600
    if cid in {CARMINE, LILLIE}:
        return 2300
    if cid in {DUSK_BALL, FIGHTING_GONG, POKE_PAD}:
        return 2200
    if cid == PREMIUM_POWER_PRO:
        return 2100 if active_card and card_id(active_card) in KEY_ATTACKERS else 900
    if cid == HERO_CAPE:
        return 1800 if active_card and card_id(active_card) == MEGA_LUCARIO_EX else 700
    if cid == SWITCH:
        return 850
    if cid == GRAVITY_MOUNTAIN:
        return 1200
    return 300


def score_attack(option, my_active, op_active, op_prizes_left: int) -> int:
    if my_active is None or op_active is None:
        return 0
    score = 1800 + target_score(op_active)
    attack = ATTACK_TABLE.get(getattr(option, "attackId", None))
    damage = effective_damage(getattr(attack, "damage", 0), op_active) if attack is not None else 0
    if damage <= 0:
        cid = card_id(my_active)
        damage = 270 if cid == MEGA_LUCARIO_EX else 210 if cid == HARIYAMA else 70 if cid == SOLROCK else 30
    if damage >= hp_left(op_active):
        score += 8000
        if prize_value(op_active) >= op_prizes_left:
            score += 50000
    else:
        score += min(damage, 500)
    if hp_left(my_active) <= 60:
        score += 500
    return score


def fallback_selection(obs_dict):
    try:
        obs = to_observation_class(obs_dict)
        select = getattr(obs, "select", None)
        if select is None:
            return _deck_from_file()
        options = safe_list(getattr(select, "option", []))
        max_count = max(1, int(getattr(select, "maxCount", 1) or 1))
        return list(range(min(max_count, len(options)))) or [0]
    except Exception:
        return _deck_from_file() if obs_dict is None else [0]


def agent(obs_dict):
    try:
        return _agent(obs_dict)
    except Exception:
        return fallback_selection(obs_dict)


def _agent(obs_dict):
    obs = to_observation_class(obs_dict)
    select = getattr(obs, "select", None)
    if select is None:
        return _deck_from_file()

    state = getattr(obs, "current", None)
    my_index = int(getattr(state, "yourIndex", 0) or 0) if state is not None else 0
    my_player = get_player(state, my_index) if state is not None else None
    op_player = get_player(state, 1 - my_index) if state is not None else None
    my_active = safe_list(getattr(my_player, "active", []))[0] if my_player and safe_list(getattr(my_player, "active", [])) else None
    op_active = safe_list(getattr(op_player, "active", []))[0] if op_player and safe_list(getattr(op_player, "active", [])) else None
    op_prizes_left = len(safe_list(getattr(op_player, "prize", []))) or 6

    options = safe_list(getattr(select, "option", []))
    context = enum_name(getattr(select, "context", ""))
    scores = []

    for option in options:
        option_type = enum_name(getattr(option, "type", ""))
        score = 0

        if option_type == "NUMBER":
            score = int(getattr(option, "number", 0) or 0)
        elif option_type == "YES":
            score = 100
        elif option_type == "NO":
            score = -20
        elif option_type == "CARD":
            card = get_card(
                obs,
                getattr(option, "area", None),
                getattr(option, "index", None),
                int(getattr(option, "playerIndex", my_index) or my_index),
            )
            score = score_card_choice(card, context, my_player, op_player, my_active)
        elif option_type == "PLAY":
            card = get_card(obs, "HAND", getattr(option, "index", None), my_index)
            score = score_play_option(card, my_player, my_active)
        elif option_type == "ATTACH":
            target = get_card(
                obs,
                getattr(option, "inPlayArea", None),
                getattr(option, "inPlayIndex", None),
                my_index,
            )
            score = 1200 + attach_target_score(target, my_active)
        elif option_type == "EVOLVE":
            target = get_card(
                obs,
                getattr(option, "inPlayArea", None),
                getattr(option, "inPlayIndex", None),
                my_index,
            )
            score = 2800 + attach_target_score(target, my_active)
        elif option_type == "ABILITY":
            score = 1600
        elif option_type == "RETREAT":
            score = 650 if my_active and hp_left(my_active) <= 60 else -250
        elif option_type == "ATTACK":
            score = score_attack(option, my_active, op_active, op_prizes_left)
        elif option_type == "END":
            score = -100
        else:
            score = 0

        scores.append(score)

    ranked = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
    max_count = max(1, int(getattr(select, "maxCount", 1) or 1))
    return ranked[:max_count] or [0]
