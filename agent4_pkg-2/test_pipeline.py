# -*- coding: utf-8 -*-
"""test_pipeline.py — v1.2 E2E: Agent2 확정 봉투 스키마 + failed/empty 케이스."""
import json
from report_generator import Agent4ReportGenerator, Agent4Input
from adapters import adapt_agent1, adapt_agent2, adapt_agent3

# 1) agent3: 신포맷(일본 단일) + 구포맷(베트남) 혼용 검증
new = json.load(open("sample_data/agent3_new_format.json", encoding="utf-8"))
old = json.load(open("sample_data/result_sample.json", encoding="utf-8"))
agent3 = adapt_agent3(new) | adapt_agent3({"베트남": old["베트남"]})

# 2) agent1 더미
agent1_raw = {
    "일본": {"country": "일본",
             "travel_warning_level": "1단계 여행유의",
             "recent_safety_notices": [
                 {"date": "2024-04-01", "title": "STSS 관련 안전공지", "summary": "..."}],
             "security_environment": {}, "entrance_visa":
                 {"general_passport_visa_required": "N",
                  "general_passport_visa_note": "90일 무비자"},
             "recent_situations": [
                 {"date": "2026-06-20", "event": "한일 경제협력 회담"}]},
    "베트남": {"country": "베트남",
               "travel_warning_level": "2단계 여행자제 (일부 지역)",
               "recent_safety_notices": [], "security_environment": {},
               "entrance_visa": {"general_passport_visa_note": "45일 무비자"},
               "recent_situations": [
                   {"date": "2026-06-28", "event": "총리, 경제 개혁안 발표"}]},
}

# 3) agent2: 확정 봉투 스키마 {status, data, error}
#    베트남 — oda.cumulative ok, oda.yearly ok, overseas_presence empty
#    일본   — oda.cumulative failed, oda.yearly failed, overseas_presence ok
agent2_raw = {
    "베트남": {
        "country_nm": "베트남",
        "iso2": "VN",
        "queried_at": "2026-07-10T12:00:00",
        "diplomatic": {
            "status": "ok",
            "data": {"established_year": 1992, "expat_count": 156000},
            "error": None,
        },
        "trade": {
            "status": "ok",
            "data": {"volume_usd_million": 79400},
            "error": None,
        },
        "oda": {
            "cumulative": {
                "status": "ok",
                "data": {"usd_million": 2100.5},
                "error": None,
            },
            "yearly": {
                "status": "ok",
                "data": {"by_year": {
                    "2020": 180.2, "2021": 210.5, "2022": 195.0,
                    "2023": 240.8, "2024": 260.1,
                }},
                "error": None,
            },
        },
        "overseas_presence": {
            "status": "empty",
            "data": None,
            "error": None,
        },
        "_evidence": {
            "sources_used": ["diplomatic", "trade", "oda_cumulative", "oda_yearly"],
            "sources_failed": [],
            "sources_empty": ["overseas_presence"],
        },
    },
    "일본": {
        "country_nm": "일본",
        "iso2": "JP",
        "queried_at": "2026-07-10T12:00:00",
        "diplomatic": {
            "status": "ok",
            "data": {"established_year": 1965, "expat_count": 820000},
            "error": None,
        },
        "trade": {
            "status": "ok",
            "data": {"volume_usd_million": 76600},
            "error": None,
        },
        "oda": {
            "cumulative": {
                "status": "failed",
                "data": None,
                "error": "404 Not Found",
            },
            "yearly": {
                "status": "failed",
                "data": None,
                "error": "404 Not Found",
            },
        },
        "overseas_presence": {
            "status": "ok",
            "data": [
                {"공공기관명": "KOTRA 도쿄무역관", "공공기관유형": "공공기관",
                 "공공기관진출내용": "무역·투자 지원"},
                {"공공기관명": "한국관광공사 도쿄지사", "공공기관유형": "공공기관"},
            ],
            "error": None,
        },
        "_evidence": {
            "sources_used": ["diplomatic", "trade", "overseas_presence"],
            "sources_failed": ["oda_cumulative", "oda_yearly"],
            "sources_empty": [],
        },
    },
}

inp_common = dict(
    agent1={c: adapt_agent1(v) for c, v in agent1_raw.items()},
    agent2={c: adapt_agent2(v) for c, v in agent2_raw.items()},
    agent3=agent3,
)

for target in ["기업", "연구자"]:
    inp = Agent4Input(request={"user_query": "일본 vs 베트남 협력 비교",
                               "target": target,
                               "countries": ["일본", "베트남"]}, **inp_common)
    out = Agent4ReportGenerator().generate(inp, html=True)
    j = out.model_dump()
    print(f"[{target}] cards={[c['id'] for c in j['cards']]}")
    print(f"       layers={[l['id'] for l in j['map']['layers']]}")
    print(f"       charts={[c['id'] for c in j['dashboard']['charts']]}")
    print(f"       evidence={len(j['evidence'])}건, html={j['files']['html']}")

# 검증 포인트
j2 = out.model_dump()
chart_ids = [c["id"] for c in j2["dashboard"]["charts"]]
assert "opportunity_ranking" not in chart_ids, "opportunity_ranking 차트가 남아 있음"
assert any("실패→대체" in e["action"] for e in j2["evidence"]), "폴백 투명성 누락"

# 봉투 스키마 파싱 검증
a2_vn = inp_common["agent2"]["베트남"]
a2_jp = inp_common["agent2"]["일본"]
assert a2_vn.iso2 == "VN", "iso2 파싱 실패"
assert a2_vn.oda_cumulative_usd_million == 2100.5, "누적 ODA 파싱 실패"
assert a2_vn.oda_yearly.get("2024") == 260.1, "연도별 ODA 파싱 실패"
assert a2_vn.korea_orgs == [], "empty overseas_presence → 빈 목록이어야 함"
assert a2_jp.oda_cumulative_usd_million is None, "failed 봉투 → None이어야 함"
assert len(a2_jp.korea_orgs) == 2, "overseas_presence ok → 2건이어야 함"

print("\n✅ v1.2 E2E 통과 — 봉투 스키마, failed/empty 케이스, Opportunity Score 폐지 확인")
