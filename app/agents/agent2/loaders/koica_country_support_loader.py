# app/agents/agent2/loaders/koica_country_support_loader.py
import pandas as pd

FILE_PATH = "data/raw/koica_country_support_2024.csv"
ENCODING = "cp949"

REGION_COL = "지역"
COUNTRY_COL = "국가명"
YEAR_COL = "연도"
KRW_COL = "원"
USD_COL = "달러"

EXCLUDE_VALUES = ["국제기구", "일반"]  # 국가 단위 집계에서 제외해야 하는 값


def _load_clean() -> pd.DataFrame:
    df = pd.read_csv(FILE_PATH, encoding=ENCODING)
    df = df[df[REGION_COL] != "국제기구"]
    df = df[~df[COUNTRY_COL].isin(EXCLUDE_VALUES)]
    return df


def load_oda_cumulative_by_country(country_nm: str = None) -> pd.DataFrame:
    """
    국가별 누적 ODA 지원액 (원/달러).
    country_nm 지정 시 해당 국가만, 없으면 전체 반환.
    Cooperation Index의 "ODA 누적액×30%" 계산에 직접 사용.
    """
    df = _load_clean()
    result = df.groupby(COUNTRY_COL)[[KRW_COL, USD_COL]].sum().reset_index()

    if country_nm:
        result = result[result[COUNTRY_COL] == country_nm]

    return result.sort_values(USD_COL, ascending=False)


def load_oda_yearly_by_country(country_nm: str) -> pd.DataFrame:
    """연도별 ODA 추이 (연구자용 트렌드 시각화에 사용)"""
    df = _load_clean()
    filtered = df[df[COUNTRY_COL] == country_nm]
    return filtered.groupby(YEAR_COL)[[KRW_COL, USD_COL]].sum().reset_index()