"""
Memory & History Manager for YieldChat
Handles SQLite persistence for multi-turn chat sessions and long-term learned insights.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")
INSIGHTS_PATH = os.path.join(os.path.dirname(__file__), "learned_insights.json")


def init_db():
    """Inicializa las tablas en SQLite si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        tool_calls TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()
    
    # Inicializar archivo de aprendizajes si no existe
    if not os.path.exists(INSIGHTS_PATH):
        save_all_insights([])


# ── Gestión de Sesiones y Mensajes (SQLite) ──────────────────────────────────

def list_sessions() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    cursor.execute("SELECT id, role, content, tool_calls, created_at FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    messages = [dict(m) for m in cursor.fetchall()]
    conn.close()
    
    res = dict(row)
    res["messages"] = messages
    return res


def create_session(session_id: str, title: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, title, now, now)
    )
    conn.commit()
    conn.close()
    return {"id": session_id, "title": title, "created_at": now, "updated_at": now, "messages": []}


def update_session_title(session_id: str, title: str):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def add_message(session_id: str, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
    now = datetime.now(timezone.utc).isoformat()
    tool_calls_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, tool_calls_json, now)
    )
    cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()


# ── Memoria a Largo Plazo y Aprendizajes Evolutivos (JSON) ────────────────────

def get_all_insights() -> List[Dict[str, Any]]:
    if not os.path.exists(INSIGHTS_PATH):
        return []
    try:
        with open(INSIGHTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_all_insights(insights: List[Dict[str, Any]]):
    with open(INSIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)


def add_insight(categoria: str, regla: str) -> Dict[str, Any]:
    insights = get_all_insights()
    now = datetime.now(timezone.utc).isoformat()
    new_item = {
        "id": len(insights) + 1,
        "categoria": categoria,
        "regla": regla,
        "created_at": now
    }
    insights.append(new_item)
    save_all_insights(insights)
    return new_item


def delete_insight(insight_id: int):
    insights = get_all_insights()
    insights = [i for i in insights if i.get("id") != insight_id]
    save_all_insights(insights)


def format_memory_for_system_prompt() -> str:
    insights = get_all_insights()
    if not insights:
        return "No hay reglas de memoria previa registradas todavía."
        
    formatted = "### REGLAS DE NEGOCIO Y APRENDIZAJES PERMANENTES:\n"
    for i in insights:
        formatted += f"- [{i.get('categoria', 'GENERAL').upper()}]: {i.get('regla')}\n"
    return formatted
