# -*- coding: utf-8 -*-
"""generator.py — Agent 4 진입점. 모든 블록을 조립해 Agent4Output 생성."""

from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

from .schemas import (Agent4Input, Agent4Output, ReportMeta, MapBlock,
                      Verification)
from .cards import build_cards
from .map_layers import build_map
from .dashboard import build_dashboard
from .llm import generate_briefing
from .evidence import build_evidence
from .validator import verify_briefing
from .html_renderer import render_html

logger = logging.getLogger("agent4")

REPORT_TYPE = {"기업": "Business Intelligence Report",
               "연구자": "Policy & Research Brief"}

# 검증 통과 기준: 수치 인용 정확도가 이 값 미만이면 브리핑 1회 재생성
VERIFY_THRESHOLD = 0.9


class Agent4ReportGenerator:
    """사용:
        gen = Agent4ReportGenerator()
        output = gen.generate(agent4_input)           # Agent4Output (JSON 계약)
        output = gen.generate(agent4_input, html=True)  # + files.html 생성
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)

    def generate(self, inp: Agent4Input, html: bool = True,
                 verify: bool = True) -> Agent4Output:
        req = inp.request
        countries = [c for c in req.countries if c in inp.agent3]
        if not countries:
            raise ValueError("agent3 결과에 존재하는 국가가 없습니다.")
        logger.info(f"[Agent4] {req.target} 보고서 생성: {countries}")

        main = countries[0]

        # 결정적 블록들 (LLM 미사용)
        cards = build_cards(main, inp.agent3[main], req.target)
        map_block = build_map(countries, inp.agent1, inp.agent2,
                              inp.agent3, req.target)
        dash = build_dashboard(countries, inp.agent1, inp.agent2,
                               inp.agent3, req.target)

        # briefing (유일한 LLM 블록)
        briefing, model_used = generate_briefing(
            req.user_query, req.target, countries,
            inp.agent1, inp.agent2, inp.agent3)

        # 브리핑 수치 검증 — LLM이 데이터에 없는 숫자를 쓰지 않았는지 대조
        verification = Verification()
        if verify:
            verification = verify_briefing(briefing, countries,
                                           inp.agent1, inp.agent2, inp.agent3)
            logger.info(f"[Agent4] 수치 검증 {verification.verified}/"
                        f"{verification.checked} (정확도 {verification.rate:.0%})")
            # 임계치 미달 시 1회 재생성 (무한루프 방지를 위해 재시도 없음)
            if verification.rate < VERIFY_THRESHOLD and verification.checked:
                logger.warning("[Agent4] 검증 임계치 미달 → 브리핑 재생성 1회 시도")
                retry_briefing, retry_model = generate_briefing(
                    req.user_query, req.target, countries,
                    inp.agent1, inp.agent2, inp.agent3,
                    unverified=verification.unverified)
                retry_verification = verify_briefing(
                    retry_briefing, countries,
                    inp.agent1, inp.agent2, inp.agent3)
                # 개선된 경우에만 교체
                if retry_verification.rate > verification.rate:
                    briefing, model_used = retry_briefing, retry_model
                    verification = retry_verification
                verification.regenerated = True

        evidence = build_evidence(inp.logs, countries,
                                  inp.agent2, inp.agent3, model_used)

        out = Agent4Output(
            meta=ReportMeta(
                report_type=REPORT_TYPE[req.target], target=req.target,
                countries=countries, user_query=req.user_query,
                generated_at=datetime.now().isoformat(timespec="seconds"),
                llm_model=model_used),
            briefing=briefing, cards=cards, map=map_block,
            dashboard=dash, evidence=evidence, verification=verification,
        )

        if html:
            self.output_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.output_dir / f"report_{req.target}_{ts}.html"
            path.write_text(render_html(out), encoding="utf-8")
            out.files["html"] = str(path)
            logger.info(f"[Agent4] HTML 저장: {path}")

        return out
