"""
관계 API / 무역관계 API 테스트 스크립트
(KOICA API는 서버 502라 일단 제외하고, 이 둘이 살아있는지 먼저 확인)

실행 위치: MOFA-I 루트 폴더에서
    python test_relation_trade_api.py
"""

import requests
from app.config import (
    RELATION_API_BASE_URL,
    RELATION_API_ENDPOINT,
    RELATION_API_KEY_PARAM,
    TRADE_API_BASE_URL,
    TRADE_API_ENDPOINT,
    TRADE_API_KEY_PARAM,
    DATA_GO_KR_SERVICE_KEY,
)

TEST_COUNTRY = "베트남"


def test_api(name, base_url, endpoint, key_param):
    print("=" * 60)
    print(f"[{name}] 테스트")
    url = base_url + endpoint
    params = {
        key_param: DATA_GO_KR_SERVICE_KEY,   # serviceKey 또는 ServiceKey (API마다 다름)
        "pageNo": 1,
        "numOfRows": 5,
        "cond[country_nm::EQ]": TEST_COUNTRY,
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        print(f"  URL: {url}")
        print(f"  상태코드: {res.status_code}")
        print(f"  응답 (앞 500자):\n{res.text[:500]}")
    except requests.exceptions.RequestException as e:
        print(f"  요청 실패: {e}")
    print()


if DATA_GO_KR_SERVICE_KEY is None:
    print("DATA_GO_KR_SERVICE_KEY가 None입니다. .env 파일/load_dotenv() 확인하세요.")
else:
    test_api("관계 API", RELATION_API_BASE_URL, RELATION_API_ENDPOINT, RELATION_API_KEY_PARAM)
    test_api("무역관계 API", TRADE_API_BASE_URL, TRADE_API_ENDPOINT, TRADE_API_KEY_PARAM)