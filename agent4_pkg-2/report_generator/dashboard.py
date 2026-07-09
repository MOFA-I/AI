# -*- coding: utf-8 -*-
"""dashboard.py — dashboard.charts 블록. v1.1

변경: oda_trend는 지원실적 CSV의 실데이터(oda_yearly, 총액만) 사용.
     opportunity_ranking은 분야 데이터 유의미할 때만.
     risk_components(위험도 세부요인) 신설 — agent3 v2 components 활용.
"""

from __future__ import annotations
from typing import Optional

from .schemas import Agent1Data, Agent2Data, Agent3Data, Chart

_COMP_LABEL = {"travel_advisory": "여행경보", "safety_notice_freq": "안전공지 빈도",
               "socio_indicator_risk": "사회지표"}


def build_dashboard(countries: list[str],
                    agent1: dict[str, Agent1Data],
                    agent2: Optional[dict[str, Agent2Data]],
                    agent3: dict[str, Agent3Data],
                    target: str) -> dict:
    main = countries[0]
    a3_main = agent3[main]
    charts: list[Chart] = []

    # 1) 위험도 × 협력지수 (다국가 비교)
    charts.append(Chart(
        id="risk_vs_coop", source_agent="agent3", type="scatter",
        title="위험도 vs 협력지수",
        data=[{"country": c, "x": a3.risk_score.score,
               "y": a3.cooperation_index.score,
               "grade": a3.cooperation_index.grade}
              for c, a3 in agent3.items()]))

    # 2) 위험도 세부요인 (agent3 v2 components)
    if a3_main.risk_score.components:
        charts.append(Chart(
            id="risk_components", source_agent="agent3", type="bar",
            title=f"{main} 위험도 구성요인",
            data=[[_COMP_LABEL.get(k, k), round(v, 1)]
                  for k, v in a3_main.risk_score.components.items()]))

    # 3) 유망분야 랭킹 — 분야 데이터 유의미할 때만 (KOICA API 복구 시 자동 부활)
    if a3_main.opportunity_meaningful:
        charts.append(Chart(
            id="opportunity_ranking", source_agent="agent3", type="bar_h",
            title=f"{main} 분야별 협력 기회",
            data={"country": main,
                  "ranking": [[f, s] for f, s in a3_main.opportunity_ranking]}))

    # 4) 유사국가
    if a3_main.similar_countries:
        charts.append(Chart(
            id="similar_countries", source_agent="agent3", type="bar",
            title="대안 국가 (유사도)" if target == "기업" else "유사 외교 패턴 국가",
            data=[[n, round(float(s), 3)] for n, s in a3_main.similar_countries]))

    # 5) ODA 연도별 추이 — 지원실적 CSV 실데이터 (총액만, 분야별 없음)
    a2_main = (agent2 or {}).get(main)
    if a2_main and a2_main.oda_yearly:
        years = sorted(a2_main.oda_yearly)
        charts.append(Chart(
            id="oda_trend", source_agent="agent2", type="line",
            title=f"{main} ODA 지원실적 연도별 추이 (백만$)",
            data={"years": years,
                  "values": [round(a2_main.oda_yearly[y], 2) for y in years]}))

    # 6) 외교 타임라인 (연구자): 수교연도 + Agent1 최근정세 + 안전공지
    if target == "연구자":
        events = []
        if a2_main and a2_main.diplomatic_year:
            events.append({"date": str(a2_main.diplomatic_year),
                           "event": f"한-{main} 수교", "kind": "milestone"})
        a1_main = agent1.get(main)
        if a1_main:
            events += [{"date": s.get("date", ""), "event": s.get("event", ""),
                        "kind": "recent"} for s in a1_main.recent_situations]
            events += [{"date": n.date or "", "event": n.title or "",
                        "kind": "notice"}
                       for n in a1_main.recent_safety_notices if n.title]
        if events:
            charts.append(Chart(
                id="diplomatic_timeline", source_agent="agent1+agent2",
                type="timeline", title=f"{main} 외교·안전 타임라인",
                data={"events": events}))

    return {"charts": [c.model_dump() for c in charts]}
