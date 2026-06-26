from __future__ import annotations


DECK_VARIANTS: dict[str, dict[int, int]] = {
    "lucario_resilient": {
        678: 4,  # Mega Lucario ex
        677: 4,  # Riolu
        674: 2,  # Hariyama
        673: 2,  # Makuhita
        675: 2,  # Lunatone
        676: 3,  # Solrock
        1159: 1,  # Hero's Cape
        1182: 2,  # Boss's Orders
        1192: 4,  # Carmine
        1227: 4,  # Lillie's Determination
        1102: 4,  # Dusk Ball
        1141: 4,  # Premium Power Pro
        1142: 4,  # Fighting Gong
        1152: 4,  # Poke Pad
        1123: 2,  # Switch
        1252: 2,  # Gravity Mountain
        6: 12,  # Basic Fighting Energy
    },
    "lucario_anti_wall": {
        678: 3,
        677: 4,
        674: 3,
        673: 3,
        675: 2,
        676: 3,
        681: 2,  # Marshadow
        1159: 1,
        1182: 3,
        1192: 4,
        1227: 4,
        1102: 4,
        1141: 3,
        1142: 4,
        1152: 2,
        1123: 2,
        1252: 2,
        6: 11,
    },
    "lucario_consistency": {
        678: 4,
        677: 4,
        674: 2,
        673: 2,
        675: 3,
        676: 3,
        681: 2,
        1159: 1,
        1182: 2,
        1192: 4,
        1227: 4,
        1102: 4,
        1141: 3,
        1142: 4,
        1152: 3,
        1123: 2,
        1252: 2,
        6: 11,
    },
    "lucario_power": {
        678: 4,
        677: 4,
        674: 2,
        673: 2,
        675: 2,
        676: 2,
        681: 1,
        1159: 1,
        1182: 3,
        1192: 4,
        1227: 4,
        1102: 3,
        1141: 4,
        1142: 4,
        1152: 3,
        1123: 2,
        1252: 2,
        6: 13,
    },
}


def expanded_deck(deck_counts: dict[int, int]) -> list[int]:
    deck: list[int] = []
    for card_id, count in deck_counts.items():
        deck.extend([card_id] * count)
    if len(deck) != 60:
        raise ValueError(f"Deck has {len(deck)} cards, expected 60")
    return deck
