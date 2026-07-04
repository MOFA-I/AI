# -*- coding: utf-8 -*-
"""
data/dummy_data.py

더미데이터 생성 모듈.
- 실제 API/DB 연동 전, 로직 검증용 국가별 원본 데이터를 생성한다.
- 실데이터로 교체할 때는 이 파일의 generate_countries() 반환 형식만 맞추면 됨.
"""

import random

random.seed(42)  # 재현 가능하도록 고정 (원하면 제거)

COUNTRIES = [
    "베트남", "인도네시아", "필리핀", "우즈베키스탄", "케냐",
    "에티오피아", "몽골", "캄보디아", "라오스", "미얀마",
    "가나", "탄자니아", "네팔", "방글라데시", "볼리비아",
]

# KOICA ODA 중점 분야 (예시)
ODA_FIELDS = ["농업", "보건의료", "교육", "공공행정", "기후환경", "ICT/디지털"]

# 협력 가능성 스코어링 대상 분야
OPPORTUNITY_FIELDS = ["AI", "스마트팜", "의료", "문화", "인프라", "에너지"]


def _rand_range(lo, hi, as_int=True):
    v = random.uniform(lo, hi)
    return int(round(v)) if as_int else round(v, 2)


def generate_countries():
    """
    국가별 원본(raw) 데이터를 생성한다.
    반환: { 국가명: { ...raw fields... } }
    """
    data = {}
    for country in COUNTRIES:
        data[country] = {
            # --- 위험도 점수 원본 ---
            "travel_advisory_level": random.choice([1, 1, 1, 2, 2, 3, 4]),
            "safety_notice_count_monthly": _rand_range(0, 15),
            "political_risk_keyword_score": _rand_range(0, 100),

            # --- Cooperation Index 원본 ---
            "trade_volume_usd_million": _rand_range(50, 20000),
            "oda_cumulative_usd_million": _rand_range(10, 3000),
            "expat_count": _rand_range(200, 200000),
            "diplomatic_year": random.choice(range(1948, 2021)),

            # --- Cooperation Opportunity Score 원본 ---
            "koica_oda_field_freq": {f: _rand_range(0, 20) for f in ODA_FIELDS},
            "industry_status": {
                "AI": _rand_range(0, 100),
                "스마트팜": _rand_range(0, 100),
                "의료": _rand_range(0, 100),
                "문화": _rand_range(0, 100),
                "인프라": _rand_range(0, 100),
                "에너지": _rand_range(0, 100),
            },
            "keyword_relevance": {
                f: _rand_range(0, 100) for f in OPPORTUNITY_FIELDS
            },
            "cooperation_history_score": {
                f: _rand_range(0, 100) for f in OPPORTUNITY_FIELDS
            },
        }
    return data


if __name__ == "__main__":
    import json
    d = generate_countries()
    print(json.dumps(d, ensure_ascii=False, indent=2)[:1500], "...")
