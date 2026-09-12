"""채널별 어댑터.

세 가지 형태로 나뉩니다.
  1. JsonLdChannel   — 상품 페이지에 schema.org Product JSON-LD를 넣어두는 쇼핑몰
  2. MusinsaChannel  — 목록을 JSON으로 내려주는 내부 엔드포인트
  3. NaverApiChannel — 공식 공개 API

선택자와 엔드포인트는 사이트 개편 때마다 바뀝니다. 새 채널을 붙일 때는
`python run.py --probe <channel>`로 응답 구조를 먼저 확인하세요.
"""
from __future__ import annotations

import json
import logging
import os
import re

from bs4 import BeautifulSoup

from base import Channel, RawItem

log = logging.getLogger(__name__)


def _price(value) -> int | None:
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


class JsonLdChannel(Channel):
    """카테고리 페이지를 순회하며 JSON-LD의 Product/ItemList를 읽습니다."""

    max_pages = 5

    def fetch_category(self, key: str, path: str) -> list[RawItem]:
        items: list[RawItem] = []
        for page in range(1, self.max_pages + 1):
            url = path.format(page=page) if "{page}" in path else path
            res = self.get(url, params=None if "{page}" in path else {"page": page})
            if res is None:
                break
            found = self._parse(res.text, key)
            if not found:
                break
            items.extend(found)
        return items

    def _parse(self, html: str, key: str) -> list[RawItem]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[RawItem] = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "{}")
            except json.JSONDecodeError:
                continue
            for node in self._products(data):
                item = self._to_item(node, key)
                if item:
                    out.append(item)
        return out

    def _products(self, node):
        """중첩된 JSON-LD에서 Product 노드만 끌어냅니다."""
        if isinstance(node, list):
            for child in node:
                yield from self._products(child)
        elif isinstance(node, dict):
            types = node.get("@type", "")
            types = types if isinstance(types, list) else [types]
            if "Product" in types:
                yield node
            for value in node.values():
                if isinstance(value, (list, dict)):
                    yield from self._products(value)

    def _to_item(self, node: dict, key: str) -> RawItem | None:
        offers = node.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = _price(offers.get("price") or offers.get("lowPrice"))
        name = (node.get("name") or "").strip()
        if not price or not name:
            return None
        brand = node.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name", "")
        rating = (node.get("aggregateRating") or {}).get("ratingValue")
        reviews = (node.get("aggregateRating") or {}).get("reviewCount")
        return RawItem(
            channel=self.spec.name, brand=(brand or "").strip(), name=name, price=price,
            url=node.get("url", ""),
            rating=float(rating) if rating else None,
            reviews=int(_price(reviews) or 0) or None,
            category_hint=key,
        )


class MusinsaChannel(Channel):
    """목록 JSON을 그대로 읽는 형태."""

    max_pages = 6

    def fetch_category(self, key: str, path: str) -> list[RawItem]:
        items: list[RawItem] = []
        for page in range(1, self.max_pages + 1):
            res = self.get(path.format(page=page))
            if res is None:
                break
            try:
                payload = res.json()
            except ValueError:
                log.warning("%s: JSON이 아닌 응답", self.spec.key)
                break
            goods = payload.get("data", {}).get("list", [])
            if not goods:
                break
            for g in goods:
                price = _price(g.get("price") or g.get("normalPrice"))
                if not price:
                    continue
                items.append(RawItem(
                    channel=self.spec.name,
                    brand=(g.get("brandName") or g.get("brand") or "").strip(),
                    name=(g.get("goodsName") or "").strip(),
                    price=price,
                    url=g.get("linkUrl", ""),
                    rating=g.get("reviewScore"),
                    reviews=g.get("reviewCount"),
                    category_hint=key,
                ))
        return items


class NaverApiChannel(Channel):
    """네이버 검색 API(shop). HTML을 긁지 않고 공식 API를 씁니다."""

    QUERIES = ["토너", "세럼", "앰플", "수분크림", "선크림", "쿠션", "립틴트",
               "클렌징오일", "샴푸", "바디로션", "핸드크림", "향수"]

    def __init__(self, spec, use_cache: bool = True):
        super().__init__(spec, use_cache)
        cid, secret = os.getenv("NAVER_CLIENT_ID"), os.getenv("NAVER_CLIENT_SECRET")
        self.enabled = bool(cid and secret)
        if self.enabled:
            self.session.headers.update({"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret})
        else:
            log.warning("naver: NAVER_CLIENT_ID/SECRET이 없어 이 채널을 건너뜁니다")

    def allowed(self, url: str) -> bool:      # 공개 API는 robots 대상이 아닙니다
        return True

    def fetch_category(self, key: str, path: str) -> list[RawItem]:
        if not self.enabled:
            return []
        items: list[RawItem] = []
        for query in self.QUERIES:
            res = self.get(path, params={"query": query, "display": 100, "sort": "sim"})
            if res is None:
                continue
            for row in res.json().get("items", []):
                lo = _price(row.get("lprice"))
                if not lo:
                    continue
                hi = _price(row.get("hprice")) or lo
                # mallName 이 있으면 실제 판매처, 없으면 가격비교 묶음입니다
                seller = (row.get("mallName") or "").strip() or self.spec.name
                items.append(RawItem(
                    channel=seller,
                    brand=(row.get("brand") or row.get("maker") or "").strip(),
                    name=re.sub(r"<[^>]+>", "", row.get("title", "")).strip(),
                    price=lo,
                    url=row.get("link", ""),
                    category_hint=query,
                    extra={"hprice": hi, "productId": row.get("productId", "")},
                ))
        return items


REGISTRY = {
    "JsonLdChannel": JsonLdChannel,
    "MusinsaChannel": MusinsaChannel,
    "NaverApiChannel": NaverApiChannel,
}


def build(spec, **kwargs) -> Channel:
    return REGISTRY[spec.adapter](spec, **kwargs)
