# -*- coding: utf-8 -*-
"""main.py — Agent 4 FastAPI 테스트 서버 (agent1 브랜치 컨벤션 미러링).

실행:  uvicorn main:app --reload --port 8004
문서:  http://localhost:8004/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from report_generator import Agent4ReportGenerator, Agent4Input

app = FastAPI(title="MOFA Intelligence - Agent 4 (Report Generator)")
generator = Agent4ReportGenerator()

_last_html: str | None = None  # 데모 편의용


@app.post("/report", summary="타깃별 보고서 생성 (JSON 계약 v1.0)")
def create_report(payload: Agent4Input):
    """Orchestrator가 호출: agent1/2/3 결과 봉투 → 출력 JSON (+HTML 파일)."""
    global _last_html
    try:
        out = generator.generate(payload, html=True)
        if out.files.get("html"):
            _last_html = open(out.files["html"], encoding="utf-8").read()
        return out
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/report/last", response_class=HTMLResponse,
         summary="마지막 생성 보고서 HTML 미리보기 (데모용)")
def last_report():
    if _last_html is None:
        raise HTTPException(status_code=404, detail="아직 생성된 보고서가 없습니다.")
    return _last_html
