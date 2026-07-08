import streamlit as st


st.title("홈")

st.write("Hello, World!")

st.header("Text Elements")

st.markdown("Hello **world!**")


##############

from openai import OpenAI
from dotenv import load_dotenv

# 닷env
load_dotenv()

# LLM 호출 
client = OpenAI()

# 모델 호출해서 연결 잘 됐는지 확인
models = client.models.list()

with st.chat_message("assistant"):
    st.markdown("API key 연결 성공: " + str(models.data[0].id))
    st.markdown("반갑습니다.")

# 챗봇에 쓸 메세지 리스트 session_state에 최초 1회 생성
if "messages" not in st.session_state:
    st.session_state.messages = []

# 
for message in st.session_state.messages :
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("무엇을 도와드릴까요?", submit_mode="disable")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("답변을 생성하는 중입니다."):
            response = client.responses.create(
                model="gpt-4o-mini",
                input=prompt,
            )
        st.markdown(response.output_text)

    st.session_state.messages.append(
        {"role": "assistant", "content": response.output_text}
    )
