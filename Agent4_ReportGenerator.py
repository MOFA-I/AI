# -*- coding: utf-8 -*-
"""
agents/agent4_report.py

Agent 4 - Report Generator
Agent 3 (agent3_quant.analyze())의 실제 출력 JSON을 입력받아
타깃별 브리핑 보고서(HTML)를 생성한다.

Agent 3 출력 스키마 (팀원 C의 analyze() 반환값 - 확정):
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

실행:
    python agent4_report_generator.py
"""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Agent4")


# ============================================================================
# 국가 좌표 테이블
# ============================================================================
# ⚠️ Agent 3 출력에는 좌표가 없다!
# → Agent 4가 자체적으로 국가명 → 좌표 변환을 담당한다.
# 여기 없는 국가는 Nominatim 지오코딩으로 폴백 (geopy 필요, 선택)

COUNTRY_COORDS = {
    "베트남": (14.0583, 108.2772),
    "인도네시아": (-0.7893, 113.9213),
    "태국": (15.8700, 100.9925),
    "필리핀": (12.8797, 121.7740),
    "몽골": (46.8625, 103.8467),
    "말레이시아": (4.2105, 101.9758),
    "캄보디아": (12.5657, 104.9910),
    "라오스": (19.8563, 102.4955),
    "미얀마": (21.9162, 95.9560),
    "인도": (20.5937, 78.9629),
    "방글라데시": (23.6850, 90.3563),
    "네팔": (28.3949, 84.1240),
    "스리랑카": (7.8731, 80.7718),
    "우즈베키스탄": (41.3775, 64.5853),
    "카자흐스탄": (48.0196, 66.9237),
    "사우디아라비아": (23.8859, 45.0792),
    "UAE": (23.4241, 53.8478),
    "아랍에미리트": (23.4241, 53.8478),
    "이란": (32.4279, 53.6880),
    "이라크": (33.2232, 43.6793),
    "이집트": (26.8206, 30.8025),
    "에티오피아": (9.1450, 40.4897),
    "케냐": (-0.0236, 37.9062),
    "탄자니아": (-6.3690, 34.8888),
    "가나": (7.9465, -1.0232),
    "나이지리아": (9.0820, 8.6753),
    "페루": (-9.1900, -75.0152),
    "콜롬비아": (4.5709, -74.2973),
    "볼리비아": (-16.2902, -63.5887),
    "파라과이": (-23.4425, -58.4438),
    "우크라이나": (48.3794, 31.1656),
    "중국": (35.8617, 104.1954),
    "일본": (36.2048, 138.2529),
    "미국": (37.0902, -95.7129),
}


def get_country_coords(country: str) -> Optional[tuple]:
    """국가명 → (위도, 경도). 테이블에 없으면 Nominatim 지오코딩 시도."""
    if country in COUNTRY_COORDS:
        return COUNTRY_COORDS[country]
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="mofa_intelligence")
        loc = geolocator.geocode(country, timeout=5)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception as e:
        logger.warning(f"지오코딩 실패 ({country}): {e}")
    return None


# ============================================================================
# LLM Provider (교체 가능한 추상화 - 이전에 만든 구조 그대로)
# ============================================================================

class LLMProvider:
    """LLM 추상 인터페이스. Groq/Claude/GPT 뭐든 교체 가능"""
    def generate(self, prompt: str, max_tokens: int = 1500,
                 temperature: float = 0.7) -> str:
        raise NotImplementedError


class GroqProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None,
                 model: str = "llama-3.3-70b-versatile"):
        from groq import Groq
        resolved_key = api_key or os.getenv("GROQ_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Groq API 키가 없습니다. "
                "export GROQ_API_KEY='gsk_...' 로 설정하거나 GroqProvider(api_key='...')를 사용하세요."
            )
        self.client = Groq(api_key=resolved_key)
        self.model = model

    def generate(self, prompt, max_tokens=1500, temperature=0.7):
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content


class RuleBasedFallback(LLMProvider):
    """API 키가 없거나 LLM 호출 실패 시 규칙 기반 폴백.
    개발/테스트 단계에서 LLM 없이도 전체 파이프라인이 돌아가게 해준다."""

    def generate(self, prompt, max_tokens=1500, temperature=0.7):
        return (
            "### Executive Summary\n"
            "(규칙 기반 폴백 브리핑 - LLM 연결 시 자동 대체됩니다)\n\n"
            "분석 데이터에 따라 자동 생성된 요약입니다. "
            "위험도와 협력지수를 종합했을 때 아래 대시보드의 지표를 참고하십시오.\n\n"
            "### Recommendation\n"
            "정량 지표 기반의 상세 권고는 LLM 연동 후 제공됩니다."
        )


# ============================================================================
# Agent 4: Report Generator
# ============================================================================

# 타깃별 브리핑 설정
TARGET_CONFIG = {
    "일반": {
        "tone": "친근하고 쉬운 말투. 외교 용어는 일상 언어로 풀어서 설명",
        "focus": "여행 안전, 일상에 미치는 영향 (환율·유가·비행편)",
        "length": "250-350단어",
        "report_name": "Travel Intelligence Brief",
    },
    "기업": {
        "tone": "전문적이고 실용적. 의사결정에 바로 쓸 수 있게",
        "focus": "진출 리스크, 협력 공백 분야, 경쟁 후보국 비교, 진출 추천/관망/비추천 판단",
        "length": "300-400단어",
        "report_name": "Business Intelligence Report",
    },
    "연구자": {
        "tone": "학술적이고 객관적. 데이터와 출처 중심",
        "focus": "외교 패턴 분석, 유사국가 비교, ODA 트렌드, 정책 시사점",
        "length": "400-500단어",
        "report_name": "Policy & Research Brief",
    },
}


class Agent4ReportGenerator:
    """
    Agent 3의 analyze() 출력을 받아 최종 보고서 생성.

    입력: agent3_result (dict) - analyze()의 반환값 그대로
    출력: HTML 보고서 파일 경로
    """

    def __init__(self, llm_provider: LLMProvider = None):
        if llm_provider is not None:
            self.llm = llm_provider
        elif os.getenv("GROQ_API_KEY"):
            self.llm = GroqProvider()
        else:
            logger.warning("GROQ_API_KEY 미설정 → RuleBasedFallback 사용")
            self.llm = RuleBasedFallback()

    # ------------------------------------------------------------------
    # 공개 인터페이스 (Orchestrator가 호출)
    # ------------------------------------------------------------------
    def generate_report(self,
                        agent3_result: Dict[str, Any],
                        target_type: str = "기업",
                        user_query: str = "",
                        agent1_data: Optional[Dict] = None,
                        agent2_data: Optional[Dict] = None,
                        output_path: Optional[str] = None) -> str:
        """
        Args:
            agent3_result: analyze()의 반환값 (국가별 dict)
            target_type: "일반" | "기업" | "연구자"
            user_query: 사용자 원본 질문 (헤더 표시용)
            agent1_data: Agent 1 결과 (있으면 Evidence에 포함)
            agent2_data: Agent 2 결과 (있으면 Evidence에 포함)
            output_path: 저장 경로 (기본: report_{target}_{timestamp}.html)

        Returns:
            생성된 HTML 파일 경로
        """
        if target_type not in TARGET_CONFIG:
            raise ValueError(f"target_type은 {list(TARGET_CONFIG)} 중 하나여야 합니다")

        countries = list(agent3_result.keys())
        logger.info(f"[Agent4] {len(countries)}개국 보고서 생성 시작 (타깃: {target_type})")

        # 1. 지도 생성 (Folium) - 지리공간 시각화 (핵심 요구사항)
        map_html = self._build_map(agent3_result, target_type)

        # 2. 대시보드 생성 (Plotly) - Agent 3 스키마 그대로 사용
        dashboard_html = self._build_dashboard(agent3_result, target_type)

        # 3. LLM 브리핑 생성
        briefing_text = self._build_briefing(agent3_result, target_type, user_query)

        # 4. Evidence 섹션 (전 Agent 작업 로그)
        evidence_html = self._build_evidence(agent3_result, agent1_data, agent2_data)

        # 5. HTML 통합
        html = self._integrate_html(
            map_html, dashboard_html, briefing_text, evidence_html,
            target_type, user_query, countries
        )

        # 5. 저장
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"report_{target_type}_{ts}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"[Agent4] 완료 -> {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # 1. 지도: Agent 3 데이터의 지리공간 시각화 (Folium)
    # ------------------------------------------------------------------
    def _build_map(self, agent3_result: Dict, target_type: str) -> str:
        """
        Agent 3 출력(좌표 없음)을 지도로 시각화.
        - 원 크기 = cooperation_index.score
        - 원 색상 = risk_score (초록→노랑→빨강)
        - 팝업 = 위험도, 협력지수, 분야별 TOP3, 유사국가
        - 유사국가 연결선 = 주 분석 대상 국가 기준
        """
        # 좌표 확보 (Agent 4가 자체 변환)
        coords = {}
        for country in agent3_result:
            c = get_country_coords(country)
            if c:
                coords[country] = c
            else:
                logger.warning(f"좌표를 찾을 수 없어 지도에서 제외: {country}")

        if not coords:
            return "<p>좌표 데이터가 없어 지도를 생성할 수 없습니다.</p>"

        # 지도 중심 = 분석 국가들의 평균 좌표
        avg_lat = sum(c[0] for c in coords.values()) / len(coords)
        avg_lon = sum(c[1] for c in coords.values()) / len(coords)

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=4,
                       tiles="CartoDB positron")

        # ---- 계층 1: 국가별 위험도/협력지수 마커 ----
        marker_layer = folium.FeatureGroup(name="위험도 × 협력지수", show=True)

        for country, (lat, lon) in coords.items():
            d = agent3_result[country]
            risk = d["risk_score"]
            coop_score = d["cooperation_index"]["score"]
            coop_grade = d["cooperation_index"]["grade"]

            # 색상: 위험도 기반
            color = "#2e7d32" if risk < 40 else "#f9a825" if risk < 70 else "#c62828"
            # 크기: 협력지수 기반 (10~35px)
            radius = 10 + (coop_score / 100) * 25

            top3 = d["opportunity_ranking"][:3]
            top3_html = "<br>".join(f"&nbsp;&nbsp;{i+1}. {f}: {s}점"
                                     for i, (f, s) in enumerate(top3))
            similar_html = ", ".join(
                f"{name}({sim:.2f})" for name, sim in d["similar_countries"][:3])

            popup_html = f"""
            <div style="font-family:sans-serif; min-width:220px">
              <h4 style="margin:0 0 8px">{country}</h4>
              <b>위험도:</b> {risk}/100<br>
              <b>협력지수:</b> {coop_score} (등급 {coop_grade}/5)<br>
              <b>유망 분야 TOP3:</b><br>{top3_html}<br>
              <b>유사국가:</b> {similar_html}<br>
              <small style="color:#888">출처: 외교부·KOICA 공공데이터</small>
            </div>
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{country} — 위험도 {risk} / 협력 {coop_grade}등급",
                color=color, fill=True, fillColor=color,
                fillOpacity=0.65, weight=2,
            ).add_to(marker_layer)

            # 국가명 라벨
            folium.Marker(
                location=[lat, lon],
                icon=folium.DivIcon(html=f"""
                    <div style="font-size:12px; font-weight:bold; color:#333;
                                text-shadow:1px 1px 2px #fff; white-space:nowrap;
                                transform:translate(-50%, 10px)">{country}</div>"""),
            ).add_to(marker_layer)

        marker_layer.add_to(m)

        # ---- 계층 2: 유사국가 연결선 (주 분석 대상 기준) ----
        main_country = list(agent3_result.keys())[0]
        if main_country in coords:
            similar_layer = folium.FeatureGroup(
                name=f"{main_country} 유사국가 연결", show=True)
            main_coord = coords[main_country]

            for name, sim in agent3_result[main_country]["similar_countries"]:
                target_coord = coords.get(name) or get_country_coords(name)
                if not target_coord:
                    continue
                folium.PolyLine(
                    locations=[main_coord, target_coord],
                    color="#1a2980",
                    weight=max(1, sim * 5),  # 유사도 높을수록 굵게
                    opacity=0.6,
                    dash_array="8",
                    tooltip=f"{main_country} ↔ {name} 유사도 {sim:.2f}",
                ).add_to(similar_layer)
            similar_layer.add_to(m)

        folium.LayerControl().add_to(m)

        # 범례
        legend = """
        <div style="position:absolute; bottom:20px; left:20px; z-index:9999;
                    background:#fff; border:1px solid #ccc; border-radius:6px;
                    padding:12px 16px; font-size:13px; font-family:sans-serif;
                    box-shadow:0 2px 6px rgba(0,0,0,.15)">
          <b>범례</b><br>
          <span style="color:#2e7d32">●</span> 위험도 낮음 (&lt;40)<br>
          <span style="color:#f9a825">●</span> 위험도 중간 (40–70)<br>
          <span style="color:#c62828">●</span> 위험도 높음 (&gt;70)<br>
          원 크기 = 협력지수 &nbsp;·&nbsp; 점선 = 유사국가
        </div>"""
        m.get_root().html.add_child(folium.Element(legend))

        # iframe(srcdoc) 형태로 반환 → 보고서 HTML에 안전하게 임베드
        return m._repr_html_()

    # ------------------------------------------------------------------
    # 2. 대시보드: Agent 3의 실제 필드를 그대로 시각화
    # ------------------------------------------------------------------
    def _build_dashboard(self, agent3_result: Dict, target_type: str) -> str:
        countries = list(agent3_result.keys())

        # ---- Agent 3 스키마에서 데이터 추출 ----
        risk_scores = [agent3_result[c]["risk_score"] for c in countries]
        coop_scores = [agent3_result[c]["cooperation_index"]["score"] for c in countries]
        coop_grades = [agent3_result[c]["cooperation_index"]["grade"] for c in countries]

        # 첫 번째(주요 분석 대상) 국가 기준
        main_country = countries[0]
        main = agent3_result[main_country]

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                f"{main_country} 위험도",
                "국가별 위험도 vs 협력지수",
                f"{main_country} 분야별 협력 기회 (opportunity_ranking)",
                f"{main_country} 유사국가 (cosine similarity)",
            ),
            specs=[
                [{"type": "indicator"}, {"type": "scatter"}],
                [{"type": "bar"}, {"type": "bar"}],
            ],
            vertical_spacing=0.18,
        )

        # (1) 위험도 게이지 - risk_score (0~100)
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=main["risk_score"],
            title={"text": "risk_score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 40], "color": "lightgreen"},
                    {"range": [40, 70], "color": "gold"},
                    {"range": [70, 100], "color": "salmon"},
                ],
            },
        ), row=1, col=1)

        # (2) 위험도 vs 협력지수 산점도 (grade로 마커 크기)
        fig.add_trace(go.Scatter(
            x=risk_scores, y=coop_scores,
            mode="markers+text",
            text=countries,
            textposition="top center",
            marker=dict(
                size=[g * 8 for g in coop_grades],
                color=coop_grades,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="grade", x=1.02, len=0.4, y=0.8),
            ),
            hovertemplate="<b>%{text}</b><br>위험도: %{x:.1f}<br>협력지수: %{y:.1f}<extra></extra>",
        ), row=1, col=2)

        # (3) opportunity_ranking → 가로 막대 (이미 정렬된 상태로 옴)
        opp_ranking = main["opportunity_ranking"]  # [["AI", 55.6], ...]
        opp_fields = [item[0] for item in opp_ranking]
        opp_values = [item[1] for item in opp_ranking]
        fig.add_trace(go.Bar(
            y=opp_fields[::-1], x=opp_values[::-1],
            orientation="h",
            marker_color="steelblue",
            hovertemplate="<b>%{y}</b>: %{x:.1f}점<extra></extra>",
        ), row=2, col=1)

        # (4) similar_countries → 유사도 막대
        similar = main["similar_countries"]  # [["몽골", 0.83], ...]
        sim_names = [s[0] for s in similar]
        sim_values = [s[1] for s in similar]
        fig.add_trace(go.Bar(
            x=sim_names, y=sim_values,
            marker_color="mediumseagreen",
            hovertemplate="<b>%{x}</b><br>유사도: %{y:.3f}<extra></extra>",
        ), row=2, col=2)

        fig.update_xaxes(title_text="위험도", row=1, col=2)
        fig.update_yaxes(title_text="협력지수", row=1, col=2)
        fig.update_xaxes(title_text="점수", row=2, col=1)
        fig.update_yaxes(title_text="유사도", range=[0, 1], row=2, col=2)

        fig.update_layout(
            height=800, showlegend=False, template="plotly_white",
            title_text=f"{main_country} 정량 분석 대시보드 (Agent 3 출력 기반)",
        )

        # HTML fragment로 반환 (전체 페이지에 임베드)
        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    # ------------------------------------------------------------------
    # 2. LLM 브리핑: Agent 3 데이터를 프롬프트에 구조화
    # ------------------------------------------------------------------
    def _build_briefing(self, agent3_result: Dict,
                        target_type: str, user_query: str) -> str:
        cfg = TARGET_CONFIG[target_type]

        # Agent 3 결과를 프롬프트용으로 요약 (토큰 절약)
        data_summary = []
        for country, d in agent3_result.items():
            top3_opp = d["opportunity_ranking"][:3]
            data_summary.append(
                f"- {country}: 위험도 {d['risk_score']}, "
                f"협력지수 {d['cooperation_index']['score']} (등급 {d['cooperation_index']['grade']}/5), "
                f"유망분야 {', '.join(f'{f}({s})' for f, s in top3_opp)}, "
                f"유사국가 {', '.join(s[0] for s in d['similar_countries'][:3])}"
            )

        prompt = f"""당신은 한국 외교부 공공데이터 기반의 외교 인텔리전스 분석가입니다.

[사용자 질문]
{user_query or "국가 분석 요청"}

[정량 분석 데이터 (Agent 3 산출)]
{chr(10).join(data_summary)}

[지표 설명]
- 위험도: 0~100 (여행경보 40% + 안전공지 빈도 30% + 정세 키워드 30%)
- 협력지수: 0~100점 + 1~5등급 (무역 30% + ODA 30% + 교민 20% + 수교연도 20%)
- 분야별 점수: KOICA ODA 빈도 + 산업현황 + 정세키워드 + 협력이력 가중합

[타깃: {target_type}]
- 톤: {cfg['tone']}
- 초점: {cfg['focus']}
- 분량: {cfg['length']}

[출력 형식 - 마크다운]
### Executive Summary
(핵심 3줄)
### Situation Analysis
### Risk Analysis
### Opportunity Analysis
### Recommendation

위 정량 데이터의 수치를 반드시 인용하며 작성하세요. 데이터에 없는 내용은 추측하지 마세요."""

        try:
            return self.llm.generate(prompt, max_tokens=1500, temperature=0.7)
        except Exception as e:
            logger.warning(f"LLM 호출 실패, 폴백 사용: {e}")
            return RuleBasedFallback().generate(prompt)

    # ------------------------------------------------------------------
    # 3. Evidence 섹션: 전 Agent 작업 로그 (Explainable AI)
    # ------------------------------------------------------------------
    def _build_evidence(self, agent3_result: Dict,
                        agent1_data: Optional[Dict],
                        agent2_data: Optional[Dict]) -> str:
        rows = []
        if agent1_data:
            rows.append(("Agent 1 · Issue Analyzer",
                         "외교부 안전정보/여행경보/주요정세 API",
                         json.dumps(agent1_data, ensure_ascii=False)[:200] + "..."))
        if agent2_data:
            rows.append(("Agent 2 · Intelligence Collector",
                         "외교부 관계/무역 API + KOICA ODA CSV",
                         json.dumps(agent2_data, ensure_ascii=False)[:200] + "..."))
        rows.append(("Agent 3 · Insight Generator",
                     "pandas + scikit-learn (MinMaxScaler, cosine_similarity, KMeans)",
                     f"{len(agent3_result)}개국 정량 분석: risk_score, cooperation_index, "
                     f"opportunity_score, similar_countries 산출"))
        rows.append(("Agent 4 · Report Generator",
                     "LLM 브리핑 + Plotly 대시보드",
                     "타깃별 보고서 생성 및 Evidence 자동 기록"))

        rows_html = "".join(
            f"<tr><td><b>{name}</b></td><td>{source}</td><td>{log}</td></tr>"
            for name, source, log in rows
        )
        return f"""
        <table class="evidence-table">
          <thead><tr><th>Agent</th><th>데이터 출처 / 기술</th><th>작업 로그</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
        """

    # ------------------------------------------------------------------
    # 4. HTML 통합
    # ------------------------------------------------------------------
    def _integrate_html(self, map_html: str, dashboard_html: str,
                        briefing_text: str, evidence_html: str,
                        target_type: str, user_query: str,
                        countries: list) -> str:
        cfg = TARGET_CONFIG[target_type]
        briefing_html = self._markdown_to_html(briefing_text)

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MOFA Intelligence - {cfg['report_name']}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Noto Sans KR',sans-serif; background:#f0f2f5; color:#333; }}
  .container {{ max-width:1400px; margin:0 auto; background:#fff; }}
  .header {{ background:linear-gradient(135deg,#1a2980,#26d0ce); color:#fff; padding:40px; }}
  .header h1 {{ font-size:1.9em; margin-bottom:8px; }}
  .header .meta {{ opacity:.9; font-size:.95em; margin-top:12px; }}
  .header .meta span {{ margin-right:24px; }}
  section {{ padding:36px 40px; }}
  section h2 {{ color:#1a2980; border-bottom:3px solid #26d0ce; padding-bottom:8px; margin-bottom:20px; }}
  .briefing {{ line-height:1.9; max-width:900px; }}
  .map-wrap {{ border:1px solid #ddd; border-radius:8px; overflow:hidden; }}
  .map-wrap iframe {{ width:100% !important; height:520px !important; border:none; }}
  .briefing h3 {{ color:#1a2980; margin:22px 0 10px; }}
  .briefing ul {{ margin:0 0 14px 24px; }}
  .briefing p {{ margin-bottom:14px; }}
  .evidence-table {{ width:100%; border-collapse:collapse; font-size:.9em; }}
  .evidence-table th, .evidence-table td {{ border:1px solid #ddd; padding:10px; text-align:left; vertical-align:top; }}
  .evidence-table th {{ background:#1a2980; color:#fff; }}
  .evidence-table tr:nth-child(even) {{ background:#f8f9fb; }}
  .disclaimer {{ background:#fff8e1; border-left:4px solid #ffb300; padding:14px 18px; margin-top:24px; font-size:.9em; color:#795548; }}
  .footer {{ background:#1a2980; color:#fff; text-align:center; padding:22px; font-size:.9em; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🌍 {cfg['report_name']}</h1>
    <p>MOFA Intelligence · 멀티에이전트 외교 인텔리전스 플랫폼</p>
    <div class="meta">
      <span>📋 질문: {user_query or '-'}</span>
      <span>🌏 대상국: {', '.join(countries)}</span>
      <span>👥 타깃: {target_type}</span>
      <span>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
    </div>
  </div>

  <section>
    <h2>📝 AI 종합 브리핑</h2>
    <div class="briefing">{briefing_html}</div>
  </section>

  <section>
    <h2>🗺️ 지도로 보기</h2>
    <p style="color:#666; margin-bottom:14px; font-size:.92em">
      원 색상 = 위험도 · 원 크기 = 협력지수 · 점선 = 유사국가 연결 (마커 클릭 시 상세 정보)
    </p>
    <div class="map-wrap">{map_html}</div>
  </section>

  <section>
    <h2>📊 정량 분석 대시보드</h2>
    {dashboard_html}
  </section>

  <section>
    <h2>🔍 Evidence — 전 Agent 작업 로그</h2>
    {evidence_html}
    <div class="disclaimer">
      ⚠️ 본 보고서는 외교부·KOICA 공공데이터 기반 자동 분석 결과이며 정책 참고용입니다.
      최종 의사결정 전 최신 공식 정보 확인을 권장합니다.
    </div>
  </section>

  <div class="footer">
    <p>🤖 MOFA Intelligence v1.0 — ReAct 기반 멀티에이전트 시스템</p>
    <p>데이터: 외교부 공공데이터포털 · KOICA</p>
  </div>
</div>
</body>
</html>"""

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """간단한 마크다운 → HTML 변환 (LLM 출력용)"""
        import re
        html = text
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.M)
        html = re.sub(r"^## (.+)$", r"<h3>\1</h3>", html, flags=re.M)
        html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
        # 리스트
        html = re.sub(r"^[-*] (.+)$", r"<li>\1</li>", html, flags=re.M)
        html = re.sub(r"((?:<li>.*?</li>\n?)+)", r"<ul>\1</ul>", html)
        # 문단
        paragraphs = html.split("\n\n")
        html = "".join(
            p if p.strip().startswith("<") else f"<p>{p}</p>"
            for p in paragraphs if p.strip()
        )
        return html


# ============================================================================
# 테스트: Agent 3 출력 스키마와 100% 동일한 더미 데이터
# ============================================================================

# 팀원 C의 analyze() 반환값과 동일한 구조
SAMPLE_AGENT3_OUTPUT = {
    "베트남": {
        "risk_score": 42.3,
        "cooperation_index": {"score": 61.2, "grade": 4},
        "opportunity_score": {"AI": 55.6, "스마트팜": 48.2, "의료": 50.1,
                              "에너지": 39.4, "문화": 30.2},
        "opportunity_ranking": [["AI", 55.6], ["의료", 50.1], ["스마트팜", 48.2],
                                ["에너지", 39.4], ["문화", 30.2]],
        "cluster": 0,
        "similar_countries": [["몽골", 0.83], ["필리핀", 0.80], ["인도네시아", 0.76]],
    },
    "인도네시아": {
        "risk_score": 35.8,
        "cooperation_index": {"score": 72.5, "grade": 5},
        "opportunity_score": {"AI": 61.2, "스마트팜": 66.8, "의료": 44.3,
                              "에너지": 58.7, "문화": 41.0},
        "opportunity_ranking": [["스마트팜", 66.8], ["AI", 61.2], ["에너지", 58.7],
                                ["의료", 44.3], ["문화", 41.0]],
        "cluster": 1,
        "similar_countries": [["베트남", 0.76], ["태국", 0.74], ["필리핀", 0.69]],
    },
    "태국": {
        "risk_score": 55.1,
        "cooperation_index": {"score": 58.9, "grade": 3},
        "opportunity_score": {"AI": 47.3, "스마트팜": 52.1, "의료": 61.5,
                              "에너지": 35.2, "문화": 68.9},
        "opportunity_ranking": [["문화", 68.9], ["의료", 61.5], ["스마트팜", 52.1],
                                ["AI", 47.3], ["에너지", 35.2]],
        "cluster": 1,
        "similar_countries": [["인도네시아", 0.74], ["베트남", 0.71], ["말레이시아", 0.65]],
    },
}


if __name__ == "__main__":
    # GROQ_API_KEY 설정 시 Groq LLM 사용, 미설정 시 RuleBasedFallback
    # export GROQ_API_KEY='gsk_...'  (https://console.groq.com/keys)
    agent4 = Agent4ReportGenerator()

    output = agent4.generate_report(
        agent3_result=SAMPLE_AGENT3_OUTPUT,
        target_type="기업",
        user_query="베트남 vs 인도네시아 vs 태국 진출 비교",
        agent2_data={"note": "Agent2 더미 (통합 시 실데이터 교체)"},
        output_path="report_기업_sample.html",
    )
    print(f"\n✅ 보고서 생성 완료: {output}")
