# -*- coding: utf-8 -*-
"""cards.py — 핵심 지표 카드 (결정적 계산). v1.1: cluster 제거, opportunity 조건부."""

from __future__ import annotations
from .schemas import Agent3Data, Card
from .verdict import entry_verdict

RISK_COLORS = {"low": "#2e7d32", "mid": "#f9a825", "high": "#c62828"}


def _risk_color(r: float) -> str:
    return RISK_COLORS["low"] if r < 40 else \
           RISK_COLORS["mid"] if r < 70 else RISK_COLORS["high"]


def build_cards(main_country: str, a3: Agent3Data, target: str) -> list[Card]:
    risk = a3.risk_score.score
    risk_sub = f"경보 {a3.risk_score.level}단계 기준" if a3.risk_score.level else None
    coop = a3.cooperation_index

    cards: list[Card] = []
    if target == "기업":
        v = entry_verdict(a3)
        cards.append(Card(id="entry_verdict", label="진출 판정",
                          value=v["value"], confidence=v["confidence"],
                          grounds=v["grounds"]))
    cards += [
        Card(id="risk", label="위험도", value=round(risk, 1), max=100,
             color=_risk_color(risk), sub=risk_sub),
        Card(id="coop_grade" if target == "기업" else "coop_index",
             label="협력등급" if target == "기업" else "Cooperation Index",
             value=coop.grade if target == "기업" else round(coop.score, 1),
             max=5 if target == "기업" else None,
             sub=f"Cooperation Index {coop.score:.1f}" if target == "기업"
                 else f"{coop.grade}등급/5"),
    ]
    return cards
