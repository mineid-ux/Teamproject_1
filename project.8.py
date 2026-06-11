import os

# 1. 하정님 컴퓨터의 실제 자바 경로 주입
os.environ['JAVA_HOME'] = r'C:\Program Files\Java\jdk-26'

import streamlit as st
import requests
import matplotlib.pyplot as plt
import platform
import pandas as pd
import time
from datetime import datetime
import jpype  # 자바 상태를 직접 체크하기 위해 jpype 소환!
from wordcloud import WordCloud  # 워드클라우드 라이브러리
from collections import Counter  # 단어 빈도수 계산용

# 운영체제별 한글 폰트 자동 설정 (그래프 및 워드클라우드 글자 깨짐 방지)
system_os = platform.system()
font_path = "Malgun Gothic"  # 기본 윈도우 폰트
if system_os == "Windows":
    plt.rc('font', family='Malgun Gothic')
    font_path = "C:/Windows/Fonts/malgun.ttf"
elif system_os == "Darwin":
    plt.rc('font', family='AppleGothic')
    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
else:
    plt.rc('font', family='NanumGothic')
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
plt.rcParams['axes.unicode_minus'] = False

# 스트림릿 페이지 기본 레이아웃 및 제목 설정
st.set_page_config(page_title="네이버 블로그 리뷰 및 유동인구 융합 분석기", layout="wide")

st.title("☕ 네이버 블로그 리뷰 & 유동인구 트렌드 융합 분석기 (인기순 1,000개 Ver.)")
st.markdown("네이버에서 **가장 인기 있고 조회수가 높은 콘텐츠(유사도순) 상위 1,000개**를 수집하여 Okt 형태로 분석하고, 유동인구 데이터와 융합합니다.")

# ----------------------------------------------------
# 📅 1. 최상단 기간 설정 셀렉트 박스 (년도 및 월)
# ----------------------------------------------------
st.subheader("📅 분석 기간 설정")

col_start_y, col_start_m, col_end_y, col_end_m = st.columns(4)

with col_start_y:
    start_year = st.selectbox("시작 년도", [2024, 2025, 2026], index=0)
with col_start_m:
    start_month = st.selectbox("시작 월", list(range(1, 13)), index=0)
with col_end_y:
    end_year = st.selectbox("종료 년도", [2024, 2025, 2026], index=1)
with col_end_m:
    end_month = st.selectbox("종료 월", list(range(1, 13)), index=11)

# 시작일과 종료일 범위 설정
start_date_bound = datetime(start_year, start_month, 1)
end_date_bound = datetime(end_year, end_month, 28)

# 차트의 X축에 표시될 시작부터 끝까지의 모든 '연월' 리스트 생성
all_months = pd.date_range(start=start_date_bound, end=end_date_bound, freq='MS').strftime('%Y-%m').tolist()

st.markdown("---")

# ----------------------------------------------------
# 🔍 2. 분석 대상 설정 및 외부 CSV 파일 업로드
# ----------------------------------------------------
st.subheader("🔍 분석 대상 및 파일 설정")

col_input, col_upload = st.columns(2)

with col_input:
    search_query = st.text_input("검색어를 입력하세요", value="전포 느좋 카페")

with col_upload:
    uploaded_file = st.file_uploader("유동인구 데이터 CSV 파일을 업로드 하세요 (프로젝트 데이터.csv)", type=["csv"])


# 자바 JVM이 이미 가동 중인지 체크하고 안전하게 Okt를 가져오는 함수
def get_okt_safely():
    from konlpy.tag import Okt
    return Okt()


# 하정님의 고유 네이버 API 키 설정
NAVER_CLIENT_ID = "a7IuYEXKtUN_P7ZsI3TP"
NAVER_CLIENT_SECRET = "IuiF7ZsRYQ"

# ----------------------------------------------------
# 🚀 3. 분석 시작 버튼 이벤트
# ----------------------------------------------------
if st.button("Okt 형태소 문맥 & 유동인구 데이터 융합 분석 시작 🚀"):
    if not search_query.strip():
        st.error("검색어를 입력해주세요.")
    elif uploaded_file is None:
        st.error("오른쪽 업로드 박스에 '프로젝트 데이터.csv' 파일을 업로드해주세요.")
    else:
        all_items = []

        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }

        # 진행 상황 프로그레스 바
        progress_bar = st.progress(0, text=f"'{search_query}' 인기 콘텐츠 상위 1,000개 수집 중...")

        # 🌟 [핵심 변경] 100개씩 10번 = 총 1,000개의 '인기순(sort=sim)' 글 검색 루프
        for i in range(10):
            start_index = (i * 100) + 1
            # 💡 sort=sim 을 추가하여 조회수, 주목도, 정확도가 높은 '인기 글' 순서대로 페이지네이션 빌드
            url = f"https://openapi.naver.com/v1/search/blog.json?query={search_query}&display=100&start={start_index}&sort=sim"

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                blog_items = data.get("items", [])

                if not blog_items:
                    break

                # 순위를 기억하기 위해 인덱스 정보를 매핑하여 저장
                for idx, item in enumerate(blog_items):
                    item['popular_rank'] = start_index + idx
                    all_items.append(item)
            else:
                st.error(f"크롤링 중 오류가 발생했습니다. (코드: {response.status_code})")
                break

            progress_bar.progress((i + 1) * 10, text=f"인기 콘텐츠 데이터 수집 중... ({i + 1}/10 단계 완료)")
            time.sleep(0.5)  # 0.5초 디레이 시간 유지

        progress_bar.empty()

        if len(all_items) == 0:
            st.warning("⚠️ 검색 결과가 없습니다. 검색어를 변경해 보세요.")
        else:
            with st.spinner("인기 블로그 Okt 문맥 검사 및 유동인구 매핑 분석 중..."):
                try:
                    okt = get_okt_safely()
                except Exception as e:
                    if "JVM is already started" in str(e) or "IllegalStateException" in str(e):
                        from konlpy.tag import Okt

                        okt = Okt()
                    else:
                        st.error(f"❌ 자바 초기화 중 예상치 못한 에러 발생: {e}")
                        st.stop()

                # 감정 사전 및 반전 단어 정의
                positive_dict = {
                    '좋다': 1.0, '맛있다': 1.5, '친절하다': 1.5, '추천': 1.5, '예쁘다': 1.0,
                    '최고': 2.0, '감성': 1.0, '괜찮다': 1.0, '평타': 0.5, '느좋': 2.0, '만족': 1.5, '문제없다': 1.2
                }
                negative_dict = {
                    '부족하다': 1.0, '아쉽다': 1.5, '아쉬움': 1.5, '별로': 1.5, '실망': 2.0,
                    '불친절하다': 2.0, '맛없다': 2.0, '웨이팅': 1.0, '비싸다': 1.2, '유감': 1.5,
                    '후회': 2.0, '불만': 1.5
                }
                invert_words = ['않다', '아님', '아니다', '못하다', '없다', '별로', '그저']

                pos_count, neg_count = 0, 0
                results_list = []
                all_words_for_cloud = []

                # 월별 긍정 리뷰 수 딕셔너리 초기화
                monthly_pos_review_counts = {ym: 0 for ym in all_months}

                # 수집된 인기 데이터 가공 시작
                for item in all_items:
                    title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                    description = item.get("description", "").replace("<b>", "").replace("</b>", "")
                    blog_url = item.get("link", "")
                    rank_num = item.get("popular_rank", 0)
                    full_text = title + " " + description

                    # 날짜 가공 및 연월 파싱
                    raw_date = item.get("postdate", "")
                    try:
                        date_obj = datetime.strptime(raw_date, "%Y%m%d")
                        year_month = date_obj.strftime("%Y-%m")
                        formatted_date = date_obj.strftime("%Y-%m-%d")
                    except:
                        continue

                    # 기간 필터링 적용
                    if start_date_bound <= date_obj <= end_date_bound:
                        stemmed_tokens = okt.morphs(full_text, stem=True)

                        # 워드클라우드용 토큰 추출 (명사, 형용사 중 2글자 이상)
                        pos_tags = okt.pos(full_text, stem=True)
                        for word, tag in pos_tags:
                            if tag in ['Noun', 'Adjective'] and len(word) >= 2:
                                if word not in search_query:
                                    all_words_for_cloud.append(word)

                        pos_score, neg_score = 0.0, 0.0

                        # 감정 및 역전 문맥 스캔
                        for word, score in positive_dict.items():
                            if word in stemmed_tokens:
                                idx = stemmed_tokens.index(word)
                                if any(inv in stemmed_tokens[idx:idx + 5] for inv in invert_words):
                                    neg_score += score
                                else:
                                    pos_score += score

                        for word, score in negative_dict.items():
                            if word in stemmed_tokens:
                                idx = stemmed_tokens.index(word)
                                if any(inv in stemmed_tokens[idx:idx + 5] for inv in invert_words):
                                    pos_score += score
                                else:
                                    neg_score += score

                        # 최종 판단 및 월별 긍정 카운터 누적
                        if pos_score > neg_score:
                            sentiment = "긍정"
                            pos_count += 1
                            if year_month in monthly_pos_review_counts:
                                monthly_pos_review_counts[year_month] += 1
                        elif neg_score > pos_score:
                            sentiment = "부정"
                            neg_count += 1
                        else:
                            if any(w in stemmed_tokens for w in negative_dict) or any(
                                    inv in stemmed_tokens for inv in invert_words):
                                sentiment = "부정"
                                neg_count += 1
                            else:
                                sentiment = "긍정"
                                pos_count += 1
                                if year_month in monthly_pos_review_counts:
                                    monthly_pos_review_counts[year_month] += 1

                        results_list.append({
                            "인기순위": rank_num,
                            "작성일": formatted_date,
                            "연월": year_month,
                            "블로그_제목": title,
                            "내용_요약": description,
                            "감정_분류": sentiment,
                            "긍정_점수": round(pos_score, 1),
                            "부정_점수": round(neg_score, 1),
                            "블로그_주소": blog_url
                        })

                # 차트용 막대 수치 매핑
                review_bar_data = [monthly_pos_review_counts[ym] for ym in all_months]

                # 업로드한 프로젝트 데이터 CSV 연동 전처리
                try:
                    df_uploaded = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                    df_uploaded = df_uploaded[df_uploaded['월'] != '총합계']

                    month_map = {f"{m}월": f"{m:02d}" for m in range(1, 13)}
                    df_uploaded['월_clean'] = df_uploaded['월'].map(month_map)

                    population_series = []
                    for ym in all_months:
                        year_part, month_part = ym.split('-')
                        col_name = f"{year_part}년 유동인구 총합계(명)"

                        if col_name in df_uploaded.columns:
                            row = df_uploaded[df_uploaded['월_clean'] == month_part]
                            if not row.empty:
                                val = row[col_name].values[0]
                                population_series.append(0 if pd.isna(val) else float(val))
                            else:
                                population_series.append(0)
                        else:
                            population_series.append(0)
                    csv_load_success = True
                except Exception as e:
                    st.error(f"❌ 업로드한 유동인구 파일을 매핑하는 중 오류가 발생했습니다. (사유: {e})")
                    csv_load_success = False

            # 데이터프레임 빌드 (우측 분석 리스트 가독성을 위해 인기순 정렬 유지)
            if results_list:
                df = pd.DataFrame(results_list)
                df = df.sort_values(by="인기순위", ascending=True)
                csv_data = df.to_csv(index=False).encode('utf-8-sig')
            else:
                csv_data = None

            # ----------------------------------------------------
            # 📊 4. 대시보드 화면 시각화 레이아웃 배치
            # ----------------------------------------------------
            col1, col2 = st.columns([1, 1])

            with col1:
                if csv_load_success:
                    st.subheader("📊 융합 분석 차트 (인기 콘텐츠 긍정 수 vs 월별 유동인구)")

                    fig_mix, ax1 = plt.subplots(figsize=(8, 5))

                    # 왼쪽 축: 긍정 리뷰 수 막대그래프
                    ax1.bar(all_months, review_bar_data, width=0.5, color='#3498db', alpha=0.6, edgecolor='black',
                            label='인기글 중 긍정 수')
                    ax1.set_ylabel('긍정 리뷰 수 (건)', color='#2980b9', fontsize=11)
                    ax1.tick_params(axis='y', labelcolor='#2980b9')
                    ax1.set_xticklabels(all_months, rotation=45)
                    ax1.grid(True, axis='y', linestyle='--', alpha=0.3)

                    # 오른쪽 축: 유동인구 꺾은선그래프
                    ax2 = ax1.twinx()
                    ax2.plot(all_months, population_series, marker='o', color='#e74c3c', linewidth=3, markersize=7,
                             label='유동인구(명)')
                    ax2.set_ylabel('유동인구 총합계 (명)', color='#e74c3c', fontsize=11)
                    ax2.tick_params(axis='y', labelcolor='#e74c3c')
                    ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

                    # 범례 결합
                    lines, labels = ax1.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax2.legend(lines + lines2, labels + labels2, loc='upper left')

                    plt.tight_layout()
                    st.pyplot(fig_mix)

                # 파이 차트 및 통계 데이터 표시
                st.subheader("📈 인기 콘텐츠 소비자 감정 비율 (원그래프)")
                labels_pie = ['긍정', '부정']
                sizes_pie = [pos_count, neg_count]
                colors_pie = ['#2ecc71', '#e74c3c']

                fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
                if sum(sizes_pie) > 0:
                    ax_pie.pie(sizes_pie, labels=labels_pie, autopct='%1.1f%%', startangle=90, colors=colors_pie)
                ax_pie.axis('equal')
                st.pyplot(fig_pie)

                total_total = len(results_list)
                st.metric(label="📊 수집 및 분석된 총 블로그 리뷰 수", value=f"{total_total}개")
                st.metric(label="📈 인기 콘텐츠 긍정 반응 비율",
                          value=f"{(pos_count / total_total) * 100:.1f}%" if total_total > 0 else "0%")

                # 워드클라우드 레이아웃
                st.markdown("---")
                st.subheader("☁️ 인기 리뷰 핵심 빈출 키워드 (워드클라우드)")
                if all_words_for_cloud:
                    word_counts = Counter(all_words_for_cloud)
                    wordcloud = WordCloud(
                        font_path=font_path, background_color='white',
                        width=800, height=450, max_words=80, colormap='plasma'
                    ).generate_from_frequencies(word_counts)

                    fig_wc, ax_wc = plt.subplots(figsize=(8, 4.5))
                    ax_wc.imshow(wordcloud, interpolation='bilinear')
                    ax_wc.axis('off')
                    st.pyplot(fig_wc)

                if csv_data:
                    st.markdown("---")
                    st.subheader("💾 데이터 분석 파일 받기")
                    st.download_button(
                        label="📥 인기글 분석 결과 CSV 다운로드",
                        data=csv_data,
                        file_name=f"{search_query}_인기순_통합분석결과.csv",
                        mime="text/csv"
                    )

            with col2:
                # 💡 사용자가 직관적으로 조회수 순위를 인지하도록 [인기 1위], [인기 2위] 형태로 리스트업합니다.
                st.subheader("🔍 상위 인기 블로그 실시간 문맥 분석 리스트")
                if results_list:
                    for idx, row in enumerate(df.itertuples(), 1):
                        badge = "🟢" if row.감정_분류 == "긍정" else "🔴"
                        st.write(f"**[인기 {row.인기순위}위] {badge} {row.블로그_제목}**")
                        st.caption(
                            f"📅 작성일: {row.작성일} | 결과: **{row.감정_분류}** "
                            f"(긍정: {row.긍정_점수}점 / 부정: {row.부정_점수}점)"
                        )
                        st.markdown("---")
                else:
                    st.info("지정한 분석 기간 내에 수집된 블로그 글이 없습니다.")