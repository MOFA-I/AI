# -*- coding: utf-8 -*-
"""test_pipeline.py — v1.2 E2E: Agent2 실구현 봉투 스키마 + loader records 형태."""
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

# 3) agent2: 실구현 봉투 스키마 (collector.py 실 출력 형태)
#    - oda.cumulative/yearly.data = loader DataFrame → records (raw USD)
#    - overseas_presence.data = {"status":…, "orgs":[…], "org_count":N}
#    - _evidence source 이름 = selector.py SOURCE_FUNCTIONS 키 그대로
#    베트남 — oda ok, overseas_presence empty
#    일본   — oda cumulative/yearly failed, overseas_presence ok
agent2_raw = {
    "베트남": {
        "country_nm": "베트남",
        "iso2": "VN",
        "queried_at": "2026-07-11T03:00:00+00:00",
        "diplomatic": {
            "status": "ok",
            "data": {"response": {"body": {"items": {"item": {
                "country_nm": "베트남",
                "country_iso_alp2": "VN",
                "diplomatic_relations": "1992.12.22. 수교",
                "oks_status": "약 173,000명('21)",
                "export_amount": 15000000000,
                "import_amount": 9000000000,
            }}}}},
            "error": None,
        },
        "trade": {
            "status": "ok",
            "data": {"response": {"body": {"items": {"item": {
                "country_nm": "베트남",
                "country_iso_alp2": "VN",
                "yt_export_amount": 15000000000,
                "yt_income_amount": 9000000000,
                "yt_trade_year": 2023,
            }}}}},
            "error": None,
        },
        "oda": {
            "cumulative": {
                "status": "ok",
                # loader DataFrame.to_dict("records") 형태 — 단위: raw USD
                "data": [{"국가명": "베트남", "원": 654321000000.0, "달러": 560857532}],
                "error": None,
            },
            "yearly": {
                "status": "ok",
                # loader DataFrame.to_dict("records") 형태 — 단위: raw USD
                "data": [
                    {"연도": 2020, "원": 195000000000.0, "달러": 180200000},
                    {"연도": 2021, "원": 228000000000.0, "달러": 210500000},
                    {"연도": 2022, "원": 211000000000.0, "달러": 195000000},
                    {"연도": 2023, "원": 260000000000.0, "달러": 240800000},
                    {"연도": 2024, "원": 281000000000.0, "달러": 260100000},
                ],
                "error": None,
            },
        },
        "overseas_presence": {
            "status": "empty",
            "data": None,
            "error": None,
        },
        "_evidence": {
            "sources_used": [
                "relation", "trade",
                "koica_country_support_cumulative",
                "koica_country_support_yearly",
            ],
            "sources_failed": [],
            "sources_empty": ["overseas_org"],
        },
    },
    "일본": {
        "country_nm": "일본",
        "iso2": "JP",
        "queried_at": "2026-07-11T03:00:00+00:00",
        "diplomatic": {
            "status": "ok",
            "data": {"response": {"body": {"items": {"item": {
                "country_nm": "일본",
                "country_iso_alp2": "JP",
                "diplomatic_relations": "1965.12.18. 수교",
                "oks_status": "약 818,865명('21)",
                "export_amount": 30000000000,
                "import_amount": 54000000000,
            }}}}},
            "error": None,
        },
        "trade": {
            "status": "ok",
            "data": {"response": {"body": {"items": {"item": {
                "country_nm": "일본",
                "country_iso_alp2": "JP",
                "yt_export_amount": 30000000000,
                "yt_income_amount": 54000000000,
                "yt_trade_year": 2023,
            }}}}},
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
            # _wrap_loader_result: data = loader 반환 dict 그대로
            "data": {
                "status": "ok",
                "country": "일본",
                "org_count": 2,
                "orgs": [
                    {"공공기관유형": "공공기관", "공공기관명": "KOTRA 도쿄무역관"},
                    {"공공기관유형": "공공기관", "공공기관명": "한국관광공사 도쿄지사"},
                ],
            },
            "error": None,
        },
        "_evidence": {
            "sources_used": ["relation", "trade", "overseas_org"],
            "sources_failed": [
                "koica_country_support_cumulative",
                "koica_country_support_yearly",
            ],
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

# agent2 loader records 파싱 검증
a2_vn = inp_common["agent2"]["베트남"]
a2_jp = inp_common["agent2"]["일본"]

assert a2_vn.iso2 == "VN", "iso2 파싱 실패"

# diplomatic/trade 텍스트 파싱 검증
assert a2_vn.diplomatic_year == 1992, f"수교연도 파싱 실패: {a2_vn.diplomatic_year}"
assert a2_vn.expat_count == 173000, f"교민수 파싱 실패: {a2_vn.expat_count}"
assert a2_vn.trade_volume_usd_million is not None, "교역액 None"
assert abs(a2_vn.trade_volume_usd_million - 24000.0) < 1, \
    f"교역액 단위 오류: {a2_vn.trade_volume_usd_million}"  # (15B+9B)/1M = 24,000백만$

# oda.cumulative: raw USD → /1_000_000 변환
assert a2_vn.oda_cumulative_usd_million is not None, "누적 ODA None — list 파싱 실패"
assert abs(a2_vn.oda_cumulative_usd_million - 560.86) < 0.1, \
    f"누적 ODA 단위 오류: {a2_vn.oda_cumulative_usd_million}"

# oda.yearly: raw USD → /1_000_000 변환
assert abs(a2_vn.oda_yearly.get("2024", 0) - 260.1) < 0.5, \
    f"연도별 ODA 단위 오류: {a2_vn.oda_yearly}"

# overseas_presence: empty → 빈 목록
assert a2_vn.korea_orgs == [], "empty overseas_presence → 빈 목록이어야 함"

# failed 봉투 → None
assert a2_jp.oda_cumulative_usd_million is None, "failed 봉투 → None이어야 함"

# overseas_presence ok: "orgs" 키 파싱
assert len(a2_jp.korea_orgs) == 2, \
    f"overseas_presence ok → 2건이어야 함, 실제: {len(a2_jp.korea_orgs)}"

# evidence 소스 레이블 검증 (실제 source 이름 매핑)
ev_actions = [e["action"] for e in j2["evidence"]]
assert any("KOICA ODA 누적지원" in a or "koica_country_support_cumulative" in a
           for a in ev_actions), "KOICA 누적 소스 레이블 누락"

print("\n✅ v1.2 E2E 통과 — agent2 실구현 형태(loader records, raw USD→백만달러 변환, orgs 키) 검증")
