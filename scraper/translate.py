"""한국어 리뷰 → 영어 번역 파이프라인.

기계번역은 화장품 용어에서 특히 잘 틀립니다. "속당김"을 inner pull,
"백탁"을 white turbidity 로 옮기는 식입니다. 그래서 순서를 이렇게 둡니다.

    용어 보호 → 엔진 번역 → 용어 복원 → 사후 교정 → 캐시 저장

캐시가 핵심입니다. 같은 문장을 두 번 번역하면 요금이 두 번 나갑니다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).parent / ".cache" / "translations.json"
BATCH = 40                      # 엔진 한 번에 보낼 문장 수

# ------------------------------------------------------------------ 용어집
# 번역 엔진이 손대지 못하게 잠갔다가, 승인된 영어로 되돌립니다.
GLOSSARY = {
    "속당김": "tightness",
    "백탁": "white cast",
    "겉돌": "pilling",
    "밀림": "pilling",
    "속건조": "dehydration under the surface",
    "각질": "flaking",
    "피지": "sebum",
    "모공": "pores",
    "트러블": "breakouts",
    "홍조": "flushing",
    "붉은기": "redness",
    "진정": "soothing",
    "보습": "moisture",
    "발색": "colour payoff",
    "지속력": "wear time",
    "묻어남": "transfer",
    "잔향": "dry-down",
    "시술": "in-clinic treatment",
    "무기자차": "mineral sunscreen",
    "유기자차": "chemical sunscreen",
    "닦토": "swipe toning",
    "이중세안": "double cleansing",
    "쿠션": "cushion compact",
    "톤업": "tone-up",
    "재구매": "repurchase",
    "가성비": "value for money",
}

# 엔진이 자주 내놓는 어색한 결과를 손봅니다.
POST_EDIT = [
    (re.compile(r"\bskin trouble\b", re.I), "breakouts"),
    (re.compile(r"\bwhite turbidity\b", re.I), "white cast"),
    (re.compile(r"\bmoisturizing power\b", re.I), "moisture"),
    (re.compile(r"\bsticky feeling\b", re.I), "tackiness"),
    (re.compile(r"\bit is good\b", re.I), "it works well"),
    (re.compile(r"\s+([.,!?])"), r"\1"),
]


class Glossary:
    """번역 전후로 용어를 잠그고 푸는 래퍼."""

    TOKEN = "⸤{}⸥"       # 엔진이 건드리지 않을 만한 기호

    def protect(self, text: str) -> tuple[str, dict]:
        found = {}
        for i, (ko, en) in enumerate(GLOSSARY.items()):
            if ko in text:
                tok = self.TOKEN.format(i)
                text = text.replace(ko, tok)
                found[tok] = en
        return text, found

    def restore(self, text: str, found: dict) -> str:
        for tok, en in found.items():
            text = text.replace(tok, en)
        return text


def post_edit(text: str) -> str:
    for pat, rep in POST_EDIT:
        text = pat.sub(rep, text)
    return text[:1].upper() + text[1:] if text else text


# ------------------------------------------------------------------ 캐시
class Cache:
    def __init__(self, engine: str):
        self.engine = engine
        CACHE_PATH.parent.mkdir(exist_ok=True)
        try:
            self.data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            self.data = {}

    def key(self, text: str) -> str:
        return hashlib.sha1(f"{self.engine}|{text}".encode()).hexdigest()

    def get(self, text: str):
        return self.data.get(self.key(text))

    def put(self, text: str, out: str) -> None:
        self.data[self.key(text)] = out

    def flush(self) -> None:
        CACHE_PATH.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ 엔진
class Engine:
    name = "null"

    def ready(self) -> bool:
        return True

    def run(self, texts: list[str]) -> list[str]:
        raise NotImplementedError


class NullEngine(Engine):
    """자격증명 없이 파이프라인을 돌려볼 때 쓰는 통과 엔진."""

    def run(self, texts):
        return list(texts)


class DeepL(Engine):
    name = "deepl"
    URL = "https://api-free.deepl.com/v2/translate"

    def __init__(self):
        self.key = os.getenv("DEEPL_API_KEY")

    def ready(self):
        return bool(self.key)

    def run(self, texts):
        res = requests.post(self.URL, timeout=25, data=[
            ("auth_key", self.key), ("source_lang", "KO"), ("target_lang", "EN-GB"),
            *[("text", t) for t in texts],
        ])
        res.raise_for_status()
        return [t["text"] for t in res.json()["translations"]]


class Papago(Engine):
    name = "papago"
    URL = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"

    def __init__(self):
        self.cid = os.getenv("NAVER_CLOUD_ID")
        self.secret = os.getenv("NAVER_CLOUD_SECRET")

    def ready(self):
        return bool(self.cid and self.secret)

    def run(self, texts):
        head = {"X-NCP-APIGW-API-KEY-ID": self.cid, "X-NCP-APIGW-API-KEY": self.secret}
        out = []
        for t in texts:                      # 파파고는 문장 단위 호출입니다
            res = requests.post(self.URL, headers=head, timeout=20,
                                data={"source": "ko", "target": "en", "text": t})
            res.raise_for_status()
            out.append(res.json()["message"]["result"]["translatedText"])
            time.sleep(0.1)
        return out


ENGINES = {"deepl": DeepL, "papago": Papago, "null": NullEngine}


def build(name: str = "deepl") -> Engine:
    engine = ENGINES.get(name, NullEngine)()
    if not engine.ready():
        log.warning("%s: credentials missing — falling back to passthrough", name)
        return NullEngine()
    return engine


# ------------------------------------------------------------------ 진입점
def translate_all(texts: list[str], engine_name: str = "deepl") -> dict[str, str]:
    """한국어 문장 목록 → {원문: 번역} 사전. 중복과 캐시를 먼저 걷어냅니다."""
    engine, gloss = build(engine_name), Glossary()
    cache = Cache(engine.name)
    unique = list(dict.fromkeys(t.strip() for t in texts if t and t.strip()))

    out, todo = {}, []
    for t in unique:
        hit = cache.get(t)
        if hit is not None:
            out[t] = hit
        else:
            todo.append(t)
    log.info("translate: %d unique, %d cached, %d to send", len(unique), len(out), len(todo))

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        locked, tokens = zip(*(gloss.protect(t) for t in chunk))
        try:
            raw = engine.run(list(locked))
        except Exception as exc:
            log.error("translate batch failed (%s) — keeping source text", exc)
            raw = list(chunk)
        for src, got, found in zip(chunk, raw, tokens):
            done = post_edit(gloss.restore(got, found))
            out[src] = done
            cache.put(src, done)

    cache.flush()
    return out
