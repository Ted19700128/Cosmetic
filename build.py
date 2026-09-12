#!/usr/bin/env python3
"""index.html(조각) → dist/index.html(독립 실행 문서).

루트의 index.html 은 아티팩트 호스트가 감싸주는 걸 전제로 한 조각이라
doctype·charset·viewport 가 없습니다. 그대로 올리면 한글이 깨지고
모바일 레이아웃이 무너집니다. 이 스크립트가 문서로 만들어 줍니다.

    python build.py                                # og:image/og:url 에 DEFAULT_URL 사용
    python build.py --url https://yourname.dev     # 커스텀 도메인으로 덮어쓰기
"""
from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "index.html"
OUT = ROOT / "dist" / "index.html"

DEFAULT_URL = "https://yun-concierge.vercel.app"

DESC = ("Answer four cards and one Korean beauty product is left standing — with the price band "
        "across eleven online stores and where it ranks cheapest.")

FAVICON = ("data:image/svg+xml,"
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Ccircle cx='32' cy='32' r='30' fill='%230A0A0C'/%3E"
           "%3Ccircle cx='32' cy='32' r='27' fill='none' stroke='%23C9A45C' stroke-width='2'/%3E"
           "%3Ctext x='32' y='44' text-anchor='middle' font-family='Georgia,serif'"
           " font-size='34' fill='%23E8C87E'%3EY%3C/text%3E%3C/svg%3E")


def build(base_url: str) -> Path:
    src = io.open(SRC, encoding="utf-8").read()

    title = re.search(r"<title>(.*?)</title>\s*", src, re.S)
    if not title:
        raise SystemExit("index.html 에 <title> 이 없습니다")
    body = src.replace(title.group(0), "", 1)

    # 폰트 링크는 head 로 올립니다
    links = re.findall(r'<link rel="(?:preconnect|stylesheet)"[^>]*>\s*', body)
    for link in links:
        body = body.replace(link, "", 1)

    name = title.group(1)
    og_img = f"{base_url}/og.png"
    head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<meta name="description" content="{DESC}">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#0A0A0C">
<link rel="icon" href="{FAVICON}">

<meta property="og:type" content="website">
<meta property="og:title" content="{name}">
<meta property="og:description" content="{DESC}">
<meta property="og:image" content="{og_img}">
<meta property="og:url" content="{base_url}/">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{name}">
<meta name="twitter:description" content="{DESC}">
<meta name="twitter:image" content="{og_img}">

{''.join(links).strip()}
</head>
<body>
"""
    OUT.parent.mkdir(exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(head + body.lstrip() + "\n</body>\n</html>\n")
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL,
                    help=f"배포될 주소. 링크 미리보기(og:image, og:url)에 쓰입니다 (기본: {DEFAULT_URL})")
    args = ap.parse_args()
    out = build(args.url.rstrip("/"))
    size = out.stat().st_size
    print(f"built {out} ({size / 1024:.0f}KB)")
    if "example.com" in args.url:
        print("warning: og:image still points at example.com - pass --url")
