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
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

import config

class Agent3Analyzer:
    """정량 분석 파이프라인. raw dict -> DataFrame -> 4대 지표 -> (선택)군집/PCA"""

    def __init__(self, raw_data: dict):
        self.raw = raw_data
        self.countries = list(raw_data.keys())
        self.df = self._build_base_dataframe()

    def _parse_travel_level(self, warning_level: str | None) -> float:
        # 문자열 경보 레벨을 정량 점수로 변환 (예: '1단계' -> 1.0, 없으면 0.0)
        if not warning_level:
            return 0.0
        try:
            # 문자열에서 숫자만 추출 시도 (예: "2단계" -> 2.0)
            digits = "".join([c for c in str(warning_level) if c.isdigit()])
            return float(digits) if digits else 0.0
        except Exception:
            return 0.0

    def _parse_diplomatic_year(self, diplomatic_data: dict | None) -> float:
        # 외교 관계 원본 데이터 등에서 수교 연도를 추출
        if not diplomatic_data or not isinstance(diplomatic_data, dict):
            return 2026.0
        # Agent2 원본 응답 구조에 맞게 커스텀 파싱 (예: "수교일자": "1992-12-22" -> 1992)
        # 아래는 예시 필드명이며 실제 데이터 구조에 맞게 매핑 필요합니다.
        for key, val in diplomatic_data.items():
            if "연도" in key or "수교" in key:
                digits = "".join([c for c in str(val) if c.isdigit()][:4])
                if len(digits) == 4:
                    return float(digits)
      

    def _safe_minmax_scale(self, series: pd.Series) -> np.ndarray:
        # 수학적 에러 방지: 데이터가 모두 같거나 부족해서 분모가 0이 되는 현상 방지
        if series.nunique() <= 1:
            # 모든 값이 같으면 중간값인 50.0으로 통일하거나 원래 값이 0이면 0으로 반환
            return np.full(series.shape, 50.0) if series.max() != 0 else np.zeros(series.shape)
        
        scaler = MinMaxScaler((0, 100))
        return scaler.fit_transform(series.to_frame()).flatten()
    def _build_base_dataframe(self) -> pd.DataFrame:
        country_mapping = getattr(self, "country_mapping", {}) 

        aggregated_rows = {}
        for input_key, v in self.raw.items():
            # 1. Agent2 매핑 딕셔너리에서 표준 국가명 찾기
            mapping_info = country_mapping.get(input_key, {})
            standard_country = mapping_info.get("matched_to", input_key) # 없으면 본래 키 유지
            
            # 2. 나미비아 같은 iso2 NaN 값 처리
            iso2 = mapping_info.get("iso2")
            iso2_str = "" if pd.isna(iso2) else str(iso2)

            # 기존 데이터 추출 로직
            security = v.get("security_environment", {})
            oda = v.get("oda", {})
            oda_cum_list = oda.get("cumulative", {}).get("data")
            oda_cum_usd = 0.0
            if oda_cum_list and isinstance(oda_cum_list, list) and len(oda_cum_list) > 0:
                oda_cum_usd = float(oda_cum_list[0].get("달러", 0))

            trade_data = v.get("trade", {}).get("data", {})
            trade_volume = float(trade_data.get("trade_volume", 0.0)) if isinstance(trade_data, dict) else 0.0

            # 3. 표준 국가명 기준으로 데이터를 수집할 딕셔너리 생성 및 누적
            if standard_country not in aggregated_rows:
                aggregated_rows[standard_country] = {
                    "country": standard_country,
                    "iso2": iso2_str,
                    "travel_advisory_level": self._parse_travel_level(v.get("travel_warning_level")),
                    "safety_notice_count_monthly": len(v.get("recent_safety_notices", [])),
                    "political_risk_keyword_score": float(security.get("suicide_death_rate", 0.0)),
                    "trade_volume_usd_million": trade_volume,
                    "oda_cumulative_usd_million": oda_cum_usd / 1_000_000.0,
                    "expat_count": float(v.get("overseas_presence", {}).get("data", {}).get("org_count", 0) or 0),
                    "diplomatic_year": self._parse_diplomatic_year(v.get("diplomatic", {}).get("data")),
                }
                for f in ODA_FIELDS:
                    aggregated_rows[standard_country][f"oda_freq__{f}"] = float(v.get("koica_oda_field_freq", {}).get(f, 0.0))
                for f in OPPORTUNITY_FIELDS:
                    aggregated_rows[standard_country][f"industry__{f}"] = float(v.get("industry_status", {}).get(f, 0.0))
                    aggregated_rows[standard_country][f"keyword__{f}"] = float(v.get("keyword_relevance", {}).get(f, 0.0))
                    aggregated_rows[standard_country][f"history__{f}"] = float(v.get("cooperation_history_score", {}).get(f, 0.0))
            else:
                # 이미 표준 국가명이 등록되어 있다면(예: 가나대학교 이후 가나 데이터 처리 시) 수치형 데이터 가산/최대값 갱신
                existing = aggregated_rows[standard_country]
                existing["trade_volume_usd_million"] += trade_volume
                existing["oda_cumulative_usd_million"] += (oda_cum_usd / 1_000_000.0)
                existing["expat_count"] += float(v.get("overseas_presence", {}).get("data", {}).get("org_count", 0) or 0)
                # 경보 레벨이나 위험도는 더 높은(위험한) 값을 보수적으로 선택
                existing["travel_advisory_level"] = max(existing["travel_advisory_level"], self._parse_travel_level(v.get("travel_warning_level")))
                existing["safety_notice_count_monthly"] += len(v.get("recent_safety_notices", []))

        # 4. 딕셔너리를 DataFrame으로 변환 후 Index 지정
        return pd.DataFrame(list(aggregated_rows.values())).set_index("country")

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
        n_components = min(2, scaled.shape[1], scaled.shape[0])
        pca = PCA(n_components=n_components, random_state=config.RANDOM_STATE)
        coords = pca.fit_transform(scaled)
        cols = [f"pc{i+1}" for i in range(n_components)]
        return pd.DataFrame(coords, index=feature_df.index, columns=cols)

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
