#!/usr/bin/env python3
"""결 컨시어지 수집기 CLI.

    python run.py --channels oliveyoung,musinsa --out ../data/catalog.json
    python run.py --list-channels
    python run.py --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

import adapters
import normalize
import pipeline
from config import CHANNELS, CHANNELS_BY_KEY


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="국내 온라인 뷰티 채널 상품·가격 수집기")
    ap.add_argument("--channels", default="", help="쉼표로 구분한 채널 키 (비우면 전체)")
    ap.add_argument("--out", default="../data/catalog.json", help="내보낼 JSON 경로")
    ap.add_argument("--no-cache", action="store_true", help="응답 캐시를 쓰지 않습니다")
    ap.add_argument("--reviews", action="store_true", help="리뷰까지 수집해 번역합니다")
    ap.add_argument("--engine", default="null", choices=["deepl", "papago", "null"],
                    help="번역 엔진. 게시물에는 쓰이지 않고, 주제 사전을 늘릴 때만 씁니다")
    ap.add_argument("--dry-run", action="store_true", help="요청 없이 수집 계획만 출력")
    ap.add_argument("--list-channels", action="store_true", help="등록된 채널 목록")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    if args.list_channels:
        for spec in CHANNELS:
            print(f"{spec.key:12s} {spec.name:12s} {spec.adapter:16s} "
                  f"delay={spec.delay}s paths={len(spec.paths)}")
        return 0

    keys = [k.strip() for k in args.channels.split(",") if k.strip()] or list(CHANNELS_BY_KEY)
    unknown = [k for k in keys if k not in CHANNELS_BY_KEY]
    if unknown:
        print(f"모르는 채널입니다: {', '.join(unknown)}", file=sys.stderr)
        return 2
    specs = [CHANNELS_BY_KEY[k] for k in keys]

    if args.dry_run:
        for spec in specs:
            paths = ", ".join(spec.paths) or "(경로 미설정)"
            print(f"{spec.name}: {spec.adapter} · {spec.concurrency}동시 · {spec.delay}초 간격 · {paths}")
        return 0

    channels = [adapters.build(spec, use_cache=not args.no_cache) for spec in specs]
    raw = []
    with ThreadPoolExecutor(max_workers=min(4, len(channels))) as pool:
        for items in pool.map(lambda c: c.collect(), channels):
            raw.extend(items)

    if not raw:
        logging.error("수집된 항목이 없습니다. robots.txt 차단이나 선택자 변경을 확인하세요.")
        return 1

    rows = [normalize.item(r) for r in raw]
    rows = [r for r in rows if r["brand"] and r["name"] and r["price"] > 0]
    products = pipeline.group(rows)

    if args.reviews:
        collected = collect_reviews(specs, products, use_cache=not args.no_cache)
        logging.info("리뷰 %d건 수집", len(collected))
        pipeline.attach_verdict(products, collected)

    path = pipeline.export(products, args.out)
    logging.info("원본 %d건 → 상품 %d개 → %s", len(raw), len(products), path)
    return 0


def collect_reviews(specs, products, use_cache=True):
    """리뷰 어댑터가 등록된 채널에서만 수집합니다."""
    import normalize
    import reviews as R

    out = []
    for spec in specs:
        if not spec.review_adapter:
            continue
        cls = R.REVIEW_REGISTRY.get(spec.review_adapter)
        if cls is None:
            logging.warning("%s: 모르는 리뷰 어댑터 %s", spec.key, spec.review_adapter)
            continue
        source = cls(spec, use_cache=use_cache)
        for product in products:
            url = product.get("url") or ""
            if not url:
                continue                      # 상품 URL이 없으면 리뷰 위치를 모릅니다
            key = normalize.key(product["brand"], product["name"], product["spec"])
            try:
                out.extend(source.fetch(key, url))
            except Exception as exc:
                logging.debug("%s 리뷰 수집 실패: %s", key, exc)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
