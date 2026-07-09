# -*- coding: utf-8 -*-
"""adapters.py — Agent 간 스키마 변환 계층 (v1.1).

adapt_agent1 : 팀원 A 실출력(레거시 문자열 포함) → Agent1Data
adapt_agent2 : 팀원 B collector 원본 → Agent2Data (방어적 키 탐색)
adapt_agent3 : 팀원 C 신/구 포맷 모두 → dict[국가, Agent3Data]
"""

from __future__ import annotations
import re
from typing import Optional

from report_generator.schemas import (
    Agent1Data, Agent2Data, Agent3Data, OdaProject, KoreaOrg)


# ── Agent 1 ─────────────────────────────────────────────────
def adapt_agent1(raw: dict) -> Agent1Data:
    data = dict(raw)
    if not data.get("travel_warning"):
        data["travel_warning"] = _parse_warning_string(
            data.get("travel_warning_level"))
    notices = data.get("recent_safety_notices") or []
    if notices and isinstance(notices[0], str):
        data["recent_safety_notices"] = [
            {"date": None, "title": None, "summary": s} for s in notices]
    return Agent1Data(**data)


def _parse_warning_string(s: Optional[str]) -> dict:
    if not s:
        return {"level": 0, "label": None, "partial": False}
    m = re.search(r"([1-4])단계\s*(\S+)", s)
    return {"level": int(m.group(1)) if m else 0,
            "label": m.group(2) if m else None,
            "partial": "일부" in s}


# ── Agent 2 ─────────────────────────────────────────────────
def _pick(d: dict, *keys, default=None):
    """중첩·이명 키 방어적 탐색: _pick(raw, 'oda.cumulative_usd', 'oda_cumulative')"""
    for k in keys:
        cur = d
        ok = True
        for part in k.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None:
            return cur
    return default


def adapt_agent2(raw: dict) -> Agent2Data:
    """팀원 B collector 결과(국가 1개분) → Agent2Data.
    ※ agent2 브랜치 미push 상태라 키 이름은 문서 기반 추정 → push 후 이 함수만 조정."""
    ev = raw.get("_evidence", {})

    # ODA 사업 목록 (fallback: 사업명/시작·종료연도/링크)
    projects = []
    plist = _pick(raw, "oda.project_list_fallback.projects",
                  "oda.project_list_fallback", "oda_projects", default=[])
    if isinstance(plist, dict):
        plist = plist.get("projects", plist.get("items", []))
    for p in plist if isinstance(plist, list) else []:
        if isinstance(p, str):
            projects.append(OdaProject(name=p))
        elif isinstance(p, dict):
            projects.append(OdaProject(
                name=_pick(p, "name", "사업명", "project_name", default="(무제)"),
                start_year=_to_int(_pick(p, "start_year", "시작연도")),
                end_year=_to_int(_pick(p, "end_year", "종료연도")),
                link=_pick(p, "link", "사업개요서링크")))

    # 한국기관 (도시 정보 없음)
    orgs = []
    olist = _pick(raw, "overseas_org.items", "overseas_org", "korea_orgs",
                  default=[])
    if isinstance(olist, dict):
        olist = olist.get("items", [])
    for o in olist if isinstance(olist, list) else []:
        if isinstance(o, dict):
            orgs.append(KoreaOrg(
                name=_pick(o, "name", "공공기관명", default="(기관)"),
                org_type=_pick(o, "org_type", "공공기관유형"),
                note=_pick(o, "note", "공공기관진출내용")))

    # 연도별 ODA (지원실적 CSV)
    yearly = _pick(raw, "oda.country_support_yearly.by_year",
                   "oda.country_support_yearly", "oda_yearly", default={}) or {}
    if isinstance(yearly, list):  # [{연도, 달러}] 형태 대비
        yearly = {str(_pick(r, "year", "연도")):
                  float(_pick(r, "usd", "달러", default=0) or 0)
                  for r in yearly if isinstance(r, dict)}
    yearly = {str(k): float(v) for k, v in yearly.items()
              if v is not None and str(k).isdigit()}

    field_status = _pick(raw, "oda.by_sport_realm.status",
                         default="unavailable") or "unavailable"

    return Agent2Data(
        trade_volume_usd_million=_to_float(_pick(
            raw, "trade.volume_usd_million", "trade.total_usd_million",
            "trade_volume_usd_million")),
        oda_cumulative_usd_million=_to_float(_pick(
            raw, "oda.country_support_cumulative.usd_million",
            "oda.cumulative_usd_million", "oda_cumulative_usd_million")),
        oda_yearly=yearly,
        oda_projects=projects,
        oda_field_status=str(field_status),
        korea_orgs=orgs,
        expat_count=_to_int(_pick(
            raw, "diplomatic.expat_count", "relation.expat_count",
            "expat_count")),
        diplomatic_year=_to_int(_pick(
            raw, "diplomatic.established_year", "relation.diplomatic_year",
            "diplomatic_year")),
        sources_used=ev.get("sources_used", []),
        sources_failed=ev.get("sources_failed", []),
        sources_empty=ev.get("sources_empty", []),
    )


def _to_int(v):
    try:
        return int(float(str(v).replace(",", ""))) if v is not None else None
    except (ValueError, TypeError):
        return None


def _to_float(v):
    try:
        return float(str(v).replace(",", "")) if v is not None else None
    except (ValueError, TypeError):
        return None


# ── Agent 3 ─────────────────────────────────────────────────
def adapt_agent3(raw) -> dict[str, Agent3Data]:
    """신/구 포맷 모두 수용:
    - 구: {"베트남": {...}, "몽골": {...}}
    - 신(단일): {"country": "일본", "risk_score": {...}, ...}
    - 신(리스트): [{...}, {...}]
    """
    if isinstance(raw, list):
        return {r.get("country", f"국가{i}"): Agent3Data(**r)
                for i, r in enumerate(raw)}
    if isinstance(raw, dict):
        if "risk_score" in raw:  # 단일 국가 신포맷
            return {raw.get("country", "unknown"): Agent3Data(**raw)}
        return {c: Agent3Data(**(v | {"country": c}) if "country" not in v
                              else v)
                for c, v in raw.items()}
    raise ValueError("지원하지 않는 agent3 포맷")
