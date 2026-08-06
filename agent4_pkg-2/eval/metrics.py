# -*- coding: utf-8 -*-
"""metrics.py — 브리핑 자동 평가 지표.

LLM 없이 계산 가능한 결정적 지표만 사용한다(재현성 확보).
LLM-as-judge는 이 자동 지표가 안정된 뒤에 추가할 것.
"""

from __future__ import annotations
import re

from report_generator.schemas import Briefing, Verification

# 타깃별 필수 섹션
REQUIRED_SECTIONS = ["executive_summary", "situation_analysis",
                     "risk_analysis", "opportunity_analysis", "recommendation"]
RESEARCHER_EXTRA = ["korea_perspective", "counterpart_perspective"]

# 타깃별 기대 어휘 — 초점이 실제로 반영됐는지 대리 측정
TARGET_KEYWORDS = {
    "기업": ["진출", "리스크", "위험", "기회", "협력", "교역", "판정", "권고"],
    "연구자": ["정책", "협력", "추이", "패턴", "시사", "분석", "지표", "비교"],
}

# 타깃별 권장 분량(문장 수) — prompts.py의 length 지침과 대응
SENTENCE_RANGE = {"기업": (2, 5), "연구자": (3, 7)}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?]\s+|\n+", str(text or ""))
    return [p for p in parts if len(p.strip()) > 5]


def evaluate(briefing: Briefing, target: str, verification: Verification,
             forbidden: list[str] | None = None) -> dict:
    """브리핑 하나를 평가해 지표 dict 반환. 모든 점수는 0~1."""
    data = briefing.model_dump()
    forbidden = forbidden or []

    # 1. 섹션 완성도 — 필수 섹션이 비어있지 않은 비율
    required = REQUIRED_SECTIONS + (
        RESEARCHER_EXTRA if target == "연구자" else [])
    filled = [s for s in required if str(data.get(s) or "").strip()]
    section_score = len(filled) / len(required)
    missing = [s for s in required if s not in filled]

    # 2. 수치 인용 정확도 — validator 결과 재사용
    accuracy = verification.rate

    # 3. 수치 인용 밀도 — 데이터 기반 서술인지 (섹션당 1건 이상이 목표)
    density = min(1.0, verification.checked / max(1, len(filled)))

    # 4. 분량 준수 — 섹션별 문장 수가 권장 범위에 드는 비율
    lo, hi = SENTENCE_RANGE.get(target, (2, 6))
    in_range = 0
    for s in filled:
        n = len(_sentences(data[s]))
        if lo <= n <= hi:
            in_range += 1
    length_score = in_range / len(filled) if filled else 0.0

    # 5. 타깃 적합도 — 기대 어휘 등장 비율
    full_text = " ".join(str(data.get(s) or "") for s in required)
    kws = TARGET_KEYWORDS.get(target, [])
    hit = [k for k in kws if k in full_text]
    target_fit = len(hit) / len(kws) if kws else 1.0

    # 6. 금지어 위반 — 데이터 없는 항목을 언급했는지 (위반 시 0)
    violations = [w for w in forbidden if w in full_text]
    forbidden_score = 0.0 if violations else 1.0

    # 종합 — 정확도와 금지어에 가중(신뢰성 우선 원칙 반영)
    overall = (accuracy * 0.35 + forbidden_score * 0.2 + section_score * 0.2
               + length_score * 0.1 + target_fit * 0.1 + density * 0.05)

    return {
        "overall": round(overall, 3),
        "accuracy": round(accuracy, 3),
        "sections": round(section_score, 3),
        "length": round(length_score, 3),
        "target_fit": round(target_fit, 3),
        "density": round(density, 3),
        "forbidden_ok": forbidden_score == 1.0,
        "missing_sections": missing,
        "violations": violations,
        "unverified_count": len(verification.unverified),
    }
