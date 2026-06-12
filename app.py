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
if st.sidebar.text_input("비밀번호 4자리", type="password") != "1117":
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
    sheet_allowance = sh.worksheet("용돈")
    sheet_invest = sh.worksheet("투자")
except Exception as e:
    st.error(f"시트 연결 오류: {e}")
    st.stop()

st.title("🐶 강생이네 경제공동체")

# 데이터 불러오기 함수 (강제 새로고침 포함)
def get_fresh_data(ws):
    data = ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

df_living = get_fresh_data(sheet_living)
df_allowance = get_fresh_data(sheet_allowance)
df_invest = get_fresh_data(sheet_invest)

def safe_sum(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
    return 0

# 대시보드
col1, col2, col3 = st.columns(3)
col1.metric("📊 총 생활비", f"{safe_sum(df_living, '금액'):,} 원")
col2.metric("👥 총 용돈", f"{safe_sum(df_allowance, '금액'):,} 원")
col3.metric("🏦 총 자산", f"{safe_sum(df_invest, '평가 금액'):,} 원")

# 사이드바 입력
menu = st.sidebar.selectbox("기록", ["생활비 입력", "용돈 입력"])
input_date = st.sidebar.date_input("날짜 선택", datetime.today())

if menu == "생활비 입력":
    cat = st.sidebar.selectbox("분류", ["정기결제", "생필품", "식비", "먼지", "교통", "룰루랄라", "기타"])
    amt = st.sidebar.number_input("금액", step=1000)
    memo = st.sidebar.text_input("메모")
    if st.sidebar.button("저장"):
        sheet_living.append_row([str(input_date), cat, amt, memo])
        st.rerun()
elif menu == "용돈 입력":
    who = st.sidebar.selectbox("이름", ["은솔", "강쥐"])
    amt = st.sidebar.number_input("금액", step=1000)
    memo = st.sidebar.text_input("메모")
    if st.sidebar.button("저장"):
        sheet_allowance.append_row([str(input_date), who, amt, memo])
        st.rerun()

# 탭 구성 및 업데이트 로직 (데이터 덮어쓰기 방식)
tab1, tab2, tab3 = st.tabs(["📋 생활비", "👥 용돈", "📈 투자"])

with tab1:
    edited = st.data_editor(df_living, num_rows="dynamic", use_container_width=True)
    if st.button("생활비 수정 저장"):
        sheet_living.update([edited.columns.values.tolist()] + edited.fillna("").values.tolist())
        st.success("저장되었습니다.")
        st.rerun() # 수정 후 바로 전체 새로고침
    if not df_living.empty and '카테고리' in df_living.columns: 
        st.plotly_chart(px.pie(df_living.groupby('카테고리')['금액'].sum().reset_index(), values='금액', names='카테고리', hole=0.3))

with tab2:
    edited = st.data_editor(df_allowance, num_rows="dynamic", use_container_width=True)
    if st.button("용돈 수정 저장"):
        sheet_allowance.update([edited.columns.values.tolist()] + edited.fillna("").values.tolist())
        st.success("저장되었습니다.")
        st.rerun() # 수정 후 바로 전체 새로고침
    if not df_allowance.empty and '이름' in df_allowance.columns: 
        st.plotly_chart(px.pie(df_allowance.groupby('이름')['금액'].sum().reset_index(), values='금액', names='이름', hole=0.3))

with tab3:
    st.info("투자 내역은 구글 시트에서 관리됩니다.")
    st.dataframe(df_invest, use_container_width=True)
