# -*- coding: utf-8 -*-
"""
config.py - 프로젝트 전체 설정값 모음
"""

# ── 1) 위험도 점수 가중치 ────────────────────────────────────────────
RISK_WEIGHTS = {
    "travel_advisory": 0.40,   # 여행경보 단계
    "safety_notice": 0.30,     # 안전공지 빈도
    "political_keyword": 0.30,  # 주요정세 키워드 위험도
}

# ── 2) Cooperation Index 가중치 ─────────────────────────────────────
COOPERATION_WEIGHTS = {
    "trade_volume": 0.30,      # 무역 규모
    "oda_cumulative": 0.30,    # ODA 누적액
    "expat_count": 0.20,       # 교민 수
    "diplomatic_year": 0.20,   # 수교연도 (오래될수록 가점)
}
COOPERATION_GRADE_COUNT = 5  # 등급 단계 수 (5단계)

# ── 3) Cooperation Opportunity Score 가중치 ─────────────────────────
OPPORTUNITY_WEIGHTS = {
    "oda_freq": 0.25,      # KOICA ODA 사업 분야별 빈도
    "industry": 0.25,      # 해당국 주요산업 현황
    "keyword": 0.25,       # 외교부 주요정세 키워드
    "history": 0.25,       # 한국과의 협력 이력
}

# ── 4) 유사국가 추천 ─────────────────────────────────────────────────
SIMILARITY_TOP_N = 3       # 기본 추천 개수
CLUSTER_N = 4               # KMeans 군집 개수
RANDOM_STATE = 42           # 재현성을 위한 시드 고정

# ── 4-1) Agent1 raw 데이터 파싱용 설정 (여행경보/안전공지/사회지표) ──
# 여행경보 문자열에 "N단계" 숫자가 없을 때 사용
ADVISORY_KEYWORD_LEVEL = {
    "여행금지": 4,
    "철수권고": 3,
    "여행자제": 2,
    "여행유의": 1,
}
ADVISORY_DEFAULT_LEVEL = 2  # 파싱 실패 시 중간값으로 처리

# 안전공지 개수를 0~100 점수로 환산할 때 기준 (이 건수 이상이면 만점 100)
SAFETY_NOTICE_MAX_COUNT = 10
SAFETY_NOTICE_RECENT_WINDOW_DAYS = 365  # 이 기간 내 공지만 우선 집계, 없으면 전체 건수로 대체

# 실업률/자살률을 0~100 위험도로 환산할 때 기준
UNEMPLOYMENT_RATE_GLOBAL_AVG = 4.9    # % (ILO, 2024)
UNEMPLOYMENT_RATE_MAX = 25.0          # % (고실업 위기국 수준 상한)

SUICIDE_DEATH_RATE_GLOBAL_AVG = 9.1   # 인구 10만명당 (World Bank, 2021)
SUICIDE_DEATH_RATE_MAX = 30.0         # 인구 10만명당 (WHO 통계 최상위권 국가 수준 상한)



# ── 5) ODA 분야 <-> Opportunity 분야 매핑 ───────────────────────────
# 실제 KOICA/외교부 코드북이 확정되면 이 매핑만 교체하면 됨
ODA_TO_OPPORTUNITY = {
    "ICT/디지털": "AI",
    "농업": "스마트팜",
    "보건의료": "의료",
    "교육": "문화",
    "공공행정": "인프라",
    "기후환경": "에너지",
}
