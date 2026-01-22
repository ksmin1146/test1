# 실행 방법: 터미널에서 'streamlit run teacher.py' 입력
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. 페이지 설정
st.set_page_config(page_title="교사용 서술형 평가 대시보드", layout="wide")

# 2. Supabase 클라이언트 설정
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Supabase 설정(secrets.toml)을 확인해주세요.")
        st.stop()

supabase = get_supabase_client()

# 3. 데이터 불러오기 함수
def fetch_data():
    # 'student_submissions' 테이블에서 모든 데이터를 생성일시 내림차순으로 가져옴
    response = supabase.table("student_submissions").select("*").order("created_at", desc=True).execute()
    return response.data

# ─── UI 시작 ───
st.title("📊 서술형 평가 교사용 대시보드")
st.write("학생들이 제출한 답안과 AI 피드백을 실시간으로 확인합니다.")

# 새로고침 버튼
if st.button("데이터 새로고침 🔄"):
    st.cache_data.clear()
    st.rerun()

# 데이터 로드
raw_data = fetch_data()

if not raw_data:
    st.info("아직 제출된 답안이 없습니다.")
else:
    # 4. 데이터프레임 변환 및 전처리
    df = pd.DataFrame(raw_data)
    
    # 시간 데이터 보기 좋게 변경 (ISO 포맷 -> YYYY-MM-DD HH:MM)
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

    # 5. 상단 요약 통계 (Metric)
    total_students = len(df['student_id'].unique())
    total_submissions = len(df)
    
    # 정답(O:) 비율 계산 (단순 예시: 1번 문항 기준)
    q1_correct_count = df['feedback_1'].str.startswith("O:").sum()
    correct_rate = (q1_correct_count / total_submissions) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("참여 학생 수", f"{total_students}명")
    col2.metric("총 제출 건수", f"{total_submissions}건")
    col3.metric("문항1 정답률", f"{correct_rate:.1f}%")

    st.divider()

    # 6. 필터 및 검색
    st.subheader("🔍 상세 답안 조회")
    search_id = st.text_input("학번으로 검색", "")
    
    filtered_df = df
    if search_id:
        filtered_df = df[df['student_id'].str.contains(search_id)]

    # 7. 메인 데이터 테이블
    # 교사가 보기 편하도록 주요 열만 먼저 배치
    display_cols = ['student_id', 'created_at', 'answer_1', 'feedback_1', 'answer_2', 'feedback_2', 'answer_3', 'feedback_3']
    st.dataframe(filtered_df[display_cols], use_container_width=True)

    # 8. 개별 학생 상세 보기 (Expander)
    st.subheader("📝 학생별 심층 확인")
    for index, row in filtered_df.iterrows():
        with st.expander(f"[{row['student_id']}] 제출 시간: {row['created_at']}"):
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("**[문항 1]**")
                st.info(row['answer_1'])
                st.markdown("**[문항 2]**")
                st.info(row['answer_2'])
                st.markdown("**[문항 3]**")
                st.info(row['answer_3'])
                
            with c2:
                st.markdown("**[AI 피드백 1]**")
                st.success(row['feedback_1']) if "O:" in row['feedback_1'] else st.warning(row['feedback_1'])
                st.markdown("**[AI 피드백 2]**")
                st.success(row['feedback_2']) if "O:" in row['feedback_2'] else st.warning(row['feedback_2'])
                st.markdown("**[AI 피드백 3]**")
                st.success(row['feedback_3']) if "O:" in row['feedback_3'] else st.warning(row['feedback_3'])

    # 9. 데이터 다운로드 (Excel/CSV)
    st.divider()
    st.subheader("💾 데이터 내보내기")
    
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8-sig') # 한글 깨짐 방지 cp949 대신 utf-8-sig

    csv = convert_df(df)
    st.download_button(
        label="CSV 파일로 다운로드 (엑셀 호환)",
        data=csv,
        file_name=f"submissions_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

st.sidebar.markdown("### Dashboard Info")
st.sidebar.info("이 대시보드는 Supabase 실시간 DB와 연동되어 있습니다. 학생이 제출 버튼을 누르면 즉시 반영됩니다.")
