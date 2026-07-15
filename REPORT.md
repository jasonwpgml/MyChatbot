# REPORT — Streamlit AI 챗봇 미니 프로젝트

## 1. Agent 활용 과정

### Agent에게 전달한 주요 요구사항

- 요구사항 명세서(README)와 ERD 예시 사진을 전달하고, 채팅방–메시지 구조의 ERD 설계를 요청했다.
- 설계된 ERD와 README를 기반으로 단계별 구현 계획을 먼저 세우게 한 뒤, 계획을 검토하고 구현을 지시했다.
- OpenAI API 연동, SQLite 영구 저장, 사이드바 채팅방 관리(생성/선택/삭제/비우기), 오류 처리를 필수 조건으로 명시했다.

### Agent와 주고받으며 구현한 과정

1. **ERD 설계**: Agent가 `chat_room`(1) : `message`(N) 구조의 ERD를 Mermaid와 draw.io 파일로 작성했다. 채팅방 삭제 시 메시지가 함께 삭제되도록 FK에 `ON DELETE CASCADE`를 두는 설계를 채택했다.
2. **구현 계획 수립**: Agent가 기존 코드(`page_1.py`의 session_state 기반 챗봇)를 분석하고, DB 계층 분리 → 챗봇 페이지 개편 → 부속 파일 → 검증 순서의 계획을 제시했다.
3. **구현**: 계획대로 `database.py`(DB 계층)와 `page_1.py`(챗봇 UI)를 구현했다.

### Agent가 만든 결과를 직접 검토하거나 수정한 내용

- 기존 코드에 있던 `client.models.list()` 연결 확인 호출이 매 rerun마다 실행되어 불필요한 API 호출이 발생하는 문제를 확인하고 제거했다.
- 메시지 정렬 기준을 `create_date`가 아닌 `id`로 하는 이유(같은 초에 저장된 사용자 메시지와 AI 답변의 순서 보장)를 확인했다.
- 제출물에 SQLite DB 파일은 포함해야 하므로 `.gitignore`에 `chatbot.db`를 넣지 않고 `.env`만 제외하도록 검토했다.

---

## 2. 새롭게 배운 내용

- **SQLite 외래 키**: SQLite는 FK 제약이 기본적으로 꺼져 있어서, 연결마다 `PRAGMA foreign_keys = ON`을 실행해야 `ON DELETE CASCADE`가 동작한다.
- **Streamlit의 rerun 모델**: 버튼 클릭, 채팅 입력 등 모든 상호작용마다 스크립트 전체가 위에서부터 다시 실행된다. 따라서 "화면에 보이는 대화"를 변수에 들고 있는 게 아니라, 매 실행마다 DB에서 다시 조회하는 구조가 자연스럽고 안전하다.
- **OpenAI Responses API**: `input`에 문자열 하나가 아니라 `[{"role": ..., "content": ...}, ...]` 형태의 대화 이력 리스트를 넘기면 문맥이 유지된 답변을 받을 수 있다.
- **session_state의 올바른 용도**: 대화 내용 전체가 아니라 "현재 선택된 채팅방 id" 같은 최소한의 UI 상태만 보관하는 것이 화면과 DB의 불일치를 막는 방법이다.

---

## 3. 프로그램 동작 원리

### Streamlit이 코드를 다시 실행하는 방식과 화면 상태 관리

Streamlit은 사용자가 입력하거나 버튼을 누를 때마다 페이지 스크립트를 처음부터 끝까지 다시 실행한다. 이때 일반 변수는 초기화되지만 `st.session_state`는 유지된다. 이 프로젝트에서는 `st.session_state.current_room_id`(선택된 채팅방)만 유지하고, 대화 내용은 매 실행마다 `db.get_messages()`로 DB에서 조회한다. 그래서 채팅방 생성·삭제·비우기 후 `st.rerun()`만 호출하면 화면이 항상 DB의 최신 상태로 갱신된다.

### 채팅방과 메시지 테이블의 관계

- `chat_room` 1 : N `message` 관계다. `message.chat_room_id`가 `chat_room.id`를 참조하는 외래 키다.
- FK에 `ON DELETE CASCADE`가 걸려 있어 채팅방을 삭제하면 그 방의 메시지가 DB 차원에서 자동으로 함께 삭제된다.

### 메시지 저장, 조회, 대화 비우기, 채팅방 삭제 원리

- **저장**: `add_message(room_id, role, content)` — role에 'user'/'assistant'를 넣어 구분한다. API 호출 실패 시에는 'error' role로 오류 내용을 저장해 대화 기록에 남긴다.
- **조회**: `get_messages(room_id)` — `WHERE chat_room_id = ?`로 현재 방의 메시지만, `ORDER BY id`로 생성 순서대로 가져온다.
- **대화 비우기**: `clear_messages(room_id)` — `DELETE FROM message WHERE chat_room_id = ?`. 메시지만 지우므로 채팅방은 유지된다.
- **채팅방 삭제**: `delete_chat_room(room_id)` — `DELETE FROM chat_room WHERE id = ?`. CASCADE로 메시지도 함께 삭제된다.

### 선택한 채팅방의 이전 대화를 불러오는 원리

사이드바의 라디오 버튼으로 방을 선택하면 `session_state.current_room_id`가 바뀌고, rerun 시 해당 id로 `get_messages()`를 호출해 그 방의 메시지만 화면에 그린다. 방을 바꾸면 조회 조건(`chat_room_id`)이 바뀌므로 화면의 대화도 함께 바뀐다.

### 이전 대화 문맥을 OpenAI API에 전달하는 원리

사용자 입력을 DB에 저장한 뒤, 현재 방의 전체 메시지를 `[{"role": ..., "content": ...}]` 리스트로 만들어 `client.responses.create(model=..., input=history)`로 전달한다. API는 이력 전체를 보고 답변을 생성하므로 "방금 말한 것"을 기억하는 것처럼 동작한다.

### 사용자 입력부터 AI 답변 저장까지의 전체 흐름

1. `st.chat_input`으로 사용자 입력 수신
2. `add_message(방, "user", 입력)` — DB 저장
3. `get_messages(방)`로 전체 이력 조회 → API `input`으로 전달
4. 응답의 `output_text`를 화면에 표시
5. `add_message(방, "assistant", 답변)` — DB 저장
6. 다음 rerun부터는 이 대화가 DB 조회 결과에 포함되어 계속 표시됨

---

## 4. 오류 해결 및 개선 과정

- **기존 코드의 휘발성 문제**: 처음 구현은 `st.session_state.messages` 리스트에만 대화를 저장해서 새로고침하면 사라지고, 채팅방 개념도 없었다. DB를 유일한 기준으로 삼는 구조로 개편했다.
- **매 rerun마다 불필요한 API 호출**: 연결 확인용 `client.models.list()`가 페이지가 다시 실행될 때마다 호출되고 있었다. 과금과 지연을 유발하므로 제거하고, 키 존재 여부 확인 + 실제 호출 시 try/except 오류 처리로 대체했다.
- **문맥 미전달 문제**: 기존 코드는 `input=prompt`로 마지막 질문 하나만 보내서 이전 대화를 기억하지 못했다. 전체 이력을 리스트로 전달하도록 수정했다.
- **API 오류 시 처리**: API 호출이 실패해도 사용자 메시지는 이미 DB에 저장되어 있어 기록이 유실되지 않는다. 오류 내용은 화면에 표시될 뿐 아니라 'error' role의 메시지로 DB에 저장되어 대화 기록에 남는다. 단, 오류 기록은 대화 문맥이 아니므로 OpenAI API에 전달하는 이력에서는 제외한다.
- **기본 채팅방 보호 및 시간 표시**: "기본 채팅방"은 항상 존재하도록 자동 생성되며 삭제 버튼이 비활성화된다. 각 메시지에는 저장 시각(DB의 UTC 값을 로컬 시간으로 변환)이 함께 표시된다.
- **삭제된 방 참조 오류 방지**: 채팅방 삭제 직후 `session_state.current_room_id`가 존재하지 않는 방을 가리킬 수 있어, 매 실행 시 유효성을 검사하고 유효하지 않으면 첫 번째 방으로 되돌리는 방어 코드를 넣었다.
