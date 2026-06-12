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
    st.warning("로그인하세요.")
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

# 사이드바 입력
menu = st.sidebar.selectbox("메뉴", ["생활비 입력", "용돈 입력"])
if menu == "생활비 입력":
    date = st.sidebar.date_input("날짜", datetime.today())
    cat = st.sidebar.selectbox("분류", ["대출이자", "관리비", "식비", "기타"])
    amt = st.sidebar.number_input("금액", step=1000)
    if st.sidebar.button("입력"):
        sheet_living.append_row([str(date), cat, amt, ""])
        st.rerun()

elif menu == "용돈 입력":
    date = st.sidebar.date_input("날짜", datetime.today())
    who = st.sidebar.selectbox("이름", ["은솔", "강쥐"])
    amt = st.sidebar.number_input("금액", step=1000)
    if st.sidebar.button("입력"):
        sheet_allowance.append_row([str(date), who, amt, ""])
        st.rerun()

# 메인 화면
tab1, tab2, tab3 = st.tabs(["생활비", "용돈", "투자"])
with tab1:
    df = pd.DataFrame(sheet_living.get_all_records())
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("생활비 저장"):
        sheet_living.clear()
        sheet_living.update([edited.columns.values.tolist()] + edited.fillna("").values.tolist())
        st.rerun()
with tab2:
    df = pd.DataFrame(sheet_allowance.get_all_records())
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("용돈 저장"):
        sheet_allowance.clear()
        sheet_allowance.update([edited.columns.values.tolist()] + edited.fillna("").values.tolist())
        st.rerun()
with tab3:
    st.dataframe(pd.DataFrame(sheet_invest.get_all_records()))
