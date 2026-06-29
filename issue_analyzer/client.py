import httpx
import xmltodict

from issue_analyzer.config import DATA_GO_KR_API_KEY


def _get(base_url: str, operation: str, params: dict) -> dict:
    query = {"serviceKey": DATA_GO_KR_API_KEY, "returnType": "JSON", **params}
    response = httpx.get(f"{base_url}{operation}", params=query, timeout=10.0)
    response.raise_for_status()
    return response.json()


def _get_xml(base_url: str, operation: str, params: dict) -> dict:
    """CountrySafetyService는 returnType 옵션이 없고 항상 XML로만 응답한다."""
    query = {"serviceKey": DATA_GO_KR_API_KEY, **params}
    response = httpx.get(f"{base_url}{operation}", params=query, timeout=10.0)
    response.raise_for_status()
    return xmltodict.parse(response.text)


TRAVEL_WARNING_BASE = "https://apis.data.go.kr/1262000/TravelWarningServiceV3"
COUNTRY_SAFETY_BASE = "https://apis.data.go.kr/1262000/CountrySafetyService"
SECURITY_ENVIRONMENT_BASE = "https://apis.data.go.kr/1262000/SecurityEnvironmentService"
OVERVIEW_SITUATION_BASE = "https://apis.data.go.kr/1262000/OverviewSituationService"
ENTRANCE_VISA_BASE = "https://apis.data.go.kr/1262000/EntranceVisaService2"



# 여행경보제도 목록조회 (경보 1~4단계). 한글/영문 국가명, ISO코드는 중복 사용 불가.
def get_travel_warning_list(
    country_name: str | None = None,
    country_en_name: str | None = None,
    iso_code: str | None = None,
    numOfRows: int = 10,
    pageNo: int = 1,
) -> dict:
    params = {"numOfRows": numOfRows, "pageNo": pageNo}
    if country_name:
        params["cond[country_name::EQ]"] = country_name
    if country_en_name:
        params["cond[country_en_name::EQ]"] = country_en_name
    if iso_code:
        params["cond[iso_code::EQ]"] = iso_code
    return _get(TRAVEL_WARNING_BASE, "/getTravelWarningListV3", params)


# 국가별 안전정보 목록 조회
def get_country_safety_list(
    title: str | None = None,
    content: str | None = None,
    numOfRows: int = 10,
    pageNo: int = 1,
) -> dict:
    params = {"numOfRows": numOfRows, "pageNo": pageNo}
    if title:
        params["title"] = title
    if content:
        params["content"] = content
    return _get_xml(COUNTRY_SAFETY_BASE, "/getCountrySafetyList", params)


# 국가별 안전정보 단일 조회
def get_country_safety_info(id: str) -> dict:
    """id: 목록 조회 결과의 고유값"""
    return _get_xml(COUNTRY_SAFETY_BASE, "/getCountrySafetyInfo", {"id": id})


# 국가·지역별 치안환경 목록조회 (Agent 2에도 전달)
def get_security_environment_list(
    country_name: str | None = None,
    country_iso_alp2: str | None = None,
    numOfRows: int = 10,
    pageNo: int = 1,
) -> dict:
    params = {"numOfRows": numOfRows, "pageNo": pageNo}
    if country_name:
        params["cond[country_nm::EQ]"] = country_name
    if country_iso_alp2:
        params["cond[country_iso_alp2::EQ]"] = country_iso_alp2
    return _get(SECURITY_ENVIRONMENT_BASE, "/getSecurityEnvironmentList", params)


# 국가·지역별 주요 정세 정보 목록 조회
def get_overview_situation_list(
    country_name: str | None = None,
    country_iso_alp2: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    numOfRows: int = 10,
    pageNo: int = 1,
) -> dict:
    params = {"numOfRows": numOfRows, "pageNo": pageNo}
    if country_name:
        params["cond[country_nm::EQ]"] = country_name
    if country_iso_alp2:
        params["cond[country_iso_alp2::EQ]"] = country_iso_alp2
    if year_from:
        params["cond[year::GT]"] = year_from
    if year_to:
        params["cond[year::LT]"] = year_to
    return _get(OVERVIEW_SITUATION_BASE, "/getOverviewSituationList", params)


# 국가·지역별 입국허가요건 조회 (비자 정보)
def get_entrance_visa_list(
    country_name: str | None = None,
    country_iso_alp2: str | None = None,
    numOfRows: int = 10,
    pageNo: int = 1,
) -> dict:
    params = {"numOfRows": numOfRows, "pageNo": pageNo}
    if country_name:
        params["cond[country_nm::EQ]"] = country_name
    if country_iso_alp2:
        params["cond[country_iso_alp2::EQ]"] = country_iso_alp2
    return _get(ENTRANCE_VISA_BASE, "/getEntranceVisaList2", params)
