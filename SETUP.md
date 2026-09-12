# 내 저장소로 가져가기

이 폴더를 통째로 복사해서 **내 GitHub 저장소와 내 Vercel 계정**으로 옮기는 방법입니다.
처음부터 끝까지 따라 하면 30분 안에 내 주소로 사이트가 뜹니다.

## 이게 무슨 프로젝트인가

카드 네 장에 답하면 한국 화장품 하나를 추천해 주는 **웹사이트 한 장**입니다.
온라인 쇼핑몰 11곳의 가격대와 최저가 순위를 같이 보여줍니다.

```
index.html    사이트 원본 (이것을 고칩니다)
build.py      원본 → 배포본을 만드는 스크립트
dist/         실제로 배포되는 결과물
scraper/      가격·리뷰를 모으는 파이썬 도구 (사이트 배포와는 무관)
```

## 준비물

- Git, Python 3
- GitHub 계정
- Vercel 계정 (GitHub 계정으로 로그인하면 됩니다)

---

## 1. 폴더를 복사하고 git을 새로 시작합니다

복사한 폴더에는 **원래 주인의 `.git` 폴더가 딸려 옵니다.** 그 안에는 원래 저장소
주소가 들어 있어서, 그대로 두고 `git push` 하면 **내 저장소가 아니라 원래 저장소로
올라갑니다.** 지우고 새로 시작하세요.

```bash
cd <복사한 폴더>
rm -rf .git
git init
git branch -M main
```

이어서 **내 이름으로 커밋되도록** 설정합니다. 이 두 줄을 빼먹으면 GitHub에서
커밋 작성자가 다른 사람으로 표시되고, 내 잔디에도 기록이 남지 않습니다.

```bash
git config user.name  "<내 GitHub 사용자명>"
git config user.email "<내 GitHub 계정 이메일>"
```

## 2. 내 정보로 바꿔야 할 곳

`scraper/base.py` 19번째 줄에 **원래 주인의 이메일**이 들어 있습니다.

```python
UA = "GyeolConciergeBot/0.3 (+portfolio project; contact: 원래주인@example.com)"
```

수집기가 쇼핑몰에 접속할 때 자기 신원으로 보내는 값입니다. 내 이메일로 바꾸거나,
수집기를 쓸 생각이 없으면 연락처 부분을 지우세요.

개인정보는 저장소 전체에서 이 한 줄뿐입니다. 사이트 파일에는 없습니다.

## 3. GitHub에 올립니다

<https://github.com/new> 에서 새 저장소를 만듭니다.
**README·.gitignore·license는 체크하지 마세요** — 이미 파일이 있어서 충돌합니다.

```bash
git add -A
git commit -m "Yun Beauty Concierge"
git remote add origin https://github.com/<내 사용자명>/<저장소 이름>.git
git push -u origin main
```

## 4. Vercel에 배포합니다 — 여기가 가장 중요합니다

1. <https://vercel.com/new> 에서 방금 만든 저장소를 임포트합니다
2. **Deploy** 를 누릅니다
3. 배포가 끝나면 **Settings → Build and Deployment → Root Directory** 에
   **`dist`** 를 입력하고 **Save**
4. 다시 배포되기를 기다립니다

### `dist` 를 지정하지 않으면 사이트가 깨집니다

`dist` 를 지정하지 않으면 Vercel은 폴더 맨 바깥을 서빙합니다. 그런데 거기 있는
`index.html` 은 **완성된 문서가 아니라 조각**입니다. `<!doctype>` 도, 한글 인코딩
설정도 없습니다. 그 상태로 뜨면:

| 증상 | 원인 |
|---|---|
| 404 화면만 나온다 | 서빙할 파일을 못 찾음 |
| 한국어가 `ì` 같은 깨진 글자로 나온다 | `charset` 누락 |
| 모바일에서 글씨가 깨알같이 작다 | `viewport` 누락 |

`dist/index.html` 은 이 설정이 모두 들어간 완성본입니다. 그래서 Vercel이
`dist` 를 보게 만들어야 합니다.

## 5. 주소가 정해졌으면 다시 빌드합니다

배포가 끝나면 `내프로젝트이름.vercel.app` 같은 주소가 생깁니다.
마음에 안 들면 **Settings → General → Project Name** 에서 바꿀 수 있습니다.

주소가 확정되면 `build.py` 22번째 줄을 내 주소로 고칩니다.

```python
DEFAULT_URL = "https://내주소.vercel.app"
```

그리고 다시 빌드해서 올립니다.

```bash
python build.py
git add -A
git commit -m "배포 주소 반영"
git push
```

### 왜 이걸 해야 하나

카카오톡이나 슬랙에 링크를 붙이면 제목·설명·이미지가 카드로 뜹니다. 그 카드에
쓸 이미지 주소가 파일 안에 **절대 주소로** 박혀 있습니다. 이걸 안 고치면 카드가
원래 주인의 사이트를 가리키거나, 아예 안 뜹니다.

## 6. 문서 정리 (선택)

`DEPLOY.md` 에 원래 주인의 저장소·사이트 주소가 남아 있습니다. 3 · 7 · 85 · 96행을
내 주소로 바꾸거나, 필요 없으면 파일을 지우세요.

---

## 고칠 때의 작업 흐름

사이트를 수정할 때는 **항상 이 순서**입니다.

```bash
# 1. index.html 을 고칩니다 (맨 바깥 파일)

# 2. 배포본을 다시 만듭니다  ← 빼먹으면 바뀐 게 반영되지 않습니다
python build.py

# 3. 로컬에서 확인합니다
python -m http.server 8000 --directory dist
#    브라우저에서 http://localhost:8000
```

확인이 끝나면 `git add -A && git commit -m "..." && git push`.
push하면 Vercel이 30초 안에 자동으로 다시 배포합니다.

**맨 바깥 `index.html` 을 브라우저로 직접 열지 마세요.** 조각 파일이라 한글이
깨져 보입니다. 반드시 위처럼 `dist` 를 띄워서 확인해야 합니다.

---

## 막혔을 때

| 증상 | 확인할 것 |
|---|---|
| 사이트가 404 | Vercel의 Root Directory 가 `dist` 인지 |
| 한글이 깨져 보임 | `dist` 가 아니라 맨 바깥 파일을 보고 있지 않은지 |
| 고쳤는데 안 바뀜 | `python build.py` 를 돌렸는지 |
| push가 거부됨 | `git remote -v` 가 **내** 저장소를 가리키는지 |
| 커밋이 남의 이름으로 | `git config user.name` / `user.email` 설정했는지 |
| 카톡 미리보기가 안 뜸 | `build.py` 의 `DEFAULT_URL` 을 내 주소로 고치고 재빌드했는지 |

## 수집기(`scraper/`)를 돌리고 싶다면

사이트를 띄우는 데는 **필요 없습니다.** 실제 가격을 새로 모을 때만 씁니다.
API 키는 저장소에 들어 있지 않으니 직접 발급받아 환경변수로 넣어야 합니다.

```
NAVER_CLIENT_ID / NAVER_CLIENT_SECRET     가격 수집
DEEPL_API_KEY                              리뷰 번역
```

키가 없으면 그 부분만 건너뛰고 나머지는 그대로 돕니다.
자세한 내용은 `scraper/README.md` 에 있습니다.

---

## 체크리스트

- [ ] `.git` 지우고 `git init` 새로
- [ ] `git config user.name` / `user.email` 설정
- [ ] `scraper/base.py` 의 이메일 교체
- [ ] GitHub 새 저장소에 push
- [ ] Vercel **Root Directory = `dist`**
- [ ] `build.py` 의 `DEFAULT_URL` 을 내 주소로 → `python build.py` → push
- [ ] 휴대폰으로 열어서 레이아웃 확인
- [ ] 한국어 라벨이 안 깨지는지 확인
