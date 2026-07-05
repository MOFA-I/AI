from issue_analyzer.service import IssueAnalyzer
from orchestrator.llm import extract_intent, generate_chat_answer, generate_briefing

_analyzer = IssueAnalyzer()

GENERAL_USER = "일반사용자"
BUSINESS = "기업"
RESEARCHER = "연구자"


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

    # 기업/연구자: Agent 1 기반 브리핑 초안 + 추후 Agent 2~4 연결
    briefing = generate_briefing(country_name, agent1_result)
    return {
        "type": "report",
        "country": country_name,
        "briefing": briefing,
        "agent1_data": agent1_result,
        # TODO: agent2_result = IntelligenceCollector().collect(country_name)
        # TODO: agent3_result = InsightGenerator().analyze(agent1_result, agent2_result)
    }
