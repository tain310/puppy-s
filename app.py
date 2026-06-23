import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import plotly.express as px
import time

st.set_page_config(page_title="강생이네 가계부", layout="wide", page_icon="🐶")

# 🔒 로그인
st.sidebar.header("🔒 로그인")
if st.sidebar.text_input("비밀번호 4자리", type="password", key="login_pwd") != "1234":
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

# 💡 [구조 혁명] 엉키던 캐시 함수를 3개로 완전히 찢어발겨 서로 침범할 수 없게 구획했사옵니다.
@st.cache_data(ttl=5, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_living_data(_ws):
    data = _ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["날짜", "카테고리", "결제수단", "금액", "메모"])
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=5, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_loan_data(_ws):
    data = _ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["날짜", "이름", "금액", "메모"])
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=5, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_income_data(_ws):
    data = _ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["날짜", "분류", "금액", "메모"])
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=900, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_invest_data(_ws):
    data = _ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()

# 각자 고유한 방에서 데이터를 긁어오므로 절대 섞이지 않사옵니다.
df_living = get_living_data(sheet_living)
df_loan = get_loan_data(sheet_loan)
df_income = get_income_data(sheet_income)
df_invest = get_invest_data(sheet_invest)

# 글자가 섞여도 무조건 숫자만 발라내어 더하는 독한 수식 수호
def safe_sum(df, col):
    if col in df.columns:
        cleaned = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        return pd.to_numeric(cleaned, errors='coerce').fillna(0).sum()
    return 0

def df_to_sheet_values(df):
    df_copy = df.copy()
    if '날짜' in df_copy.columns:
        df_copy['날짜'] = pd.to_datetime(df_copy['날짜'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
    return [df_copy.columns.tolist()] + df_copy.fillna("").astype(str).values.tolist()

# 🎯 계산 로직 (수입과 자산의 정밀 계수)
loan_target = 3300000
loan_paid = safe_sum(df_loan, '금액')
loan_remaining = max(0, loan_target - loan_paid)

total_income = safe_sum(df_income, '금액')
total_living = safe_sum(df_living, '금액')
total_invest = safe_sum(df_invest, '평가 금액')
total_assets = total_income + total_invest - total_living

# 📊 대시보드 요약창 (이제 수입 합계가 완벽히 따로 계산되어 꽂힙니다)
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 총 수입 현황", f"{total_income:,} 원")
col2.metric("📊 총 생활비 지출", f"{total_living:,} 원")
col3.metric("💸 대출금 상환액", f"{loan_paid:,} 원", f"남은 목표: -{loan_remaining:,} 원")
col4.metric("🏦 총 자산 규모", f"{total_assets:,} 원")

# ✍️ 사이드바 입력창 (Form 저장 즉시 고유 캐시 박멸)
st.sidebar.subheader("✍️ 장부 기록 창고")
menu = st.sidebar.radio("기록할 항목", ["생활비", "대출금 상환", "수입"], horizontal=True, key="sidebar_menu_radio")

if menu == "생활비":
    with st.sidebar.form("living_form", clear_on_submit=True):
        input_date = st.date_input("날짜 선택", datetime.today(), key="date_input_living")
        cat = st.selectbox("분류", ["정기결제", "생필품", "식비", "먼지", "교통", "룰루랄라", "기타"], key="cat_input_living")
        pay_method = st.selectbox("결제 수단", ["은솔카드", "강쥐카드", "공동체크카드", "현금", "기타페이"], key="pay_input_living")
        amt = st.number_input("금액", step=1000, key="amt_input_living")
        memo = st.text_input("메모", key="memo_input_living")
        if st.form_submit_button("저장하기"):
            # 🌟 괄호가 완벽하게 닫힌 올바른 코드이옵니다!
            sheet_living.append_row([str(input_date), cat, pay_method, amt, memo])
            get_living_data.clear() 
            time.sleep(1.5)
            st.rerun()
