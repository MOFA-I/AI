# -*- coding: utf-8 -*-
"""test_pipeline.py — v1.1 E2E: agent3 신포맷 + 팀원B collector 원본 구조."""
import json
from report_generator import Agent4ReportGenerator, Agent4Input
from adapters import adapt_agent1, adapt_agent2, adapt_agent3

# 1) agent3: 신포맷(일본 단일) + 구포맷(15개국) 혼용 검증
new = json.load(open("sample_data/agent3_new_format.json", encoding="utf-8"))
old = json.load(open("sample_data/result_sample.json", encoding="utf-8"))
agent3 = adapt_agent3(new) | adapt_agent3({"베트남": old["베트남"]})

# 2) agent1 더미 (팀원 A 실스키마)
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

# 3) agent2: 팀원 B collector 원본 구조 그대로 (문서의 실행결과 형태)
agent2_raw = {
    "베트남": {
        "diplomatic": {"status": "ok", "established_year": 1992,
                       "expat_count": 156000},
        "trade": {"status": "ok", "volume_usd_million": 79400},
        "oda": {
            "by_sport_realm": {"status": "failed", "error": "502 Bad Gateway"},
            "project_list_fallback": {"status": "ok", "projects": [
                {"name": "베트남 부동산 가격 DB 구축", "start_year": 2022,
                 "end_year": 2024},
                {"name": "베트남 직업훈련 역량강화", "start_year": 2023,
                 "end_year": 2026},
                {"name": "베트남 기후변화 대응", "start_year": 2021,
                 "end_year": 2023}]},
            "country_support_cumulative": {"status": "ok",
                                           "usd_million": 2100.5},
            "country_support_yearly": {"status": "ok", "by_year": {
                "2020": 180.2, "2021": 210.5, "2022": 195.0,
                "2023": 240.8, "2024": 260.1}},
        },
        "overseas_org": {"status": "empty", "items": []},
        "_evidence": {
            "sources_used": ["relation", "trade",
                             "koica_country_support_cumulative",
                             "koica_country_support_yearly",
                             "koica_project_list_fallback"],
            "sources_failed": ["koica_business"],
            "sources_empty": ["overseas_org"]},
    },
    "일본": {
        "diplomatic": {"status": "ok", "established_year": 1965,
                       "expat_count": 820000},
        "trade": {"status": "ok", "volume_usd_million": 76600},
        "oda": {"by_sport_realm": {"status": "failed", "error": "502"},
                "project_list_fallback": {"status": "ok", "projects": []}},
        "overseas_org": {"status": "ok", "items": [
            {"공공기관명": "KOTRA 도쿄무역관", "공공기관유형": "공공기관",
             "공공기관진출내용": "무역·투자 지원"},
            {"공공기관명": "한국관광공사 도쿄지사", "공공기관유형": "공공기관"}]},
        "_evidence": {"sources_used": ["relation", "trade", "overseas_org"],
                      "sources_failed": ["koica_business"],
                      "sources_empty": []},
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
assert "opportunity_ranking" not in [c["id"] for c in j2["dashboard"]["charts"]] \
    or agent3["일본"].opportunity_meaningful
assert any("실패→대체" in e["action"] for e in j2["evidence"]), "폴백 투명성 누락"
print("\n✅ v1.1 E2E 통과 — agent3 신포맷 + agent2 실구조 + 폴백투명성 확인")
