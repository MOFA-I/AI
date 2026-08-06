# -*- coding: utf-8 -*-
"""cases.py — 브리핑 품질 평가용 고정 입력 케이스.

케이스 수보다 다양성이 중요하다. 특히 데이터 결측·소스 장애 케이스가
프롬프트의 취약점을 잘 드러낸다(없는 데이터를 지어내는지).
"""

from __future__ import annotations

from report_generator.schemas import Agent4Input, Agent2Data, Agent3Data
from adapters import adapt_agent1


def _a1(country, warning, notices=(), situations=(), visa_note="", secenv=None):
    return adapt_agent1({
        "country": country,
        "travel_warning_level": warning,
        "recent_safety_notices": [
            {"date": d, "title": t, "summary": ""} for d, t in notices],
        "security_environment": secenv or {},
        "recent_situations": [{"date": d, "event": e} for d, e in situations],
        "entrance_visa": {"general_passport_visa_note": visa_note},
    })


# ── 케이스 정의 ────────────────────────────────────────────
CASES: dict[str, dict] = {}


def _register(cid, desc, target, countries, agent1, agent2, agent3, query,
              forbidden=()):
    CASES[cid] = {
        "id": cid, "desc": desc, "forbidden": list(forbidden),
        "input": Agent4Input(
            request={"user_query": query, "target": target,
                     "countries": countries},
            agent1=agent1, agent2=agent2, agent3=agent3),
    }


# 1. 저위험·고협력 (기업) — 진출 추천이 나와야 하는 전형 케이스
_register(
    "biz_low_risk", "저위험·고협력 국가, 기업 타깃", "기업", ["베트남"],
    {"베트남": _a1("베트남", "1단계 여행유의",
                 [("2026-07-01", "우기 교통 유의")],
                 [("2026-06-28", "총리 경제 개혁안 발표")], "45일 무비자",
                 {"unemployment_rate": 2.3})},
    {"베트남": Agent2Data(trade_volume_usd_million=79400,
                        oda_cumulative_usd_million=2100,
                        expat_count=156000, diplomatic_year=1992,
                        oda_yearly={"2023": 240.8, "2024": 260.1},
                        sources_used=["relation", "trade"])},
    {"베트남": Agent3Data(risk_score={"score": 28.4, "level": 1,
                                   "components": {"travel_advisory": 33.3,
                                                  "safety_notice_freq": 20.0,
                                                  "socio_indicator_risk": 30.0}},
                       cooperation_index={"score": 78.5, "grade": 4},
                       similar_countries=[["인도네시아", 0.81], ["태국", 0.77]])},
    "베트남 진출 검토 중인데 리스크가 어떤가요?")

# 2. 고위험 (기업) — 비추천 판정 + 위험 서술이 강해야 함
_register(
    "biz_high_risk", "고위험 국가, 기업 타깃", "기업", ["미얀마"],
    {"미얀마": _a1("미얀마", "3단계 철수권고",
                 [("2026-07-05", "무장 충돌 지역 접근 금지"),
                  ("2026-06-30", "통신 차단 관련 유의")],
                 [("2026-06-15", "군정 비상사태 연장")], "사증 필요")},
    {"미얀마": Agent2Data(trade_volume_usd_million=1120,
                        oda_cumulative_usd_million=430,
                        expat_count=3200, diplomatic_year=1975,
                        sources_used=["relation", "trade"])},
    {"미얀마": Agent3Data(risk_score={"score": 84.2, "level": 3,
                                   "components": {"travel_advisory": 100.0,
                                                  "safety_notice_freq": 80.0}},
                       cooperation_index={"score": 22.1, "grade": 2},
                       similar_countries=[["라오스", 0.68]])},
    "미얀마 사업 진출 가능한가요?")

# 3. 연구자 타깃 — 양측 관점 분리 서술이 나와야 함
_register(
    "res_standard", "연구자 타깃 표준 케이스", "연구자", ["인도네시아"],
    {"인도네시아": _a1("인도네시아", "1단계 여행유의", [],
                   [("2026-06-30", "신수도 이전 사업 가속")], "도착비자 가능")},
    {"인도네시아": Agent2Data(trade_volume_usd_million=20800,
                         oda_cumulative_usd_million=1800,
                         expat_count=25000, diplomatic_year=1973,
                         oda_yearly={"2022": 150.0, "2023": 180.5,
                                     "2024": 210.0})},
    {"인도네시아": Agent3Data(risk_score={"score": 35.8, "level": 1,
                                    "components": {"travel_advisory": 33.3}},
                        cooperation_index={"score": 72.5, "grade": 4},
                        similar_countries=[["베트남", 0.81], ["필리핀", 0.69]])},
    "한-인도네시아 개발협력 흐름을 분석해주세요.")

# 4. 데이터 결측 — 없는 데이터를 지어내는지 검사 (핵심 케이스)
_register(
    "missing_agent2", "Agent2 전면 결측(소스 장애)", "기업", ["가나"],
    {"가나": _a1("가나", "1단계 여행유의", [], [], "사증 필요")},
    {"가나": Agent2Data(sources_failed=["relation", "trade"],
                      sources_empty=["overseas_presence"])},
    {"가나": Agent3Data(risk_score={"score": 41.0, "level": 1},
                      cooperation_index={"score": 15.2, "grade": 1},
                      similar_countries=[])},
    "가나 진출 시 교역 규모와 ODA 실적이 어떤가요?",
    forbidden=["교역액", "무역액"])   # 데이터 없으므로 수치 서술 금지

# 5. 다국가 비교 — 비교 서술이 실제로 나오는지
_register(
    "multi_compare", "다국가 비교(기업)", "기업", ["베트남", "인도네시아", "미얀마"],
    {"베트남": _a1("베트남", "1단계 여행유의", [], [], "45일 무비자"),
     "인도네시아": _a1("인도네시아", "1단계 여행유의", [], [], "도착비자"),
     "미얀마": _a1("미얀마", "3단계 철수권고", [], [], "사증 필요")},
    {"베트남": Agent2Data(trade_volume_usd_million=79400, diplomatic_year=1992),
     "인도네시아": Agent2Data(trade_volume_usd_million=20800, diplomatic_year=1973),
     "미얀마": Agent2Data(trade_volume_usd_million=1120, diplomatic_year=1975)},
    {"베트남": Agent3Data(risk_score={"score": 28.4},
                       cooperation_index={"score": 78.5, "grade": 4}),
     "인도네시아": Agent3Data(risk_score={"score": 35.8},
                        cooperation_index={"score": 72.5, "grade": 4}),
     "미얀마": Agent3Data(risk_score={"score": 84.2},
                      cooperation_index={"score": 22.1, "grade": 2})},
    "베트남, 인도네시아, 미얀마 중 어디가 진출에 유리한가요?")
