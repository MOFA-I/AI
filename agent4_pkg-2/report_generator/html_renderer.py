# -*- coding: utf-8 -*-
"""html_renderer.py — Agent4Output(JSON) → HTML 보고서.

JSON이 계약이고 HTML은 그 표현 중 하나. React 프론트는 같은 JSON을 직접 렌더.
folium(지도)·plotly(차트)를 여기서만 사용 — map_layers/dashboard는 순수 데이터.
"""

from __future__ import annotations
import folium
import plotly.graph_objects as go

from .schemas import Agent4Output, MapBlock, Card

ALERT_STYLE = {
    0: ("#78909c", 14), 1: ("#1e88e5", 16), 2: ("#fbc02d", 20),
    3: ("#e53935", 24), 4: ("#212121", 28),
}
FIELD_COLORS = {"농업": "green", "보건의료": "red", "교육": "purple",
                "공공행정": "gray", "기후환경": "darkgreen",
                "ICT/디지털": "blue"}


# ── 지도 렌더 ────────────────────────────────────────────────
def render_map(block: MapBlock) -> str:
    m = folium.Map(location=block.center, zoom_start=block.zoom,
                   tiles="CartoDB positron")

    for layer in block.layers:
        fg = folium.FeatureGroup(name=layer.title or layer.id, show=True)

        if layer.type == "alert_markers":
            for f in layer.features:
                color, radius = ALERT_STYLE.get(f["alert_level"], ALERT_STYLE[0])
                scope = " · 일부지역" if f.get("partial") else ""
                folium.CircleMarker(
                    location=[f["lat"], f["lon"]], radius=radius,
                    color=color, fill=True, fillColor=color, fillOpacity=0.5,
                    dash_array="6" if f.get("partial") else None,
                    tooltip=f"{f['country']} — {f['alert_level']}단계 "
                            f"{f['alert_label']}{scope}",
                ).add_to(fg)

        elif layer.type == "point_markers":
            for f in layer.features:
                is_oda = layer.id == "oda_projects"
                icon_color = FIELD_COLORS.get(f.get("field"), "blue") \
                    if is_oda else "cadetblue"
                budget = f.get("budget_usd_million")
                popup = (f"<b>{f['name']}</b><br>"
                         + (f"분야: {f.get('field')}<br>" if f.get('field') else "")
                         + (f"지역: {f.get('region')}<br>" if f.get('region') else "")
                         + (f"연도: {f.get('year')}<br>" if f.get('year') else "")
                         + (f"예산: {budget}백만$<br>" if budget else "")
                         + f"<small>{'KOICA ODA' if is_oda else '한국기관'}</small>")
                folium.Marker(
                    location=[f["lat"], f["lon"]],
                    popup=folium.Popup(popup, max_width=280),
                    tooltip=f["name"],
                    icon=folium.Icon(color=icon_color,
                                     icon="briefcase" if is_oda else "home",
                                     prefix="fa"),
                ).add_to(fg)

        elif layer.type == "agg_markers":
            is_oda = layer.id == "oda_summary"
            for f in layer.features:
                if is_oda:
                    items = "".join(
                        f"<li>{p['name'][:30]}"
                        + (f" ({p['start_year']}~)" if p.get('start_year') else "")
                        + "</li>"
                        for p in f.get("recent_projects", []))
                    cum = f.get("cumulative_usd_million")
                    popup = (f"<b>{f['country']} — KOICA ODA {f['count']}건</b><br>"
                             + (f"누적 지원 {cum:,.1f}백만$<br>" if cum else "")
                             + f"<u>최근 사업</u><ul style='margin:4px 0 0 16px'>{items}</ul>"
                             + "<small>※ 사업 위치정보 미제공 → 국가 단위 표시</small>")
                    icon = folium.Icon(color="blue", icon="briefcase", prefix="fa")
                    tip = f"{f['country']} ODA {f['count']}건"
                else:
                    items = "".join(
                        f"<li>{o['name']}"
                        + (f" ({o['org_type']})" if o.get('org_type') else "")
                        + "</li>"
                        for o in f.get("orgs", []))
                    popup = (f"<b>{f['country']} — 한국기관 {f['count']}곳</b>"
                             f"<ul style='margin:4px 0 0 16px'>{items}</ul>")
                    icon = folium.Icon(color="cadetblue", icon="home", prefix="fa")
                    tip = f"{f['country']} 한국기관 {f['count']}곳"
                folium.Marker(location=[f["lat"], f["lon"]],
                              popup=folium.Popup(popup, max_width=300),
                              tooltip=tip, icon=icon).add_to(fg)

        elif layer.type == "arc":
            for f in layer.features:
                v = f.get("value_usd_million", 0)
                folium.PolyLine(
                    locations=[f["from"], f["to"]],
                    color="#1a2980", weight=max(2, min(10, v / 15000)),
                    opacity=0.7,
                    tooltip=f"{f['label']}: {v:,.0f}백만$",
                ).add_to(fg)

        elif layer.type == "similarity_lines":
            for f in layer.features:
                folium.PolyLine(
                    locations=[f["from"], f["to"]],
                    color="#6a1b9a", weight=max(1, f["similarity"] * 5),
                    opacity=0.6, dash_array="8",
                    tooltip=f"{f['label']} 유사도 {f['similarity']}",
                ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl().add_to(m)
    return m._repr_html_()


# ── 차트 렌더 ────────────────────────────────────────────────
def render_chart(chart: dict) -> str:
    t, d = chart["type"], chart["data"]
    fig = None

    if t == "scatter":
        fig = go.Figure(go.Scatter(
            x=[p["x"] for p in d], y=[p["y"] for p in d],
            mode="markers+text", text=[p["country"] for p in d],
            textposition="top center",
            marker=dict(size=[p["grade"] * 7 + 6 for p in d],
                        color=[p["grade"] for p in d],
                        colorscale="Viridis", showscale=True,
                        colorbar=dict(title="등급")),
        ))
        fig.update_layout(xaxis_title="위험도", yaxis_title="협력지수")

    elif t == "bar_h":
        rk = d["ranking"]
        fig = go.Figure(go.Bar(
            y=[r[0] for r in rk][::-1], x=[r[1] for r in rk][::-1],
            orientation="h", marker_color="steelblue"))

    elif t == "bar":
        fig = go.Figure(go.Bar(
            x=[r[0] for r in d], y=[r[1] for r in d],
            marker_color="mediumseagreen"))
        fig.update_yaxes(range=[0, 1])

    elif t == "line":
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["years"], y=d["values"],
                                 mode="lines+markers", name="전체",
                                 line=dict(width=3)))
        for field, vals in d.get("by_field", {}).items():
            fig.add_trace(go.Scatter(x=d["years"], y=vals,
                                     mode="lines", name=field,
                                     line=dict(dash="dot")))

    elif t == "timeline":
        events = sorted(d["events"], key=lambda e: str(e.get("date", "")))
        colors = {"milestone": "#1a2980", "diplomatic": "#26a69a",
                  "recent": "#ef6c00"}
        fig = go.Figure(go.Scatter(
            x=[e["date"] for e in events], y=[1] * len(events),
            mode="markers+text",
            text=[e["event"][:24] for e in events],
            textposition="top center", textfont=dict(size=10),
            marker=dict(size=12,
                        color=[colors.get(e.get("kind"), "#999")
                               for e in events]),
        ))
        fig.update_yaxes(visible=False)
        fig.update_layout(height=260)

    if fig is None:
        return ""
    fig.update_layout(title=chart.get("title", ""), template="plotly_white",
                      height=fig.layout.height or 380,
                      margin=dict(l=40, r=20, t=50, b=40))
    return fig.to_html(full_html=False, include_plotlyjs=False)


# ── 카드 렌더 ────────────────────────────────────────────────
def render_cards(cards: list[Card]) -> str:
    html = '<div class="cards">'
    for c in cards:
        grounds = ""
        if c.grounds:
            grounds = ("<ul class='grounds'>"
                       + "".join(f"<li>{g}</li>" for g in c.grounds)
                       + "</ul>")
        conf = f"<span class='conf'>확신도 {c.confidence:.0%}</span>" \
            if c.confidence else ""
        maxv = f"<span class='max'>/ {c.max:g}</span>" if c.max else ""
        color = f"border-top:4px solid {c.color};" if c.color else \
                "border-top:4px solid #1a2980;"
        html += (f'<div class="card" style="{color}">'
                 f'<div class="card-label">{c.label}</div>'
                 f'<div class="card-value">{c.value}{maxv}</div>'
                 f'{f"<div class=card-sub>{c.sub}</div>" if c.sub else ""}'
                 f'{conf}{grounds}</div>')
    return html + "</div>"


# ── 전체 HTML ────────────────────────────────────────────────
def render_html(out: Agent4Output) -> str:
    b = out.briefing
    briefing_html = "".join(
        f"<h3>{title}</h3><p>{text}</p>"
        for title, text in [
            ("Executive Summary", b.executive_summary),
            ("Situation Analysis", b.situation_analysis),
            ("Risk Analysis", b.risk_analysis),
            ("Opportunity Analysis", b.opportunity_analysis),
            ("Recommendation", b.recommendation),
        ] if text)
    if b.korea_perspective:
        briefing_html += (f"<h3>한국 입장</h3><p>{b.korea_perspective}</p>"
                          f"<h3>상대국 입장</h3><p>{b.counterpart_perspective}</p>")

    charts_html = "".join(f'<div class="chart">{render_chart(c)}</div>'
                          for c in out.dashboard["charts"])
    map_html = render_map(out.map)
    evidence_rows = "".join(
        f"<tr><td><b>{e.agent}</b></td><td>{e.source}</td>"
        f"<td>{e.action}</td><td>{e.at or ''}</td></tr>"
        for e in out.evidence)

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{out.meta.report_type} — {', '.join(out.meta.countries)}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans KR',sans-serif;background:#f0f2f5;color:#333}}
.container{{max-width:1400px;margin:0 auto;background:#fff}}
.header{{background:linear-gradient(135deg,#1a2980,#26d0ce);color:#fff;padding:36px 40px}}
.header h1{{font-size:1.8em}} .header .meta{{opacity:.9;margin-top:10px;font-size:.93em}}
.header .meta span{{margin-right:22px}}
section{{padding:32px 40px}}
section h2{{color:#1a2980;border-bottom:3px solid #26d0ce;padding-bottom:8px;margin-bottom:20px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}}
.card{{background:#fafbfc;border:1px solid #e3e6ea;border-radius:8px;padding:18px}}
.card-label{{font-size:.85em;color:#777}} .card-value{{font-size:1.7em;font-weight:700;margin:6px 0}}
.card-value .max{{font-size:.55em;color:#999;font-weight:400}}
.card-sub{{font-size:.85em;color:#555}} .conf{{font-size:.8em;color:#1a2980}}
.grounds{{margin:8px 0 0 18px;font-size:.82em;color:#666}}
.briefing{{line-height:1.9;max-width:920px}} .briefing h3{{color:#1a2980;margin:20px 0 8px}}
.map-wrap iframe{{width:100%!important;height:520px!important;border:none;border-radius:8px}}
.charts{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.chart{{background:#fff;border:1px solid #eee;border-radius:8px;padding:8px}}
.chart:has([id*=timeline]),.chart:has([id*=oda_trend]){{grid-column:1/-1}}
table{{width:100%;border-collapse:collapse;font-size:.88em}}
th,td{{border:1px solid #ddd;padding:9px;text-align:left}}
th{{background:#1a2980;color:#fff}} tr:nth-child(even){{background:#f8f9fb}}
.disclaimer{{background:#fff8e1;border-left:4px solid #ffb300;padding:12px 16px;margin-top:20px;font-size:.88em;color:#795548}}
.footer{{background:#1a2980;color:#fff;text-align:center;padding:20px;font-size:.88em}}
@media(max-width:900px){{.charts{{grid-template-columns:1fr}}}}
</style></head><body><div class="container">
<div class="header">
  <h1>🌍 {out.meta.report_type}</h1>
  <div class="meta">
    <span>📋 {out.meta.user_query or '-'}</span>
    <span>🌏 {', '.join(out.meta.countries)}</span>
    <span>👥 {out.meta.target}</span>
    <span>⏰ {out.meta.generated_at[:16].replace('T', ' ')}</span>
  </div>
</div>
<section><h2>📌 핵심 지표</h2>{render_cards(out.cards)}</section>
<section><h2>📝 AI 종합 브리핑</h2><div class="briefing">{briefing_html}</div></section>
<section><h2>🗺️ 지리공간 분석</h2><div class="map-wrap">{map_html}</div></section>
<section><h2>📊 정량 분석 대시보드</h2><div class="charts">{charts_html}</div></section>
<section><h2>🔍 Evidence — 전 Agent 작업 로그</h2>
<table><thead><tr><th>Agent</th><th>출처/기술</th><th>작업</th><th>시각</th></tr></thead>
<tbody>{evidence_rows}</tbody></table>
<div class="disclaimer">⚠️ 본 보고서는 외교부·KOICA 공공데이터 기반 자동 분석이며
정책 참고용입니다. 브리핑 문장은 AI가 생성했고, 모든 수치·지도·차트는 원천 데이터에서
결정적으로 계산되었습니다(LLM 미개입).</div></section>
<div class="footer"><p>🤖 MOFA Intelligence v{out.meta.pipeline_version} —
멀티에이전트 외교 인텔리전스 플랫폼</p></div>
</div></body></html>"""
