import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-haiku-4-5-20251001"


def extract_intent(user_input: str, user_type: str) -> dict:
    """사용자 입력에서 국가명(한글)과 핵심 질문을 추출한다."""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=(
            "너는 외교 인텔리전스 플랫폼의 라우터야. "
            "사용자 입력에서 아래 정보를 추출해서 반드시 JSON만 반환해. 다른 텍스트는 절대 쓰지 마.\n"
            '{"country_name": "한글 국가명", "key_question": "핵심 질문 한 줄 요약"}\n'
            "국가명은 반드시 한글로. 국가를 특정할 수 없으면 country_name을 null로."
        ),
        messages=[{"role": "user", "content": f"사용자 타입: {user_type}\n질문: {user_input}"}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_chat_answer(user_input: str, agent1_data: dict) -> str:
    """일반 사용자용: Agent 1 데이터를 바탕으로 챗봇 답변을 생성한다."""
    # recent_situations는 정치 동향 위주라 일반 여행자에게 의미 없으므로 제외
    data_for_llm = {k: v for k, v in agent1_data.items() if k != "recent_situations"}

    response = _client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=(
            "너는 외교부 공식 데이터를 바탕으로 여행 안전 정보를 안내하는 AI야.\n"
            "규칙:\n"
            "- 사용자 질문에 직접 답하는 2~3문장 핵심 요약만 써. 헤더나 목록은 쓰지 마.\n"
            "- 숫자·등급 데이터(여행경보 단계, 실업률 등)는 텍스트로 반복하지 마. 프론트에서 시각화한다.\n"
            "- 최근 안전 공지 중 가장 중요한 것 1건만 언급해.\n"
            "- 출처가 외교부 공식 데이터임을 마지막 문장에 한 번만 밝혀."
        ),
        messages=[
            {
                "role": "user",
                "content": f"질문: {user_input}\n\n외교부 데이터:\n{json.dumps(data_for_llm, ensure_ascii=False, indent=2)}",
            }
        ],
    )
    return response.content[0].text


def generate_briefing(country_name: str, agent1_data: dict) -> str:
    """브리핑용: Agent 1 데이터를 바탕으로 외교 인텔리전스 브리핑 초안을 생성한다."""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=(
            "너는 외교부 공식 데이터를 분석해 전문 브리핑 문서를 작성하는 AI야.\n"
            "다음 구조로 마크다운 브리핑을 작성해:\n"
            "1. **종합 위험 평가** (2문장, 여행경보 단계 포함)\n"
            "2. **핵심 안전 이슈** (최근 공지 기반, 3줄 이내)\n"
            "3. **입국 요건 요약** (비자 여부 + 주의사항 1줄)\n"
            "4. **권고 사항** (구체적 행동 지침 2~3가지, 불릿)\n"
            "출처: 외교부 공식 데이터 기반 AI 분석 (참고용, 최신 정보는 외교부 공식 사이트 확인 권장)"
        ),
        messages=[
            {
                "role": "user",
                "content": f"국가: {country_name}\n\n외교부 데이터:\n{json.dumps(agent1_data, ensure_ascii=False, indent=2)}",
            }
        ],
    )
    return response.content[0].text
