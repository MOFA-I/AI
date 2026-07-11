# app/agents/agent2/clients/trade_api.py
from app.config import (
    TRADE_API_BASE_URL,
    TRADE_API_ENDPOINT,
    TRADE_API_KEY_PARAM,
    DATA_GO_KR_SERVICE_KEY,
)
from .base import call_api


def get_trade(country_nm: str) -> dict:
    """국가·지역별 우리나라와의 무역관계 조회"""
    url = TRADE_API_BASE_URL + TRADE_API_ENDPOINT
    params = {
        TRADE_API_KEY_PARAM: DATA_GO_KR_SERVICE_KEY,
        "pageNo": 1,
        "numOfRows": 10,
        "cond[country_nm::EQ]": country_nm,
    }
    return call_api(url, params)