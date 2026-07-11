# app/agents/agent2/clients/koica_business_api.py
from app.config import (
    KOICA_BUSINESS_API_BASE_URL,
    KOICA_BUSINESS_NATION_ENDPOINT,
    KOICA_BUSINESS_API_KEY_PARAM,
    DATA_GO_KR_SERVICE_KEY,
)
from .base import call_api


def get_koica_business(country_cd: str, year: str = "2025", bsns_ty_cd: str = "0102") -> dict:
    """
    ODA 국가별 사업목록 조회
    주의: 서버가 502/504를 내뱉는 게 Phase 2에서 확인됨 - 우리 코드 문제 아님
    country_cd: KOICA 자체 국가코드일 가능성 있음 (ISO2와 다를 수 있음, Phase 5에서 매핑표 필요)
    """
    url = KOICA_BUSINESS_API_BASE_URL + KOICA_BUSINESS_NATION_ENDPOINT
    params = {
        KOICA_BUSINESS_API_KEY_PARAM: DATA_GO_KR_SERVICE_KEY,
        "pageNo": 1,
        "numOfRows": 10,
        "P_YEAR": year,
        "P_BSNS_TY_CD": bsns_ty_cd,
        "P_NATION_CD": country_cd,
    }
    return call_api(url, params)