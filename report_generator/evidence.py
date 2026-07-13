# -*- coding: utf-8 -*-
"""evidence.py — 전 Agent 작업 로그. v1.1: Agent2 sources_used/failed 투명 노출."""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from .schemas import Agent2Data, Agent3Data, EvidenceEntry

_SRC_LABEL = {
    "relation": "외교관계 API",
    "trade": "무역관계 API",
    "koica_country_support_cumulative": "KOICA ODA 누적지원",
    "koica_country_support_yearly": "KOICA ODA 연도별",
    "overseas_org": "해외진출현황 CSV",
}


def build_evidence(input_logs: list[dict], countries: list[str],
                   agent2: Optional[dict[str, Agent2Data]],
                   agent3: dict[str, Agent3Data],
                   llm_model: str) -> list[EvidenceEntry]:
    now = datetime.now().isoformat(timespec="seconds")
    entries = [EvidenceEntry(**{"at": now, **log}) for log in input_logs]

    if not entries:
        entries.append(EvidenceEntry(
            agent="Agent 1 · Issue Analyzer",
            source="외교부 여행경보·안전정보·치안환경·주요정세·비자 API",
            action=f"{', '.join(countries)} 현황 조회", at=now))

    # Agent 2: 소스별 성공/실패/대체 투명 기록
    if agent2:
        for c, a2 in agent2.items():
            used = [_SRC_LABEL.get(s, s) for s in a2.sources_used]
            failed = [_SRC_LABEL.get(s, s) for s in a2.sources_failed]
            action = f"[{c}] 수집: {', '.join(used) or '없음'}"
            if failed:
                action += f" / 실패→대체: {', '.join(failed)}"
            if a2.sources_empty:
                action += f" / 해당없음: {', '.join(a2.sources_empty)}"
            entries.append(EvidenceEntry(
                agent="Agent 2 · Intelligence Collector",
                source="외교부 관계·무역 API + KOICA·해외진출 CSV",
                action=action, at=now))

    # Agent 3: data_sources 패스스루 활용
    main = countries[0]
    ds = agent3.get(main, Agent3Data(risk_score={"score": 0},
                                     cooperation_index={"score": 0, "grade": 1})
                    ).data_sources
    entries.append(EvidenceEntry(
        agent="Agent 3 · Insight Generator",
        source="pandas + scikit-learn",
        action=ds.get("risk_score", "위험도·협력지수·유사국가 산출"), at=now))

    entries.append(EvidenceEntry(
        agent="Agent 4 · Report Generator", source=llm_model,
        action="타깃별 브리핑 생성 · 지도/차트는 결정적 계산(LLM 미개입)", at=now))
    return entries
