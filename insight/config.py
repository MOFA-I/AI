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
# calc_opportunity_score()가 실제로 읽는 두 성분(ODA 지원 추세 / 한국 기관 해외진출 수)에 맞춤
OPPORTUNITY_WEIGHTS = {
    "oda_trend": 0.5,      # ODA 지원 추세 (최근 5년 vs 이전 5년)
    "org_presence": 0.5,   # 한국 기관 해외진출 수
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

# ── 4-2) 안전공지/주요정세 위험도 점수 계산용 설정 ──────────────────
# main.py(quick_risk_score)가 참조하지만 이 config.py에는 정의된 적이 없던 값들.
# agent3 브랜치 커밋 히스토리 확인 결과 main.py 쪽만 4번 더 갱신되고 config.py는
# 안 따라와서 원래부터 실행 불가 상태였음 - 아래는 코드 주석(예: "최근 1년",
# top 5 리스트)에 맞춰 추정한 값. POLITICAL_RISK_KEYWORDS는 실제 제품 판단이
# 필요한 콘텐츠라 초안일 뿐 - 검수 필요.
SAFETY_NOTICE_RECENT_WINDOW_DAYS = 365   # "최근 1년 내 공지"
SAFETY_NOTICE_MAX_COUNT = 5              # Agent1이 안전공지를 최대 5건만 주므로 그 값을 만점 기준으로
POLITICAL_RISK_WINDOW_DAYS = 365         # "최근 1년 내 정세 이벤트"
POLITICAL_RISK_FREQUENCY_BONUS = 5       # 위험 키워드 매칭 건당 추가 가산점 (최대 3건)
ODA_TREND_RECENT_YEARS = 5               # "최근 5년 vs 이전 5년" ODA 추세 비교

# 주요정세 이벤트 텍스트 키워드 매칭 → 위험도 점수(0~100). 값이 클수록 위험.
# 정상적인 정권 교체(선거/내각 출범 등)는 의도적으로 키워드에서 제외 - 0점 처리됨.
# TODO(제품 검수 필요): 아래 키워드/점수는 임시 초안. 실제 서비스 전 재검토 필요.
POLITICAL_RISK_KEYWORDS = {
    90: ["쿠데타", "내전", "전쟁", "계엄", "비상사태", "테러"],
    60: ["유혈", "무력 충돌", "국경 분쟁", "경제 제재", "폭동"],
    30: ["대규모 시위", "외교 갈등", "정정 불안"],
}

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
