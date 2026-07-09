# -*- coding: utf-8 -*-
"""
agents/agent3_quant.py

Agent3 - 데이터 기반 정량 분석 엔진 (pandas + scikit-learn)

역할:
  Agent1(데이터 수집), Agent2(전처리) 등에서 넘겨받은 국가별 raw 데이터를 입력받아
    1) 위험도 점수
    2) Cooperation Index (5단계)
    3) Cooperation Opportunity Score (분야별 랭킹)
    4) 유사국가 추천 (코사인 유사도 + KMeans 군집)
  을 계산해 다음 Agent(예: 보고서 생성 Agent)에 넘길 수 있는 형태로 반환
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

import config
from data.dummy_data import generate_countries, ODA_FIELDS, OPPORTUNITY_FIELDS


class Agent3Analyzer:
    """정량 분석 파이프라인. raw dict -> DataFrame -> 4대 지표 -> (선택)군집/PCA"""

    def __init__(self, raw_data: dict):
        self.raw = raw_data
        self.countries = list(raw_data.keys())
        self.df = self._build_base_dataframe()

    def _build_base_dataframe(self) -> pd.DataFrame:
        rows = []
        for country, v in self.raw.items():
            row = {
                "country": country,
                "travel_advisory_level": v["travel_advisory_level"],
                "safety_notice_count_monthly": v["safety_notice_count_monthly"],
                "political_risk_keyword_score": v["political_risk_keyword_score"],
                "trade_volume_usd_million": v["trade_volume_usd_million"],
                "oda_cumulative_usd_million": v["oda_cumulative_usd_million"],
                "expat_count": v["expat_count"],
                "diplomatic_year": v["diplomatic_year"],
            }
            for f in ODA_FIELDS:
                row[f"oda_freq__{f}"] = v["koica_oda_field_freq"][f]
            for f in OPPORTUNITY_FIELDS:
                row[f"industry__{f}"] = v["industry_status"][f]
                row[f"keyword__{f}"] = v["keyword_relevance"][f]
                row[f"history__{f}"] = v["cooperation_history_score"][f]
            rows.append(row)
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
        trade_s = scaler.fit_transform(df[["trade_volume_usd_million"]]).flatten()
        oda_s = scaler.fit_transform(df[["oda_cumulative_usd_million"]]).flatten()
        expat_s = scaler.fit_transform(df[["expat_count"]]).flatten()
        year_s = scaler.fit_transform(-df[["diplomatic_year"]]).flatten()  # 오래될수록 가점

        score = (
            trade_s * w["trade_volume"]
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

    def calc_opportunity_score(self) -> pd.DataFrame:
        w = config.OPPORTUNITY_WEIGHTS
        df = self.df
        scaler = MinMaxScaler((0, 100))
        result = pd.DataFrame(index=df.index)

        for opp_field in OPPORTUNITY_FIELDS:
            oda_field = next(k for k, v in config.ODA_TO_OPPORTUNITY.items() if v == opp_field)
            oda_col = f"oda_freq__{oda_field}"
            oda_norm = scaler.fit_transform(df[[oda_col]]).flatten()
            industry_col = df[f"industry__{opp_field}"].to_numpy()
            keyword_col = df[f"keyword__{opp_field}"].to_numpy()
            history_col = df[f"history__{opp_field}"].to_numpy()
            total = (
                oda_norm * w["oda_freq"]
                + industry_col * w["industry"]
                + keyword_col * w["keyword"]
                + history_col * w["history"]
            )
            result[opp_field] = np.round(total, 1)
        return result

    def opportunity_ranking(self, opp_df: pd.DataFrame) -> dict:
        return {
            country: list(row.sort_values(ascending=False).items())
            for country, row in opp_df.iterrows()
        }

    def build_feature_matrix(self, risk, coop, opp) -> pd.DataFrame:
        return pd.concat([risk, coop["score"].rename("coop_score"), opp], axis=1)

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
        scaled = MinMaxScaler().fit_transform(feature_df.to_numpy())
        km = KMeans(n_clusters=config.CLUSTER_N, random_state=config.RANDOM_STATE, n_init=10)
        labels = km.fit_predict(scaled)
        return pd.Series(labels, index=feature_df.index, name="cluster")

    def pca_2d(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        scaled = MinMaxScaler().fit_transform(feature_df.to_numpy())
        coords = PCA(n_components=2, random_state=config.RANDOM_STATE).fit_transform(scaled)
        return pd.DataFrame(coords, index=feature_df.index, columns=["pc1", "pc2"])

    def run_all(self):
        risk = self.calc_risk_score()
        coop = self.calc_cooperation_index()
        opp = self.calc_opportunity_score()
        opp_rank = self.opportunity_ranking(opp)
        feature_df = self.build_feature_matrix(risk, coop, opp)
        sim = self.similarity_matrix(feature_df)
        clusters = self.cluster_countries(feature_df)
        pca_coords = self.pca_2d(feature_df)
        return {
            "risk_score": risk,
            "cooperation_index": coop,
            "opportunity_score": opp,
            "opportunity_ranking": opp_rank,
            "feature_matrix": feature_df,
            "similarity_matrix": sim,
            "cluster": clusters,
            "pca_coords": pca_coords,
        }

    # ------------------------------------------------------------------
    # 1) 위험도 점수
    # ------------------------------------------------------------------
    def calc_risk_score(self) -> pd.Series:
        df = self.df
        w = config.RISK_WEIGHTS

        advisory_scaled = MinMaxScaler((0, 100)).fit_transform(
            df[["travel_advisory_level"]]
        ).flatten()
        notice_scaled = MinMaxScaler((0, 100)).fit_transform(
            df[["safety_notice_count_monthly"]]
        ).flatten()
        keyword_score = df["political_risk_keyword_score"].to_numpy()

        risk = (
            advisory_scaled * w["travel_advisory"]
            + notice_scaled * w["safety_notice"]
            + keyword_score * w["political_keyword"]
        )
        return pd.Series(np.round(risk, 2), index=df.index, name="risk_score")

    # ------------------------------------------------------------------
    # 2) Cooperation Index
    # ------------------------------------------------------------------
    def calc_cooperation_index(self) -> pd.DataFrame:
        df = self.df
        w = config.COOPERATION_WEIGHTS
        scaler = MinMaxScaler((0, 100))

        trade_s = scaler.fit_transform(df[["trade_volume_usd_million"]]).flatten()
        oda_s = scaler.fit_transform(df[["oda_cumulative_usd_million"]]).flatten()
        expat_s = scaler.fit_transform(df[["expat_count"]]).flatten()
        year_s = scaler.fit_transform(-df[["diplomatic_year"]]).flatten()  # 오래될수록 가점

        score = (
            trade_s * w["trade_volume"]
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

    # ------------------------------------------------------------------
    # 3) Cooperation Opportunity Score
    # ------------------------------------------------------------------
    def calc_opportunity_score(self) -> pd.DataFrame:
        w = config.OPPORTUNITY_WEIGHTS
        df = self.df
        scaler = MinMaxScaler((0, 100))
        result = pd.DataFrame(index=df.index)

        for opp_field in OPPORTUNITY_FIELDS:
            oda_field = next(k for k, v in config.ODA_TO_OPPORTUNITY.items() if v == opp_field)
            oda_col = f"oda_freq__{oda_field}"

            oda_norm = scaler.fit_transform(df[[oda_col]]).flatten()
            industry_col = df[f"industry__{opp_field}"].to_numpy()
            keyword_col = df[f"keyword__{opp_field}"].to_numpy()
            history_col = df[f"history__{opp_field}"].to_numpy()

            total = (
                oda_norm * w["oda_freq"]
                + industry_col * w["industry"]
                + keyword_col * w["keyword"]
                + history_col * w["history"]
            )
            result[opp_field] = np.round(total, 1)

        return result

    def opportunity_ranking(self, opp_df: pd.DataFrame) -> dict:
        return {
            country: list(row.sort_values(ascending=False).items())
            for country, row in opp_df.iterrows()
        }

    # ------------------------------------------------------------------
    # 4) 유사국가 추천
    # ------------------------------------------------------------------
    def build_feature_matrix(self, risk, coop, opp) -> pd.DataFrame:
        return pd.concat([risk, coop["score"].rename("coop_score"), opp], axis=1)

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

    # ------------------------------------------------------------------
    # 5) KMeans 군집 (부가 인사이트)
    # ------------------------------------------------------------------
    def cluster_countries(self, feature_df: pd.DataFrame) -> pd.Series:
        scaled = MinMaxScaler().fit_transform(feature_df.to_numpy())
        km = KMeans(n_clusters=config.CLUSTER_N, random_state=config.RANDOM_STATE, n_init=10)
        labels = km.fit_predict(scaled)
        return pd.Series(labels, index=feature_df.index, name="cluster")

    # ------------------------------------------------------------------
    # 6) PCA 2D 투영 (시각화용)
    # ------------------------------------------------------------------
    def pca_2d(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        scaled = MinMaxScaler().fit_transform(feature_df.to_numpy())
        coords = PCA(n_components=2, random_state=config.RANDOM_STATE).fit_transform(scaled)
        return pd.DataFrame(coords, index=feature_df.index, columns=["pc1", "pc2"])

    # ------------------------------------------------------------------
    def run_all(self):
        risk = self.calc_risk_score()
        coop = self.calc_cooperation_index()
        opp = self.calc_opportunity_score()
        opp_rank = self.opportunity_ranking(opp)

        feature_df = self.build_feature_matrix(risk, coop, opp)
        sim = self.similarity_matrix(feature_df)
        clusters = self.cluster_countries(feature_df)
        pca_coords = self.pca_2d(feature_df)

        return {
            "risk_score": risk,
            "cooperation_index": coop,
            "opportunity_score": opp,
            "opportunity_ranking": opp_rank,
            "feature_matrix": feature_df,
            "similarity_matrix": sim,
            "cluster": clusters,
            "pca_coords": pca_coords,
        }


def analyze(reference_data: dict, target_countries: list | None = None) -> dict:
    """
    Orchestrator / Agent2 / Agent4가 호출하는 공개 인터페이스.

    Args:
        reference_data: 비교 대상이 되는 '전체' 국가 DB
            (data.dummy_data.generate_countries()와 동일한 스키마).
            정규화·유사도·군집 계산은 비교군이 있어야 의미가 있으므로,
            사용자가 특정 국가 하나만 물어봤더라도 이 인자에는 항상
            전체(혹은 최소 여러 개) 국가 데이터를 넣어야 한다.
        target_countries: 사용자가 실제로 질문한 국가 리스트 (예: ["베트남"]).
            None이면 reference_data의 모든 국가에 대해 결과를 반환한다.
            (Orchestrator가 Issue Analyzer에서 뽑아낸 국가 리스트를 여기 그대로 넣으면 됨)

    Returns:
        JSON 직렬화 가능한 dict. Agent4가 바로 report 생성에 쓸 수 있는 형태.
        {
          "베트남": {
              "risk_score": 42.3,
              "cooperation_index": {"score": 61.2, "grade": 4},
              "opportunity_score": {"AI": 55.6, "스마트팜": 48.2, ...},
              "opportunity_ranking": [["AI", 55.6], ["의료", 50.1], ...],
              "cluster": 0,
              "similar_countries": [["몽골", 0.83], ["필리핀", 0.80], ...]
          },
          ...
        }

    주의: target_countries에 reference_data에 없는 국가명이 들어오면 결과에서 조용히 제외된다.
          (Orchestrator/Agent2 단계에서 국가명 표준화·존재 여부 검증을 먼저 해두는 것을 권장)
    """
    agent3 = Agent3Analyzer(reference_data)
    out = agent3.run_all()

    all_countries = list(reference_data.keys())
    targets = target_countries if target_countries else all_countries

    result = {}
    for country in targets:
        if country not in all_countries:
            continue
        similar = agent3.recommend_similar(out["similarity_matrix"], country)
        result[country] = {
            "risk_score": float(out["risk_score"][country]),
            "cooperation_index": {
                "score": float(out["cooperation_index"].loc[country, "score"]),
                "grade": int(out["cooperation_index"].loc[country, "grade"]),
            },
            "opportunity_score": {
                k: float(v) for k, v in out["opportunity_score"].loc[country].items()
            },
            "opportunity_ranking": [
                [k, float(v)] for k, v in out["opportunity_ranking"][country]
            ],
            "cluster": int(out["cluster"][country]),
            "similar_countries": [[k, float(v)] for k, v in similar.items()],
        }
    return result


def main():
    """단독 실행용 데모. 실제 파이프라인에서는 analyze()를 직접 import해서 쓰면 됨."""
    raw = generate_countries()
    agent3 = Agent3Analyzer(raw)
    out = agent3.run_all()

    pd.set_option("display.width", 120)
    pd.set_option("display.max_columns", 20)

    print("=" * 70)
    print("[Agent3] 위험도 점수 (내림차순)")
    print("=" * 70)
    print(out["risk_score"].sort_values(ascending=False))

    print("\n" + "=" * 70)
    print("[Agent3] Cooperation Index")
    print("=" * 70)
    print(out["cooperation_index"].sort_values("score", ascending=False))

    print("\n" + "=" * 70)
    print("[Agent3] Cooperation Opportunity Score")
    print("=" * 70)
    print(out["opportunity_score"])

    print("\n" + "=" * 70)
    print("[Agent3] KMeans 군집 결과")
    print("=" * 70)
    print(out["cluster"].sort_values())

    print("\n" + "=" * 70)
    print("[Agent3] 유사국가 추천 - '베트남' 기준")
    print("=" * 70)
    print(agent3.recommend_similar(out["similarity_matrix"], "베트남"))

    # ── Orchestrator가 실제로 호출할 방식 데모 ──────────────────────
    # Agent1(Issue Analyzer)이 "베트남에 대해 물어봤다"고 판단해서 넘겨줬다고 가정.
    # reference_data는 항상 전체 DB(raw)를 넣고, target_countries만 좁혀서 넘긴다.
    print("\n" + "=" * 70)
    print("[Agent3] analyze() 인터페이스 데모 - Orchestrator가 '베트남'만 요청한 경우")
    print("=" * 70)
    single_result = analyze(reference_data=raw, target_countries=["베트남"])
    import json
    print(json.dumps(single_result, ensure_ascii=False, indent=2))

    # 전체 국가 결과는 outputs/에 저장 (배치성 리포트/대시보드용)
    import os
    full_result = analyze(reference_data=raw, target_countries=None)
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/result_sample.json", "w", encoding="utf-8") as f:
        json.dump(full_result, f, ensure_ascii=False, indent=2)
    print("\n-> outputs/result_sample.json 저장 완료 (전체 국가)")


if __name__ == "__main__":
    main()
