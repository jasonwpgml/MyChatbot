import streamlit as st



page_1 = st.Page("page_1.py", title="홈 탭", icon="😊")
page_2 = st.Page("page_2.py", title="페이지 1", icon="🎉")
page_3 = st.Page("page_3.py", title="지도", icon="🚗")
page_4 = st.Page("page_4.py", title="엑셀 데이터", icon="📊")


pages = st.navigation([page_1, page_2, page_3, page_4], position="top")

pages.run()

