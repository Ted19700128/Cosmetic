# 배포

**현재 배포되어 있습니다 → <https://yun-concierge.vercel.app>**

| | |
|---|---|
| 저장소 | <https://github.com/Ted19700128/Cosmetic> |
| 호스팅 | Vercel (`main` 브랜치에 push하면 자동 재배포) |
| 빌드 | 없음. `dist/` 를 저장소에 커밋해 두고 정적 파일만 서빙합니다 |

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

`dist/index.html` 이 이걸 모두 갖춘 배포본입니다. `python build.py` 가 만듭니다.

**호스팅이 `dist/` 를 바라보게 하는 것이 이 프로젝트 배포의 핵심입니다.**
저장소 루트를 서빙하면 위 표의 증상이 그대로 나옵니다.

---

## 일상 작업 흐름

```bash
# 1. 루트 index.html 을 고칩니다
# 2. 배포본을 다시 만듭니다
python build.py

# 3. 로컬에서 확인합니다 (dist 를 봐야 합니다. 루트 파일을 직접 열지 마세요)
python -m http.server 8000 --directory dist
#    → http://localhost:8000

# 4. 올립니다
git add -A
git commit -m "..."
git push
```

push하면 Vercel이 알아서 재배포합니다. 보통 30초 안에 반영됩니다.
핫 리로드는 없습니다 — 고칠 때마다 `python build.py` 를 다시 돌리고 새로고침하세요.

---

## Vercel 설정 (다시 세팅할 일이 있다면)

<https://vercel.com/new> 에서 저장소를 임포트한 뒤, **딱 한 가지만** 바꿉니다.

**Settings → Build and Deployment → Root Directory → `dist` → Save**

이게 전부입니다. 빌드 명령도, 프레임워크 설정도 필요 없습니다.

이 한 줄을 빠뜨리면 Vercel이 저장소 루트를 서빙하고, 위에서 말한 조각 파일이
그대로 노출되거나 404가 납니다.

`vercel.json` 으로는 이 설정을 대신할 수 없습니다. Vercel은 vercel.json 을
**Root Directory 기준으로** 찾기 때문에, 저장소 루트에 둔 파일은 읽히지 않습니다.

---

## 도메인

주소는 Vercel 프로젝트 이름에서 자동 생성됩니다.
바꾸려면 **Settings → General → Project Name** 을 고치면 `.vercel.app` 주소가 따라옵니다.

커스텀 도메인은 **Settings → Domains → Add** 에서 연결하고, 안내대로 DNS 레코드를
추가하면 됩니다 (보통 CNAME 하나). 포트폴리오 주소는 이력서에 들어가니
`yourname.dev` 쪽이 `yun-concierge.vercel.app` 보다 낫습니다.

### 주소를 바꿨다면 반드시 다시 빌드하세요

링크 미리보기 메타(`og:image` · `og:url`)에는 **절대 주소**가 박힙니다.
상대 경로는 카카오톡·슬랙에서 동작하지 않기 때문입니다. 주소가 바뀌면 이 값도
같이 바뀌어야 하고, 안 그러면 **미리보기가 통째로 안 뜹니다.**

주소는 `build.py` 의 `DEFAULT_URL` 한 곳에서 옵니다.

```python
DEFAULT_URL = "https://yun-concierge.vercel.app"
```

도메인을 바꿨다면 이 값을 고치고 `python build.py` 를 다시 돌리세요.
일회성으로 다른 주소를 쓰려면:

```bash
python build.py --url https://yourname.dev
```

---

## 다른 호스팅

### GitHub Pages

같은 저장소에 수집기 소스가 공개된다는 게 장점입니다. 다만 **함정이 하나 있습니다.**

Pages의 브랜치 배포는 폴더로 `/ (root)` 와 `/docs` **둘만** 지원합니다.
`/dist` 는 드롭다운에 아예 나오지 않습니다. 쓰려면 둘 중 하나입니다.

- `dist/` 를 `docs/` 로 이름을 바꾸고 `build.py` 의 `OUT` 경로도 함께 고치기
- GitHub Actions 워크플로로 `dist/` 를 배포하기 (`actions/deploy-pages`)

### Cloudflare Pages / Netlify

`dist` 폴더를 브라우저에 **끌어다 놓으면** 끝입니다. 30초, 계정만 있으면 됩니다.

- Cloudflare Pages → <https://pages.cloudflare.com> → Direct Upload
- Netlify → <https://app.netlify.com/drop>

둘 다 무료, HTTPS 자동, 커스텀 도메인 연결 가능.

---

## 판단이 필요한 것

### SAMPLE DATA 배지

헤더에 `SAMPLE DATA` 가 계속 떠 있습니다. **그대로 두세요.** 숫자가 표본인 이상
이 표시가 있어야 합니다. 없애고 싶다면 표시를 지울 게 아니라
[scraper/LIVE_PRICES.md](scraper/LIVE_PRICES.md) 대로 실제 가격을 넣으면
배지가 알아서 `NAVER SHOPPING API` 로 바뀝니다.

### 검색엔진 노출

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
