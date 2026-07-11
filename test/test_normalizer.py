# test/test_normalizer.py 수정
from app.agents.agent2.collector import collect
import json

result = collect("남아공", "business")
print(f"원본: {result['country_nm']}")
print(f"정규화: {result['country_nm_normalized']}")
print(f"매칭 성공: {result['country_name_matched']}")
print(f"diplomatic status: {result['diplomatic']['status']}")
print(f"trade status: {result['trade']['status']}")
print(f"oda.cumulative status: {result['oda']['cumulative']['status'] if result['oda']['cumulative'] else 'N/A'}")
print(f"overseas_presence status: {result['overseas_presence']['status'] if result['overseas_presence'] else 'N/A'}")
print()
print(json.dumps(result["_evidence"], ensure_ascii=False, indent=2))