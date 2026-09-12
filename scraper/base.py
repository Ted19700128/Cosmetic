"""채널 공통 동작: robots.txt 확인, 레이트리밋, 재시도, 응답 캐시."""
from __future__ import annotations

import hashlib
import json
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

log = logging.getLogger(__name__)

UA = "GyeolConciergeBot/0.3 (+portfolio project; contact: eth015b@gmail.com)"
CACHE_DIR = Path(__file__).parent / ".cache"


@dataclass
class RawItem:
    """어댑터가 내놓는 최소 단위. 정규화 전 상태."""
    channel: str          # 매장 이름 (예: 올리브영)
    brand: str
    name: str
    price: int
    url: str = ""
    rating: float | None = None
    reviews: int | None = None
    category_hint: str = ""
    extra: dict = field(default_factory=dict)


class RateLimiter:
    """채널당 최소 간격을 지키는 토큰 없는 단순 리미터."""

    def __init__(self, delay: float):
        self.delay = delay
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            gap = time.monotonic() - self._last
            if gap < self.delay:
                time.sleep(self.delay - gap + random.uniform(0, 0.15))
            self._last = time.monotonic()


class Channel:
    """모든 채널 어댑터의 부모.

    하위 클래스는 `fetch_category(key, path)`를 구현해 RawItem을 내놓습니다.
    """

    def __init__(self, spec, use_cache: bool = True):
        self.spec = spec
        self.limiter = RateLimiter(spec.delay)
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
        self._robots: RobotFileParser | None = None
        CACHE_DIR.mkdir(exist_ok=True)

    # -------------------------------------------------- robots
    def robots(self) -> RobotFileParser:
        if self._robots is None:
            rp = RobotFileParser()
            rp.set_url(urljoin(self.spec.base, "/robots.txt"))
            try:
                rp.read()
            except Exception as exc:                      # robots를 못 읽으면 보수적으로 차단
                log.warning("%s: robots.txt를 읽지 못했습니다 (%s)", self.spec.key, exc)
                rp.disallow_all = True
            self._robots = rp
        return self._robots

    def allowed(self, url: str) -> bool:
        try:
            return self.robots().can_fetch(UA, url)
        except Exception:
            return False

    # -------------------------------------------------- fetch
    def get(self, url: str, *, params: dict | None = None, tries: int = 3) -> requests.Response | None:
        if not url.startswith("http"):
            url = urljoin(self.spec.base, url)
        if not self.allowed(url):
            log.info("%s: robots.txt가 막은 경로 — 건너뜁니다: %s", self.spec.key, urlparse(url).path)
            return None

        cached = self._cache_read(url, params)
        if cached is not None:
            return cached

        for attempt in range(tries):
            self.limiter.wait()
            try:
                res = self.session.get(url, params=params, timeout=15)
            except requests.RequestException as exc:
                log.warning("%s: 요청 실패 (%s) — %s", self.spec.key, exc, url)
                time.sleep(2 ** attempt)
                continue

            if res.status_code in (429, 503):
                back = (2 ** attempt) * 3
                log.info("%s: %s 응답 — %.0f초 후 재시도", self.spec.key, res.status_code, back)
                time.sleep(back)
                continue
            if res.status_code >= 400:
                log.warning("%s: %s %s", self.spec.key, res.status_code, url)
                return None

            self._cache_write(url, params, res)
            return res
        return None

    # -------------------------------------------------- cache
    def _cache_path(self, url: str, params: dict | None) -> Path:
        key = hashlib.sha1(f"{url}{json.dumps(params, sort_keys=True)}".encode()).hexdigest()[:20]
        return CACHE_DIR / f"{self.spec.key}-{key}.txt"

    def _cache_read(self, url: str, params: dict | None):
        if not self.use_cache:
            return None
        path = self._cache_path(url, params)
        if not path.exists() or time.time() - path.stat().st_mtime > 60 * 60 * 12:
            return None
        res = requests.Response()
        res.status_code = 200
        res._content = path.read_bytes()
        res.encoding = "utf-8"
        return res

    def _cache_write(self, url: str, params: dict | None, res: requests.Response) -> None:
        if self.use_cache:
            self._cache_path(url, params).write_bytes(res.content)

    # -------------------------------------------------- 하위 클래스 구현부
    def fetch_category(self, key: str, path: str) -> list[RawItem]:
        raise NotImplementedError

    def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        for key, path in self.spec.paths.items():
            try:
                found = self.fetch_category(key, path)
            except Exception as exc:
                log.exception("%s/%s 수집 중 오류: %s", self.spec.key, key, exc)
                continue
            log.info("%s/%s: %d건", self.spec.key, key, len(found))
            items.extend(found)
        return items
