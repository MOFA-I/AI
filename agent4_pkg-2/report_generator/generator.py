# -*- coding: utf-8 -*-
"""generator.py — Agent 4 진입점. 모든 블록을 조립해 Agent4Output 생성."""

from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

from .schemas import Agent4Input, Agent4Output, ReportMeta, MapBlock
from .cards import build_cards
from .map_layers import build_map
from .dashboard import build_dashboard
from .llm import generate_briefing
from .evidence import build_evidence
from .html_renderer import render_html

logger = logging.getLogger("agent4")

REPORT_TYPE = {"기업": "Business Intelligence Report",
               "연구자": "Policy & Research Brief"}


class Agent4ReportGenerator:
    """사용:
        gen = Agent4ReportGenerator()
        output = gen.generate(agent4_input)           # Agent4Output (JSON 계약)
        output = gen.generate(agent4_input, html=True)  # + files.html 생성
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)

    def generate(self, inp: Agent4Input, html: bool = True) -> Agent4Output:
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

        evidence = build_evidence(inp.logs, countries,
                                  inp.agent2, inp.agent3, model_used)

        out = Agent4Output(
            meta=ReportMeta(
                report_type=REPORT_TYPE[req.target], target=req.target,
                countries=countries, user_query=req.user_query,
                generated_at=datetime.now().isoformat(timespec="seconds"),
                llm_model=model_used),
            briefing=briefing, cards=cards, map=map_block,
            dashboard=dash, evidence=evidence,
        )

        if html:
            self.output_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.output_dir / f"report_{req.target}_{ts}.html"
            path.write_text(render_html(out), encoding="utf-8")
            out.files["html"] = str(path)
            logger.info(f"[Agent4] HTML 저장: {path}")

        return out
