# app/config.py
from dotenv import load_dotenv
load_dotenv()

import os

RELATION_API_BASE_URL = "https://apis.data.go.kr/1262000/OverviewKorRelationService"
RELATION_API_ENDPOINT = "/getOverviewKorRelationList"
RELATION_API_KEY_PARAM = "serviceKey"

TRADE_API_BASE_URL = "https://apis.data.go.kr/1262000/CountryKorTradeService2"
TRADE_API_ENDPOINT = "/getCountryKorTradeList2"
TRADE_API_KEY_PARAM = "ServiceKey"

KOICA_BUSINESS_API_BASE_URL = "https://apis.data.go.kr/B260003/BsnsAddService"
KOICA_BUSINESS_NATION_ENDPOINT = "/getBsnsInfoNationList"
KOICA_BUSINESS_REALM_ENDPOINT = "/getBsnsInfoRealmList"
KOICA_BUSINESS_API_KEY_PARAM = "serviceKey"

# Phase 2 남은 일: 코드표 문서(15~16p) 확인 후 채우기
KOICA_BSNS_TY_CD_MAP = {}      # 사업유형코드
KOICA_SPORT_REALM_CD_MAP = {}  # 분야코드
KOICA_NATION_CD_MAP = {}       # KOICA 자체 국가코드

DATA_GO_KR_SERVICE_KEY = os.getenv("DATA_GO_KR_API_KEY")