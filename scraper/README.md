# Yun Concierge — 수집기 (scraper)

국내 온라인 뷰티 채널에서 상품·가격을 모아 웹페이지(`index.html`)가 쓰는 JSON으로 내보내는 파이프라인입니다.

> **지금 페이지는 가격 데이터 없이 나갑니다.** 화면의 숫자는 레이아웃용 표본이고, 헤더 배지가
> `SAMPLE DATA`로 이를 계속 알립니다. 실제 가격을 넣는 방법은 [LIVE_PRICES.md](LIVE_PRICES.md) —
> 네이버 쇼핑 공식 API로 20분이면 됩니다.

```
채널 어댑터 → 정규화 → 동일 상품 매칭 → 속성 태깅 → catalog.json
```

## 실행

```bash
pip install -r requirements.txt
export NAVER_CLIENT_ID=...        # 네이버 검색 API (선택)
export NAVER_CLIENT_SECRET=...
python run.py --channels oliveyoung,musinsa,naver --out ../data/catalog.json
python run.py --reviews           # 리뷰를 수집해 주제별 총평으로 집계
python run.py --list-channels     # 등록된 채널 확인
python run.py --dry-run           # 요청 없이 계획만 출력
```

## 구조

| 파일 | 역할 |
|---|---|
| `config.py` | 채널 정의(베이스 URL, 카테고리 경로, 요청 간격), 태깅 사전 |
| `base.py` | `Channel` 추상 클래스. robots.txt 확인, 레이트리밋, 재시도, 캐시 |
| `adapters.py` | 채널별 구현 (JSON-LD 파싱형 / 내부 JSON API형 / 공개 API형) |
| `normalize.py` | 브랜드명 통일, 용량·SPF·수량 분리, 가격 정수화 |
| `pipeline.py` | 동일 상품 매칭(키 + 유사도), 속성 태깅, JSON 내보내기 |
| `reviews.py` | 리뷰 수집 어댑터, 대가성·중복 필터, 주제 19종 집계 (본문 미저장) |
| `translate.py` | 한→영 번역. 주제 사전을 키울 때 보조로만 사용 (게시물에는 미사용) |
| `run.py` | CLI 엔트리포인트 |

## 수집 원칙

- **robots.txt 우선.** 채널마다 `RobotFileParser`로 해당 경로가 허용되는지 먼저 확인하고, 막혀 있으면 그 채널을 건너뜁니다(`base.Channel.allowed`).
- **공개 API 우선.** 네이버처럼 공식 검색 API가 있으면 HTML을 긁지 않고 API를 씁니다.
- **낮은 요청률.** 채널당 동시 요청 2건, 요청 간 기본 1.2초(`config.CHANNELS[*].delay`). 429/503은 지수 백오프.
- **공개 정보만.** 로그인·개인화 페이지, 회원 전용가는 수집 대상이 아닙니다.
- **캐시.** 응답을 `.cache/`에 저장해 개발 중 같은 페이지를 반복 요청하지 않습니다.

리뷰는 가격과 성격이 다릅니다 — 본문에 저작권이 있습니다. 그래서 **본문을 저장하지도 게시하지도 않고**,
주제별 언급 비율만 내보냅니다. 실제 글은 페이지의 채널 링크로 원 사이트에서 읽습니다.
자세한 내용은 [REVIEWS.md](REVIEWS.md) 참고.

각 채널의 이용약관은 사이트마다 다릅니다. 실제 운영 전에 대상 채널의 약관과 API 정책을 확인하고, 상업적 재배포가 필요하면 제휴/오픈API 경로를 쓰세요. 이 코드는 포트폴리오 데모 목적으로 작성되었습니다.

## 출력 스키마

`index.html`의 `P` 배열과 동일한 형태입니다.

```json
{
  "i": 1,
  "b": "아누아",
  "n": "어성초 77 수분진정 토너",
  "sp": "250ml",
  "c": "skin",
  "f": "ton",
  "h": 148,
  "a": [20, 30],
  "g": "a",
  "v": "clean",
  "cn": ["cal", "hyd"],
  "r": 4.8,
  "rv": 42130,
  "o": [["올리브영", 19900], ["쿠팡", 17900]]
}
```

`h`(제품 색상 hue)와 `f`(용기 형태)는 카테고리·제품명 키워드에서 추론합니다(`pipeline.infer_form`, `pipeline.infer_hue`). 페이지는 이 두 값으로 제품 이미지를 SVG로 그립니다.
