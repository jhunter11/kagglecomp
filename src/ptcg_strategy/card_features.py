from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


CANONICAL_COLUMNS = [
    "card_id",
    "card_name",
    "expansion",
    "collection_no",
    "stage_type",
    "rule",
    "category",
    "previous_stage",
    "hp",
    "type",
    "weakness",
    "resistance",
    "retreat",
    "move_name",
    "cost",
    "damage",
    "effect",
]


def load_card_data(path: str | Path) -> pd.DataFrame:
    """Load EN or JP card CSV data and normalize to stable column names."""
    df = pd.read_csv(path)
    if len(df.columns) < len(CANONICAL_COLUMNS):
        raise ValueError(f"Expected at least {len(CANONICAL_COLUMNS)} columns in {path}")

    rename = {old: new for old, new in zip(df.columns[: len(CANONICAL_COLUMNS)], CANONICAL_COLUMNS)}
    df = df.rename(columns=rename)
    df = df[CANONICAL_COLUMNS].copy()

    for col in df.select_dtypes(include="object").columns:
        df[col] = (
            df[col]
            .astype("string")
            .str.strip()
            .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "n/a": pd.NA})
        )

    for col in ["card_id", "collection_no"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["hp", "retreat"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def parse_damage(value: object) -> tuple[float, str]:
    """Parse a printed damage field into a numeric base and a coarse kind."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return np.nan, "none"

    text = str(value).strip()
    if not text:
        return np.nan, "none"

    numbers = re.findall(r"\d+", text)
    if not numbers:
        return np.nan, "text"

    amount = float(numbers[0])
    if "\u00d7" in text or "x" in text.lower():
        kind = "multiplier"
    elif "+" in text:
        kind = "bonus"
    elif "-" in text:
        kind = "conditional"
    else:
        kind = "static"
    return amount, kind


def parse_energy_cost(value: object) -> tuple[int, int, int]:
    """Return total, typed, and colorless energy symbols from an attack cost."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return 0, 0, 0

    text = str(value).strip()
    if not text or text.lower() in {"no cost", "nan"}:
        return 0, 0, 0

    typed = text.count("{")
    colorless = text.count("\u25cf")
    return typed + colorless, typed, colorless


def add_attack_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add parsed attack damage, cost, and efficiency fields."""
    out = df.copy()

    parsed_damage = out["damage"].map(parse_damage)
    out["parsed_damage"] = [x[0] for x in parsed_damage]
    out["damage_kind"] = [x[1] for x in parsed_damage]

    parsed_cost = out["cost"].map(parse_energy_cost)
    out["energy_cost"] = [x[0] for x in parsed_cost]
    out["typed_energy_cost"] = [x[1] for x in parsed_cost]
    out["colorless_energy_cost"] = [x[2] for x in parsed_cost]

    out["damage_per_energy"] = np.where(
        out["energy_cost"] > 0,
        out["parsed_damage"] / out["energy_cost"],
        np.nan,
    )
    return out


def _contains(series: pd.Series, pattern: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(pattern, case=False, regex=True, na=False)


def _join_text(values: Iterable[object]) -> str:
    return " ".join(str(v) for v in values if pd.notna(v))


def card_level_features(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse move-level card rows into one feature row per card."""
    attacks = add_attack_features(df)

    grouped = attacks.groupby("card_id", dropna=False)
    base = grouped.agg(
        card_name=("card_name", "first"),
        expansion=("expansion", "first"),
        collection_no=("collection_no", "first"),
        stage_type=("stage_type", "first"),
        rule=("rule", "first"),
        category=("category", "first"),
        previous_stage=("previous_stage", "first"),
        hp=("hp", "max"),
        type=("type", "first"),
        weakness=("weakness", "first"),
        resistance=("resistance", "first"),
        retreat=("retreat", "max"),
        attack_count=("move_name", lambda s: int(s.notna().sum())),
        max_damage=("parsed_damage", "max"),
        mean_damage=("parsed_damage", "mean"),
        max_damage_per_energy=("damage_per_energy", "max"),
        min_attack_cost=("energy_cost", lambda s: int(s[s > 0].min()) if (s > 0).any() else 0),
        text=("effect", _join_text),
        move_text=("move_name", _join_text),
    ).reset_index()

    stage = base["stage_type"].fillna("").astype(str)
    rule = base["rule"].fillna("").astype(str)
    text = (base["text"].fillna("") + " " + rule + " " + base["card_name"].fillna("")).astype(str)

    base["is_pokemon"] = _contains(stage, r"Pok.mon|Pokemon|\u30dd\u30b1\u30e2\u30f3")
    base["is_basic"] = _contains(stage, r"Basic|\u305f\u306d")
    base["is_stage1"] = _contains(stage, r"Stage 1|1\u9032\u5316")
    base["is_stage2"] = _contains(stage, r"Stage 2|2\u9032\u5316")
    base["is_trainer"] = _contains(stage, r"Item|Supporter|Stadium|Tool")
    base["is_energy"] = _contains(stage, r"Energy|\u30a8\u30cd\u30eb\u30ae\u30fc")
    base["is_ex"] = _contains(rule, r"\bex\b")
    base["is_mega_ex"] = _contains(rule + " " + base["card_name"].fillna(""), r"Mega")
    base["is_ace_spec"] = _contains(rule, r"ACE SPEC")
    base["has_draw"] = _contains(text, r"\bdraw\b|shuffle your hand")
    base["has_search"] = _contains(text, r"search your deck|look at the bottom|put .* into your hand")
    base["has_gust"] = _contains(text, r"opponent.*Bench.*Active|switch in 1 of your opponent")
    base["has_energy_accel"] = _contains(text, r"attach .*Energy|Energy .*discard|discard.*Energy")
    base["has_damage_boost"] = _contains(text, r"do \d+ more damage|\+\d+ damage|damage to your opponent")

    for col in ["hp", "retreat", "max_damage", "mean_damage", "max_damage_per_energy"]:
        base[col] = base[col].fillna(0)

    return base.sort_values("card_id").reset_index(drop=True)
