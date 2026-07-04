# Agent3 - 데이터 기반 정량 분석

외교부/KOICA 데이터를 기반으로 국가별
1) 위험도 점수, 2) Cooperation Index, 3) Cooperation Opportunity Score(분야별),
4) 유사국가 추천 을 계산하는 정량분석 Agent. (pandas + scikit-learn)

현재는 `data/dummy_data.py`로 생성한 더미데이터로 로직 검증한 상태.

## 폴더 구조

```
agent3/
├── main.py                    # 4대 지표 계산 로직
├── config.py                  # 가중치·설정값 
├── requirements.txt
├── data/
│   └── dummy_data.py          # 더미데이터 생성기 (실제 데이터 연동 시 이 파일만 교체)
├── notebooks/
│   └── agent3_analysis.ipynb  # 결과 시각화/탐색용
└── outputs/
    └── result_sample.json     # 실행 결과 예시
```

## 지표 정의

- **위험도 점수(0~100)**: 여행경보 단계 40% + 안전공지 빈도 30% + 주요정세 키워드 위험도 30%
- **Cooperation Index(5단계)**: 무역규모 30% + ODA누적액 30% + 교민수 20% + 수교연도 20%
- **Cooperation Opportunity Score**: KOICA ODA 분야별 빈도 + 주요산업 현황 + 정세키워드 + 협력이력 → 분야별 점수화·랭킹
- **유사국가 추천**: 위험도·Cooperation Index·분야별 점수를 벡터화 → 코사인 유사도

## 실데이터 연동 시 수정할 부분

1. `data/dummy_data.py`의 `generate_countries()` — 실제 API/DB 조회 코드로 교체 (반환 스키마만 유지하면 `main.py`는 수정 불필요)
2. `config.py`의 `ODA_TO_OPPORTUNITY` — 실제 코드북에 맞게 매핑 수정
3. `config.py`의 가중치들 — 팀 기획 의도에 맞게 조정

## Orchestrator / Agent1·2·4 연동 방법

```python
from main import analyze

result = analyze(
    reference_data=raw,              # 비교 대상 전체 국가 DB (아래 "중요" 참고)
    target_countries=["베트남"],       # Agent1이 사용자 질문에서 뽑아낸 국가. None이면 전체 국가 반환
)
```

반환값은 JSON

```json
{
  "베트남": {
    "risk_score": 48.87,
    "cooperation_index": {"score": 9.28, "grade": 1},
    "opportunity_score": {"AI": 13.8, "스마트팜": 41.7, "...": "..."},
    "opportunity_ranking": [["에너지", 78.8], ["의료", 44.6], "..."],
    "cluster": 0,
    "similar_countries": [["몽골", 0.825], ["필리핀", 0.799], ["라오스", 0.714]]
  }
}
```
