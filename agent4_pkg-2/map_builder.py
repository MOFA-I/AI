# -*- coding: utf-8 -*-
"""
map_builder.py — Agent 1 출력 → 여행경보 지도 HTML (일반 사용자용)

사용법 (Agent 1의 FastAPI에서):
    from map_builder import build_alert_map
    result = analyzer.analyze(country_name)
    result["map_html"] = build_alert_map(result)

- 입력: IssueAnalyzer.analyze()의 반환 dict 그대로
- 반환: 셀프컨테인드 HTML 문자열 (srcdoc iframe, 프론트에 바로 임베드 가능)
- 좌표: 내장 테이블 → 없으면 Nominatim 지오코딩 폴백 (geopy 설치 시)
- 경보 단계: 구조화 필드 "travel_warning"이 있으면 사용,
  없으면 기존 "travel_warning_level" 문자열("2단계 여행자제 (일부 지역)")을 파싱

작성: Agent 4 담당 (지민) / 문의 환영
"""

from __future__ import annotations
import re
import logging
from typing import Optional

import folium

logger = logging.getLogger("map_builder")

# ── 국가 좌표 (KOICA 협력국 + 주요국) ─────────────────────────────
COUNTRY_COORDS = {
    "베트남": (14.0583, 108.2772), "인도네시아": (-0.7893, 113.9213),
    "태국": (15.8700, 100.9925), "필리핀": (12.8797, 121.7740),
    "몽골": (46.8625, 103.8467), "말레이시아": (4.2105, 101.9758),
    "캄보디아": (12.5657, 104.9910), "라오스": (19.8563, 102.4955),
    "미얀마": (21.9162, 95.9560), "인도": (20.5937, 78.9629),
    "방글라데시": (23.6850, 90.3563), "네팔": (28.3949, 84.1240),
    "스리랑카": (7.8731, 80.7718), "우즈베키스탄": (41.3775, 64.5853),
    "카자흐스탄": (48.0196, 66.9237), "사우디아라비아": (23.8859, 45.0792),
    "아랍에미리트": (23.4241, 53.8478), "이란": (32.4279, 53.6880),
    "이집트": (26.8206, 30.8025), "에티오피아": (9.1450, 40.4897),
    "케냐": (-0.0236, 37.9062), "탄자니아": (-6.3690, 34.8888),
    "가나": (7.9465, -1.0232), "나이지리아": (9.0820, 8.6753),
    "페루": (-9.1900, -75.0152), "콜롬비아": (4.5709, -74.2973),
    "볼리비아": (-16.2902, -63.5887), "파라과이": (-23.4425, -58.4438),
    "우크라이나": (48.3794, 31.1656), "중국": (35.8617, 104.1954),
    "일본": (36.2048, 138.2529), "미국": (37.0902, -95.7129),
    "튀르키예": (38.9637, 35.2433), "터키": (38.9637, 35.2433),
}

# 경보 단계별 스타일 (외교부 공식 색상 체계 준용)
ALERT_STYLE = {
    0: {"color": "#1e88e5", "label": "경보 없음", "radius": 18},
    1: {"color": "#1e88e5", "label": "여행유의(남색)", "radius": 20},
    2: {"color": "#fbc02d", "label": "여행자제(황색)", "radius": 24},
    3: {"color": "#e53935", "label": "철수권고(적색)", "radius": 28},
    4: {"color": "#212121", "label": "여행금지(흑색)", "radius": 32},
}


def _get_coords(country: str) -> Optional[tuple]:
    if country in COUNTRY_COORDS:
        return COUNTRY_COORDS[country]
    try:  # 지오코딩 폴백 (geopy 있을 때만)
        from geopy.geocoders import Nominatim
        loc = Nominatim(user_agent="mofa_intelligence").geocode(country, timeout=5)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception as e:
        logger.warning(f"지오코딩 실패({country}): {e}")
    return None


def _parse_warning(agent1: dict) -> dict:
    """구조화 필드 우선, 없으면 기존 문자열 파싱."""
    tw = agent1.get("travel_warning")
    if isinstance(tw, dict) and "level" in tw:
        return {"level": tw.get("level", 0),
                "label": tw.get("label") or ALERT_STYLE.get(tw.get("level", 0), {}).get("label", ""),
                "partial": bool(tw.get("partial"))}

    # 레거시: "2단계 여행자제 (일부 지역)" 파싱
    s = agent1.get("travel_warning_level") or ""
    m = re.search(r"([1-4])단계\s*(\S+)", s)
    level = int(m.group(1)) if m else 0
    label = m.group(2) if m else "경보 없음"
    partial = "일부" in s
    return {"level": level, "label": label, "partial": partial}


def build_alert_map(agent1_output: dict) -> str:
    """
    Agent 1 출력 → 여행경보 지도 HTML.

    Args:
        agent1_output: IssueAnalyzer.analyze() 반환 dict
    Returns:
        HTML 문자열 (iframe srcdoc 방식, 실패 시 안내 문구 HTML)
    """
    country = agent1_output.get("country", "")
    coords = _get_coords(country)
    if not coords:
        return f"<p>'{country}' 좌표를 찾지 못해 지도를 생성할 수 없습니다.</p>"

    warning = _parse_warning(agent1_output)
    style = ALERT_STYLE.get(warning["level"], ALERT_STYLE[0])
    visa = agent1_output.get("entrance_visa") or {}
    notices = agent1_output.get("recent_safety_notices") or []

    m = folium.Map(location=coords, zoom_start=6, tiles="CartoDB positron")

    # 경보 마커 (색상=단계)
    scope = " · 일부 지역" if warning["partial"] else ""
    notice_html = "<br>".join(
        f"· {(n.get('title') or n.get('summary', ''))[:40]}" if isinstance(n, dict) else f"· {str(n)[:40]}"
        for n in notices[:3]
    ) or "최근 공지 없음"

    popup = f"""
    <div style="font-family:sans-serif; min-width:230px">
      <h4 style="margin:0 0 6px">{country}</h4>
      <div style="background:{style['color']}; color:#fff; display:inline-block;
                  padding:3px 10px; border-radius:12px; font-size:13px; margin-bottom:8px">
        {warning['level']}단계 {warning['label']}{scope}
      </div><br>
      <b>비자:</b> {visa.get('general_passport_visa_note') or '정보 없음'}<br>
      <b>최근 안전공지:</b><br>{notice_html}<br>
      <small style="color:#888">출처: 외교부 여행경보·안전정보 API</small>
    </div>"""

    folium.CircleMarker(
        location=coords, radius=style["radius"],
        color=style["color"], fill=True, fillColor=style["color"],
        fillOpacity=0.55 if warning["partial"] else 0.8, weight=3,
        dash_array="6" if warning["partial"] else None,  # 일부 지역 = 점선 테두리
        popup=folium.Popup(popup, max_width=320),
        tooltip=f"{country} — {warning['level']}단계 {warning['label']}{scope}",
    ).add_to(m)

    folium.Marker(location=coords, icon=folium.DivIcon(html=(
        f'<div style="font-size:13px;font-weight:bold;color:#333;'
        f'text-shadow:1px 1px 2px #fff;white-space:nowrap;'
        f'transform:translate(-50%,{style["radius"] + 6}px)">{country}</div>'
    ))).add_to(m)

    # 범례
    m.get_root().html.add_child(folium.Element("""
    <div style="position:absolute; bottom:16px; left:16px; z-index:9999;
                background:#fff; border:1px solid #ccc; border-radius:6px;
                padding:10px 14px; font:12px sans-serif; box-shadow:0 2px 6px rgba(0,0,0,.15)">
      <b>여행경보 단계</b><br>
      <span style="color:#1e88e5">●</span> 1단계 여행유의&nbsp;
      <span style="color:#fbc02d">●</span> 2단계 여행자제<br>
      <span style="color:#e53935">●</span> 3단계 철수권고&nbsp;
      <span style="color:#212121">●</span> 4단계 여행금지<br>
      <small>점선 테두리 = 일부 지역만 해당</small>
    </div>"""))

    return m._repr_html_()


# ── 단독 테스트 ──────────────────────────────────────────────────
if __name__ == "__main__":
    # 케이스 1: 현재 Agent 1 출력 (구조화 필드 없음 → 문자열 파싱)
    legacy = {
        "country": "베트남",
        "travel_warning_level": "2단계 여행자제 (일부 지역)",
        "recent_safety_notices": [
            {"date": "2026-07-01", "title": "하노이 집회 유의", "summary": "..."}],
        "entrance_visa": {"general_passport_visa_required": "N",
                          "general_passport_visa_note": "45일 무비자"},
    }
    html1 = build_alert_map(legacy)

    # 케이스 2: 구조화 필드 추가 후 (요청 반영 시)
    structured = {**legacy, "travel_warning": {"level": 3, "label": "철수권고", "partial": False}}
    html2 = build_alert_map(structured)

    with open("test_map_legacy.html", "w", encoding="utf-8") as f:
        f.write(html1)
    with open("test_map_structured.html", "w", encoding="utf-8") as f:
        f.write(html2)
    print(f"legacy: {len(html1):,}자 / structured: {len(html2):,}자 — 두 케이스 모두 생성 성공")
