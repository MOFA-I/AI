import html

from issue_analyzer import client


def _items(api_response: dict) -> list[dict]:
    """공통 응답 구조(response.body.items.item)에서 결과 리스트를 꺼낸다. item이 1개면 dict로 오므로 리스트로 통일."""
    items = api_response.get("response", {}).get("body", {}).get("items")
    if not items:
        return []
    item = items.get("item")
    if item is None:
        return []
    return item if isinstance(item, list) else [item]


def _travel_warning_level(entry: dict) -> str | None:
    """attention(1단계)~ban(4단계) 중 활성화된 가장 높은 단계를 찾는다. _partial이면 일부 지역에만 적용."""
    levels = [
        (1, "여행유의", "attention"),
        (2, "여행자제", "control"),
        (3, "철수권고", "limita"),
        (4, "여행금지", "ban"),
    ]
    highest = None
    for level, label, key in levels:
        full = entry.get(key) or entry.get(f"{key}_yna")
        partial = entry.get(f"{key}_partial") or entry.get(f"{key}_yn_partial")
        if full or partial:
            scope = "전역" if full else "일부 지역"
            highest = f"{level}단계 {label} ({scope})"
    return highest


class IssueAnalyzer:
    """사용자 입력에서 국가/이슈를 추출하고, 관련 외교부 데이터를 모아 현황을 요약한다."""

    def analyze(self, country_name: str) -> dict:
        warning_items = _items(client.get_travel_warning_list(country_name=country_name))
        safety_items = _items(client.get_country_safety_list(content=country_name))
        security_items = _items(client.get_security_environment_list(country_name=country_name))
        situation_items = _items(client.get_overview_situation_list(country_name=country_name))
        visa_items = _items(client.get_entrance_visa_list(country_name=country_name))

        security = security_items[0] if security_items else {}
        visa = visa_items[0] if visa_items else {}

        return {
            "country": country_name,
            "travel_warning_level": _travel_warning_level(warning_items[0]) if warning_items else None,
            "recent_safety_notices": [
                html.unescape(item.get("content", "")).replace("\r\n", " ")[:200]
                for item in safety_items[:5]
            ],
            "security_environment": {
                "current_travel_alarm": security.get("current_travel_alarm"),
                "unemployment_rate": security.get("unemployment_rate"),
                "suicide_death_rate": security.get("suicide_death_rate"),
            },
            "recent_situations": [
                {
                    "date": f"{item.get('year')}-{item.get('month'):02}-{item.get('day'):02}",
                    "event": item.get("situation_info_cn"),
                }
                for item in situation_items[:5]
            ],
            "entrance_visa": {
                "general_passport_visa_required": visa.get("gnrl_pspt_visa_yn"),
                "general_passport_visa_note": visa.get("gnrl_pspt_visa_cn"),
            },
        }
