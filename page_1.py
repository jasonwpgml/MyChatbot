import os
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

import database as db

DEFAULT_ROOM_NAME = "기본 채팅방"

# 선택 가능한 GPT 모델 목록 (첫 번째가 기본값)
AVAILABLE_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-4.1",
]


def format_time(utc_str):
    """DB의 UTC 시각 문자열을 로컬 시간 'YYYY-MM-DD HH:MM' 형식으로 변환한다."""
    dt = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


st.title("💬 AI 챗봇")
st.caption("저의 챗봇과 이야기를 나눠 보세요. 대화는 SQLite에 저장되어 다시 실행해도 유지됩니다.")

load_dotenv()
db.init_db()

# --- API 키 확인 (요구사항 1-5) ---
if not os.getenv("OPENAI_API_KEY"):
    st.error(
        "OPENAI_API_KEY가 설정되지 않았습니다.\n\n"
        "프로젝트 폴더에 `.env` 파일을 만들고 키를 입력해 주세요. "
        "(`.env.example` 참고)"
    )
    st.stop()

client = OpenAI()

# --- 기본 채팅방이 없으면 자동 생성 (기본 채팅방은 항상 존재) ---
rooms = db.get_chat_rooms()
if not any(room["name"] == DEFAULT_ROOM_NAME for room in rooms):
    db.create_chat_room(DEFAULT_ROOM_NAME)
    rooms = db.get_chat_rooms()

room_ids = [room["id"] for room in rooms]
room_names = {room["id"]: room["name"] for room in rooms}

# 선택된 채팅방 id는 session_state에 보관한다.
# (삭제 등으로 더 이상 존재하지 않으면 첫 번째 방으로 되돌린다)
if (
    "current_room_id" not in st.session_state
    or st.session_state.current_room_id not in room_ids
):
    st.session_state.current_room_id = room_ids[0]

# --- 사이드바: 모델 선택 + 채팅방 관리 (요구사항 4, 5) ---
with st.sidebar:
    st.header("모델 설정")
    gpt_model = st.selectbox("사용할 GPT 모델", AVAILABLE_MODELS)

    st.divider()

    st.header("채팅방 관리")

    # 1. 새로운 채팅방 생성
    new_name = st.text_input("새 채팅방 이름", placeholder="예: 파이썬 공부방")
    if st.button("➕ 채팅방 생성", use_container_width=True):
        if new_name.strip():
            new_id = db.create_chat_room(new_name.strip())
            st.session_state.current_room_id = new_id
            st.rerun()
        else:
            st.warning("채팅방 이름을 입력해 주세요.")

    st.divider()

    # 2~4. 채팅방 목록 조회 / 선택 / 이전 대화 불러오기
    selected_id = st.radio(
        "채팅방 목록",
        room_ids,
        index=room_ids.index(st.session_state.current_room_id),
        format_func=lambda rid: room_names[rid],
    )
    st.session_state.current_room_id = selected_id

    st.divider()

    # 대화 전체 비우기: 메시지만 삭제, 채팅방은 유지 (요구사항 5)
    if st.button("🧹 대화 전체 비우기", use_container_width=True):
        db.clear_messages(selected_id)
        st.rerun()

    # 채팅방 삭제: 방과 소속 메시지를 함께 삭제 (요구사항 4-5)
    # 단, 기본 채팅방은 삭제할 수 없다.
    is_default_room = room_names[selected_id] == DEFAULT_ROOM_NAME
    if st.button(
        "🗑️ 채팅방 삭제",
        use_container_width=True,
        disabled=is_default_room,
        help="기본 채팅방은 삭제할 수 없습니다." if is_default_room else None,
    ):
        db.delete_chat_room(selected_id)
        del st.session_state["current_room_id"]
        st.rerun()

# --- 현재 채팅방의 대화 표시 ---
# 화면의 기준은 session_state가 아니라 항상 DB다. (요구사항 2, 6)
current_room_id = st.session_state.current_room_id
st.subheader(f"🗨️ {room_names[current_room_id]}")

for message in db.get_messages(current_room_id):
    # AI 답변/오류에는 어떤 모델이 생성했는지 시간과 함께 표시한다.
    caption = format_time(message["create_date"])
    if message["model"]:
        caption = f"{message['model']} · {caption}"

    if message["role"] == "error":
        # API 호출 실패 기록도 대화의 일부로 표시한다.
        with st.chat_message("assistant", avatar="⚠️"):
            st.error(message["content"])
            st.caption(caption)
    else:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            st.caption(caption)

# --- 사용자 입력 → 저장 → 문맥 포함 API 호출 → 답변 저장 (요구사항 1, 3) ---
prompt = st.chat_input("무엇을 도와드릴까요?")

if prompt:
    # 1) 사용자 메시지를 DB에 저장하고 화면에 표시
    db.add_message(current_room_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)
        st.caption(datetime.now().strftime("%Y-%m-%d %H:%M"))

    # 2) 현재 채팅방의 전체 대화 이력을 API에 전달하여 문맥 유지
    #    (오류 기록은 대화 문맥이 아니므로 제외)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in db.get_messages(current_room_id)
        if m["role"] in ("user", "assistant")
    ]

    with st.chat_message("assistant"):
        with st.spinner("답변을 생성하는 중입니다..."):
            try:
                response = client.responses.create(
                    model=gpt_model,
                    input=history,
                )
                answer = response.output_text
            except Exception as error:
                # 오류 내용도 메시지로 저장해 대화 기록에 남긴다.
                error_text = f"API 호출에 실패했습니다: {error}"
                db.add_message(current_room_id, "error", error_text, model=gpt_model)
                st.error(error_text)
                st.stop()
        st.markdown(answer)
        st.caption(f"{gpt_model} · " + datetime.now().strftime("%Y-%m-%d %H:%M"))

    # 3) AI 답변도 어떤 모델이 생성했는지와 함께 DB에 저장
    db.add_message(current_room_id, "assistant", answer, model=gpt_model)
