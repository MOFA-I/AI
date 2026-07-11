# app/agents/agent2/loaders/overseas_org_loader.py
import pandas as pd

FILE_PATH = "data/raw/overseas_org_20201231.csv"
ENCODING = "cp949"

COUNTRY_COL = "국가"
COUNTRY_ISO_COL = "국가코드(ISO 2자리 코드)"
ORG_TYPE_COL = "공공기관유형"
ORG_NAME_COL = "공공기관명"
DETAIL_COL = "공공기관진출내용"  # 90.6% 결측, 참고용으로만 남겨둠


def load_overseas_org_by_country(country_nm: str) -> dict:
    """
    특정 국가의 해외진출현황 요약 반환.
    DETAIL_COL은 결측이 많아 count 위주로 사용.
    """
    df = pd.read_csv(FILE_PATH, encoding=ENCODING)
    filtered = df[df[COUNTRY_COL] == country_nm]

    if filtered.empty:
        return {"status": "empty", "country": country_nm, "org_count": 0, "orgs": []}

    return {
        "status": "ok",
        "country": country_nm,
        "org_count": len(filtered),
        "orgs": filtered[[ORG_TYPE_COL, ORG_NAME_COL]].to_dict("records"),
    }


def load_org_count_by_country() -> pd.DataFrame:
    """전체 국가별 진출기관수 집계 (Cooperation Index 계산용)"""
    df = pd.read_csv(FILE_PATH, encoding=ENCODING)
    return df.groupby(COUNTRY_COL).size().reset_index(name="org_count")