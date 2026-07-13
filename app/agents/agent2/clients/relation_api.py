# app/agents/agent2/clients/relation_api.py
from app.config import (
    RELATION_API_BASE_URL,
    RELATION_API_ENDPOINT,
    RELATION_API_KEY_PARAM,
    DATA_GO_KR_SERVICE_KEY,
)
from .base import call_api


def get_relation(country_nm: str) -> dict:
    """국가·지역별 우리나라와의 관계 조회"""
    url = RELATION_API_BASE_URL + RELATION_API_ENDPOINT
    params = {
        RELATION_API_KEY_PARAM: DATA_GO_KR_SERVICE_KEY,
        "pageNo": 1,
        "numOfRows": 10,
        "cond[country_nm::EQ]": country_nm,
    }
    return call_api(url, params)