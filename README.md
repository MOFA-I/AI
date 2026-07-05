## Agent 1: Issue Analyzer
사용자가 입력한 국가명을 받아 외교부 공공데이터 API 5종을 호출하고, 보고서에 바로 쓸 수 있는 현황 요약 데이터를 반환한다.  
Orchestrator로부터 `country_name`을 받아 실행되며, 결과는 Agent 3으로 전달된다. 사용되는 API 종류는 아래와 같다.

- 여행경보제도 목록조회
- 국가별 안전정보 목록 조회
  - 국가별 안전정보 단일 조회 (전체 목록 조회 후 고유값 ID 사용)
- 국가·지역별 치안 환경 목록 조회
- 국가·지역별 주요 정세 정보 목록 조회
- 국가·지역별 입국허가요건 조회 (비자 정보)

<br>

#### 사용법
```python
from issue_analyzer.service import IssueAnalyzer

result = IssueAnalyzer().analyze("일본")
```

<br>

#### 출력 형태
```json
{
  "country": "string",
  "travel_warning_level": "string",
  "recent_safety_notices": [
    { "date": "string", "title": "string", "summary": "string" }
  ],
  "security_environment": {
    "current_travel_alarm": "string",
    "unemployment_rate": 0,
    "suicide_death_rate": 0
  },
  "recent_situations": [
    { "date": "string", "event": "string" }
  ],
  "entrance_visa": {
    "general_passport_visa_required": "string",
    "general_passport_visa_note": "string"
  }
}
```

