import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import plotly.express as px

st.set_page_config(page_title="강생이네 가계부", layout="wide", page_icon="🐶")

# 🔒 로그인
st.sidebar.header("🔒 로그인")
if st.sidebar.text_input("비밀번호 4자리", type="password") != "1234":
    st.warning("비밀번호를 입력하세요.")
    st.stop()

# 구글 시트 연결
@st.cache_resource
def get_gspread_client():
    creds_json = st.secrets["gcp_json_credentials"]
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = get_gspread_client()
    sh = gc.open("강생이네 가계부")
    sheet_living = sh.worksheet("생활비")
    sheet_loan = sh.worksheet("대출금") # ✨ 용돈에서 '대출금'으로 변경되었습니다.
    sheet_invest = sh.worksheet("투자")
except Exception as e:
    st.error(f"시트 연결 오류: {e}")
    st.stop()

st.title("🐶 강생이네 경제공동체")

# 데이터 불러오기 (캐시 적용)
@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_living_data(ws):
    data = ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_loan_data(ws):
    data = ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_invest_data(ws):
    data = ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()

df_living = get_living_data(sheet_living)
df_loan = get_loan_data(sheet_loan)
df_invest = get_invest_data(sheet_invest)

def safe_sum(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
    return 0

# 🎯 대출금 목표 및 차액 계산 로직
loan_target = 3300000
loan_paid = safe_sum(df_loan, '금액')
loan_remaining = max(0, loan_target - loan_paid)

# 대시보드
col1, col2, col3 = st.columns(3)
col1.metric("📊 총 생활비", f"{safe_sum(df_living, '금액'):,} 원")
# 💸 대출 상환액을 보여주고, 하단 우측에 남은 차액을 표시합니다.
col2.metric("💸 대출금 상환액", f"{loan_paid:,} 원", f"남은 목표: -{loan_remaining:,} 원")
col3.metric("🏦 총 자산", f"{safe_sum(df_invest, '평가 금액'):,} 원")

# 사이드바 입력
menu = st.sidebar.selectbox("기록", ["생활비 입력", "대출금 상환 입력"])
input_date = st.sidebar.date_input("날짜 선택", datetime.today())

if menu == "생활비 입력":
    cat = st.sidebar.selectbox("분류", ["정기결제", "생필품", "식비", "먼지", "교통", "룰루랄라", "기타"])
    amt = st.sidebar.number_input("금액", step=1000)
    memo = st.sidebar.text_input("메모")
    if st.sidebar.button("저장"):
        sheet_living.append_row([str(input_date), cat, amt, memo])
        st.rerun()
elif menu == "대출금 상환 입력":
    who = st.sidebar.selectbox("상환자", ["은솔", "강쥐"])
    amt = st.sidebar.number_input("상환 금액", step=1000)
    memo = st.sidebar.text_input("메모")
    if st.sidebar.button("저장"):
        sheet_loan.append_row([str(input_date), who, amt, memo])
        st.rerun()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📋 생활비", "💸 대출금 현황", "📈 투자"])

with tab1:
    edited = st.data_editor(df_living, num_rows="dynamic", use_container_width=True, key="living_editor")
    if st.button("생활비 수정 저장"):
        sheet_living.update(values=[edited.columns.tolist()] + edited.astype(str).values.tolist(), range_name='A1')
        st.success("저장되었습니다.")
        st.rerun()
    if not df_living.empty and '카테고리' in df_living.columns: 
        st.plotly_chart(px.pie(df_living.groupby('카테고리')['금액'].sum().reset_index(), values='금액', names='카테고리', hole=0.3))

with tab2:
    st.subheader("🎯 대출금 상환 목표: 3,300,000 원")
    
    # 📈 실시간 달성률 프로그레스 바 추가
    progress_per = min(float(loan_paid / loan_target), 1.0) if loan_target > 0 else 0.0
    st.progress(progress_per, text=f"현재 상환율: {progress_per * 100:.1f}% (남은 금액: {loan_remaining:,} 원)")
    
    edited = st.data_editor(df_loan, num_rows="dynamic", use_container_width=True, key="loan_editor")
    if st.button("대출금 내역 수정 저장"):
        sheet_loan.update(values=[edited.columns.tolist()] + edited.astype(str).values.tolist(), range_name='A1')
        st.success("저장되었습니다.")
        st.rerun()
        
    if not df_loan.empty and '이름' in df_loan.columns: 
        df_user = df_loan.groupby('이름')['금액'].sum().reset_index()
        fig = px.pie(df_user, values='금액', names='이름', hole=0.3, title="👨‍💻 상환금 기여도 (은솔 & 강쥐)")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.info("투자 내역은 구글 시트에서 관리됩니다. (읽기 전용)")
    st.dataframe(df_invest, use_container_width=True)
