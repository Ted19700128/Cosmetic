"""리뷰 수집 어댑터.

가격 수집과 같은 규칙을 따릅니다. robots.txt가 막으면 수집하지 않고,
채널별 레이트리밋을 지키며, 공개된 목록만 읽습니다.

리뷰 본문은 저장하지도, 내보내지도 않습니다. 여기서 나가는 것은
주제별 언급 비율과 긍정 비중뿐입니다 — 사실 통계는 인용이 아닙니다.
실제 글을 읽고 싶은 사람은 페이지의 채널 링크로 원 사이트에 갑니다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date

from bs4 import BeautifulSoup

from base import Channel

log = logging.getLogger(__name__)

MIN_CHARS = 12               # 이보다 짧으면 정보가 없다고 봅니다
POSITIVE_AT = 4              # 이 별점 이상이면 긍정으로 분류

# 대가성 후기 표지. 광고 표시 의무가 있는 글은 일반 후기와 섞지 않습니다.
SPONSORED = re.compile(
    r"체험단|서포터즈|무상\s*제공|협찬|제품을?\s*제공받아|리뷰어\s*선정|"
    r"이벤트\s*당첨|원고료|유료\s*광고", re.I)

# 아이디에 붙는 개인정보 흔적
EMAILISH = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONEISH = re.compile(r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}")


@dataclass
class RawReview:
    channel: str
    product_key: str          # normalize.key() 로 만든 상품 키
    review_id: str            # 채널 내 고유 id (증분 수집·중복 제거용)
    rating: float
    body_ko: str
    author: str = ""
    written: str = ""         # ISO date
    url: str = ""             # 원문으로 돌아가는 링크 (출처 표기에 필요)
    helpful: int = 0
    extra: dict = field(default_factory=dict)


# ------------------------------------------------------------------ 정제
def mask_author(raw: str) -> str:
    """국내 쇼핑몰 표기 방식대로 가운데를 가립니다. j***n"""
    name = EMAILISH.sub("", raw or "").strip()
    name = PHONEISH.sub("", name).strip()
    if len(name) <= 2:
        return (name or "anon") + "***"
    return f"{name[0]}{'*' * max(3, len(name) - 2)}{name[-1]}"


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind("."), cut.rfind("요"), cut.rfind("다"))
    return (cut[:stop + 1] if stop > limit * 0.5 else cut).rstrip() + "…"


def usable(r: RawReview) -> bool:
    if len(re.sub(r"\s", "", r.body_ko or "")) < MIN_CHARS:
        return False
    if SPONSORED.search(r.body_ko):
        log.debug("sponsored review dropped: %s", r.review_id)
        return False
    return True


def dedupe(items: list[RawReview]) -> list[RawReview]:
    """같은 본문이 채널을 넘나들며 복사되는 경우를 걷어냅니다."""
    seen, out = set(), []
    for r in items:
        key = hashlib.sha1(re.sub(r"\s", "", r.body_ko).encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


# ------------------------------------------------------------------ 주제 집계
# 리뷰 본문은 싣지 않습니다. 어떤 이야기가 몇 %에서 나오는지만 셉니다.
# 왼쪽이 한국어 표기, 오른쪽이 페이지에 나갈 영어 라벨입니다.
# 라벨이 고정 사전이라 게시물에는 기계번역이 한 글자도 들어가지 않습니다.
THEMES = {
    "수분 지속":      (["수분", "보습", "촉촉", "속당김", "당기지"], "Hydration that lasts"),
    "붉은기 진정":    (["진정", "붉은기", "홍조", "가라앉", "시카"], "Calms redness"),
    "트러블 진정":    (["트러블", "여드름", "뾰루지", "자국"], "Spots settle sooner"),
    "유분 억제":      (["유분", "번들", "피지", "기름"], "Less shine"),
    "톤 개선":        (["톤", "화사", "밝아", "잡티", "미백"], "Brighter tone"),
    "탄력 개선":      (["탄력", "주름", "리프팅", "처짐"], "Firmer to the touch"),
    "백탁 없음":      (["백탁", "하얗게", "밀리지"], "No white cast"),
    "커버력":         (["커버", "잡티가 가려", "다크서클"], "Covers well"),
    "발색":           (["발색", "색감", "컬러"], "True payoff"),
    "지속력":         (["지속", "오래", "무너지", "금방 지워"], "Wear time"),
    "묻어남":         (["묻어", "이염", "마스크에"], "Transfer"),
    "세정력":         (["세정", "지워", "클렌징", "잔여감"], "Cleansing power"),
    "두피 개선":      (["두피", "가려움", "비듬", "탈모"], "Scalp comfort"),
    "향":             (["향이", "향은", "냄새", "잔향"], "Scent"),
    "발림성":         (["발림", "텍스처", "제형", "흡수"], "Texture"),
    "용기·펌프":      (["펌프", "용기", "뚜껑", "스포이드", "리필"], "Packaging"),
    "가격":           (["가격", "가성비", "비싸", "저렴", "세일"], "Price"),
    "자극":           (["자극", "따가", "트러블이 나", "민감"], "Irritation"),
    "배송":           (["배송", "파손", "새어", "누락"], "Delivery"),
}


def summarise(items: list[RawReview], n_pos: int = 4, n_neg: int = 3) -> dict:
    """리뷰 묶음 → 주제별 언급 비율. 본문은 한 글자도 나가지 않습니다."""
    ok = dedupe([r for r in items if usable(r)])
    if not ok:
        return {}
    pos = [r for r in ok if r.rating >= POSITIVE_AT]
    neg = [r for r in ok if r.rating < POSITIVE_AT]

    def count(bucket):
        total = len(bucket)
        if not total:
            return []
        rows = []
        for ko, (words, en) in THEMES.items():
            hits = sum(1 for r in bucket if any(w in r.body_ko for w in words))
            if hits:
                rows.append({"ko": ko, "en": en, "pct": round(hits / total * 100)})
        return sorted(rows, key=lambda x: -x["pct"])

    return {
        "n": len(ok),
        "share": round(len(pos) / len(ok) * 100),
        "pos": count(pos)[:n_pos],
        "neg": count(neg)[:n_neg],
    }


def untagged(items: list[RawReview], limit: int = 40) -> list[str]:
    """어떤 주제에도 안 걸린 리뷰. THEMES 사전을 키울 때 이걸 보고 늘립니다."""
    out = []
    for r in items:
        if not any(any(w in r.body_ko for w in words) for words, _ in THEMES.values()):
            out.append(r.body_ko)
        if len(out) >= limit:
            break
    return out


# ------------------------------------------------------------------ 어댑터
class ReviewSource(Channel):
    """상품 하나에 대한 리뷰를 가져옵니다. 하위 클래스가 fetch()를 구현합니다."""

    def fetch(self, product_key: str, product_url: str) -> list[RawReview]:
        raise NotImplementedError

    def fetch_category(self, key, path):        # 가격 수집 경로는 쓰지 않습니다
        return []


class LdReviewSource(ReviewSource):
    """상품 페이지의 schema.org Review 블록을 읽습니다.

    검색 노출을 위해 상품 페이지에 직접 심어두는 쇼핑몰이 있습니다.
    별도 엔드포인트가 아니라 공개 페이지의 구조화 데이터라 가장 다루기 쉽습니다.
    """

    def fetch(self, product_key: str, product_url: str) -> list[RawReview]:
        res = self.get(product_url)
        if res is None:
            return []
        soup = BeautifulSoup(res.text, "html.parser")
        out: list[RawReview] = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "{}")
            except json.JSONDecodeError:
                continue
            for node in self._reviews(data):
                r = self._to_review(node, product_key, product_url)
                if r:
                    out.append(r)
        return out

    def _reviews(self, node):
        if isinstance(node, list):
            for c in node:
                yield from self._reviews(c)
        elif isinstance(node, dict):
            types = node.get("@type", "")
            types = types if isinstance(types, list) else [types]
            if "Review" in types:
                yield node
            for v in node.values():
                if isinstance(v, (list, dict)):
                    yield from self._reviews(v)

    def _to_review(self, node: dict, key: str, url: str) -> RawReview | None:
        body = (node.get("reviewBody") or "").strip()
        if not body:
            return None
        rating = (node.get("reviewRating") or {}).get("ratingValue")
        author = node.get("author")
        if isinstance(author, dict):
            author = author.get("name", "")
        rid = node.get("@id") or hashlib.sha1(body.encode()).hexdigest()[:16]
        return RawReview(
            channel=self.spec.name, product_key=key, review_id=str(rid),
            rating=float(rating) if rating else 5.0,
            body_ko=body, author=mask_author(str(author or "")),
            written=str(node.get("datePublished") or date.today()), url=url,
        )


class JsonReviewSource(ReviewSource):
    """리뷰 목록을 JSON으로 내려주는 엔드포인트를 읽습니다.

    spec.paths['reviews'] 에 {goods}/{page} 자리표시자가 있는 경로를 넣고,
    FIELD_MAP 으로 응답 구조를 맞춥니다. 사이트 개편 때마다 확인이 필요합니다.
    """

    max_pages = 3
    LIST_AT = ("data", "list")          # 응답에서 배열이 있는 위치
    FIELD_MAP = {
        "id": "reviewNo", "rating": "score", "body": "content",
        "author": "memberId", "date": "regDate", "helpful": "likeCount",
    }

    def fetch(self, product_key: str, product_url: str) -> list[RawReview]:
        tmpl = self.spec.paths.get("reviews")
        goods = self._goods_id(product_url)
        if not tmpl or not goods:
            return []
        out: list[RawReview] = []
        for page in range(1, self.max_pages + 1):
            res = self.get(tmpl.format(goods=goods, page=page))
            if res is None:
                break
            try:
                payload = res.json()
            except ValueError:
                log.warning("%s: review endpoint did not return JSON", self.spec.key)
                break
            rows = payload
            for step in self.LIST_AT:
                rows = (rows or {}).get(step, []) if isinstance(rows, dict) else []
            if not rows:
                break
            m = self.FIELD_MAP
            for row in rows:
                body = (row.get(m["body"]) or "").strip()
                if not body:
                    continue
                out.append(RawReview(
                    channel=self.spec.name, product_key=product_key,
                    review_id=str(row.get(m["id"], "")),
                    rating=float(row.get(m["rating"], 5) or 5),
                    body_ko=body,
                    author=mask_author(str(row.get(m["author"], ""))),
                    written=str(row.get(m["date"], "")),
                    url=product_url,
                    helpful=int(row.get(m["helpful"], 0) or 0),
                ))
        return out


REVIEW_REGISTRY = {"LdReviewSource": LdReviewSource, "JsonReviewSource": JsonReviewSource}
