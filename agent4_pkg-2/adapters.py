# -*- coding: utf-8 -*-
"""adapters.py — Agent 간 스키마 변환 계층 (v1.2).

adapt_agent1 : 팀원 A 실출력(레거시 문자열 포함) → Agent1Data
adapt_agent2 : 팀원 B collector 원본(봉투 스키마) → Agent2Data
adapt_agent3 : 팀원 C 신/구 포맷 모두 → dict[국가, Agent3Data]
"""

from __future__ import annotations
import re
from typing import Optional

from report_generator.schemas import (
    Agent1Data, Agent2Data, Agent3Data, KoreaOrg)


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
def _unwrap(block) -> dict | list | None:
    """봉투 {status, data, error} → status=="ok"면 data, 아니면 None."""
    if isinstance(block, dict) and block.get("status") == "ok":
        return block.get("data")
    return None


def _pick(d: dict, *keys, default=None):
    """중첩·이명 키 방어적 탐색: _pick(d, 'by_year', 'data')"""
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
    """팀원 B collector 결과(봉투 스키마, 국가 1개분) → Agent2Data.

    loader 반환값(DataFrame→records) 처리:
    - oda.cumulative.data : [{"국가명":…, "원":…, "달러":…}]  단위: raw USD → /1_000_000
    - oda.yearly.data     : [{"연도":…, "원":…, "달러":…}]    단위: raw USD → /1_000_000
    - overseas_presence.data : {"status":…, "orgs":[…], "org_count":…}
    """
    ev = raw.get("_evidence", {})

    diplomatic = _unwrap(raw.get("diplomatic")) or {}
    trade = _unwrap(raw.get("trade")) or {}
    oda = raw.get("oda") or {}
    oda_cum = _unwrap(oda.get("cumulative"))   # list 또는 dict 또는 None
    oda_yr = _unwrap(oda.get("yearly"))         # list 또는 dict 또는 None
    presence = _unwrap(raw.get("overseas_presence"))

    # 한국기관 — overseas_presence.data = {"orgs": [...], "org_count": N, ...}
    orgs = []
    if isinstance(presence, list):
        olist = presence
    elif isinstance(presence, dict):
        olist = _pick(presence, "orgs", "items", default=[])
    else:
        olist = []
    for o in olist if isinstance(olist, list) else []:
        if isinstance(o, dict):
            orgs.append(KoreaOrg(
                name=_pick(o, "name", "공공기관명", default="(기관)"),
                org_type=_pick(o, "org_type", "공공기관유형"),
                note=_pick(o, "note", "공공기관진출내용")))

    # 누적 ODA — list 형태(loader)면 첫 레코드 "달러" 추출 후 /1M 변환
    if isinstance(oda_cum, list) and oda_cum:
        raw_usd = _to_float(_pick(oda_cum[0], "달러", "dollar"))
        oda_cumulative = round(raw_usd / 1_000_000, 2) if raw_usd is not None else None
    else:
        oda_cumulative = _to_float(
            _pick(oda_cum or {}, "usd_million", "cumulative_usd_million"))

    # 연도별 ODA — list 형태면 "달러" 추출 후 /1M 변환, dict 형태면 그대로
    by_year = _pick(oda_yr or {}, "by_year") or oda_yr
    if isinstance(by_year, list):
        by_year = {str(_pick(r, "year", "연도")):
                   round(float(_pick(r, "usd", "달러", default=0) or 0) / 1_000_000, 2)
                   for r in by_year if isinstance(r, dict)}
    yearly = {str(k): float(v) for k, v in (by_year or {}).items()
              if v is not None and str(k).isdigit()}

    return Agent2Data(
        iso2=raw.get("iso2"),
        queried_at=raw.get("queried_at"),
        trade_volume_usd_million=_to_float(
            _pick(trade, "volume_usd_million", "total_usd_million")),
        oda_cumulative_usd_million=oda_cumulative,
        oda_yearly=yearly,
        korea_orgs=orgs,
        expat_count=_to_int(_pick(diplomatic, "expat_count")),
        diplomatic_year=_to_int(_pick(diplomatic, "established_year",
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
