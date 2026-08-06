# -*- coding: utf-8 -*-
"""validator.py — 브리핑 사실 검증기.

"LLM은 문장만, 수치는 데이터만"을 프롬프트 요청이 아니라 코드 검증으로 증명한다.
LLM이 생성한 브리핑에서 수치를 추출해 입력 데이터에 실존하는지 대조하고,
근거 없는 수치를 unverified로 표시한다.

설계 원칙:
- 오탐(false positive) 최소화가 최우선. 일반 표현("5단계 중", "3개국")까지
  잡으면 검증 결과 자체를 신뢰할 수 없게 된다.
  → 지표 단위가 붙은 수치만 검사 대상으로 좁힌다(화이트리스트 방식).
- 반올림 허용. 원본 48.87 → 브리핑 "48.9" 또는 "49"는 정상 인용으로 간주.
"""

from __future__ import annotations
import re
from typing import Optional

from .schemas import (Agent1Data, Agent2Data, Agent3Data,
                      Briefing, Verification, NumericClaim)

# ── 검사 대상 수치 패턴 ────────────────────────────────────
# 지표 단위·문맥이 명확한 수치만 추출한다. 각 패턴은 (라벨, 정규식) 쌍.
# 캡처그룹 1이 수치.
CLAIM_PATTERNS: list[tuple[str, str]] = [
    # 위험도/협력지수 점수: "48.9점", "위험도 48.9", "협력지수 9.3"
    ("score", r"(?:위험도|협력지수|점수)\s*(?:는|가|은|이)?\s*(\d+(?:\.\d+)?)\s*점?"),
    ("score", r"(\d+(?:\.\d+)?)\s*점"),
    # 등급: "1등급", "3등급/5"
    ("grade", r"(\d+)\s*등급"),
    # 여행경보 단계: "2단계"
    ("alert_level", r"(\d)\s*단계"),
    # 금액: "79,400백만$", "2,100백만 달러", "8500만 달러"
    ("amount", r"([\d,]+(?:\.\d+)?)\s*(?:백만|만)?\s*(?:달러|\$|USD)"),
    # 교민 수: "156,000명", "15만 6천 명"
    ("count", r"([\d,]+)\s*명"),
    # 연도: "1992년 수교", "2024년"
    ("year", r"((?:19|20)\d{2})\s*년"),
    # 건수: "12건"
    ("count", r"([\d,]+)\s*건"),
    # 백분율: "28%"
    ("percent", r"(\d+(?:\.\d+)?)\s*%"),
]

# 검증 면제 수치 — 지표가 아니라 서식·구조를 가리키는 상수
EXEMPT_VALUES = {
    5.0,    # "5등급 중", "5단계 척도" 등 스케일 상한
    100.0,  # "100점 만점"
    0.0,
}


def _norm(v: float) -> float:
    return round(v, 4)


def _variants(v: float) -> set[float]:
    """원본 값 하나에서 허용되는 표기 변형 집합.
    48.87 → {48.87, 48.9, 49} / 79400 → {79400, 79.4(백만→십억 환산 표기)}
    """
    out = {_norm(v), _norm(round(v, 1)), _norm(float(round(v)))}
    # 내림 표기도 허용 (48.87 → 48)
    out.add(_norm(float(int(v))))
    # 큰 금액의 단위 축약 표기 (79400백만 → 794억/79.4십억)
    if abs(v) >= 1000:
        out.add(_norm(round(v / 1000, 1)))
        out.add(_norm(round(v / 10000, 1)))
    return out


def _collect_facts(countries: list[str],
                   agent1: dict[str, Agent1Data],
                   agent2: Optional[dict[str, Agent2Data]],
                   agent3: dict[str, Agent3Data]) -> set[float]:
    """입력 데이터에 실제로 존재하는 모든 수치의 허용 집합."""
    facts: set[float] = set(EXEMPT_VALUES)

    def add(v):
        if v is None:
            return
        try:
            facts.update(_variants(float(v)))
        except (TypeError, ValueError):
            return

    for c in countries:
        a3 = agent3.get(c)
        if a3:
            add(a3.risk_score.score)
            add(a3.risk_score.level)
            add(a3.risk_score.notice_count_used)
            for v in a3.risk_score.components.values():
                add(v)
            add(a3.cooperation_index.score)
            add(a3.cooperation_index.grade)
            for _, sim in a3.similar_countries:
                add(sim)
                # 유사도는 백분율로 인용될 수 있음 (0.825 → 82.5%)
                try:
                    add(float(sim) * 100)
                except (TypeError, ValueError):
                    pass

        a1 = agent1.get(c)
        if a1:
            if a1.travel_warning:
                add(a1.travel_warning.level)
            add(len(a1.recent_safety_notices))
            add(len(a1.recent_situations))
            for k, v in (a1.security_environment or {}).items():
                add(v)
            # 정세·공지의 날짜에서 연도 추출
            for s in a1.recent_situations:
                for m in re.finditer(r"(19|20)\d{2}", str(s.get("date", ""))):
                    add(int(m.group()))
            for n in a1.recent_safety_notices:
                for m in re.finditer(r"(19|20)\d{2}", str(n.date or "")):
                    add(int(m.group()))

        a2 = (agent2 or {}).get(c)
        if a2:
            add(a2.trade_volume_usd_million)
            add(a2.oda_cumulative_usd_million)
            add(a2.expat_count)
            add(a2.diplomatic_year)
            add(len(a2.korea_orgs))
            for year, amount in a2.oda_yearly.items():
                add(year)
                add(amount)
            # 수교 연차 (2026 - 1992 = 34년)도 정당한 파생 수치
            if a2.diplomatic_year:
                from datetime import datetime
                add(datetime.now().year - int(a2.diplomatic_year))

    return facts


def _extract_claims(briefing: Briefing) -> list[tuple[str, str, float, str]]:
    """브리핑 각 섹션에서 (섹션, 종류, 값, 원문맥) 추출."""
    claims = []
    seen: set[tuple[str, float]] = set()

    for section, text in briefing.model_dump().items():
        if not text:
            continue
        for kind, pattern in CLAIM_PATTERNS:
            for m in re.finditer(pattern, str(text)):
                raw = m.group(1).replace(",", "")
                try:
                    value = float(raw)
                except ValueError:
                    continue
                key = (section, _norm(value))
                if key in seen:      # 같은 섹션의 동일 수치는 1회만
                    continue
                seen.add(key)
                start = max(0, m.start() - 25)
                context = str(text)[start:m.end() + 15].replace("\n", " ")
                claims.append((section, kind, value, context.strip()))
    return claims


def verify_briefing(briefing: Briefing,
                    countries: list[str],
                    agent1: dict[str, Agent1Data],
                    agent2: Optional[dict[str, Agent2Data]],
                    agent3: dict[str, Agent3Data]) -> Verification:
    """브리핑의 수치를 입력 데이터와 대조해 검증 결과를 반환."""
    facts = _collect_facts(countries, agent1, agent2, agent3)
    claims = _extract_claims(briefing)

    unverified: list[NumericClaim] = []
    verified_count = 0

    for section, kind, value, context in claims:
        if _norm(value) in facts:
            verified_count += 1
        else:
            unverified.append(NumericClaim(
                section=section, kind=kind, value=value, context=context))

    checked = len(claims)
    rate = round(verified_count / checked, 3) if checked else 1.0

    return Verification(
        checked=checked,
        verified=verified_count,
        rate=rate,
        unverified=unverified,
        passed=(not unverified),
    )
