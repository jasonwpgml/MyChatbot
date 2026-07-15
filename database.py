"""SQLite 데이터베이스 계층.

ERD (Agent/ERD.drawio) 기준:
- chat_room: id(PK), name, create_date
- message:   id(PK), chat_room_id(FK -> chat_room.id, ON DELETE CASCADE),
             role, content, model, create_date
  (model: 답변을 생성한 GPT 모델 이름. 사용자 메시지는 NULL)
"""

import sqlite3

DB_PATH = "chatbot.db"


def get_connection():
    # SQLite는 외래 키 제약이 기본으로 꺼져 있으므로 연결마다 켜 준다.
    # (채팅방 삭제 시 메시지 CASCADE 삭제에 필요)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """필요한 테이블이 없으면 자동 생성한다. (요구사항 2)"""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_room (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                create_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_room_id INTEGER NOT NULL,
                role         TEXT NOT NULL,
                content      TEXT NOT NULL,
                model        TEXT,
                create_date  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_room_id)
                    REFERENCES chat_room (id) ON DELETE CASCADE
            )
            """
        )
        # 마이그레이션: model 컬럼이 없는 기존 DB에 컬럼을 추가한다.
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(message)")]
        if "model" not in columns:
            conn.execute("ALTER TABLE message ADD COLUMN model TEXT")


def create_chat_room(name):
    """채팅방을 생성하고 새 채팅방의 id를 반환한다."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO chat_room (name) VALUES (?)", (name,)
        )
        return cursor.lastrowid


def get_chat_rooms():
    """모든 채팅방을 생성 순서대로 반환한다."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, create_date FROM chat_room ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def delete_chat_room(room_id):
    """채팅방을 삭제한다. 소속 메시지는 CASCADE로 함께 삭제된다."""
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_room WHERE id = ?", (room_id,))


def clear_messages(room_id):
    """해당 채팅방의 메시지만 모두 삭제한다. 채팅방 자체는 유지된다."""
    with get_connection() as conn:
        conn.execute("DELETE FROM message WHERE chat_room_id = ?", (room_id,))


def add_message(room_id, role, content, model=None):
    """메시지를 저장한다.

    role은 'user', 'assistant' 또는 'error'(API 호출 실패 기록).
    model은 답변을 생성한(또는 생성에 실패한) GPT 모델 이름. 사용자 메시지는 None.
    """
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO message (chat_room_id, role, content, model) "
            "VALUES (?, ?, ?, ?)",
            (room_id, role, content, model),
        )


def get_messages(room_id):
    """해당 채팅방의 메시지를 생성 순서대로 반환한다.

    create_date는 초 단위라 같은 초에 저장된 메시지의 순서가 뒤섞일 수
    있으므로, 항상 증가하는 id를 정렬 기준으로 사용한다.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, model, create_date FROM message "
            "WHERE chat_room_id = ? ORDER BY id",
            (room_id,),
        ).fetchall()
        return [dict(row) for row in rows]
