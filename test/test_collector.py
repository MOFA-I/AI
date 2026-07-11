# test/test_collector.py
import json
from app.agents.agent2.collector import collect

TEST_CASES = [
    ("필리핀", "general"),
    ("베트남", "business"),
    ("몽골", "researcher"),
]

for country, t_type in TEST_CASES:
    print("=" * 60)
    print(f"[{country} / {t_type}]")
    result = collect(country, t_type)
    print(json.dumps(result["_evidence"], ensure_ascii=False, indent=2))
    print(f"diplomatic status: {result['diplomatic']['status'] if result['diplomatic'] else 'N/A'}")