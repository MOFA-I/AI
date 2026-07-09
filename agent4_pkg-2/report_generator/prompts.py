# -*- coding: utf-8 -*-
"""prompts.py — 타깃별 브리핑 프롬프트 템플릿.

프롬프트 튜닝은 이 파일에서만. (llm.py는 호출 로직만)
"""

from __future__ import annotations
import json
from typing import Optional

from .schemas import Agent1Data, Agent2Data, Agent3Data

SYSTEM = (
    "너는 한국 외교부·KOICA 공공데이터 기반의 외교 인텔리전스 분석가다. "
    "반드시 제공된 수치만 인용하고, 데이터에 없는 사실은 추측하지 마라. "
    "출력은 지정된 JSON 형식만. 다른 텍스트 금지."
)

TARGET_GUIDE = {
    "기업": {
        "tone": "전문적·실용적. 의사결정에 바로 쓸 수 있게.",
        "focus": "진출 리스크, 유망 협력 분야, 경쟁·대안 국가 비교, 진출 판정 근거 해설",
        "length": "섹션당 2~4문장",
        "extra_fields": "",
    },
    "연구자": {
        "tone": "학술적·객관적. 수치와 출처 중심.",
        "focus": "외교 패턴, ODA 트렌드, 유사국가 비교의 함의, 정책 시사점",
        "length": "섹션당 3~5문장",
        "extra_fields": ',\n  "korea_perspective": "...", "counterpart_perspective": "..."',
    },
}


def _summarize_inputs(countries, agent1, agent2, agent3) -> str:
    lines = []
    for c in countries:
        a3: Agent3Data = agent3[c]
        line = (f"[{c}] 위험도 {a3.risk_score.score:.1f}/100, "
                f"협력지수 {a3.cooperation_index.score:.1f} "
                f"({a3.cooperation_index.grade}등급/5)")
        if a3.risk_score.components:
            comp = ", ".join(f"{k} {v:.0f}" for k, v in a3.risk_score.components.items())
            line += f" [위험요인: {comp}]"
        if a3.opportunity_meaningful:
            top3 = a3.opportunity_ranking[:3]
            line += f", 유망분야 {', '.join(f'{f}({s})' for f, s in top3)}"
        if a3.similar_countries:
            line += f", 유사국가 {', '.join(n for n, _ in a3.similar_countries[:3])}"
        a1: Optional[Agent1Data] = agent1.get(c)
        if a1:
            tw = a1.travel_warning
            if tw and tw.level:
                line += f", 여행경보 {tw.level}단계 {tw.label or ''}" \
                        + ("(일부지역)" if tw.partial else "")
            if a1.recent_situations:
                ev = "; ".join(f"{s.get('date')}: {s.get('event')}"
                               for s in a1.recent_situations[:3])
                line += f"\n  최근정세: {ev}"
        a2: Optional[Agent2Data] = (agent2 or {}).get(c)
        if a2:
            if a2.trade_volume_usd_million:
                line += f"\n  교역액 {a2.trade_volume_usd_million:,.0f}백만$"
            if a2.oda_projects:
                line += f", KOICA 사업 {len(a2.oda_projects)}건"
            if a2.sources_failed:
                line += f" (일부 소스 장애→대체자료 사용: {', '.join(a2.sources_failed)})"
            if a2.oda_cumulative_usd_million:
                line += f", ODA누적 {a2.oda_cumulative_usd_million:,.0f}백만$"
            if a2.diplomatic_year:
                line += f", 수교 {a2.diplomatic_year}년"
        lines.append(line)
    return "\n".join(lines)


def build_briefing_prompt(user_query: str, target: str, countries: list[str],
                          agent1, agent2, agent3) -> str:
    g = TARGET_GUIDE[target]
    data = _summarize_inputs(countries, agent1, agent2, agent3)

    return f"""[사용자 질문]
{user_query or "국가 분석 요청"}

[타깃] {target} — 톤: {g['tone']} / 초점: {g['focus']} / 분량: {g['length']}

[정량 데이터 (전 Agent 산출)]
{data}

[지표 정의]
- 위험도(0~100): 여행경보 40% + 안전공지 빈도 30% + 정세키워드 30%
- Cooperation Index: 무역 30% + ODA 30% + 교민 20% + 수교연도 20% → 5등급
- 분야별 점수: KOICA ODA 분야별 빈도 기반 (분야 데이터 제공 시에만 유효)

[출력 — 아래 JSON만, 수치는 위 데이터 그대로 인용]
{{
  "executive_summary": "핵심 3줄",
  "situation_analysis": "...",
  "risk_analysis": "...",
  "opportunity_analysis": "...",
  "recommendation": "..."{g['extra_fields']}
}}"""
