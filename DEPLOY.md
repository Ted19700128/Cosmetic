# 배포

정적 파일 하나입니다. 서버도, 빌드도, 의존성도 없습니다.

```
dist/
  index.html    115KB — 이 파일 하나가 사이트 전부입니다
  og.png        링크 미리보기 이미지 (카카오톡·슬랙·링크드인)
```

`scraper/` 는 **배포 대상이 아닙니다.** 데이터를 만들 때 로컬에서 돌리는 도구입니다.
다만 포트폴리오라면 저장소에는 같이 올리세요 — 보는 사람에게는 그쪽이 더 중요합니다.

---

## 먼저 — 왜 `index.html` 을 그냥 올리면 안 되나

루트의 `index.html` 은 **문서 조각**입니다. `<!doctype>` · `<html>` · `<head>` 가 없습니다.
아티팩트 호스트가 감싸주는 걸 전제로 만들어졌기 때문입니다. 그대로 올리면:

| 빠진 것 | 증상 |
|---|---|
| `<meta charset="utf-8">` | 총평의 한국어 라벨(수분 지속·백탁 없음)이 깨집니다 |
| `<meta name="viewport">` | 모바일이 980px로 렌더돼 전부 축소됩니다 |
| `<!doctype html>` | 브라우저가 쿼크 모드로 떨어져 레이아웃이 틀어집니다 |

`dist/index.html` 이 이걸 모두 갖춘 배포본입니다. 앞으로 루트 파일을 고치면
`python build.py` 로 다시 만드세요.

---

## 방법 1. GitHub Pages — 포트폴리오라면 이걸 권합니다

수집기 소스가 같은 저장소에 공개된다는 게 장점입니다. 채용 담당자가 보는 건 결국 코드입니다.

```bash
cd /c/Cosmetic
git init
git add .
git commit -m "Yun Beauty Concierge"
git branch -M main
git remote add origin https://github.com/<사용자명>/yun-concierge.git
git push -u origin main
```

저장소 → **Settings → Pages** → Source를 `main` / `/dist` 로 지정하면 1~2분 뒤
`https://<사용자명>.github.io/yun-concierge/` 에 뜹니다.

`/dist` 를 못 고르면 `dist/` 내용을 저장소 루트에 두거나, `docs/` 로 이름을 바꾸세요.

## 방법 2. Cloudflare Pages / Netlify — 가장 빠릅니다

`dist` 폴더를 브라우저에 **끌어다 놓으면** 끝입니다. 30초, 계정만 있으면 됩니다.

- Cloudflare Pages → <https://pages.cloudflare.com> → Direct Upload
- Netlify → <https://app.netlify.com/drop>

둘 다 무료, HTTPS 자동, 커스텀 도메인 연결 가능. Git 연동도 지원해서
push할 때마다 자동 배포되게 할 수 있습니다.

## 방법 3. 도메인 연결

포트폴리오는 주소가 이력서에 들어갑니다. `yun-concierge.pages.dev` 보다
`yourname.dev` 가 낫습니다.

1. 도메인 구입 (가비아·Cloudflare Registrar, 연 1~2만원)
2. 호스팅 대시보드 → Custom domain → 도메인 입력
3. 안내대로 DNS 레코드 추가 (보통 CNAME 하나)

---

## 올리기 전에 고칠 것

### 링크 미리보기 URL (필수)

`dist/index.html` 의 `og:image` · `og:url` 이 `https://example.com` 으로 되어 있습니다.
실제 주소로 바꾸세요. 상대 경로는 카카오톡·슬랙에서 동작하지 않습니다.

```html
<meta property="og:image" content="https://yourname.dev/og.png">
<meta property="og:url" content="https://yourname.dev/">
```

### SAMPLE DATA 배지 (판단 필요)

헤더에 `SAMPLE DATA` 가 계속 떠 있습니다. **그대로 두세요.** 숫자가 표본인 이상
이 표시가 있어야 합니다. 없애고 싶다면 표시를 지울 게 아니라
[scraper/LIVE_PRICES.md](scraper/LIVE_PRICES.md) 대로 실제 가격을 넣으면
배지가 알아서 `NAVER SHOPPING API` 로 바뀝니다.

### 검색엔진 (선택)

데모 사이트를 검색에 노출하고 싶지 않다면 `dist/robots.txt` 를 만드세요.

```
User-agent: *
Disallow: /
```

---

## 확인

배포 후 아래만 훑어보면 충분합니다.

- [ ] 모바일에서 헤더가 두 줄로 접히고 카드가 세로로 쌓이는가
- [ ] 색상 원 6개가 모두 적용되는가 (선택이 `localStorage` 에 남는가)
- [ ] 총평의 한국어 라벨이 깨지지 않는가 → 깨지면 `charset` 문제입니다
- [ ] 매장 링크가 새 탭에서 열리는가
- [ ] 카카오톡에 링크를 붙여 미리보기 이미지가 뜨는가
