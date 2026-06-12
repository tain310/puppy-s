import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

st.set_page_config(page_title="강생이네 가계부", layout="wide", page_icon="🐶")

# 🔒 비밀번호 잠금
st.sidebar.header("🔒 로그인")
user_pw = st.sidebar.text_input("비밀번호 4자리", type="password")
if user_pw != "1234":
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
    st.error(f"연결 오류: {e}")
    st.stop()

st.title("🐶 강생이네 경제공동체")

# 데이터 불러오기
df_living = pd.DataFrame(sheet_living.get_all_records())
df_allowance = pd.DataFrame(sheet_allowance.get_all_records())
df_invest = pd.DataFrame(sheet_invest.get_all_records())

# 숫자 계산용 데이터 전처리
def clean_num(df, col):
    return pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# 대시보드 요약
col1, col2, col3 = st.columns(3)
col1.metric("📊 총 생활비", f"{clean_num(df_living, '금액').sum():,} 원")
col2.metric("👥 총 용돈", f"{clean_num(df_allowance, '금액').sum():,} 원")
col3.metric("🏦 총 자산", f"{clean_num(df_invest, '평가금액').sum():,} 원")

# 사이드바 입력
menu = st.sidebar.selectbox("메뉴", ["생활비 입력", "용돈 입력"])
if menu == "생활비 입력":
    cat = st.sidebar.selectbox("분류", ["대출이자", "관리비", "식비", "기타"])
    amt = st.sidebar.number_input("금액", step=1000)
    if st.sidebar.button("입력"):
        sheet_living.append_row([str(datetime.today().date()), cat, amt, ""])
        st.rerun()
elif menu == "용돈 입력":
    who = st.sidebar.selectbox("이름", ["은솔", "강쥐"])
    amt = st.sidebar.number_input("금액", step=1000)
    if st.sidebar.button("입력"):
        sheet_allowance.append_row([str(datetime.today().date()), who, amt, ""])
        st.rerun()

# 탭 구성 (그래프 포함)
tab1, tab2, tab3 = st.tabs(["📋 생활비", "👥 용돈", "📈 투자"])

with tab1:
    edited = st.data_editor(df_living, num_rows="dynamic")
    if st.button("생활비 저장"):
        sheet_living.clear()
        sheet_living.update([edited.columns.values.tolist()] + edited.fillna("").values.tolist())
        st.rerun()
    if not df_living.empty: st.bar_chart(df_living.groupby('카테고리')['금액'].sum())

with tab2:
    edited = st.data_editor(df_allowance, num_rows="dynamic")
    if st.button("용돈 저장"):
        sheet_allowance.clear()
        sheet_allowance.update([edited.columns.values.tolist()] + edited.fillna("").values.tolist())
        st.rerun()
    if not df_allowance.empty: st.bar_chart(df_allowance.groupby('이름')['금액'].sum())

with tab3:
    st.dataframe(df_invest)
