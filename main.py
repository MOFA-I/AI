from fastapi import FastAPI
from pydantic import BaseModel
from issue_analyzer.service import IssueAnalyzer


class SafetyNotice(BaseModel):
    date: str | None
    title: str | None
    summary: str | None


class SecurityEnvironment(BaseModel):
    current_travel_alarm: str | None
    unemployment_rate: float | None
    suicide_death_rate: float | None


class RecentSituation(BaseModel):
    date: str
    event: str | None


class EntranceVisa(BaseModel):
    general_passport_visa_required: str | None
    general_passport_visa_note: str | None


class AnalyzeResponse(BaseModel):
    country: str
    travel_warning_level: str | None
    recent_safety_notices: list[SafetyNotice]
    security_environment: SecurityEnvironment
    recent_situations: list[RecentSituation]
    entrance_visa: EntranceVisa


app = FastAPI(title="MOFA Intelligence - Agent 1 테스트")
analyzer = IssueAnalyzer()


@app.get("/analyze/{country_name}", summary="Agent 1 통합 분석 (5개 API 요약)", response_model=AnalyzeResponse)
def analyze(country_name: str):
    return analyzer.analyze(country_name)
