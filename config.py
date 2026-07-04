# -*- coding: utf-8 -*-
"""
config.py - 프로젝트 전체 설정값 모음

가중치가 코드 여기저기 흩어져 있으면 나중에 정책이 바뀔 때(예: "위험도 가중치를
여행경보 50%로 올려라") 여러 파일을 뒤져야 함. 여기 숫자만 고치면 전체 반영되도록 모아둠.
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
