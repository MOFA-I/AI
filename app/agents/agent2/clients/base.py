# app/agents/agent2/clients/base.py
import time
import requests


def call_api(url: str, params: dict, timeout: int = 15, max_retries: int = 3) -> dict:
    """
    표준화된 API 호출 함수 (재시도 포함).

    - 최대 max_retries번까지 자동 재시도 (지수 백오프: 1초, 2초, 4초...)
    - 성공/실패 관계없이 항상 이 형태로 반환:
        {"status": "ok" | "failed", "data": ..., "error": ...}
    - KOICA처럼 JSON이 아닐 수도 있어서 JSON 파싱 실패 시 원문 텍스트를 담아 반환함
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            res = requests.get(url, params=params, timeout=timeout)

            if res.status_code != 200:
                last_error = f"HTTP {res.status_code}: {res.text[:200]}"
            else:
                try:
                    return {"status": "ok", "data": res.json(), "error": None}
                except ValueError:
                    # JSON이 아니면(XML 등) 원문 텍스트 그대로 담아서 반환
                    return {
                        "status": "ok",
                        "data": res.text,
                        "error": "JSON 파싱 실패 - XML일 수 있음, data는 원문 텍스트",
                    }

        except requests.exceptions.RequestException as e:
            last_error = str(e)

        # 마지막 시도가 아니면 대기 후 재시도
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1초, 2초, 4초...
            print(f"  [재시도 {attempt + 1}/{max_retries}] {wait_time}초 대기 후 재시도... (에러: {last_error})")
            time.sleep(wait_time)

    return {"status": "failed", "data": None, "error": last_error}