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

st.title("🐶 강생이네 가계부")

# 데이터 불러오기 (캐시 오류 방지)
@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_living_data(ws):
    data = ws.get_all_records()
    df = pd.DataFrame(data) if data else pd.DataFrame()
    if not df.empty and '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.sort_values(by='날짜', ascending=False)
    return df

@st.cache_data(ttl=600, hash_funcs={"gspread.worksheet.Worksheet": lambda _: None})
def get_allowance_data(ws):
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

# 데이터 호출
df_living = get_living_data(sheet_living)
df_allowance = get_allowance_data(sheet_allowance)
df_invest = get_invest_data(sheet_invest)

# (중략 - 대시보드 및 사이드바 입력 코드는 동일하게 유지)

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📋 생활비", "👥 용돈", "📈 투자"])

with tab1:
    edited = st.data_editor(df_living, num_rows="dynamic", use_container_width=True, key="living_editor")
    if st.button("생활비 수정 저장"):
        sheet_living.update(values=[edited.columns.tolist()] + edited.astype(str).values.tolist(), range_name='A1')
        st.success("저장되었습니다.")
        st.rerun()
    if not df_living.empty and '카테고리' in df_living.columns: 
        st.plotly_chart(px.pie(df_living.groupby('카테고리')['금액'].sum().reset_index(), values='금액', names='카테고리', hole=0.3))

with tab2:
    # 🌟 이제 용돈 데이터를 정확히 보여줍니다.
    edited = st.data_editor(df_allowance, num_rows="dynamic", use_container_width=True, key="allowance_editor")
    if st.button("용돈 수정 저장"):
        sheet_allowance.update(values=[edited.columns.tolist()] + edited.astype(str).values.tolist(), range_name='A1')
        st.success("저장되었습니다.")
        st.rerun()
    if not df_allowance.empty and '이름' in df_allowance.columns: 
        st.plotly_chart(px.pie(df_allowance.groupby('이름')['금액'].sum().reset_index(), values='금액', names='이름', hole=0.3))

with tab3:
    # 🌟 이제 투자 데이터를 정확히 보여줍니다.
    st.dataframe(df_invest, use_container_width=True, key="invest_df")
