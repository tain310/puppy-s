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

# 💡 [핵심 비책] 앱 내 메모리에 데이터를 올려 구글 지연 없이 즉각 반응하게 만듭니다.
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

if "df_invest" not in st.session_state:
    data = sheet_invest.get_all_records()
    st.session_state["df_invest"] = pd.DataFrame(data) if data else pd.DataFrame()

# 🔄 구글 시트 웹창에서 직접 타이핑했을 때를 위한 강제 연동 버튼
if st.sidebar.button("🔄 구글시트 강제 동기화"):
    for key in ["df_living", "df_loan", "df_income", "df_invest"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

df_living = st.session_state["df_living"]
df_loan = st.session_state["df_loan"]
df_income = st.session_state["df_income"]
df_invest = st.session_state["df_invest"]

def safe_sum(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
    return 0

# 날짜 데이터를 시트 저장용 문자열로 안전하게 다듬는 함수
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

# ✍️ 사이드바 입력창 (Form 저장 즉시 내부 메모리 갱신)
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
            # ✨ 구글과 동시에 화면 메모리에도 즉각 꽂아 넣어 지연을 지웁니다.
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
            # ✨ 수입 저장 즉시 메모리에 합산하여 상단 총액을 실시간으로 바꿉니다.
            new_row = pd.DataFrame([{"날짜": pd.to_datetime(input_date), "분류": cat, "금액": amt, "메모": memo}])
            st.session_state["df_income"] = pd.concat([new_row, st.session_state["df_income"]], ignore_index=True).sort_values(by='날짜', ascending=False)
            st.rerun()

# 🗂️ 메인 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📋 생활비", "💸 대출금 현황", "💰 수입 현황", "📈 투자"])

with tab1:
    edited = st.data_editor(df_living, num_rows="dynamic", use_container_width=True, key="living_editor")
    if st.button("생활비 수정 저장"):
        sheet_living.update(values=df_to_sheet_values(edited), range_name='A1')
        st.session_state["df_living"] = edited
        st.success("저장되었습니다.")
        st.rerun()
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
    st.subheader("🎯 대출금 상환 목표: 4,150,000 원")
    progress_per = min(float(loan_paid / loan_target), 1.0) if loan_target > 0 else 0.0
    st.progress(progress_per, text=f"현재 상환율: {progress_per * 100:.1f}% (남은 금액: {loan_remaining:,} 원)")
    edited = st.data_editor(df_loan, num_rows="dynamic", use_container_width=True, key="loan_editor")
    if st.button("대출금 내역 수정 저장"):
        sheet_loan.update(values=df_to_sheet_values(edited), range_name='A1')
        st.session_state["df_loan"] = edited
        st.success("저장되었습니다.")
        st.rerun()
    if not df_loan.empty and '이름' in df_loan.columns: 
        df_user = df_loan.groupby('이름')['금액'].sum().reset_index()
        st.plotly_chart(px.pie(df_user, values='금액', names='이름', hole=0.3, title="👨‍💻 상환금 기여도 (은솔 & 강쥐)"), use_container_width=True)

with tab3:
    st.subheader("💰 수입 세부 내역 (더블클릭하여 수정 가능)")
    edited = st.data_editor(df_income, num_rows="dynamic", use_container_width=True, key="income_editor")
    if st.button("수입 내역 수정 저장"):
        sheet_income.update(values=df_to_sheet_values(edited), range_name='A1')
        st.session_state["df_income"] = edited
        st.success("저장되었습니다.")
        st.rerun()
    if not df_income.empty and '분류' in df_income.columns:
        df_inc_cat = df_income.groupby('분류')['금액'].sum().reset_index()
        st.plotly_chart(px.pie(df_inc_cat, values='금액', names='분류', hole=0.3, title="💵 수입 출처별 비중"), use_container_width=True)

with tab4:
    st.info("투자 내역은 구글 시트에서 관리됩니다. (읽기 전용)")
    st.dataframe(df_invest, use_container_width=True)
