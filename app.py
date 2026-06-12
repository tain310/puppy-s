import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

st.set_page_config(page_title="강생이네 가계부", layout="wide", page_icon="🐶")

# ------------------ 🔒 비밀번호 잠금 기능 ------------------
st.sidebar.header("🔒 로그인")
user_pw = st.sidebar.text_input("비밀번호 4자리를 입력하세요", type="password")

if user_pw != "1234":
    if user_pw:
        st.sidebar.error("비밀번호가 틀렸습니다 멍! 🐾")
    st.warning("👈 왼쪽 메뉴에서 비밀번호를 입력해야 가계부가 열립니다.")
    st.stop()

st.sidebar.success("로그인 성공! 환영합니다 뼈다귀 🦴")
st.sidebar.write("---")

# ------------------ 구글 시트 안전하게 연결 ------------------
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
    connection_success = True
except Exception as e:
    st.error(f"구글 시트 연결에 실패했습니다. 에러 내용: {e}")
    connection_success = False

if connection_success:
    st.title("🐶 강생이네 경제공동체 가계부")
    
    # ------------------ 사이드바 입력창 ------------------
    st.sidebar.header("📊 지출 기록창")
    menu = st.sidebar.selectbox("기록할 항목", ["생활비 지출", "용돈 지출"])
    
    if menu == "생활비 지출":
        st.sidebar.subheader("💸 공동 생활비 입력")
        date = st.sidebar.date_input("날짜", datetime.today())
        category = st.sidebar.selectbox("카테고리", ["아파트 대출 이자", "관리비", "식비", "구독료", "핸드폰 비용", "기타 지출"])
        amount = st.sidebar.number_input("금액 (원)", min_value=0, step=1000)
        memo = st.sidebar.text_input("메모 (예: 이마트 장보기)")
        
        if st.sidebar.button("생활비 기록하기"):
            sheet_living.append_row([str(date), category,
