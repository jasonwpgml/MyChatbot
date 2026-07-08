import pandas as pd
import streamlit as st


st.title("엑셀 데이터")

uploaded_file = st.file_uploader("엑셀 파일", type=["xlsx"])

if uploaded_file is None:
    st.info("엑셀 파일을 업로드하세요.")
    st.stop()

try:
    excel_file = pd.ExcelFile(uploaded_file)
except Exception as error:
    st.error(f"파일을 읽을 수 없습니다: {error}")
    st.stop()

sheet_name = st.selectbox("시트", excel_file.sheet_names)

try:
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
except Exception as error:
    st.error(f"시트 데이터를 불러올 수 없습니다: {error}")
    st.stop()

st.caption(f"{uploaded_file.name} / {sheet_name}")

col1, col2 = st.columns(2)
col1.metric("행", f"{len(df):,}")
col2.metric("열", f"{len(df.columns):,}")

if df.empty:
    st.warning("선택한 시트에 데이터가 없습니다.")
else:
    st.dataframe(df, hide_index=True)
