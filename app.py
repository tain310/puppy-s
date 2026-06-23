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
    sheet_loan = sh.worksheet("대출금")
    sheet_income = sh.worksheet("수입")
    sheet_invest = sh.worksheet("투자")
except Exception as e:
    st.error(f"시트 연결 오류: {e}")
    st.stop()

st.title("🐶 강생이네 경제공동체")

# 💡 [핵심 비책 1] 지출, 수입, 대출은 즉각 반응하도록 앱 내 메모리에 저장합니다.
if "df_living" not in st.session_state:
    data = sheet_living.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["날짜", "카테고리", "결제수단", "금액", "메모"])
    if '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    st.session_state["df_living"] = df

if "df_loan" not in st.session_state:
    data = sheet_loan.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["날짜", "이름", "금액", "메모"])
    if '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    st.session_state["df_loan"] = df

if "df_income" not in st.session_state:
    data = sheet_income.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["날짜", "분류", "금액", "메모"])
    if '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    st.session_state["df_income"] = df

# 💡 [핵심 비책 2] 투자 시트는 15분(900초)마다 자동으로 구글에서 최신 시세를 읽어오게 합니다.
@st.cache_data(ttl=900, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_invest_data(_ws):
    data = _ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()

df_invest = get_invest_data(sheet_invest)

# 🔄 구글 시트 웹창에서 직접 타이핑했을 때를 위한 강제 연동 버튼
if st.sidebar.button("🔄 구글시트 강제 동기화"):
    for key in ["df_living", "df_loan", "df_income"]:
        if key in st.session_state:
            del st.session_state[key]
    get_invest_data.clear() # 투자 시트의 옛 기억도 함께 날립니다!
    st.rerun()

df_living = st.session_state["df_living"]
df_loan = st.session_state["df_loan"]
df_income = st.session_state["df_income"]

def safe_sum(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
    return 0

def df_to_sheet_values(df):
    df_copy = df.copy()
    if '날짜' in df_copy.columns:
        df_copy['날짜'] = pd.to_datetime(df_copy['날짜'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
    return [df_copy.columns.tolist()] + df_copy.fillna("").astype(str).values.tolist()

# 🎯 계산 로직
loan_target = 4150000
loan_paid = safe_sum(df_loan, '금액')
loan_remaining = max(0, loan_target - loan_paid)

total_income = safe_sum(df_income, '금액')
total_living = safe_sum(df_living, '금액')
total_invest = safe_sum(df_invest, '평가 금액')
total_assets = total_income + total_invest - total_living

# 📊 대시보드 요약창
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 총 수입 현황", f"{total_income:,} 원")
col2.metric("📊 총 생활비 지출", f"{total_living:,} 원")
col3.metric("💸 대출금 상환액", f"{loan_paid:,} 원", f"남은 목표: -{loan_remaining:,} 원")
col4.metric("🏦 총 자산 규모", f"{total_assets:,} 원")

# ✍️ 사이드바 입력창
st.sidebar.subheader("✍️ 장부 기록 창고")
menu = st.sidebar.radio("기록할 항목", ["생활비", "대출금 상환", "수입"], horizontal=True)

if menu == "생활비":
    with st.sidebar.form("living_form", clear_on_submit=True):
        input_date = st.date_input("날짜 선택", datetime.today())
        cat = st.selectbox("분류", ["정기결제", "생필품", "식비", "먼지", "교통", "룰루랄라", "기타"])
        pay_method = st.selectbox("결제 수단", ["은솔카드", "강쥐카드", "공동체크카드", "현금", "기타페이"])
        amt = st.number_input("금액", step=1000)
        memo = st.text_input("메모")
        if st.form_submit_button("저장하기"):
            sheet_living.append_row([str(input_date), cat, pay_method, amt, memo])
            new_row = pd.DataFrame([{"날짜": pd.to_datetime(input_date), "카테고리": cat, "결제수단": pay_method, "금액": amt, "메모": memo}])
            st.session_state["df_living"] = pd.concat([new_row, st.session_state["df_living"]], ignore_index=True).sort_values(by='날짜', ascending=False)
            st.rerun()       

elif menu == "대출금 상환":
    with st.sidebar.form("loan_form", clear_on_submit=True):
        input_date = st.date_input("날짜 선택", datetime.today())
        who = st.selectbox("상환자", ["은솔", "강쥐"])
        amt = st.number_input("상환 금액", step=1000)
        memo = st.text_input("메모")
        if st.form_submit_button("저장하기"):
            sheet_loan.append_row([str(input_date), who, amt, memo])
            new_row = pd.DataFrame([{"날짜": pd.to_datetime(input_date), "이름": who, "금액": amt, "메모": memo}])
            st.session_state["df_loan"] = pd.concat([new_row, st.session_state["df_loan"]], ignore_index=True).sort_values(by='날짜', ascending=False)
            st.rerun()

elif menu == "수입":
    with st.sidebar.form("income_form", clear_on_submit=True):
        input_date = st.date_input("날짜 선택", datetime.today())
        cat = st.selectbox("수입 분류", ["월급", "보너스", "부수입", "당근마켓", "기타"])
        amt = st.number_input("수입 금액", step=1000)
        memo = st.text_input("메모")
        if st.form_submit_button("저장하기"):
            sheet_income.append_row([str(input_date), cat, amt, memo])
            new_row
