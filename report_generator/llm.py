# -*- coding: utf-8 -*-
"""llm.py — briefing 블록 생성 (LLM이 관여하는 유일한 지점).

기본: Claude (orchestrator 팀 결정과 통일). API 키 없거나 실패 시 규칙 기반 폴백
→ 키 없이도 전체 파이프라인 개발·테스트 가능.
"""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime

from .schemas import Briefing
from .prompts import SYSTEM, build_briefing_prompt

logger = logging.getLogger("agent4.llm")

MODEL = os.getenv("AGENT4_LLM_MODEL", "claude-sonnet-4-6")


def generate_briefing(user_query: str, target: str, countries: list[str],
                      agent1, agent2, agent3) -> tuple[Briefing, str]:
    """반환: (Briefing, 사용된 모델명)"""
    prompt = build_briefing_prompt(user_query, target, countries,
                                   agent1, agent2, agent3)
    try:
        import anthropic
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수
        resp = client.messages.create(
            model=MODEL, max_tokens=3000, system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return Briefing(**json.loads(text.strip())), MODEL
    except Exception as e:
        logger.warning(f"LLM 호출 실패 → 폴백 사용: {e}")
        return _fallback(countries, agent3), "rule-based-fallback"


def _fallback(countries: list[str], agent3) -> Briefing:
    """규칙 기반 폴백 — 데이터 수치로 최소한의 문장 조립."""
    main = countries[0]
    a3 = agent3[main]
    return Briefing(
        executive_summary=(
            f"{main}의 위험도는 {a3.risk_score.score:.1f}/100, "
            f"협력지수는 {a3.cooperation_index.score:.1f}"
            f"({a3.cooperation_index.grade}등급)입니다. "
            f"(LLM 연결 시 상세 브리핑으로 대체됩니다)"),
        situation_analysis="상세 정세 분석은 LLM 연동 후 제공됩니다.",
        risk_analysis=f"정량 위험도 {a3.risk_score.score:.1f}점 — 대시보드 지표를 참고하십시오.",
        opportunity_analysis="ODA 및 무역 데이터를 바탕으로 협력 기회를 검토하십시오.",
        recommendation="카드의 진출 판정(규칙 기반)을 참고하십시오.",
    )
