"""제품명 정리: 브랜드 통일, 용량·수량 분리, 판촉 문구 제거."""
from __future__ import annotations

import re

from config import BRAND_ALIASES

# [올리브영단독], (기획), 1+1 같은 판촉 표기
NOISE = re.compile(
    r"\[[^\]]*\]|\([^)]*기획[^)]*\)|\b\d\s*\+\s*\d\b|무료배송|당일발송|사은품|증정|한정|세트", re.I)
VOLUME = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|mL|ML|g|G|매|ea|EA|정)\b")
SPF = re.compile(r"(SPF\s?\d{1,2}\+?)", re.I)
COUNT = re.compile(r"(\d+)\s*(?:매|개입|팩)")
SPACES = re.compile(r"\s{2,}")


def brand(raw: str) -> str:
    raw = (raw or "").strip()
    if raw in BRAND_ALIASES:
        return BRAND_ALIASES[raw]
    # "아누아(ANUA)" 처럼 괄호에 로마자를 붙인 표기 정리
    stripped = re.sub(r"\s*\([^)]*\)\s*$", "", raw).strip()
    return BRAND_ALIASES.get(stripped, stripped or raw)


def spec(name: str) -> str:
    """제품명에서 용량/수량 표기를 뽑아냅니다. 없으면 빈 문자열."""
    volumes = VOLUME.findall(name)
    if volumes:
        amount, unit = volumes[0]
        amount = amount.rstrip("0").rstrip(".") if "." in amount else amount
        return f"{amount}{unit.lower().replace('ea', '개')}"
    counted = COUNT.search(name)
    return f"{counted.group(1)}매" if counted else ""


def title(name: str, brand_name: str = "") -> str:
    """판촉 문구와 브랜드 접두어를 떼고 제품명만 남깁니다."""
    cleaned = NOISE.sub(" ", name or "")
    if brand_name and cleaned.strip().startswith(brand_name):
        cleaned = cleaned.strip()[len(brand_name):]
    cleaned = VOLUME.sub(" ", cleaned)
    cleaned = SPACES.sub(" ", cleaned).strip(" -·,")
    spf = SPF.search(name or "")
    if spf and spf.group(1).upper().replace(" ", "") not in cleaned.upper().replace(" ", ""):
        cleaned = f"{cleaned} {spf.group(1).upper().replace(' ', '')}"
    return cleaned.strip()


def key(brand_name: str, product_name: str, product_spec: str) -> str:
    """같은 상품인지 비교할 때 쓰는 키. 공백·기호·대소문자를 지웁니다."""
    joined = f"{brand_name}|{product_name}|{product_spec}"
    return re.sub(r"[\s\-_·,.()/]+", "", joined).lower()


def item(raw) -> dict:
    """RawItem -> 정규화된 dict."""
    b = brand(raw.brand)
    n = title(raw.name, b)
    s = spec(raw.name)
    return {
        "brand": b, "name": n, "spec": s, "key": key(b, n, s),
        "channel": raw.channel, "price": int(raw.price), "url": raw.url,
        "rating": raw.rating, "reviews": raw.reviews,
        "source_name": raw.name, "category_hint": raw.category_hint,
    }
