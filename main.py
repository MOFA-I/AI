"""
agent1_result = IssueAnalyzer().analyze(country_name)
agent2_result = IntelligenceCollector().collect(country_name)   # 아직 없으면 None
agent3_result = InsightGenerator().analyze(agent1_result, agent2_result)
report = ReportGenerator().generate(agent1_result, agent2_result, agent3_result, user_type)


일반 여행자용 "위험도 점수만 빠르게" 필요한 경우를 위해 quick_risk_score()도
별도로 노출한다. Orchestrator가 사용자 타입(여행자/기업/연구자)에 따라
InsightGenerator 전체를 돌릴지, quick_risk_score만 쓸지 선택하면 된다.

"""

from __future__ import annotations
import sys
import os
import re
import json
import datetime as _dt

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

import config

# 0) Agent3Analyzer - 여러 국가를 한 번에 비교분석하는 내부 계산 엔진
#    (Cooperation Index / Opportunity Score / 유사국가 추천은 비교 대상
#     국가군이 있어야 정규화·유사도 계산이 성립하해서 배치 엔진으로 둠)
class Agent3Analyzer:
    # 정량 분석 파이프라인. raw dict -> DataFrame -> 4대 지표 -> (선택)군집/PCA

    def __init__(self, raw_data: dict):
        self.raw = raw_data
        self.countries = list(raw_data.keys())
        self.df = self._build_base_dataframe()

    def _build_base_dataframe(self) -> pd.DataFrame:
        rows = []
        for country, v in self.raw.items():
            rows.append({
                "country": country,
                "travel_advisory_level": v["travel_advisory_level"],
                "safety_notice_count_monthly": v["safety_notice_count_monthly"],
                "political_risk_keyword_score": v["political_risk_keyword_score"],
                "expat_count": v["expat_count"],
                "diplomatic_year": v["diplomatic_year"],
                "trade_volume": v["trade_volume"], # 무역 규모
                "oda_cumulative_usd_million": v["oda_cumulative_usd_million"],
                "oda_trend_score": v["oda_trend_score"],
                "org_count": v["org_count"],
            })
        return pd.DataFrame(rows).set_index("country")

    def calc_risk_score(self) -> pd.Series:
        df = self.df
        w = config.RISK_WEIGHTS
        advisory_scaled = MinMaxScaler((0, 100)).fit_transform(df[["travel_advisory_level"]]).flatten()
        notice_scaled = MinMaxScaler((0, 100)).fit_transform(df[["safety_notice_count_monthly"]]).flatten()
        keyword_score = df["political_risk_keyword_score"].to_numpy()
        risk = (
            advisory_scaled * w["travel_advisory"]
            + notice_scaled * w["safety_notice"]
            + keyword_score * w["political_keyword"]
        )
        return pd.Series(np.round(risk, 2), index=df.index, name="risk_score")

    def calc_cooperation_index(self) -> pd.DataFrame:
        df = self.df
        w = config.COOPERATION_WEIGHTS
        scaler = MinMaxScaler((0, 100))
        trade_s = scaler.fit_transform(df[["trade_volume"]]).flatten() # 무역 규모 
        oda_s = scaler.fit_transform(df[["oda_cumulative_usd_million"]]).flatten()
        expat_s = scaler.fit_transform(df[["expat_count"]]).flatten()
        year_s = scaler.fit_transform(-df[["diplomatic_year"]]).flatten()  # 오래될수록 가점

        score = (
            trade_s * w["trade_volume"] # 무역 규모
            + oda_s * w["oda_cumulative"]
            + expat_s * w["expat_count"]
            + year_s * w["diplomatic_year"]
        )
        score = pd.Series(np.round(score, 2), index=df.index, name="score")

        grade = pd.qcut(
            score.rank(method="first"), config.COOPERATION_GRADE_COUNT,
            labels=list(range(1, config.COOPERATION_GRADE_COUNT + 1))
        ).astype(int)
        grade.name = "grade"
        return pd.concat([score, grade], axis=1)

    def calc_opportunity_score(self) -> pd.Series:
        w = config.OPPORTUNITY_WEIGHTS
        df = self.df
        scaler = MinMaxScaler((0, 100))

        trend_s = scaler.fit_transform(df[["oda_trend_score"]]).flatten()
        org_s = scaler.fit_transform(df[["org_count"]]).flatten()

        score = trend_s * w["oda_trend"] + org_s * w["org_presence"]
        return pd.Series(np.round(score, 2), index=df.index, name="opportunity_score")

    def build_feature_matrix(self, risk, coop, opp) -> pd.DataFrame:
        return pd.concat([
            risk,
            coop["score"].rename("coop_score"),
            opp.rename("opportunity_score"),
        ], axis=1)

    def similarity_matrix(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        scaled = MinMaxScaler().fit_transform(feature_df.to_numpy())
        sim = cosine_similarity(scaled)
        return pd.DataFrame(sim, index=feature_df.index, columns=feature_df.index)

    def recommend_similar(self, sim_matrix: pd.DataFrame, target: str, top_n: int = None):
        top_n = top_n or config.SIMILARITY_TOP_N
        if target not in sim_matrix.index:
            raise ValueError(f"'{target}' 은(는) 데이터에 없습니다.")
        s = sim_matrix.loc[target].drop(target).sort_values(ascending=False)
        return s.head(top_n)

    def cluster_countries(self, feature_df: pd.DataFrame) -> pd.Series:
        n_samples = len(feature_df)
        k = min(config.CLUSTER_N, n_samples)  # 참조국 수가 적으면 군집 수도 줄임
        if k < 2:
            return pd.Series([0] * n_samples, index=feature_df.index, name="cluster")
        scaled = MinMaxScaler().fit_transform(feature_df.to_numpy())
        km = KMeans(n_clusters=k, random_state=config.RANDOM_STATE, n_init=10)
        labels = km.fit_predict(scaled)
        return pd.Series(labels, index=feature_df.index, name="cluster")

    def pca_2d(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        scaled = MinMaxScaler().fit_transform(feature_df.to_numpy())
        n_components = min(2, scaled.shape[0], scaled.shape[1])
        if n_components < 1:
            return pd.DataFrame(index=feature_df.index)
        coords = PCA(n_components=n_components, random_state=config.RANDOM_STATE).fit_transform(scaled)
        cols = [f"pc{i+1}" for i in range(n_components)]
        return pd.DataFrame(coords, index=feature_df.index, columns=cols)

    def run_all(self):
        risk = self.calc_risk_score()
        coop = self.calc_cooperation_index()
        opp = self.calc_opportunity_score()
        feature_df = self.build_feature_matrix(risk, coop, opp)
        sim = self.similarity_matrix(feature_df)
        clusters = self.cluster_countries(feature_df)
        pca_coords = self.pca_2d(feature_df)
        return {
            "risk_score": risk,
            "cooperation_index": coop,
            "opportunity_score": opp,
            "feature_matrix": feature_df,
            "similarity_matrix": sim,
            "cluster": clusters,
            "pca_coords": pca_coords,
        }


# 1) 위험도 점수
def _extract_advisory_level(agent1_data: dict) -> int:
    # 3단계 철수권고 (일부 지역)' 같은 문자열에서 1~4단계 숫자 추출
    text = (
        agent1_data.get("security_environment", {}).get("current_travel_alarm")
        or agent1_data.get("travel_warning_level")
        or ""
    )
    m = re.search(r"([1-4])\s*단계", text)
    if m:
        return int(m.group(1))
    for keyword, level in config.ADVISORY_KEYWORD_LEVEL.items():
        if keyword in text:
            return level
    return config.ADVISORY_DEFAULT_LEVEL


def _safety_notice_score(agent1_data: dict) -> tuple[float, int]:
    # 안전공지 리스트를 0~100 점수로 환산.
    # 외교부 API에 최근 1년 내 공지가 있으면 그것만 세고, 없으면 전체 리스트 건수로 대체
    
    notices = agent1_data.get("recent_safety_notices") or []
    today = _dt.date.today()
    recent = []
    for n in notices:
        try:
            d = _dt.date.fromisoformat(n.get("date", ""))
            if (today - d).days <= config.SAFETY_NOTICE_RECENT_WINDOW_DAYS:
                recent.append(n)
        except (ValueError, TypeError):
            continue
    count = len(recent) if recent else len(notices)
    score = min(count, config.SAFETY_NOTICE_MAX_COUNT) / config.SAFETY_NOTICE_MAX_COUNT * 100
    return round(score, 2), count


def _political_situation_risk_score(agent1_data: dict) -> tuple[float, list]:
    situations = agent1_data.get("recent_situations") or []
    today = _dt.date.today()

    def _within_window(s: dict) -> bool:
        try:
            d = _dt.date.fromisoformat(s.get("date", ""))
            return (today - d).days <= config.POLITICAL_RISK_WINDOW_DAYS
        except (ValueError, TypeError):
            return True  # 날짜 파싱 실패하면 배제하지 않고 포함

    def _match(pool: list) -> list:
        matched = []
        for s in pool:
            event_text = s.get("event", "")
            for severity in sorted(config.POLITICAL_RISK_KEYWORDS.keys(), reverse=True):
                if any(kw in event_text for kw in config.POLITICAL_RISK_KEYWORDS[severity]):
                    matched.append((event_text, severity))
                    break
        return matched

    recent = [s for s in situations if _within_window(s)]
    pool = recent if recent else situations  # 기간 내 이벤트가 아예 없으면 전체로 폴백
    matched = _match(pool)

    if not matched:
        return 0.0, []

    max_severity = max(sev for _, sev in matched)
    extra_events = min(len(matched) - 1, 3)  # 추가 매칭은 최대 3건까지만 가산 반영
    score = min(100, max_severity + extra_events * config.POLITICAL_RISK_FREQUENCY_BONUS)
    return round(float(score), 2), matched

# 위험도 점수만 계산하고 Agent2 안 거침 (일반 여행자용)
def quick_risk_score(agent1_data: dict) -> dict:
    w = config.RISK_WEIGHTS
    advisory_level = _extract_advisory_level(agent1_data)
    advisory_score = (advisory_level - 1) / (4 - 1) * 100
    notice_score, notice_count = _safety_notice_score(agent1_data)
    political_score, matched_events = _political_situation_risk_score(agent1_data)

    total = (
        advisory_score * w["travel_advisory"]
        + notice_score * w["safety_notice"]
        + political_score * w["political_keyword"]
    )
    return {
        "score": round(total, 2),
        "level": advisory_level,
        "level_label": f"{advisory_level}단계",
        "components": {
            "travel_advisory": round(advisory_score, 2),
            "safety_notice_freq": notice_score,
            "political_keyword_risk": political_score,
        },
        "notice_count_used": notice_count,
        "matched_risk_events": [{"event": e, "severity": s} for e, s in matched_events],
    }

# 2) InsightGenerator
# 1-2) Agent2 실제 스키마 파싱

# agent2_data['oda']['cumulative']['data'][0]['달러'] 를 추출
def _extract_oda_cumulative_usd(agent2_data: dict) -> float:
    node = ((agent2_data or {}).get("oda") or {}).get("cumulative") or {}
    if node.get("status") != "ok":
        return 0.0
    data = node.get("data") or []
    if not data:
        return 0.0
    return float(data[0].get("달러", 0) or 0)


def _extract_oda_trend_score(agent2_data: dict) -> float:
    """
    agent2_data['oda']['yearly']['data'] (연도별 [{'연도':int,'달러':int}, ...])에서
    최근 config.ODA_TREND_RECENT_YEARS년의 합계를 그 이전 같은 기간 합계와 비교해
    "증가 추세면 높은 점수" 식으로 0~100 근사치 계산
    """
    node = ((agent2_data or {}).get("oda") or {}).get("yearly") or {}
    if node.get("status") != "ok":
        return 0.0
    data = node.get("data") or []
    if len(data) < 2:
        return 0.0

    sorted_data = sorted(data, key=lambda d: d.get("연도", 0))
    n = config.ODA_TREND_RECENT_YEARS
    recent = sorted_data[-n:]
    previous = sorted_data[-2 * n:-n] if len(sorted_data) >= 2 * n else sorted_data[:-n]

    recent_sum = sum(d.get("달러", 0) or 0 for d in recent)
    previous_sum = sum(d.get("달러", 0) or 0 for d in previous)

    if previous_sum <= 0:
        return 100.0 if recent_sum > 0 else 0.0

    growth_ratio = recent_sum / previous_sum  # 1.0 = 변화 없음, 2.0 = 2배 증가
    score = min(100.0, max(0.0, (growth_ratio - 1.0) * 100))
    return round(score, 2)

# agent2_data['overseas_presence']['data']['org_count'] 추출
def _extract_org_count(agent2_data: dict) -> float:
    node = (agent2_data or {}).get("overseas_presence") or {}
    if node.get("status") != "ok":
        return 0.0
    data = node.get("data") or {}
    return float(data.get("org_count", 0) or 0)


def _build_country_row(agent1_data: dict, agent2_data: dict) -> dict:
    """
    agent1_data + agent2_data(raw) 한 쌍을 Agent3Analyzer가 바로 쓸 수 있는
    flat 딕셔너리로 변환 
    질문받은 국가뿐 아니라 참조국(비교 대상) 처리에서도 재사용
    """
    risk = quick_risk_score(agent1_data)
    missing = [k for k in ("expat_count", "diplomatic_year") if k not in agent1_data]
    if missing:
        raise KeyError(
            f"agent1_data({agent1_data.get('country', '?')})에 {missing} 필드가 없습니다. "
            f"Cooperation Index 계산에는 Agent1이 제공하는 expat_count(교민수)/"
            f"diplomatic_year(수교연도)가 필요합니다."
        )
    return {
        "travel_advisory_level": risk["level"],
        "safety_notice_count_monthly": risk["notice_count_used"],
        "political_risk_keyword_score": risk["components"]["political_keyword_risk"],
        "expat_count": agent1_data["expat_count"],
        "diplomatic_year": agent1_data["diplomatic_year"],
        "trade_volume": _extract_trade_volume(agent2_data),  # 무역 규모 데이터 매핑 추가
        "oda_cumulative_usd_million": _extract_oda_cumulative_usd(agent2_data),
        "oda_trend_score": _extract_oda_trend_score(agent2_data),
        "org_count": _extract_org_count(agent2_data),
    }, risk


class InsightGenerator:
    def analyze(self, agent1_data: dict, agent2_data: dict | None = None,
                reference_dataset: dict | None = None) -> dict:
        country = agent1_data.get("country", "UNKNOWN")
        risk = quick_risk_score(agent1_data)

        result = {
            "country": country,
            "risk_score": risk,
            "cooperation_index": None,
            "opportunity_score": None,
            "similar_countries": None,
            # Agent1 원본 데이터를 가공 없이 그대로 넘김 - Agent4 뉴스/근거에 바로 사용
            "evidence": {
                "recent_safety_notices": agent1_data.get("recent_safety_notices", []),
                "recent_situations": agent1_data.get("recent_situations", []),
                "entrance_visa": agent1_data.get("entrance_visa", {}),
            },
            "data_sources": {
                "risk_score": "외교부 해외안전여행 API (여행경보 단계 / 안전공지 건수 / 주요정세 키워드 매칭) → Agent3가 0~100 점수로 변환",
                "evidence": "외교부 해외안전여행 API (Agent1) - 가공 없이 원본 그대로 전달",
                "cooperation_index":"무역규모(Agent2 trade.volume) + 교민수·수교연도(Agent1) + KOICA 국가별 지원실적 CSV(15051102)",
                "opportunity_score":"KOICA 국가별 지원실적 CSV(15051102) + 외교부 해외진출현황 CSV(15076565)",
                "similar_countries": "위험도, 협력지수, 기회지수를 이용한 비교 분석 (참조국 데이터셋: Orchestrator 제공)",
            },
            "meta": {"agent2_data_provided": bool(agent2_data)},
        }

        if agent2_data:
            self._fill_cooperation_and_opportunity(result, country, agent1_data, agent2_data, risk, reference_dataset)

        return result

    def _fill_cooperation_and_opportunity(self, result, country, agent1_data, agent2_data, risk, reference_dataset=None):
        if reference_dataset:
            reference = {}
            for ref_country, ref_raw in reference_dataset.items():
                try:
                    row, _ = _build_country_row(ref_raw["agent1_data"], ref_raw.get("agent2_data") or {})
                    reference[ref_country] = row
                except (KeyError, TypeError) as e:
                    print(f"[경고] 참조국 '{ref_country}' 데이터 처리 실패, 비교 대상에서 제외: {e}")
            reference_source_note = f"Orchestrator가 제공한 참조국 {len(reference)}개국 실데이터"
        

        row, _ = _build_country_row(agent1_data, agent2_data)
        reference[country] = row

        analyzer = Agent3Analyzer(reference)
        out = analyzer.run_all()
        similar = analyzer.recommend_similar(out["similarity_matrix"], country)

        result["cooperation_index"] = {
            "score": float(out["cooperation_index"].loc[country, "score"]),
            "grade": int(out["cooperation_index"].loc[country, "grade"]),
        }
        result["opportunity_score"] = float(out["opportunity_score"][country])
        result["similar_countries"] = [[k, float(v)] for k, v in similar.items()]

        result["data_sources"]["cooperation_index"] = (
            "무역규모 = 관세청/무역협회 통계 API (Agent2 trade.volume), "
            "ODA누적액 = 외교부 무역관계/KOICA ODA API (Agent2 oda.cumulative), "
            "교민수/수교연도 = 외교부 재외동포/외교관계 데이터 (Agent1). "
            f"비교 기준: {reference_source_note}"
        )
        result["data_sources"]["opportunity_score"] = (
            "ODA 지원 추세(최근 5년 vs 이전 5년) = KOICA ODA API (Agent2 oda.yearly), "
            "한국 기관 해외진출 수 = 외교부 해외진출현황 CSV (Agent2 overseas_presence). "
        )
        result["data_sources"]["similar_countries"] = (
            f"위 지표들을 벡터화 + 비교 기준: {reference_source_note}"
        )
