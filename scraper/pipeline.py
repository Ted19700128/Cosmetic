"""동일 상품 매칭, 속성 태깅, 페이지가 읽는 JSON으로 내보내기."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import normalize
from config import (AGE_HINTS, CONCERN_KEYWORDS, GENDER_KEYWORDS,
                    USE_KEYWORDS, VIBE_KEYWORDS)

SIMILARITY_FLOOR = 0.86     # 키가 다를 때 같은 상품으로 묶는 문자열 유사도 기준


# ------------------------------------------------------------------ 매칭
def group(rows: list[dict]) -> list[dict]:
    """채널별로 흩어진 같은 상품을 하나로 묶고 가격을 붙입니다."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[row["key"]].append(row)

    # 키가 살짝 어긋난 항목을 같은 브랜드 안에서 유사도로 흡수
    keys_by_brand: dict[str, list[str]] = defaultdict(list)
    for k, group_rows in buckets.items():
        keys_by_brand[group_rows[0]["brand"]].append(k)

    merged_into: dict[str, str] = {}
    for brand_keys in keys_by_brand.values():
        for i, a in enumerate(brand_keys):
            if a in merged_into:
                continue
            for b in brand_keys[i + 1:]:
                if b in merged_into:
                    continue
                if SequenceMatcher(None, a, b).ratio() >= SIMILARITY_FLOOR:
                    merged_into[b] = a

    for src, dst in merged_into.items():
        buckets[dst].extend(buckets.pop(src, []))

    products = []
    for rows_for_key in buckets.values():
        best = max(rows_for_key, key=lambda r: (bool(r["spec"]), len(r["name"])))
        offers = {}
        for row in rows_for_key:                      # 같은 채널이 여러 번 나오면 최저가만
            channel = row["channel"]
            if channel not in offers or row["price"] < offers[channel]:
                offers[channel] = row["price"]
        ratings = [r["rating"] for r in rows_for_key if r.get("rating")]
        reviews = [r["reviews"] for r in rows_for_key if r.get("reviews")]
        products.append({
            "brand": best["brand"], "name": best["name"], "spec": best["spec"],
            "source_name": best["source_name"], "category_hint": best["category_hint"],
            "url": next((r["url"] for r in rows_for_key if r.get("url")), ""),
            "offers": sorted(offers.items(), key=lambda kv: kv[1]),
            "rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "reviews": max(reviews) if reviews else None,
        })
    return products


# ------------------------------------------------------------------ 태깅
def _hits(text: str, table: dict) -> list[str]:
    text = text.lower()
    return [code for code, words in table.items() if any(w.lower() in text for w in words)]


def use_of(product: dict) -> str:
    text = f"{product['source_name']} {product['category_hint']}"
    for code, words in USE_KEYWORDS.items():          # 좁은 카테고리부터 검사
        if any(w.lower() in text.lower() for w in words):
            return code
    return "skin"


def gender_of(text: str) -> str:
    for code, words in GENDER_KEYWORDS.items():
        if any(w.lower() in text.lower() for w in words):
            return code
    return "a"


def ages_of(text: str, use: str, price: int) -> list[int]:
    ages = {age for age, words in AGE_HINTS.items() if any(w in text for w in words)}
    if not ages:                                       # 힌트가 없으면 가격대·용도로 추정
        if use == "make":
            ages = {10, 20} if price < 15000 else {20, 30}
        elif price >= 80000:
            ages = {40, 50}
        elif price >= 40000:
            ages = {30, 40}
        else:
            ages = {20, 30}
    return sorted(ages)


def vibe_of(text: str, price: int) -> str:
    found = _hits(text, VIBE_KEYWORDS)
    if found:
        return found[0]
    if price >= 90000:
        return "lux"
    return "value" if price <= 20000 else "trend"


# 용기 형태 추론 — 페이지가 이 값으로 제품 이미지를 그립니다
FORM_RULES = [
    ("sach", ["마스크", "시트"]), ("pad", ["패드"]), ("cush", ["쿠션", "팩트"]),
    ("tint", ["틴트", "립스틱", "립밤"]), ("pal", ["팔레트", "섀도", "파우더", "쉐딩"]),
    ("perf", ["향수", "퍼퓸", "오 드"]), ("stick", ["스틱", "펜슬", "아이브라우"]),
    ("tube", ["선크림", "클렌징폼", "폼 클렌저", "핸드크림", "cc"]),
    ("jar", ["크림", "밤"]), ("drop", ["앰플", "세럼"]),
    ("pump", ["에센스", "오일", "로션"]), ("ton", ["토너", "스킨"]),
    ("bot", ["샴푸", "바디워시", "워터", "트리트먼트"]),
]


def infer_form(text: str, use: str) -> str:
    for form, words in FORM_RULES:
        if any(w in text for w in words):
            return form
    return {"make": "cush", "hair": "bot", "scent": "perf", "sun": "tube"}.get(use, "ton")


# 색상(hue) 추론 — 제품 계열마다 다른 색을 주어 카드가 구분되게 합니다
HUE_RULES = [
    (145, ["센텔라", "시카", "티트리", "녹차", "어성초", "녹두"]),
    (200, ["수분", "히알루론", "아쿠아", "워터", "자작"]),
    (40, ["비타민", "비타c", "청귤", "라이스", "쌀"]),
    (350, ["로즈", "립", "틴트", "레드", "베리"]),
    (25, ["레티놀", "한방", "진액", "골드", "탄력"]),
    (265, ["퍼퓸", "향수", "나이트"]),
]


def infer_hue(text: str, use: str) -> int:
    for hue, words in HUE_RULES:
        if any(w in text.lower() for w in words):
            return hue
    return {"skin": 195, "sun": 45, "make": 340, "clean": 90, "hair": 25, "scent": 265}[use]


def tag(product: dict) -> dict:
    text = f"{product['brand']} {product['source_name']}"
    price = product["offers"][0][1] if product["offers"] else 0
    use = use_of(product)
    concerns = _hits(text, CONCERN_KEYWORDS) or ["hyd"]
    return {
        "c": use,
        "g": gender_of(text),
        "a": ages_of(text, use, price),
        "v": vibe_of(text, price),
        "cn": concerns[:3],
        "f": infer_form(text, use),
        "h": infer_hue(text, use),
    }


# ------------------------------------------------------------------ 총평 붙이기
def attach_verdict(products, raw_reviews):
    """수집한 리뷰를 상품별 총평으로 압축합니다.

    내보내는 것은 주제별 언급 비율과 긍정 비중뿐입니다. 리뷰 본문은
    저장도 게시도 하지 않습니다 — 사실 통계는 인용이 아닙니다.
    """
    import reviews as R
    from collections import defaultdict

    by_key = defaultdict(list)
    for r in raw_reviews:
        by_key[r.product_key].append(r)

    for product in products:
        k = normalize.key(product["brand"], product["name"], product["spec"])
        summary = R.summarise(by_key.get(k, []))
        if summary:
            product["verdict"] = summary
    return products


# ------------------------------------------------------------------ 내보내기
def export(products: list[dict], out_path: str | Path, source: dict | None = None) -> Path:
    """페이지가 읽는 형태로 내보냅니다.

    source 를 함께 실어야 페이지의 데이터 배지가 SAMPLE 에서 LIVE 로 바뀝니다.
    index.html 의 인라인 블록은 이 파일의 products 배열에 대응합니다.
    """
    out = []
    for index, product in enumerate(sorted(products, key=lambda p: p["brand"]), start=1):
        if not product["offers"]:
            continue
        tags = tag(product)
        out.append({
            "i": index,
            "b": product["brand"],
            "n": product["name"],
            "sp": product["spec"],
            "r": product["rating"] or 4.5,
            "rv": product["reviews"] or 0,
            "o": [[channel, price] for channel, price in product["offers"]],
            **tags,
        })
        if product.get("verdict"):             # rv 는 리뷰 "개수", rvi 는 주제별 총평
            out[-1]["rvi"] = product["verdict"]
    from datetime import datetime, timezone, timedelta
    kst = datetime.now(timezone(timedelta(hours=9)))
    payload = {
        "source": source or {
            "mode": "live",
            "label": "Naver Shopping API",
            "when": kst.strftime("%Y-%m-%d %H:%M KST"),
        },
        "products": out,
    }
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def run(raw_items, out_path: str | Path) -> tuple[int, Path]:
    rows = [normalize.item(raw) for raw in raw_items]
    rows = [r for r in rows if r["brand"] and r["name"] and r["price"] > 0]
    products = group(rows)
    return len(products), export(products, out_path)
