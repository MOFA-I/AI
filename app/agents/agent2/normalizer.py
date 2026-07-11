# app/agents/agent2/normalizer.py
"""
국가명 정규화.
country_mapping.json(Phase 5 산출물) + 기준표(231개국)를 이용해
입력된 국가명을 소스 데이터가 실제 쓰는 표기로 변환한다.
"""

import json
import pandas as pd

_MAPPING_PATH = "data/country_mapping.json"
_ANCHOR_PATH = "data/raw/country_standard_code.csv"

_mapping_cache = None
_anchor_cache = None


def _load_mapping() -> dict:
    global _mapping_cache
    if _mapping_cache is None:
        with open(_MAPPING_PATH, "r", encoding="utf-8") as f:
            _mapping_cache = json.load(f)
    return _mapping_cache


def _load_anchor_to_iso2() -> dict:
    global _anchor_cache
    if _anchor_cache is None:
        anchor = pd.read_csv(_ANCHOR_PATH, encoding="utf-16", sep="\t")
        _anchor_cache = dict(zip(anchor["국가명(국문)"], anchor["ISO(2자리)"]))
    return _anchor_cache


def normalize_country_name(country_nm: str) -> dict:
    """
    입력된 국가명을 정규화한다.

    처리 순서:
    1. 이미 기준표(231개국)의 정식 표기와 일치하면 그대로 사용
    2. country_mapping.json에 별칭으로 등록돼 있으면 정식 표기로 변환
       (예: "남아공" -> "남아프리카공화국", "미국" -> "미합중국")
    3. 둘 다 없으면 원본 그대로 반환하되 matched=False로 표시
       (에러 아님 - 호출 자체는 원본 이름으로 계속 시도됨)

    Returns:
        {"normalized": str, "iso2": str|None, "matched": bool}
    """
    anchor_to_iso2 = _load_anchor_to_iso2()

    if country_nm in anchor_to_iso2:
        return {"normalized": country_nm, "iso2": anchor_to_iso2[country_nm], "matched": True}

    mapping = _load_mapping()
    if country_nm in mapping:
        entry = mapping[country_nm]
        return {"normalized": entry["matched_to"], "iso2": entry.get("iso2"), "matched": True}

    return {"normalized": country_nm, "iso2": None, "matched": False}