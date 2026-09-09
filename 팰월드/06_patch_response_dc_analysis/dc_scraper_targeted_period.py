"""
디시인사이드 팰월드 갤러리 - 패치 전/후 구간 타겟 수집 (개선판)
====================================================
[이전 버전과의 차이 — 문제 진단]
1) 이전 스크래핑은 게시판 1페이지(최신글)만 긁어와서, 결과적으로 9/1~9/3
   단 이틀치 스냅샷 + 상단 고정 공지글 몇 개만 수집됨. "정식출시 이전"과
   "정출~1.0.3" 구간이 통째로 비어있어 패치 전/후 비교가 근본적으로
   불가능한 데이터였음.
2) up_votes(추천수)가 전부 0으로 수집됐던 이유: 게시글 상세페이지에 박힌
   JSON-LD 구조화 데이터(interactionStatistic)에는 댓글수·조회수만
   있고 추천수 필드 자체가 없음. 추천수는 게시판 "목록 페이지" 테이블
   에서만 확인 가능한 값이라, 상세페이지 기반 파싱으로는 애초에 못
   가져오는 구조였음 (파싱 버그가 아니라 잘못된 소스를 봤던 것).

[이번 버전의 수정 사항]
1) 목록 페이지를 과거로 여러 페이지 거슬러 올라가며(page 증가) 지정한
   날짜 구간(기본: 정출 3주 전 ~ 1.0.3 다음날)에 도달할 때까지 순회
   — 스냅샷이 아니라 시간 구간을 직접 타겟팅
2) 추천수는 목록 페이지 테이블에서 직접 추출 (상세페이지 X)
3) 말머리가 "공지"/"AD"/"설문"인 상단 고정 게시글은 자동 제외
   (실제 유저 반응이 아니라 시계열 분석에 노이즈가 되는 운영진 고정글)
4) 2단계 수집 구조:
   - Phase 1: 목록 페이지만 순회하며 구간 내 전체 게시글의 메타데이터
     (제목/날짜/조회/추천)를 우선 확보 (요청량이 적어 상대적으로 빠름)
   - Phase 2: 그중 가설 키워드(제트래곤/안장/레이번/세계수 등)가 제목에
     포함된 글은 우선 전부 포함하고, 나머지는 무작위로 채워 총 N건까지
     본문을 수집. sample_method 컬럼으로 "keyword_priority"/"random"을
     구분해둠 — 이렇게 해야 나중에 "이 정도 빈도로 언급됐다"는 순수
     빈도 분석을 할 때 키워드 우선 표본이 섞여 빈도가 부풀려지는 걸
     피할 수 있음 (random 그룹만 써서 순수 빈도 추정, keyword_priority
     그룹은 "실제 사례 인용/정성 분석" 용도로 구분해서 사용)
5) 중간 저장(체크포인트) + 요청 간 딜레이(매너 크롤링)

[중요 — 실행 전 확인사항]
Claude의 실행 환경은 dcinside.com에 대한 네트워크 접근이 막혀 있어
직접 테스트가 불가능합니다. 아래 코드는 디시인사이드의 표준적인 갤러리
목록/상세 페이지 HTML 구조(오랫동안 안정적으로 유지된 class명 기준)를
바탕으로 작성했습니다.
  - 반드시 DEBUG_FIRST_PAGE=True 상태로 먼저 실행해서, 1페이지 파싱이
    잘 되는지(행 수, 원본 HTML 일부)를 콘솔에서 눈으로 확인하세요.
  - 문제가 있다면 print된 원본 HTML을 보고 select() 안의 class명을
    실제 구조에 맞게 조정한 뒤, DEBUG_FIRST_PAGE=False로 바꿔 전체
    수집을 진행하세요.
  - 날짜 파싱(parse_dc_date)도 마찬가지로 실제 표시 형식과 다르면
    정규식을 추가해야 할 수 있습니다. 콘솔에 파싱 실패 사례를 출력하니
    참고해서 보정하세요.

[규모 관련 안내]
9/1~9/3 이틀간 약 294건이 올라올 정도로 활동량이 많은 갤러리라, 7/10
이전까지 거슬러 올라가려면 목록 페이지만 수백 페이지가 될 수 있습니다.
Phase 1(목록만)은 비교적 빠르지만, Phase 2에서 매 건마다 상세페이지를
따로 요청하기 때문에 본문 수집 대상(SAMPLE_SIZE)을 무리하게 늘리면
시간이 오래 걸립니다. 필요시 SLEEP_SEC과 SAMPLE_SIZE를 조정하세요.
"""

import json
import random
import re
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

# =====================================================================
# 설정
# =====================================================================
GALLERY_ID = "palworld"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Referer": "https://gall.dcinside.com/",
}

# 정출(7/10) 이전 + 정출~1.0.3(8/12) 구간을 모두 커버하도록 넉넉히 설정
TARGET_START = datetime(2026, 6, 20)
TARGET_END = datetime(2026, 8, 13)

EXCLUDE_HEADS = {"공지", "AD", "설문"}   # 상단 고정 게시글 말머리

HYPOTHESIS_KEYWORDS = ["제트래곤", "안장", "레이번", "세계수", "팰키사이트",
                        "솔라이트", "날탈", "탈것", "제노드란"]

MAX_LIST_PAGES = 500      # 안전장치 - 예상보다 갤러리가 활발하면 늘릴 것
SLEEP_SEC = 1.5           # 매너 크롤링 딜레이 (요청 간 대기)
SAMPLE_SIZE = 300         # Phase 2에서 본문까지 수집할 최종 목표 건수

META_CSV = "dc_palworld_period_metadata.csv"     # Phase 1 산출물 (목록 메타데이터 전체)
FINAL_CSV = "dc_palworld_period_sampled.csv"      # Phase 2 산출물 (본문 포함 표본)

DEBUG_FIRST_PAGE = True   # 먼저 True로 셀렉터/파싱 확인 후 False로 전체 수집


# =====================================================================
# 날짜 파싱
# =====================================================================
def parse_dc_date(date_raw: str):
    """'26.08.02'(예전 글) 또는 '15:30'/'오늘 15:30'(당일 글) 형식을 처리.
    당일 글은 정확한 과거 날짜 비교가 필요없는 최신 구간이므로 None 반환.
    """
    date_raw = (date_raw or "").strip()
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{2})$", date_raw)
    if m:
        yy, mm, dd = m.groups()
        return datetime(2000 + int(yy), int(mm), int(dd))
    m2 = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_raw)
    if m2:
        return datetime(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    return None  # 시:분만 표시된 당일 글 등


# =====================================================================
# Phase 1 — 목록 페이지 순회 (메타데이터: 제목/날짜/조회/추천)
# =====================================================================
def parse_list_page(page: int):
    url = f"https://gall.dcinside.com/mgallery/board/lists/?id={GALLERY_ID}&page={page}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.select("table.gall_list tbody tr")
    if DEBUG_FIRST_PAGE and page == 1:
        print(f"[디버그] 요청 URL: {url}")
        print(f"[디버그] 테이블 행 수: {len(rows)}개 (0이면 selector 재확인 필요)")
        if rows:
            print("[디버그] 첫 번째 행 원본 HTML 일부:\n", str(rows[0])[:500])
        else:
            print("[디버그] 페이지 상단 500자:\n", res.text[:500])

    posts = []
    for tr in rows:
        num_td = tr.select_one("td.gall_num")
        head_td = tr.select_one("td.gall_subject")       # 말머리
        title_td = tr.select_one("td.gall_tit")
        date_td = tr.select_one("td.gall_date")
        count_td = tr.select_one("td.gall_count")          # 조회
        recommend_td = tr.select_one("td.gall_recommend")  # 추천

        if not (num_td and title_td and date_td):
            continue
        num_text = num_td.get_text(strip=True)
        if not num_text.isdigit():
            continue  # 공지/AD 등 번호가 숫자가 아닌 특수 행 스킵

        head_text = head_td.get_text(strip=True) if head_td else ""
        if head_text in EXCLUDE_HEADS:
            continue

        title_a = title_td.select_one("a")
        title = title_a.get_text(strip=True) if title_a else title_td.get_text(strip=True)
        href = title_a["href"] if (title_a and title_a.has_attr("href")) else ""
        post_url = "https://gall.dcinside.com" + href if href.startswith("/") else href

        date_raw = date_td.get("title") or date_td.get_text(strip=True)

        posts.append({
            "no": num_text,
            "head": head_text,
            "title": title,
            "date_raw": date_raw,
            "date_parsed": parse_dc_date(date_raw),
            "views": count_td.get_text(strip=True) if count_td else None,
            "up_votes": recommend_td.get_text(strip=True) if recommend_td else None,
            "url": post_url,
        })
    return posts


def collect_metadata():
    """목록 페이지를 순회하며 TARGET_START~TARGET_END 구간 게시글 메타데이터 전부 수집."""
    collected = []
    for page in range(1, MAX_LIST_PAGES + 1):
        try:
            posts = parse_list_page(page)
        except Exception as e:
            print(f"[page {page}] 요청 실패: {e} -> 스킵")
            time.sleep(SLEEP_SEC)
            continue

        if not posts:
            print(f"[page {page}] 유효 게시글 0건 - selector 문제일 수 있음, 중단")
            break

        dated = [p for p in posts if p["date_parsed"] is not None]
        undated = len(posts) - len(dated)
        if undated:
            print(f"[page {page}] 날짜 파싱 실패 {undated}건 (당일 글이거나 형식 다름 - 필요시 정규식 보정)")

        in_range = [p for p in dated if TARGET_START <= p["date_parsed"] <= TARGET_END]
        collected.extend(in_range)

        if dated:
            print(f"[page {page}] 이 페이지 날짜 범위 {min(p['date_parsed'] for p in dated).date()}"
                  f"~{max(p['date_parsed'] for p in dated).date()} | 구간 내 수집 누적 {len(collected)}건")

        # 이 페이지 전체가 타겟 구간보다 더 과거면 목표 구간을 지나쳤으므로 종료
        if dated and max(p["date_parsed"] for p in dated) < TARGET_START:
            print(f"[page {page}] 타겟 구간보다 과거로 넘어감 - Phase 1 종료")
            break

        if collected and page % 10 == 0:
            pd.DataFrame(collected).to_csv(META_CSV, index=False, encoding="utf-8-sig")
            print(f"  -> 중간 저장 완료 ({META_CSV}, {len(collected)}건)")

        time.sleep(SLEEP_SEC)

    df = pd.DataFrame(collected)
    if not df.empty:
        df.to_csv(META_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[Phase 1 완료] 구간 내 메타데이터 {len(df)}건 -> {META_CSV}")
    return df


# =====================================================================
# Phase 2 — 표본 선정 + 상세 본문 수집
# =====================================================================
def parse_post_detail(url: str):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    script = soup.find("script", {"type": "application/ld+json"})
    if not script or not script.string:
        return None
    try:
        data = json.loads(script.string)
    except (TypeError, ValueError):
        return None
    return {"content": data.get("articleBody")}


def build_sample(meta_df: pd.DataFrame, sample_size: int = SAMPLE_SIZE, seed: int = 42):
    kw_pattern = "|".join(HYPOTHESIS_KEYWORDS)
    is_keyword_hit = meta_df["title"].fillna("").str.contains(kw_pattern)

    keyword_pool = meta_df[is_keyword_hit].copy()
    keyword_pool["sample_method"] = "keyword_priority"

    remaining_n = max(sample_size - len(keyword_pool), 0)
    rest_pool = meta_df[~is_keyword_hit].copy()
    random_pool = rest_pool.sample(n=min(remaining_n, len(rest_pool)), random_state=seed).copy()
    random_pool["sample_method"] = "random"

    sample_df = pd.concat([keyword_pool, random_pool], ignore_index=True)
    print(f"[표본 구성] 키워드 우선 {len(keyword_pool)}건 + 무작위 {len(random_pool)}건 "
          f"= 총 {len(sample_df)}건")
    if len(keyword_pool) > sample_size:
        print(f"  [주의] 키워드 매칭 건수({len(keyword_pool)})가 목표 표본 수({sample_size})보다 많습니다. "
              f"전부 포함시켜 표본 크기가 커졌으니 확인하세요.")
    return sample_df


def collect_content(sample_df: pd.DataFrame):
    contents = []
    for i, row in enumerate(sample_df.itertuples(index=False)):
        try:
            detail = parse_post_detail(row.url)
            contents.append(detail["content"] if detail else None)
        except Exception as e:
            contents.append(None)
            print(f"  [{i}] 본문 수집 실패 ({row.url}): {e}")
        if i % 20 == 0:
            print(f"  본문 수집 진행: {i}/{len(sample_df)}")
        time.sleep(SLEEP_SEC)
    sample_df = sample_df.copy()
    sample_df["content"] = contents
    return sample_df


# =====================================================================
# 실행
# =====================================================================
def main():
    print("=" * 70)
    print(f"[Phase 1] 목록 페이지 순회 — 타겟 구간 {TARGET_START.date()} ~ {TARGET_END.date()}")
    print("=" * 70)
    meta_df = collect_metadata()

    if meta_df.empty:
        print("수집된 메타데이터가 없습니다. DEBUG_FIRST_PAGE=True로 selector부터 점검하세요.")
        return

    print("\n" + "=" * 70)
    print("[Phase 2] 표본 선정 + 본문 수집")
    print("=" * 70)
    sample_df = build_sample(meta_df)
    sample_df = collect_content(sample_df)

    sample_df.to_csv(FINAL_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[완료] {FINAL_CSV} 저장 ({len(sample_df)}건)")
    print("\nsample_method 분포:")
    print(sample_df["sample_method"].value_counts())
    print("\n월별 분포:")
    print(pd.to_datetime(sample_df["date_parsed"]).dt.to_period("M").value_counts().sort_index())


if __name__ == "__main__":
    main()
