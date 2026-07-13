# -*- coding: utf-8 -*-
"""verdict.py — 기업용 진출 판정 규칙 (LLM 아님 = Explainable). v1.1"""

from __future__ import annotations
from .schemas import Agent3Data

THRESHOLDS = {
    "recommend_risk_max": 40, "recommend_grade_min": 3,
    "avoid_risk_min": 70, "avoid_risk_soft": 55, "avoid_grade_max": 2,
}


def entry_verdict(a3: Agent3Data) -> dict:
    risk = a3.risk_score.score
    grade = a3.cooperation_index.grade
    t = THRESHOLDS

    grounds = [f"위험도 {risk:.1f}/100 ({_risk_label(risk)})",
               f"협력등급 {grade}/5 ({_grade_label(grade)})"]
    # 위험도 세부요인 (agent3 v2 components)
    if a3.risk_score.components:
        worst = max(a3.risk_score.components.items(), key=lambda x: x[1])
        grounds.append(f"주요 위험요인: {_comp_label(worst[0])} {worst[1]:.0f}점")

    if risk < t["recommend_risk_max"] and grade >= t["recommend_grade_min"]:
        value, margin = "추천", ((t["recommend_risk_max"] - risk)
                                / t["recommend_risk_max"]
                                + (grade - t["recommend_grade_min"]) / 5)
    elif risk > t["avoid_risk_min"] or \
            (risk > t["avoid_risk_soft"] and grade <= t["avoid_grade_max"]):
        value, margin = "비추천", (risk - t["avoid_risk_soft"]) / 45
    else:
        value, margin = "관망", 0.3

    return {"value": value,
            "confidence": round(min(0.95, max(0.5, 0.5 + margin * 0.4)), 2),
            "grounds": grounds}


def _risk_label(r): return "낮음" if r < 40 else "중간" if r < 70 else "높음"
def _grade_label(g): return "높음" if g >= 4 else "보통" if g == 3 else "낮음"
def _comp_label(k):
    return {"travel_advisory": "여행경보", "safety_notice_freq": "안전공지 빈도",
            "socio_indicator_risk": "사회지표", "political_keyword_risk": "정치 이슈 리스크"}.get(k, k)
