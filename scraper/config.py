"""채널 정의와 태깅 사전."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChannelSpec:
    key: str
    name: str            # 페이지에 노출되는 매장 이름
    base: str
    adapter: str         # adapters.py의 클래스 이름
    delay: float = 1.2   # 요청 간 최소 간격(초)
    concurrency: int = 2
    paths: dict = field(default_factory=dict)   # 카테고리 키 -> 경로/파라미터
    review_adapter: str = ""                    # reviews.py의 클래스 이름 (비면 리뷰 미수집)


CHANNELS = [
    ChannelSpec(
        key="oliveyoung", name="올리브영", base="https://www.oliveyoung.co.kr",
        adapter="JsonLdChannel", review_adapter="LdReviewSource",
        paths={
            "skin":  "/store/display/getMCategoryList.do?dispCatNo=100000100010013",
            "sun":   "/store/display/getMCategoryList.do?dispCatNo=100000100010014",
            "make":  "/store/display/getMCategoryList.do?dispCatNo=100000100020001",
            "clean": "/store/display/getMCategoryList.do?dispCatNo=100000100010015",
            "hair":  "/store/display/getMCategoryList.do?dispCatNo=100000100040001",
        },
    ),
    ChannelSpec(
        key="musinsa", name="무신사 뷰티", base="https://api.musinsa.com",
        adapter="MusinsaChannel", delay=1.0, review_adapter="JsonReviewSource",
        paths={"beauty": "/api2/dp/v1/plp/goods?category=104&size=100&page={page}",
               "reviews": "/api2/review/v1/view/list?goodsNo={goods}&page={page}&size=30"},
    ),
    ChannelSpec(
        key="naver", name="네이버 스마트스토어", base="https://openapi.naver.com",
        adapter="NaverApiChannel", delay=0.4, concurrency=1,
        paths={"search": "/v1/search/shop.json"},
    ),
    ChannelSpec(key="kurly", name="컬리뷰티", base="https://www.kurly.com", adapter="JsonLdChannel",
                paths={"beauty": "/beauty/collections/beauty-best?page={page}"}),
    ChannelSpec(key="coupang", name="쿠팡", base="https://www.coupang.com", adapter="JsonLdChannel",
                paths={"beauty": "/np/categories/176522?page={page}"}),
    ChannelSpec(key="lotteon", name="롯데온", base="https://www.lotteon.com", adapter="JsonLdChannel"),
    ChannelSpec(key="ssg", name="SSG닷컴", base="https://www.ssg.com", adapter="JsonLdChannel"),
    ChannelSpec(key="zigzag", name="지그재그", base="https://api.zigzag.kr", adapter="JsonLdChannel"),
    ChannelSpec(key="ably", name="에이블리", base="https://api.a-bly.com", adapter="JsonLdChannel"),
    ChannelSpec(key="amoremall", name="아모레몰", base="https://www.amoremall.com", adapter="JsonLdChannel"),
    ChannelSpec(key="29cm", name="29CM", base="https://www.29cm.co.kr", adapter="JsonLdChannel"),
]

CHANNELS_BY_KEY = {c.key: c for c in CHANNELS}

# ---------------------------------------------------------------- 태깅 사전
# 제품명·카테고리·설명에서 찾을 키워드 -> 페이지가 쓰는 코드
USE_KEYWORDS = {
    "sun":   ["선크림", "선스틱", "선세럼", "선스크린", "자외선", "spf"],
    "make":  ["쿠션", "파운데이션", "틴트", "립스틱", "섀도", "아이브라우", "파우더", "컨실러", "쉐딩", "블러셔"],
    "clean": ["클렌징", "클렌저", "폼", "미셀라", "클렌징오일", "클렌징밤"],
    "hair":  ["샴푸", "트리트먼트", "컨디셔너", "헤어", "바디워시", "바디로션", "두피"],
    "scent": ["향수", "퍼퓸", "오 드", "핸드크림", "핸드밤", "디퓨저"],
    "skin":  ["토너", "세럼", "앰플", "에센스", "크림", "로션", "마스크", "패드", "스킨"],
}

CONCERN_KEYWORDS = {
    "hyd":   ["수분", "히알루론", "보습", "水分"],
    "cal":   ["진정", "수딩", "시카", "센텔라", "판테놀", "장벽", "어성초"],
    "acne":  ["트러블", "여드름", "티트리", "살리실"],
    "pore":  ["모공", "피지", "블랙헤드", "블러링"],
    "tone":  ["미백", "잡티", "비타민", "나이아신아마이드", "톤업", "브라이트닝"],
    "wri":   ["주름", "탄력", "리프팅", "레티놀", "펩타이드", "안티에이징"],
    "uv":    ["자외선", "spf", "pa+"],
    "base":  ["쿠션", "파운데이션", "베이스", "컨실러", "파우더"],
    "color": ["틴트", "립스틱", "섀도", "블러셔", "아이라이너"],
    "lip":   ["립", "틴트", "립밤"],
    "oil":   ["클렌징", "세안", "메이크업 리무버"],
    "scalp": ["두피", "탈모", "샴푸", "헤어"],
    "body":  ["바디", "핸드", "풋"],
    "scent": ["향수", "퍼퓸", "오 드", "프래그런스"],
}

VIBE_KEYWORDS = {
    "derma": ["더마", "피부과", "저자극", "임상", "약국"],
    "clean": ["비건", "클린뷰티", "무향", "자연 유래", "ewg"],
    "lux":   ["프레스티지", "럭셔리", "한방", "리미티드"],
    "value": ["대용량", "1+1", "기획", "가성비"],
}

GENDER_KEYWORDS = {"m": ["옴므", "포맨", "for men", "남성", "그루밍"], "f": ["여성용"]}

AGE_HINTS = {
    10: ["학생", "첫 스킨케어", "트러블"],
    20: ["데일리", "수분", "모공"],
    30: ["톤업", "잡티", "초기 탄력"],
    40: ["주름", "탄력", "안티에이징"],
    50: ["영양", "재생", "한방"],
}

# 표기 흔들림 통일: 수집된 표기 -> 페이지 표기
BRAND_ALIASES = {
    "ANUA": "아누아", "anua": "아누아", "아누아(ANUA)": "아누아",
    "ROUND LAB": "라운드랩", "라운드랩(ROUND LAB)": "라운드랩",
    "TORRIDEN": "토리든", "goodal": "구달", "구달(goodal)": "구달",
    "MA:NYO": "마녀공장", "마녀공장(MANYO)": "마녀공장",
    "Dr.G": "닥터지", "닥터지(Dr.G)": "닥터지",
    "AESTURA": "에스트라", "에스트라(AESTURA)": "에스트라",
    "SKIN1004": "스킨1004", "COSRX": "코스알엑스", "numbuzin": "넘버즈인",
    "Beauty of Joseon": "조선미녀", "뷰티오브조선": "조선미녀",
    "LANEIGE": "라네즈", "innisfree": "이니스프리", "SULWHASOO": "설화수",
    "HERA": "헤라", "IOPE": "아이오페", "CLIO": "클리오", "rom&nd": "롬앤",
    "ROMAND": "롬앤", "peripera": "페리페라", "dasique": "데이지크",
    "AMUSE": "어뮤즈", "hince": "힌스", "LAKA": "라카", "TAMBURINS": "탬버린즈",
    "NONFICTION": "논픽션", "FORMENT": "포맨트", "GRANHAND": "그란핸드",
}
