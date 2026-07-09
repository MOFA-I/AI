# -*- coding: utf-8 -*-
"""schemas.py — Agent 4 입출력 JSON 계약 (v1.1).

v1.1 변경 (2026-07-09):
- Agent3: risk_score 구조체화({score,level,components}) 대응, cluster 제거,
  evidence/data_sources 패스스루 추가 (agent3 브랜치 신규 포맷)
- Agent2: 팀원 B 실구현 반영 — 분야(field)·도시 정보 없음(KOICA API 502),
  연도별 ODA 금액(oda_yearly) 추가, sources_used/failed 투명성 구조
원칙 불변: 숫자·좌표·판정은 데이터에서(결정적), LLM은 briefing 문장만.
"""

from __future__ import annotations
from typing import Optional, Literal, Union
from pydantic import BaseModel, field_validator

Target = Literal["기업", "연구자"]


# ══════════════════════════ 입력 ══════════════════════════

class SafetyNotice(BaseModel):
    date: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None


class TravelWarning(BaseModel):
    level: int = 0
    label: Optional[str] = None
    partial: bool = False


class Agent1Data(BaseModel):
    country: str
    travel_warning_level: Optional[str] = None
    travel_warning: Optional[TravelWarning] = None
    recent_safety_notices: list[SafetyNotice] = []
    security_environment: dict = {}
    recent_situations: list[dict] = []
    entrance_visa: dict = {}


class OdaProject(BaseModel):
    """KOICA 국별사업 보고서목록 CSV 기준 — 분야·지역·예산 없음.
    (KOICA 사업정보 API 복구 시 field/lat/lon 채워질 수 있어 optional 유지)"""
    name: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    link: Optional[str] = None
    field: Optional[str] = None      # API 복구 시
    lat: Optional[float] = None
    lon: Optional[float] = None


class KoreaOrg(BaseModel):
    """해외진출현황 CSV — 도시 정보 없음(국가 단위)."""
    name: str
    org_type: Optional[str] = None
    note: Optional[str] = None       # 진출내용


class Agent2Data(BaseModel):
    """팀원 B collector 출력의 정규화 뷰. 원본→이 형태 변환은 adapters.adapt_agent2()."""
    trade_volume_usd_million: Optional[float] = None
    oda_cumulative_usd_million: Optional[float] = None
    oda_yearly: dict[str, float] = {}          # {"2020": 12.3, ...} 지원실적 CSV
    oda_projects: list[OdaProject] = []        # fallback: 사업명·연도만
    oda_field_status: str = "unavailable"      # KOICA API 상태 (failed/ok)
    korea_orgs: list[KoreaOrg] = []
    expat_count: Optional[int] = None
    diplomatic_year: Optional[int] = None
    sources_used: list[str] = []
    sources_failed: list[str] = []
    sources_empty: list[str] = []


class RiskScore(BaseModel):
    """agent3 v2: 구조체. 구 포맷(float)은 validator가 승격."""
    score: float
    level: Optional[int] = None
    level_label: Optional[str] = None
    components: dict[str, float] = {}
    notice_count_used: Optional[int] = None


class CoopIndex(BaseModel):
    score: float
    grade: int


class Agent3Data(BaseModel):
    """agent3 신규 포맷 (cluster 제거, evidence/data_sources 추가)."""
    country: Optional[str] = None
    risk_score: RiskScore
    cooperation_index: CoopIndex
    opportunity_score: dict[str, float] = {}
    opportunity_ranking: list[list] = []
    similar_countries: list[list] = []
    evidence: dict = {}          # Agent1 원본 패스스루
    data_sources: dict = {}
    meta: dict = {}

    @field_validator("risk_score", mode="before")
    @classmethod
    def _lift_float(cls, v):
        if isinstance(v, (int, float)):
            return {"score": float(v)}
        return v

    @property
    def opportunity_meaningful(self) -> bool:
        """분야 데이터 부재 시 점수가 전부 동일/0 → 표시 무의미."""
        vals = list(self.opportunity_score.values())
        return len(vals) >= 2 and (max(vals) - min(vals)) > 1.0


class ReportRequest(BaseModel):
    user_query: str = ""
    target: Target = "기업"
    countries: list[str]


class Agent4Input(BaseModel):
    request: ReportRequest
    agent1: dict[str, Agent1Data] = {}
    agent2: Optional[dict[str, Agent2Data]] = None
    agent3: dict[str, Agent3Data]
    logs: list[dict] = []


# ══════════════════════════ 출력 ══════════════════════════

class Briefing(BaseModel):
    executive_summary: str = ""
    situation_analysis: str = ""
    risk_analysis: str = ""
    opportunity_analysis: str = ""
    recommendation: str = ""
    korea_perspective: Optional[str] = None
    counterpart_perspective: Optional[str] = None


class Card(BaseModel):
    id: str
    label: str
    value: Union[str, int, float]
    sub: Optional[str] = None
    color: Optional[str] = None
    max: Optional[float] = None
    confidence: Optional[float] = None
    grounds: Optional[list[str]] = None


class MapLayer(BaseModel):
    id: str
    source_agent: str
    type: str
    title: str = ""
    features: list[dict] = []


class MapBlock(BaseModel):
    center: list[float]
    zoom: int = 5
    layers: list[MapLayer] = []


class Chart(BaseModel):
    id: str
    source_agent: str
    type: str
    title: str = ""
    data: Union[dict, list] = {}


class EvidenceEntry(BaseModel):
    agent: str
    source: str
    action: str
    at: Optional[str] = None


class ReportMeta(BaseModel):
    report_type: str
    target: Target
    countries: list[str]
    user_query: str
    generated_at: str
    llm_model: str
    pipeline_version: str = "1.1"


class Agent4Output(BaseModel):
    meta: ReportMeta
    briefing: Briefing
    cards: list[Card] = []
    map: MapBlock
    dashboard: dict = {"charts": []}
    evidence: list[EvidenceEntry] = []
    files: dict = {"html": None, "pdf": None}
