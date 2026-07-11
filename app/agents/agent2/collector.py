# app/agents/agent2/collector.py
"""
Agent 2 (Intelligence Collector) 진입점.

Orchestrator에서 이 모듈을 쓰려면:

    from app.agents.agent2.collector import collect
    result = collect("베트남", "business")

그게 전부입니다 - 아래 collect() 함수 하나만 호출하면 됩니다.
국가명은 "남아공", "미국"처럼 통용되는 표기도 자동으로 정규화되니
Agent 1이 넘겨주는 자연어 추출 결과를 크게 다듬지 않고 넘겨도 됩니다
(단, 정규화 실패 시 결과의 country_name_matched: false로 확인 가능).
"""

from datetime import datetime, timezone

from app.agents.agent2.selector import get_sources_for_type, SOURCE_FUNCTIONS
from app.agents.agent2.normalizer import normalize_country_name


def _wrap_loader_result(fn, *args, **kwargs) -> dict:
    """
    loader 함수들(pandas 기반)은 client와 반환 형태가 달라서
    여기서 표준 형태({status, data, error})로 통일해준다.
    """
    try:
        result = fn(*args, **kwargs)
        if hasattr(result, "to_dict"):
            data = result.to_dict("records")
            status = "ok" if data else "empty"
        else:
            data = result
            status = result.get("status", "ok") if isinstance(result, dict) else "ok"
        return {"status": status, "data": data, "error": None}
    except Exception as e:
        return {"status": "failed", "data": None, "error": str(e)}


def collect(country_nm: str, target_type: str, iso2: str = None) -> dict:
    """
    Agent 2 진입점 - 특정 국가의 외교/무역/ODA 데이터를 수집한다.

    Args:
        country_nm: 국가명. 한글 정식 표기("베트남") 또는 통용 별칭("남아공", "미국")
                    모두 지원 - country_mapping.json 기준으로 자동 정규화됨.
                    매핑표에 없는 완전히 새로운 표기는 원본 그대로 시도됨
                    (실패해도 에러 아니고 각 소스가 empty로 반환될 뿐).
        target_type: "general" | "business" | "researcher" 중 하나.
        iso2: 명시적으로 ISO2를 알고 있으면 넘겨도 됨 (선택, 없으면 자동 조회됨).

    Returns:
        dict:
        {
            "country_nm": str,                # 입력값 원본 그대로
            "country_nm_normalized": str,     # 실제 소스 조회에 쓰인 정규화된 이름
            "country_name_matched": bool,     # 정규화 성공 여부
            "iso2": str | None,
            "queried_at": str,

            "diplomatic": {"status": ..., "data": ..., "error": ...},
            "trade": {...},
            "oda": {"cumulative": {...}, "yearly": {...}},
            "overseas_presence": {...},
            "_evidence": {"sources_used": [...], "sources_failed": [...], "sources_empty": [...]},
        }

    Note:
        - country_name_matched: false여도 함수는 죽지 않음. 원본 이름으로 그대로
          소스 호출을 시도하고, 매칭 실패로 인해 대부분 empty가 나올 가능성이 높음.
        - "diplomatic"/"trade"의 data는 data.go.kr 원본 JSON 구조 그대로 (평탄화 안 됨).
        - KOICA 사업정보 API(분야별 데이터)는 제외됨 - 팀 결정.

    Example:
        >>> result = collect("남아공", "business")
        >>> result["country_nm_normalized"]
        '남아프리카공화국'
        >>> result["country_name_matched"]
        True
    """
    norm = normalize_country_name(country_nm)
    lookup_nm = norm["normalized"]
    resolved_iso2 = iso2 or norm["iso2"]

    sources_needed = get_sources_for_type(target_type)
    result = {
        "country_nm": country_nm,
        "country_nm_normalized": lookup_nm,
        "country_name_matched": norm["matched"],
        "iso2": resolved_iso2,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "diplomatic": None,
        "trade": None,
        "oda": {
            "cumulative": None,
            "yearly": None,
        },
        "overseas_presence": None,
        "_evidence": {"sources_used": [], "sources_failed": [], "sources_empty": []},
    }

    for source_name in sources_needed:
        fn = SOURCE_FUNCTIONS[source_name]

        if source_name in ("relation", "trade"):
            outcome = fn(lookup_nm)
        else:
            outcome = _wrap_loader_result(fn, lookup_nm)

        if source_name == "relation":
            result["diplomatic"] = outcome
        elif source_name == "trade":
            result["trade"] = outcome
        elif source_name == "koica_country_support_cumulative":
            result["oda"]["cumulative"] = outcome
        elif source_name == "koica_country_support_yearly":
            result["oda"]["yearly"] = outcome
        elif source_name == "overseas_org":
            result["overseas_presence"] = outcome

        if outcome["status"] == "ok":
            result["_evidence"]["sources_used"].append(source_name)
        elif outcome["status"] == "failed":
            result["_evidence"]["sources_failed"].append(source_name)
        elif outcome["status"] == "empty":
            result["_evidence"]["sources_empty"].append(source_name)

    return result