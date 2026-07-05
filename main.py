from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from issue_analyzer.service import IssueAnalyzer
from orchestrator.router import run
from orchestrator.llm import generate_briefing

app = FastAPI(title="MOFA Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = IssueAnalyzer()


class QueryRequest(BaseModel):
    user_input: str
    user_type: str  # "일반사용자" | "기업" | "연구자"


@app.post("/query", summary="자연어 질문 처리 (Orchestrator)")
def query(request: QueryRequest):
    return run(request.user_input, request.user_type)


@app.get("/analyze/{country_name}", summary="Agent 1 직접 호출 (테스트용)")
def analyze(country_name: str):
    return analyzer.analyze(country_name)


@app.get("/briefing/{country_name}", summary="국가 브리핑 생성 (기업/연구자용)")
def briefing(country_name: str):
    data = analyzer.analyze(country_name)
    text = generate_briefing(country_name, data)
    return {"country": country_name, "briefing": text, "data": data}


