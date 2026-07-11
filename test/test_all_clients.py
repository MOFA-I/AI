# MOFA-I 루트에서: python test_all_clients.py
from app.agents.agent2.clients.relation_api import get_relation
from app.agents.agent2.clients.trade_api import get_trade
from app.agents.agent2.clients.koica_business_api import get_koica_business

country = "베트남"

for name, result in [
    ("관계", get_relation(country)),
    ("무역관계", get_trade(country)),
    ("KOICA사업정보", get_koica_business(country_cd="VN")),
]:
    print(f"[{name}] status={result['status']}")
    if result["status"] == "failed":
        print(f"  에러: {result['error']}")
    else:
        print(f"  데이터 일부: {str(result['data'])[:200]}")
    print()