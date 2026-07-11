# test/test_collector_full.py
import json
from app.agents.agent2.collector import collect

TEST_CASES = [
    ("필리핀", "general"),
    ("베트남", "business"),
    ("몽골", "researcher"),
]

for country, t_type in TEST_CASES:
    print("=" * 70)
    print(f"### [{country} / {t_type}] ###")
    print("=" * 70)

    result = collect(country, t_type)

    print("\n--- diplomatic ---")
    print(json.dumps(result["diplomatic"], ensure_ascii=False, indent=2, default=str))

    print("\n--- trade ---")
    print(json.dumps(result["trade"], ensure_ascii=False, indent=2, default=str))

    print("\n--- oda.cumulative ---")
    print(json.dumps(result["oda"]["cumulative"], ensure_ascii=False, indent=2, default=str))

    print("\n--- oda.yearly (앞 3개만) ---")
    yearly = result["oda"]["yearly"]
    if yearly and yearly.get("data"):
        print(json.dumps(yearly["data"][:3], ensure_ascii=False, indent=2, default=str))
    else:
        print(json.dumps(yearly, ensure_ascii=False, indent=2, default=str))

    print("\n--- overseas_presence ---")
    print(json.dumps(result["overseas_presence"], ensure_ascii=False, indent=2, default=str))

    print("\n--- _evidence ---")
    print(json.dumps(result["_evidence"], ensure_ascii=False, indent=2))

    print("\n")