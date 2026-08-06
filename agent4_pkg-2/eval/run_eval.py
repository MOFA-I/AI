# -*- coding: utf-8 -*-
"""run_eval.py — 브리핑 품질 평가 배치 실행.

프롬프트를 감으로 고치는 대신, 고정 케이스에 대해 측정해서 비교한다.

사용:
    python -m eval.run_eval                    # 전체 케이스 평가
    python -m eval.run_eval --case biz_low_risk
    python -m eval.run_eval --tag before-fix   # 결과에 라벨 붙여 저장
    python -m eval.run_eval --compare before-fix after-fix

결과는 eval/results/{tag}.json 에 저장되고, 마크다운 표로도 출력된다.
LLM 키가 없으면 규칙 기반 폴백으로 평가되므로(점수는 낮게 나옴) 파이프라인
자체 검증에는 쓸 수 있지만, 프롬프트 비교는 키가 있어야 의미가 있다.
"""

from __future__ import annotations
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from report_generator import Agent4ReportGenerator
from eval.cases import CASES
from eval.metrics import evaluate

logging.basicConfig(level=logging.WARNING)   # 평가 중 로그 소음 억제

RESULTS_DIR = Path(__file__).parent / "results"


def run(case_ids: list[str] | None = None) -> dict:
    gen = Agent4ReportGenerator(output_dir="eval/results/html")
    targets = case_ids or list(CASES)
    rows = []

    for cid in targets:
        case = CASES[cid]
        inp = case["input"]
        out = gen.generate(inp, html=False, verify=True)
        m = evaluate(out.briefing, inp.request.target, out.verification,
                     forbidden=case["forbidden"])
        rows.append({
            "case": cid, "desc": case["desc"],
            "target": inp.request.target,
            "model": out.meta.llm_model,
            "regenerated": out.verification.regenerated,
            **m,
        })
        print(f"  · {cid:16s} overall={m['overall']:.2f} "
              f"accuracy={m['accuracy']:.2f} sections={m['sections']:.2f} "
              f"{'⚠ 금지어위반' if not m['forbidden_ok'] else ''}")

    avg = {k: round(sum(r[k] for r in rows) / len(rows), 3)
           for k in ("overall", "accuracy", "sections", "length",
                     "target_fit", "density")}
    return {"generated_at": datetime.now().isoformat(timespec="seconds"),
            "cases": rows, "average": avg}


def to_markdown(result: dict) -> str:
    lines = ["| 케이스 | 타깃 | 종합 | 수치정확도 | 섹션 | 분량 | 타깃적합 | 미검증 |",
             "|---|---|---|---|---|---|---|---|"]
    for r in result["cases"]:
        lines.append(
            f"| {r['case']} | {r['target']} | **{r['overall']:.2f}** | "
            f"{r['accuracy']:.2f} | {r['sections']:.2f} | {r['length']:.2f} | "
            f"{r['target_fit']:.2f} | {r['unverified_count']} |")
    a = result["average"]
    lines.append(f"| **평균** | — | **{a['overall']:.2f}** | {a['accuracy']:.2f} "
                 f"| {a['sections']:.2f} | {a['length']:.2f} "
                 f"| {a['target_fit']:.2f} | — |")
    return "\n".join(lines)


def compare(tag_a: str, tag_b: str) -> None:
    a = json.loads((RESULTS_DIR / f"{tag_a}.json").read_text(encoding="utf-8"))
    b = json.loads((RESULTS_DIR / f"{tag_b}.json").read_text(encoding="utf-8"))
    print(f"\n{'케이스':<18}{tag_a:>10}{tag_b:>10}{'변화':>10}")
    print("-" * 48)
    bm = {r["case"]: r for r in b["cases"]}
    for r in a["cases"]:
        o = bm.get(r["case"])
        if not o:
            continue
        d = o["overall"] - r["overall"]
        mark = "▲" if d > 0.01 else ("▼" if d < -0.01 else "=")
        print(f"{r['case']:<18}{r['overall']:>10.2f}{o['overall']:>10.2f}"
              f"{mark + f' {d:+.2f}':>10}")
    da = b["average"]["overall"] - a["average"]["overall"]
    print("-" * 48)
    print(f"{'평균':<18}{a['average']['overall']:>10.2f}"
          f"{b['average']['overall']:>10.2f}{f'{da:+.2f}':>10}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", help="특정 케이스만 실행")
    ap.add_argument("--tag", default="latest", help="결과 저장 라벨")
    ap.add_argument("--compare", nargs=2, metavar=("TAG_A", "TAG_B"))
    args = ap.parse_args()

    if args.compare:
        compare(*args.compare)
        return

    print(f"[브리핑 품질 평가] 케이스 {args.case or '전체'}")
    result = run([args.case] if args.case else None)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{args.tag}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                    encoding="utf-8")

    print("\n" + to_markdown(result))
    print(f"\n→ 저장: {path}")


if __name__ == "__main__":
    main()
