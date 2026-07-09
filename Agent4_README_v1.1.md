# Agent 4 — Report Generator

Agent 1(현황)·Agent 2(무역/ODA)·Agent 3(정량지표) 결과를 종합해
**기업/연구자 타깃별 보고서(JSON + HTML)** 를 생성하는 에이전트.

> 일반 사용자는 Orchestrator + Agent 1 + `map_builder.py`로 처리 (Agent 4 미경유)

---

## 핵심 설계 원칙

**LLM은 `briefing`(문장)만 쓴다. 숫자·좌표·판정·차트는 전부 코드가 결정적으로 계산한다.**

| 출력 블록 | 생성 주체 | 파일 |
| --- | --- | --- |
| `briefing.*` (5섹션) | **LLM (Claude)** | `llm.py` + `prompts.py` |
| `cards` (진출판정 포함) | 규칙 | `verdict.py` + `cards.py` |
| `map.layers` | 데이터 | `map_layers.py` + `geo.py` |
| `dashboard.charts` | 데이터 | `dashboard.py` |
| `evidence` | 로그 | `evidence.py` |
| `files.html` | 렌더러 | `html_renderer.py` |

→ 환각 방지 + 판정 근거(`grounds`) 자동 첨부 = **Explainable AI** (발표 포인트)

---

## 폴더 구조

```
agent4/
├── report_generator/          # 메인 패키지
│   ├── __init__.py
│   ├── generator.py           # 진입점 Agent4ReportGenerator — 전체 조립
│   ├── schemas.py             # 입출력 JSON 계약 v1.1의 Pydantic 코드화
│   ├── llm.py                 # Claude 호출 (briefing만) + 규칙 폴백
│   ├── prompts.py             # 기업/연구자 프롬프트 템플릿 (튜닝은 여기서만)
│   ├── verdict.py             # 진출판정 규칙표 (추천/관망/비추천 + 근거)
│   ├── cards.py               # 핵심 지표 카드
│   ├── map_layers.py          # 지도 레이어 JSON (ODA마커·무역호·유사국선)
│   ├── dashboard.py           # 차트 데이터 JSON (산점도·랭킹·트렌드·타임라인)
│   ├── evidence.py            # 전 Agent 작업 로그
│   ├── html_renderer.py       # JSON → HTML (folium/plotly는 여기서만 사용)
│   └── geo.py                 # 국가/지역 좌표 + Nominatim 폴백 + 파일 캐시
├── adapters.py                # Agent1·2 실출력 → 스키마 변환 / Agent3 입력 브릿지
├── map_builder.py             # [팀원 A 제공용] 일반 사용자 여행경보 지도
├── main.py                    # FastAPI 테스트 서버 (POST /report)
├── test_pipeline.py           # 실데이터 E2E 테스트 (LLM 키 없이 동작)
├── sample_data/
│   └── result_sample.json     # Agent 3 실출력 샘플 (agent3 브랜치에서 복사)
├── requirements.txt
└── README.md
```

설계 규칙 두 가지:
- **JSON이 계약, HTML은 표현.** `map_layers.py`/`dashboard.py`는 순수 데이터만 만들고,
  folium/plotly는 `html_renderer.py`에서만 import. React 프론트는 같은 JSON을 직접 렌더하면 됨.
- **LLM 관련 코드는 `llm.py`/`prompts.py` 밖으로 새지 않는다.**

---

## 입출력 계약 (요약)

상세: `schemas.py` (코드가 곧 명세)

**입력 (Orchestrator → Agent 4):**
```json
{
  "request": { "user_query": "...", "target": "기업|연구자", "countries": ["베트남"] },
  "agent1": { "베트남": { "...IssueAnalyzer.analyze() 반환 그대로..." } },
  "agent2": { "베트남": { "trade_volume_usd_million": 79400, "oda_projects": [...], "..." } },
  "agent3": { "베트남": { "risk_score": 48.87, "cooperation_index": {...}, "..." } },
  "logs": [ { "agent": "...", "action": "...", "source": "..." } ]
}
```
- `agent3` = 팀원 C `analyze()` 출력 그대로 (필수)
- `agent1` = 팀원 A 스키마 그대로. `travel_warning` 구조화 필드가 없으면
  `adapters.adapt_agent1()`이 기존 문자열("2단계 여행자제 (일부 지역)")을 파싱
- `agent2` = **제안 스키마** (브랜치 미구현 → 확정 시 `schemas.Agent2Data` 조정).
  없어도(`null`) 동작함 — 관련 레이어/차트만 빠짐

**출력 (Agent 4 → 백엔드/프론트):**
`meta / briefing / cards / map.layers / dashboard.charts / evidence / files`

**타깃별 구성:**

| 블록 | 기업 | 연구자 |
| --- | --- | --- |
| cards | 진출판정(+confidence+grounds)·위험도·협력등급·유망분야 | 위험도·협력지수·군집 |
| map | ODA마커 ⭐ · 무역흐름 ⭐ · 한국기관 · 경보(참고) | ODA마커 · 경보 · 유사국연결 ⭐ |
| charts | 위험도×협력 산점도 · 유망분야랭킹 · 대안국 | + ODA연도트렌드 · 외교타임라인 |
| briefing | 공통 5섹션 | + 한국입장/상대국입장 분리 |

---

## 실행

```bash
pip install -r requirements.txt
cp ../.env.example .env   # ANTHROPIC_API_KEY 입력 (없으면 규칙 폴백으로 동작)

# E2E 테스트 (agent3 실데이터 + agent1/2 더미)
python test_pipeline.py
# → reports/report_기업_*.html, report_연구자_*.html 생성

# API 서버
uvicorn main:app --reload --port 8004
# POST /report (입력 봉투) → 출력 JSON
# GET  /report/last → 마지막 HTML 미리보기
```

코드에서 직접:
```python
from report_generator import Agent4ReportGenerator, Agent4Input
out = Agent4ReportGenerator().generate(Agent4Input(**payload))
out.model_dump()          # JSON 계약
out.files["html"]         # HTML 경로
```

---

## Orchestrator 통합 가이드 (router.py의 TODO 자리)

```python
# orchestrator/router.py 기업·연구자 분기에서:
from report_generator import Agent4ReportGenerator, Agent4Input
from adapters import adapt_agent1

inp = Agent4Input(
    request={"user_query": user_input, "target": user_type,
             "countries": [country_name]},
    agent1={country_name: adapt_agent1(agent1_result)},
    agent2=agent2_result,      # Agent 2 완성 전엔 None
    agent3=agent3_result,      # main.analyze(reference_data, [country_name])
)
return Agent4ReportGenerator().generate(inp).model_dump()
```

`adapters.build_agent3_input()`이 Agent 1·2 실출력 → Agent 3 입력(reference_data)
변환도 담당 (참조 DB 배치 생성 시 사용).

---

## 미확정 / TODO (팀 결정 필요)

1. **Agent 2 스키마 확정** — 현재 `schemas.Agent2Data`는 제안값. 특히 `oda_projects[].region` 필드명은 KOICA CSV 실제 컬럼 확인 후 조정
2. **진출판정 임계값** — `verdict.THRESHOLDS` v0: 추천(위험<40 & 등급≥3) / 비추천(위험>70 or 위험>55&등급≤2) / 관망(그 외). 회의에서 숫자 확정
3. **소스 없는 3필드** — `industry_status`·`keyword_relevance`·`cooperation_history_score`는 `adapters.py`에서 임시 중립값(50). A안(고정 참조테이블) / B안(정세 키워드 자동산출+참조테이블) 중 결정
4. **political_risk_keyword_score** — 현재 `adapters.RISK_KEYWORDS` 단순 가중합. 키워드·가중치 팀 검수
5. PDF 다운로드 (P2, weasyprint)
6. LLM 모델 — briefing은 `claude-sonnet-4-6` 기본 (`AGENT4_LLM_MODEL` 환경변수로 변경 가능). orchestrator의 라우팅은 haiku 유지

---

## 검증 이력

- Agent 3 실출력(`result_sample.json`, 15개국)으로 E2E 통과 (기업·연구자 모두)
- LLM 키 없는 환경에서 폴백으로 완주 확인
- 15개 협력국 전체 좌표 내장 확인

---

## 변경 이력

### v1.1 (2026-07-09) — Agent 2 실구현·Agent 3 신포맷 반영
- **Agent 3 신포맷 대응**: `risk_score` 구조체({score, level, components}) — 구포맷(float)도 자동 승격. `cluster` 제거. `evidence`/`data_sources` 패스스루
- **Agent 2 실데이터 제약 반영** (KOICA 사업정보 API 502 장애):
  - 분야(field) 데이터 부재 → `opportunity_ranking` 차트·`top_opportunity` 카드는 점수 변별력 있을 때만 표시 (`opportunity_meaningful` 가드, API 복구 시 자동 부활)
  - ODA 사업 좌표·지역 없음 → 지도는 국가 중심 **집계 마커**(사업 N건 + 최근 목록). 개별 사업에 lat/lon 오면 개별 마커 자동 전환
  - 한국기관 도시 없음 → 국가 중심 집계 마커
  - **신규**: KOICA 지원실적 CSV의 연도별 금액 → `oda_trend` 차트 실데이터화
  - `sources_used/failed/empty` → Evidence에 "실패→대체" 투명 기록 (기획서 Evidence 요구사항)
- `risk_components` 차트 신설 (위험도 구성요인 분해 — agent3 v2 components)
- `adapters.adapt_agent2()`: 팀원 B collector 원본 → 정규화 스키마 (방어적 키 탐색). **agent2 브랜치 push 후 이 함수만 실키에 맞춰 조정하면 됨**
- `adapters.adapt_agent3()`: 신(단일객체/리스트)·구(국가dict) 포맷 모두 수용
