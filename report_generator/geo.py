# -*- coding: utf-8 -*-
"""geo.py — 국가/지역명 → 좌표. 내장 테이블 → Nominatim 폴백 → 파일 캐시."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("agent4.geo")

_CACHE_PATH = Path(__file__).parent / ".geo_cache.json"

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

KOREA_COORDS = (36.5, 127.9)  # 무역 흐름 호(arc)의 출발점


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    try:
        _CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception as e:
        logger.warning(f"지오캐시 저장 실패: {e}")


def get_coords(name: str, country_hint: str = "") -> Optional[tuple]:
    """국가명 또는 '국가 내 지역명'(예: '달랏') → (lat, lon).

    Args:
        name: 국가명 또는 지역명
        country_hint: 지역명일 때 검색 정확도를 위한 국가명 (예: "베트남")
    """
    if name in COUNTRY_COORDS:
        return COUNTRY_COORDS[name]

    cache = _load_cache()
    key = f"{name}|{country_hint}"
    if key in cache:
        v = cache[key]
        return tuple(v) if v else None

    coords = None
    try:
        from geopy.geocoders import Nominatim
        query = f"{name}, {country_hint}" if country_hint else name
        loc = Nominatim(user_agent="mofa_intelligence").geocode(query, timeout=5)
        if loc:
            coords = (loc.latitude, loc.longitude)
    except Exception as e:
        logger.warning(f"지오코딩 실패({name}): {e}")

    cache[key] = list(coords) if coords else None
    _save_cache(cache)
    return coords
