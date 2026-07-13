import json
from pathlib import Path

from issue_analyzer.service import IssueAnalyzer
from orchestrator.llm import extract_intent, generate_chat_answer
from app.agents.agent2.collector import collect
from insight.analyzer import InsightGenerator
from report_generator import Agent4ReportGenerator
from report_generator.schemas import Agent4Input, ReportRequest
from adapters import adapt_agent1, adapt_agent2, adapt_agent3

_analyzer = IssueAnalyzer()
_report_generator = Agent4ReportGenerator()

GENERAL_USER = "일반사용자"
BUSINESS = "기업"
RESEARCHER = "연구자"

# Agent2 target_type ("general"|"business"|"researcher") <- user_type
_AGENT2_TARGET_TYPE = {BUSINESS: "business", RESEARCHER: "researcher"}

_REFERENCE_DATA_PATH = Path(__file__).resolve().parent.parent / "reference_data" / "countries.json"


def _load_reference_dataset() -> dict:
    """Agent3의 cooperation_index/opportunity_score/similar_countries 계산용 참조국 데이터.
    scripts/build_reference_dataset.py로 미리 생성해둔 캐시를 읽는다.
    아직 안 만들었으면 빈 dict로 시작 (해당 지표들은 채워지지 않음)."""
    if not _REFERENCE_DATA_PATH.exists():
        return {}
    return json.loads(_REFERENCE_DATA_PATH.read_text(encoding="utf-8"))


_reference_dataset = _load_reference_dataset()


def run(user_input: str, user_type: str) -> dict:
    """
    user_type: "일반사용자" | "기업" | "연구자"
    """
    intent = extract_intent(user_input, user_type)
    country_name = intent.get("country_name")

    if not country_name:
        return {"error": "국가명을 파악하지 못했어요. 국가명을 포함해서 다시 질문해주세요."}

    agent1_result = _analyzer.analyze(country_name)

    if user_type == GENERAL_USER:
        answer = generate_chat_answer(user_input, agent1_result)
        return {
            "type": "chat",
            "country": country_name,
            "answer": answer,
            "data": agent1_result,
        }

    # 기업/연구자: Agent 2(수집) -> Agent 3(분석) -> Agent 4(리포트 생성) 전체 파이프라인
    agent2_result = collect(country_name, _AGENT2_TARGET_TYPE[user_type])
    agent3_result = InsightGenerator().analyze(
        agent1_result, agent2_result, reference_dataset=_reference_dataset
    )

    agent4_input = Agent4Input(
        request=ReportRequest(
            user_query=user_input,
            target=BUSINESS if user_type == BUSINESS else RESEARCHER,
            countries=[country_name],
        ),
        agent1={country_name: adapt_agent1(agent1_result)},
        agent2={country_name: adapt_agent2(agent2_result)},
        agent3=adapt_agent3(agent3_result),
    )
    out = _report_generator.generate(agent4_input, html=True)

    return {
        "type": "report",
        "country": country_name,
        "report": out.model_dump(),
    }
