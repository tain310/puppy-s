import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# 브라우저 탭 이름과 아이콘 강생이 테마로 변경!
st.set_page_config(page_title="강생이네 가계부", layout="wide", page_icon="🐶")

# ------------------ 🔒 비밀번호 잠금 기능 ------------------
st.sidebar.header("🔒 로그인")
user_pw = st.sidebar.text_input("비밀번호 4자리를 입력하세요", type="password")

# ★ 여기에 원하시는 비밀번호를 적어주세요! (현재는 1234)
if user_pw != "1234":
    if user_pw: # 입력은 했는데 틀린 경우
        st.sidebar.error("비밀번호가 틀렸습니다 멍! 🐾")
    st.warning("👈 왼쪽 메뉴에서 비밀번호를 입력해야 가계부가 열립니다.")
    st.stop() # 비밀번호를 맞추기 전까지는 아래 코드를 실행하지 않고 숨김

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
    # ✨ 가계부 이름 변경 완료!
    sh = gc.open("강생이네 가계부") 
    sheet_living = sh.worksheet("생활비")
    sheet_allowance = sh.worksheet("용돈")
    sheet_invest = sh.worksheet("투자")
    connection_success = True
except Exception as e:
    st.error(f"구글 시트 연결에 실패했습니다. 권한 설정을 확인해주세요! 에러 내용: {e}")
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
            sheet_living.append_row([str(date), category, amount, memo])
            st.sidebar.success("생활비 지출이 꼼꼼하게 기록되었습니다! 멍멍!")
            st.rerun()
            
    elif menu == "용돈 지출":
        st.sidebar.subheader("☕ 개인 용돈 지출")
        date = st.sidebar.date_input("날짜", datetime.today())
        user_name = st.sidebar.selectbox("이름", ["은솔", "친구"])
        amount = st.sidebar.number_input("금액 (원)", min_value=0, step=1000)
        memo = st.sidebar.text_input("메모 (예: 카페, 옷 구매)")
        
        if st.sidebar.button("용돈 기록하기"):
            sheet_allowance.append_row([str(date), user_name, amount, memo])
            st.sidebar.success("용돈 지출이 기록되었습니다!")
            st.rerun()

    # ------------------ 데이터 가져오기 및 전처리 ------------------
    df_living = pd.DataFrame(sheet_living.get_all_records())
    df_allowance = pd.DataFrame(sheet_allowance.get_all_records())
    df_invest = pd.DataFrame(sheet_invest.get_all_records())
    
    if not df_invest.empty and '평가금액' in df_invest.columns:
        df_invest['평가금액'] = pd.to_numeric(df_invest['평가금액'].astype(str).str.replace(',', '').str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
    
    living_total = df_living['금액'].sum() if not df_living.empty and '금액' in df_living.columns else 0
    allowance_total = df_allowance['금액'].sum() if not df_allowance.empty and '금액' in df_allowance.columns else 0
    invest_total = df_invest['평가금액'].sum() if not df_invest.empty and '평가금액' in df_invest.columns else 0
    
    # ------------------ 메인 화면 대시보드 ------------------
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 이번 달 총 생활비 지출", f"{living_total:,} 원")
    with col2:
        st.metric("👥 이번 달 총 용돈 지출", f"{allowance_total:,} 원", "인당 예산 40만원")
    with col3:
        st.metric("🏦 실시간 총 자산(투자) 규모", f"{int(invest_total):,} 원", "구글시트 실시간 연동 중")
        
    st.write("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 생활비 세부내역", "👥 용돈 사용 현황", "📈 실시간 자산 상태"])
    
    with tab1:
        st.subheader("공동 생활비 지출 현황")
        if not df_living.empty:
            st.dataframe(df_living, use_container_width=True)
            if '카테고리' in df_living.columns:
                df_cat = df_living.groupby('카테고리')['금액'].sum().reset_index()
                st.bar_chart(df_cat.set_index('카테고리'))
        else:
            st.info("아직 입력된 생활비 내역이 없습니다.")
            
    with tab2:
        st.subheader("은솔 & 강쥐 용돈 사용 리스트")
        if not df_allowance.empty:
            st.dataframe(df_allowance, use_container_width=True)
            if '이름' in df_allowance.columns:
                df_user = df_allowance.groupby('이름')['금액'].sum().reset_index()
                st.bar_chart(df_user.set_index('이름'))
        else:
            st.info("아직 입력된 용돈 내역이 없습니다.")
            
    with tab3:
        st.subheader("📊 여윳돈 투자 포트폴리오")
        if not df_invest.empty:
            st.dataframe(df_invest, use_container_width=True)
            if '종목명' in df_invest.columns and '평가금액' in df_invest.columns:
                df_pie = df_invest[['종목명', '평가금액']].set_index('종목명')
                st.bar_chart(df_pie)
        else:
            st.info("구글 시트 '투자' 탭에 종목과 수량을 입력하시면 실시간 자산 대시보드가 활성화됩니다.")
