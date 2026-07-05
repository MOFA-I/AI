from fastapi import FastAPI
from issue_analyzer.service import IssueAnalyzer

app = FastAPI(title="MOFA Intelligence - Agent 1 테스트")

analyzer = IssueAnalyzer()


@app.get("/analyze/{country_name}", summary="Agent 1 통합 분석 (5개 API 요약)")
def analyze(country_name: str):
    return analyzer.analyze(country_name)
