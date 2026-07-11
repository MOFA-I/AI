# app/agents/agent2/selector.py
"""
타입별 소스 조합 결정.

2026-07 업데이트:
- koica_business API 사용 중단 (서버 502/504 지속, 팀 결정)
- Cooperation Opportunity Score(분야별 협력 가능성) 기능 자체를 제품에서 제외하기로 결정
  -> koica_business의 대체 데이터였던 koica_project_list도 함께 제거
  -> Cooperation Index(무역/ODA누적액/교민/수교연도 기반)는 영향 없음, 그대로 유지
"""

from app.agents.agent2.clients.relation_api import get_relation
from app.agents.agent2.clients.trade_api import get_trade
from app.agents.agent2.loaders.overseas_org_loader import load_overseas_org_by_country
from app.agents.agent2.loaders.koica_country_support_loader import (
    load_oda_cumulative_by_country,
    load_oda_yearly_by_country,
)

SOURCE_FUNCTIONS = {
    "relation": get_relation,
    "trade": get_trade,
    "overseas_org": load_overseas_org_by_country,
    "koica_country_support_cumulative": load_oda_cumulative_by_country,
    "koica_country_support_yearly": load_oda_yearly_by_country,
}

TARGET_TYPE_SOURCES = {
    "general": [
        "relation",
        "trade",
        "koica_country_support_cumulative",
    ],
    "business": [
        "relation",
        "trade",
        "koica_country_support_cumulative",
        "overseas_org",
    ],
    "researcher": [
        "relation",
        "trade",
        "koica_country_support_cumulative",
        "koica_country_support_yearly",
        "overseas_org",
    ],
}


def get_sources_for_type(target_type: str) -> list[str]:
    if target_type not in TARGET_TYPE_SOURCES:
        raise ValueError(f"알 수 없는 target_type: {target_type}")
    return TARGET_TYPE_SOURCES[target_type]