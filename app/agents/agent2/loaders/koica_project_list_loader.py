# app/agents/agent2/loaders/koica_project_list_loader.py
"""
2026-07 기준 미사용. Cooperation Opportunity Score(분야별 협력 가능성) 기능이
제품에서 제외되면서, 이 기능의 유일한 용도였던 이 loader도 함께 제외됨.
selector.py/collector.py에서 더 이상 import하지 않음.
(참고: 실행 시 국가 필터링이 안 되는 버그가 있었으나, 기능 자체가 제외되어 수정 불필요)
"""
import pandas as pd

FILE_PATH = "data/raw/koica_project_list_202507.csv"
ENCODING = "cp949"
PROJECT_NM_COL = "사업명"


def load_project_list() -> pd.DataFrame:
    return pd.read_csv(FILE_PATH, encoding=ENCODING)


def extract_country_guess_from_name(country_nm: str = None, df: pd.DataFrame = None) -> pd.DataFrame:
    if df is None:
        df = load_project_list()
    df = df.copy()
    df["country_guess"] = df[PROJECT_NM_COL].str.split().str[0]
    if country_nm:
        df = df[df["country_guess"] == country_nm]
    return df