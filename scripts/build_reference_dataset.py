"""
Agent3의 cooperation_index/opportunity_score/similar_countries 계산에 쓰이는
참조국(비교 대상) 데이터셋을 실제 API로 채워 reference_data/countries.json에 저장한다.

매 요청마다 15개국을 실시간 조회하면 느리고 외부 API를 과도하게 두드리게 되므로,
이 스크립트를 미리(1회) 돌려서 결과를 캐싱해두고 orchestrator는 이 JSON만 읽는다.
갱신하고 싶으면 이 스크립트를 다시 실행하면 된다.

실행 (반드시 레포 루트에서, Agent2가 data/raw/*.csv를 상대경로로 읽기 때문):
    python scripts/build_reference_dataset.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from issue_analyzer.service import IssueAnalyzer
from app.agents.agent2.collector import collect

# agent3의 원래 더미데이터(data/dummy_data.py) 기준 참조국 15개
REFERENCE_COUNTRIES = [
    "베트남", "인도네시아", "필리핀", "우즈베키스탄", "케냐",
    "에티오피아", "몽골", "캄보디아", "라오스", "미얀마",
    "가나", "탄자니아", "네팔", "방글라데시", "볼리비아",
]

OUTPUT_PATH = REPO_ROOT / "reference_data" / "countries.json"


def build() -> dict:
    analyzer = IssueAnalyzer()
    dataset = {}
    for country in REFERENCE_COUNTRIES:
        print(f"[{country}] 수집 중...")
        try:
            agent1_data = analyzer.analyze(country)
            agent2_data = collect(country, "researcher")
            dataset[country] = {"agent1_data": agent1_data, "agent2_data": agent2_data}
        except Exception as e:
            print(f"[{country}] 실패, 참조국에서 제외: {e}")
    return dataset


if __name__ == "__main__":
    dataset = build()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{len(dataset)}개국 저장 완료: {OUTPUT_PATH}")
