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
    sheet_loan = sh.worksheet("대출금")
    sheet_invest = sh.worksheet("투자")
except Exception as e:
    st.error(f"시트 연결 오류: {e}")
    st.stop()

st.title("🐶 강생이네 경제공동체")

# 데이터 불러오기
@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_living_data(_ws):
    data = _ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_loan_data(_ws):
    data = _ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_invest_data(_ws):
    data = _ws.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()

df_living = get_living_data(sheet_living)
df_loan = get_loan_data(sheet_loan)
df_invest = get_invest_data(sheet_invest)

def safe_sum(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
    return 0

# 🎯 대출금 목표 계산
loan_target = 3600000
loan_paid = safe_sum(df_loan, '금액')
loan_remaining = max(0, loan_target - loan_paid)

# 대시보드
col1, col2, col3 = st.columns(3)
col1.metric("📊 총 생활비", f"{safe_sum(df_living, '금액'):,} 원")
col2.metric("💸 대출금 상환액", f"{loan_paid:,} 원", f"남은 목표: -{loan_remaining:,} 원")
col3.metric("🏦 총 자산", f"{safe_sum(df_invest, '평가 금액'):,} 원")

# ✍️ 사이드바 입력창
st.sidebar.subheader("✍️ 지출 및 상환 기록")
menu = st.sidebar.radio("기록할 항목", ["생활비", "대출금 상환"], horizontal=True)

if menu == "생활비":
    with st.sidebar.form("living_form", clear_on_submit=True):
        input_date = st.date_input("날짜 선택", datetime.today())
        cat = st.selectbox("분류", ["정기결제", "생필품", "식비", "먼지", "교통", "룰루랄라", "기타"])
        # ✨ 결제 수단을 고르는 곳이옵니다! (필요하시면 이름들을 마음껏 바꾸시옵소서)
        pay_method = st.selectbox("결제 수단", ["은솔카드", "강쥐카드", "공동체크카드", "현금", "기타페이"])
        amt = st.number_input("금액", step=1000)
        memo = st.text_input("메모")
        
        if st.form_submit_button("저장하기"):
            # 구글 시트 1행의 순서와 똑같이 5개의 정보를 담아 보냅니다.
            sheet_living.append_row([str(input_date), cat, pay_method, amt, memo])
            get_living_data.clear()  
            time.sleep(1.5)  
            st.rerun()       

elif menu == "대출금 상환":
    with st.sidebar.form("loan_form", clear_on_submit=True):
        input_date = st.date_input("날짜 선택", datetime.today())
        who = st.selectbox("상환자", ["은솔", "강쥐"])
        amt = st.number_input("상환 금액", step=1000)
        memo = st.text_input("메모")
        
        if st.form_submit_button("저장하기"):
            sheet_loan.append_row([str(input_date), who, amt, memo])
            get_loan_data.clear()
            time.sleep(1.5)
            st.rerun()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📋 생활비", "💸 대출금 현황", "📈 투자"])

with tab1:
    edited = st.data_editor(df_living, num_rows="dynamic", use_container_width=True, key="living_editor")
    if st.button("생활비 수정 저장"):
        sheet_living.update(values=[edited.columns.tolist()] + edited.astype(str).values.tolist(), range_name='A1')
        get_living_data.clear()
        time.sleep(1.5)
        st.success("저장되었습니다.")
        st.rerun()
        
    # ✨ 그래프를 나란히 두 개 띄우기 위해 공간을 반으로 나누었사옵니다.
    if not df_living.empty:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            if '카테고리' in df_living.columns: 
                df_cat = df_living.groupby('카테고리')['금액'].sum().reset_index()
                st.plotly_chart(px.pie(df_cat, values='금액', names='카테고리', hole=0.3, title="🛒 카테고리별 지출"), use_container_width=True)
                
        with col_chart2:
            if '결제수단' in df_living.columns: 
                df_pay = df_living.groupby('결제수단')['금액'].sum().reset_index()
                st.plotly_chart(px.pie(df_pay, values='금액', names='결제수단', hole=0.3, title="💳 결제 수단별 지출"), use_container_width=True)

with tab2:
    st.subheader("🎯 대출금 상환 목표: 3,600,000 원")
    progress_per = min(float(loan_paid / loan_target), 1.0) if loan_target > 0 else 0.0
    st.progress(progress_per, text=f"현재 상환율: {progress_per * 100:.1f}% (남은 금액: {loan_remaining:,} 원)")
    
    edited = st.data_editor(df_loan, num_rows="dynamic", use_container_width=True, key="loan_editor")
    if st.button("대출금 내역 수정 저장"):
        sheet_loan.update(values=[edited.columns.tolist()] + edited.astype(str).values.tolist(), range_name='A1')
        get_loan_data.clear()
        time.sleep(1.5)
        st.success("저장되었습니다.")
        st.rerun()
        
    if not df_loan.empty and '이름' in df_loan.columns: 
        df_user = df_loan.groupby('이름')['금액'].sum().reset_index()
        st.plotly_chart(px.pie(df_user, values='금액', names='이름', hole=0.3, title="👨‍💻 상환금 기여도 (은솔 & 강쥐)"), use_container_width=True)

with tab3:
    st.info("투자 내역은 구글 시트에서 관리됩니다. (읽기 전용)")
    st.dataframe(df_invest, use_container_width=True)
