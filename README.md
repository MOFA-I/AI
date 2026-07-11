# Agent 2 — Intelligence Collector

MOFA Intelligence(외교 공공데이터·AI 활용 경진대회)의 Agent 2.
국가명을 입력받아 외교·무역·ODA 데이터를 수집해서 표준화된 JSON으로 반환한다.

## 빠른 시작

```bash
# 1. 가상환경 생성 (conda 기준)
conda create -n mofa python=3.11 -y
conda activate mofa

# 2. 패키지 설치
pip install -r requirements.txt

# 3. .env 파일 생성
cp .env.example .env
# .env 열어서 DATA_GO_KR_SERVICE_KEY에 발급받은 인증키 입력
# (data.go.kr 마이페이지 > 오픈 API > 각 데이터셋 > "Decoding" 키 사용)
```

## 사용법

```python
from app.agents.agent2.collector import collect

result = collect("베트남", "business")
```

- `country_nm`: 국가명. 한글 정식 표기("베트남") 또는 흔한 통용 별칭("남아공", "미국")
- `target_type`: `"general"` | `"business"` | `"researcher"` 중 하나

자세한 파라미터/반환값 구조는 `app/agents/agent2/collector.py`의 `collect()` docstring 참고.

## 폴더 구조

```
app/agents/agent2/
├── collector.py       # 진입점 - Orchestrator는 이것만 알면 됨
├── selector.py         # 타입별(general/business/researcher) 소스 조합 결정
├── normalizer.py        # 국가명 정규화 (별칭 -> 정식 표기)
├── clients/               # 실시간 API 2개
│   ├── base.py             # 공통 요청 로직 (재시도 3회 포함)
│   ├── relation_api.py
│   └── trade_api.py
└── loaders/                # CSV 2개
├── overseas_org_loader.py
└── koica_country_support_loader.py
```

## 알아둬야 할 것

### 1. 국가 커버리지 제약
- CSV 소스(`overseas_org`: 95개국, `koica_country_support`: 189개국)는 전체 국가를 커버하지 않음.
  데이터 없는 국가는 `status: "empty"`로 반환됨 (에러 아님, 정상 케이스)
- 북한: 기준표 자체에 미등재. 지원 범위 밖.
- 관계/무역관계 API는 원본 텍스트 필드(`diplomatic_relations`, `investment_status` 등)를 파싱하지 않고 그대로 반환함. 필요 시 호출하는 쪽에서 파싱 필요.

### 2. 출력 스키마
`collect()`의 반환값 구조는 `collector.py`의 docstring에 예시와 함께 문서화되어 있음.

```python
{
    "country_nm": str,                # 입력값 원본 그대로
    "country_nm_normalized": str,     # 실제 소스 조회에 쓰인 정규화된 이름
    "country_name_matched": bool,     # 정규화 성공 여부
    "iso2": str | None,
    "queried_at": str,                # ISO 8601 UTC 타임스탬프

    "diplomatic": {                   # 외교 관계 (관계 API 출처)
        "status": "ok" | "failed",
        "data": {...} | None,          # data.go.kr 원본 응답 그대로 (평탄화 안 됨)
        "error": str | None,
    },
    "trade": {                        # 무역 관계 (무역관계 API 출처)
        "status": "ok" | "failed",
        "data": {...} | None,
        "error": str | None,
    },
    "oda": {
        "cumulative": {                # 누적 ODA 지원액 (원/달러)
            "status": "ok" | "failed" | "empty",
            "data": [{"국가명": str, "원": float, "달러": int}] | None,
            "error": str | None,
        },
        "yearly": {                    # 연도별 ODA 지원액 (1991~2023, general 타입엔 None)
            "status": "ok" | "failed" | "empty",
            "data": [{"연도": int, "원": float, "달러": int}, ...] | None,
            "error": str | None,
        },
    },
    "overseas_presence": {            # 한국 기관 해외진출 현황 (business/researcher 타입에만 존재)
        "status": "ok" | "empty",      # 커버리지 95개국뿐이라 empty가 흔함, 정상 케이스
        "data": {"country": str, "org_count": int, "orgs": [...]} | None,
        "error": str | None,
    },

    "_evidence": {                     # 어떤 소스가 성공/실패/공백이었는지 투명하게 노출
        "sources_used": [str],
        "sources_failed": [str],
        "sources_empty": [str],
    },
}
```

## 데이터 출처

| 종류 | 이름 | ID |
|---|---|---|
| API | 외교부_국가·지역별 우리나라와의 관계 | 15099539 |
| API | 외교부_국가·지역별 우리나라와의 무역관계 | 15076258 |
| CSV | 외교부_해외진출현황 (2020) | 15076565 |
| CSV | 한국국제협력단_KOICA 국가별 지원실적 | 15051102 |
| CSV | 외교부_국가·지역별 표준코드 (정규화 기준표) | 15076566 |