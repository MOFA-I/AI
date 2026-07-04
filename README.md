# 국가 위험도·협력 지수 정량분석 Agent (Agent3)

외교부/KOICA 등 데이터를 기반으로 국가별
1) 위험도 점수, 2) Cooperation Index, 3) Cooperation Opportunity Score(분야별),
4) 유사국가 추천 을 계산하는 정량분석 모듈. 현재는 더미데이터로 로직을 검증한 상태.

## 폴더 구조

```
diplomacy_agent/
├── config.py                  # 가중치·설정값 (여기 숫자만 고치면 전체 반영)
├── requirements.txt
├── README.md
├── data/
│   └── dummy_data.py          # 더미데이터 생성기 (실제 데이터 연동 시 이 파일만 교체)
├── agents/
│   └── agent3_quant.py        # Agent3: 지표 계산 로직 (pandas + scikit-learn)
├── notebooks/
│   └── agent3_analysis.ipynb  # 결과 시각화/탐색용 노트북
└── outputs/
    └── result_sample.json     # 실행 결과 예시
```

## 실데이터 연동 시 수정할 부분
1. `data/dummy_data.py`의 `generate_countries()` — 실제 API/DB 조회 코드로 교체.
   반환 형식(딕셔너리 스키마)만 그대로 유지하면 `agent3_quant.py`는 수정 불필요.
2. `config.py`의 `ODA_TO_OPPORTUNITY` — KOICA/외교부 실제 분야 맞게 매핑 수정.
3. `config.py`의 가중치들 — 실제 정책/기획 의도에 맞게 조정.

## 지표 정의
- **위험도 점수(0~100)**: 여행경보 단계 40% + 안전공지 빈도 30% + 주요정세 키워드 위험도 30%
- **Cooperation Index(5단계)**: 무역규모 30% + ODA누적액 30% + 교민수 20% + 수교연도 20%
- **Cooperation Opportunity Score**: KOICA ODA 분야별 빈도 + 주요산업 현황 + 정세키워드 + 협력이력 → 분야별 점수화·랭킹
- **유사국가 추천**: 위험도·Cooperation Index·분야별 점수를 벡터화 → 코사인 유사도
