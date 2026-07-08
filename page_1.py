import streamlit as st


st.title("홈")

st.write("Hello, World!")

st.header("Text Elements")

st.markdown("Hello **world!**")


##############

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client = OpenAI()

# 모델 호출해서 연결 잘 됐는지 확인
models = client.models.list()

with st.chat_message("ai"):
    st.markdown("API key 연결 성공")
    st.markdown(models.data[0].id)
    st.markdown("반갑습니다.")

if "messages" not in st.session_state:
    st.session_state.messages = []

prompt = st.chat_input("무엇을 도와드릴까요?")

if prompt:
    response = client.responses.create(
        model = "gpt-4o-mini",
        input = prompt
    )

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "ai", "content": response.output_text})

for message in st.session_state.messages :
    with st.chat_message(message["role"]):
        st.markdown(message["content"])