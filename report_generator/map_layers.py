# -*- coding: utf-8 -*-
"""map_layers.py — map 블록(JSON) 생성. v1.2

oda_summary: {country, lat, lon, cumulative_usd_million} 만 포함.
cumulative 없으면 레이어 전체 스킵.
"""

from __future__ import annotations
import logging
from typing import Optional

from .schemas import Agent1Data, Agent2Data, Agent3Data, MapBlock, MapLayer
from .geo import get_coords, KOREA_COORDS

logger = logging.getLogger("agent4.map")


def build_map(countries: list[str],
              agent1: dict[str, Agent1Data],
              agent2: Optional[dict[str, Agent2Data]],
              agent3: dict[str, Agent3Data],
              target: str) -> MapBlock:

    coords = {c: get_coords(c) for c in countries}
    coords = {c: xy for c, xy in coords.items() if xy}
    if not coords:
        return MapBlock(center=[20, 100], zoom=3, layers=[])

    center = [sum(xy[0] for xy in coords.values()) / len(coords),
              sum(xy[1] for xy in coords.values()) / len(coords)]
    zoom = 5 if len(coords) == 1 else 4
    layers: list[MapLayer] = []

    # ── 여행경보 (Agent 1) ──
    alert_feats = []
    for c, xy in coords.items():
        a1 = agent1.get(c)
        if not a1:
            continue
        tw = a1.travel_warning
        alert_feats.append({"country": c, "lat": xy[0], "lon": xy[1],
                            "alert_level": tw.level if tw else 0,
                            "alert_label": (tw.label if tw else None) or "정보없음",
                            "partial": tw.partial if tw else False})
    if alert_feats:
        layers.append(MapLayer(id="travel_alert", source_agent="agent1",
                               type="alert_markers", title="여행경보",
                               features=alert_feats))

    # ── Agent 2 레이어 ──
    if agent2:
        oda_feats, org_agg, flows = [], [], []
        for c, a2 in agent2.items():
            cxy = coords.get(c) or get_coords(c)
            if not cxy:
                continue

            if a2.oda_cumulative_usd_million:
                oda_feats.append({
                    "country": c, "lat": cxy[0], "lon": cxy[1],
                    "cumulative_usd_million": a2.oda_cumulative_usd_million,
                })

            if a2.korea_orgs:
                org_agg.append({
                    "country": c, "lat": cxy[0], "lon": cxy[1],
                    "count": len(a2.korea_orgs),
                    "orgs": [{"name": o.name, "org_type": o.org_type}
                             for o in a2.korea_orgs[:8]],
                })

            if a2.trade_volume_usd_million:
                flows.append({"from": list(KOREA_COORDS), "to": list(cxy),
                              "label": f"한-{c} 교역",
                              "value_usd_million": a2.trade_volume_usd_million})

        if oda_feats:
            layers.append(MapLayer(id="oda_summary", source_agent="agent2",
                                   type="agg_markers", title="KOICA ODA 현황",
                                   features=oda_feats))
        if org_agg:
            layers.append(MapLayer(id="korea_orgs", source_agent="agent2",
                                   type="agg_markers", title="한국기관 진출",
                                   features=org_agg))
        if flows and target == "기업":
            layers.append(MapLayer(id="trade_flow", source_agent="agent2",
                                   type="arc", title="무역 흐름",
                                   features=flows))

    # ── 유사국가 연결 (연구자) ──
    if target == "연구자":
        main = countries[0]
        main_xy, a3 = coords.get(main), agent3.get(main)
        if main_xy and a3:
            feats = []
            for name, sim in a3.similar_countries:
                xy = get_coords(name)
                if xy:
                    feats.append({"from": list(main_xy), "to": list(xy),
                                  "label": f"{main} ↔ {name}",
                                  "similarity": round(float(sim), 3),
                                  "target_country": name})
            if feats:
                layers.append(MapLayer(id="similarity_lines",
                                       source_agent="agent3",
                                       type="similarity_lines",
                                       title=f"{main} 유사국가",
                                       features=feats))

    return MapBlock(center=center, zoom=zoom, layers=layers)
