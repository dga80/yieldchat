"""
Memory & History Manager for YieldChat
Handles SQLite persistence for multi-turn chat sessions and long-term learned insights.
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")
INSIGHTS_PATH = os.path.join(os.path.dirname(__file__), "learned_insights.json")


def init_db():
    """Inicializa las tablas en SQLite si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS folders (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        color TEXT DEFAULT '#F59E0B',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        folder_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
    )
    """)
    
    # Migración: asegurar que la columna folder_id existe si la tabla sessions ya existía
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in cursor.fetchall()]
    if "folder_id" not in columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN folder_id TEXT")

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'Estrategia',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generated_images (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        folder_id TEXT,
        prompt TEXT NOT NULL,
        enhanced_prompt TEXT,
        aspect_ratio TEXT DEFAULT '16:9',
        model TEXT DEFAULT 'google-banana',
        image_url TEXT NOT NULL,
        filename TEXT NOT NULL,
        created_at TEXT NOT NULL,
        metadata TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    
    # Inicializar archivo de aprendizajes si no existe
    if not os.path.exists(INSIGHTS_PATH):
        save_all_insights([])


# ── Gestión de Carpetas / Temas (SQLite) ─────────────────────────────────────

def list_folders() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.name, f.color, f.created_at, f.updated_at,
               COUNT(s.id) as session_count
        FROM folders f
        LEFT JOIN sessions s ON s.folder_id = f.id
        GROUP BY f.id
        ORDER BY f.created_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_folder(folder_id: str, name: str, color: str = "#F59E0B") -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO folders (id, name, color, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (folder_id, name, color, now, now)
    )
    conn.commit()
    conn.close()
    return {"id": folder_id, "name": name, "color": color, "created_at": now, "updated_at": now, "session_count": 0}


def update_folder(folder_id: str, name: Optional[str] = None, color: Optional[str] = None) -> Optional[Dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, color, created_at, updated_at FROM folders WHERE id = ?", (folder_id,))
    folder = cursor.fetchone()
    if not folder:
        conn.close()
        return None
    
    new_name = name if name is not None else folder["name"]
    new_color = color if color is not None else folder["color"]
    cursor.execute("UPDATE folders SET name = ?, color = ?, updated_at = ? WHERE id = ?", (new_name, new_color, now, folder_id))
    conn.commit()
    conn.close()
    return {"id": folder_id, "name": new_name, "color": new_color, "updated_at": now}


def delete_folder(folder_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Desvincular las sesiones de esta carpeta
    cursor.execute("UPDATE sessions SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
    cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    conn.commit()
    conn.close()


def assign_session_folder(session_id: str, folder_id: Optional[str]):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET folder_id = ?, updated_at = ? WHERE id = ?", (folder_id, now, session_id))
    conn.commit()
    conn.close()


# ── Gestión de Sesiones y Mensajes (SQLite) ──────────────────────────────────

def list_sessions() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.title, s.folder_id, s.created_at, s.updated_at,
               f.name as folder_name, f.color as folder_color
        FROM sessions s
        LEFT JOIN folders f ON s.folder_id = f.id
        ORDER BY s.updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.title, s.folder_id, s.created_at, s.updated_at,
               f.name as folder_name, f.color as folder_color
        FROM sessions s
        LEFT JOIN folders f ON s.folder_id = f.id
        WHERE s.id = ?
    """, (session_id,))
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


def create_session(session_id: str, title: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (id, title, folder_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, title, folder_id, now, now)
    )
    conn.commit()
    conn.close()
    return {"id": session_id, "title": title, "folder_id": folder_id, "created_at": now, "updated_at": now, "messages": []}


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


# ── Gestión de Notas de Conversación (SQLite) ────────────────────────────────

def list_notes(session_id: str) -> List[Dict[str, Any]]:
    """Devuelve todas las notas asociadas a una sesión, ordenadas por fecha de actualización descendente."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, session_id, title, content, category, created_at, updated_at
        FROM notes
        WHERE session_id = ?
        ORDER BY created_at DESC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_note(session_id: str, title: str, content: str, category: str = "Estrategia", note_id: Optional[str] = None) -> Dict[str, Any]:
    """Crea una nueva nota en la conversación activa."""
    n_id = note_id or f"note_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    clean_cat = category.strip() if category and category.strip() else "Estrategia"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notes (id, session_id, title, content, category, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (n_id, session_id, title.strip(), content.strip(), clean_cat, now, now))
    conn.commit()
    conn.close()
    
    return {
        "id": n_id,
        "session_id": session_id,
        "title": title.strip(),
        "content": content.strip(),
        "category": clean_cat,
        "created_at": now,
        "updated_at": now
    }


def update_note(note_id: str, title: Optional[str] = None, content: Optional[str] = None, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Actualiza una nota existente."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return None
        
    now = datetime.now(timezone.utc).isoformat()
    new_title = title.strip() if title is not None else existing["title"]
    new_content = content.strip() if content is not None else existing["content"]
    new_category = category.strip() if category is not None else existing["category"]
    
    cursor.execute("""
        UPDATE notes
        SET title = ?, content = ?, category = ?, updated_at = ?
        WHERE id = ?
    """, (new_title, new_content, new_category, now, note_id))
    conn.commit()
    
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated) if updated else None


def delete_note(note_id: str) -> bool:
    """Elimina una nota por su ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ── Gestión de Imágenes y Memoria Visual de Canal ───────────────────────────

def save_generated_image(
    image_id: str,
    prompt: str,
    enhanced_prompt: str,
    image_url: str,
    filename: str,
    folder_id: Optional[str] = None,
    session_id: Optional[str] = None,
    aspect_ratio: str = "16:9",
    model: str = "google-banana",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Guarda los metadatos de una imagen generada en la base de datos."""
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(metadata or {})
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO generated_images (
            id, session_id, folder_id, prompt, enhanced_prompt,
            aspect_ratio, model, image_url, filename, created_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        image_id, session_id, folder_id, prompt, enhanced_prompt,
        aspect_ratio, model, image_url, filename, now, meta_json
    ))
    conn.commit()
    conn.close()

    return {
        "id": image_id,
        "session_id": session_id,
        "folder_id": folder_id,
        "prompt": prompt,
        "enhanced_prompt": enhanced_prompt,
        "aspect_ratio": aspect_ratio,
        "model": model,
        "image_url": image_url,
        "filename": filename,
        "created_at": now,
        "metadata": metadata or {}
    }


def list_generated_images(
    folder_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lista las imágenes generadas, filtrables por carpeta o sesión."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM generated_images WHERE 1=1"
    params = []

    if folder_id:
        query += " AND folder_id = ?"
        params.append(folder_id)
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        if item.get("metadata"):
            try:
                item["metadata"] = json.loads(item["metadata"])
            except Exception:
                pass
        results.append(item)
    return results


def delete_generated_image(image_id: str) -> bool:
    """Elimina el registro de una imagen generada."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM generated_images WHERE id = ?", (image_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_channel_visual_context(folder_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Recupera el contexto visual y reglas de estilo aprendidas para una carpeta/canal.
    Devuelve las directrices de miniatura y estilo visual acumuladas.
    """
    all_insights = get_all_insights()
    channel_name = None
    folder_color = None

    if folder_id:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name, color FROM folders WHERE id = ?", (folder_id,))
        f_row = cursor.fetchone()
        conn.close()
        if f_row:
            channel_name = f_row["name"]
            folder_color = f_row["color"]

    # Extraer reglas visuales y de miniaturas
    visual_rules = []
    for ins in all_insights:
        cat = (ins.get("categoria") or "").upper()
        regla = ins.get("regla") or ""
        if any(kw in cat for kw in ["MINIATURA", "VISUAL", "IMAGEN", "ESTILO"]):
            visual_rules.append(regla)
        elif any(kw in regla.lower() for kw in ["ghibli", "makoto shinkai", "miniatura", "anime", "ken burns", "partículas"]):
            visual_rules.append(regla)

    # Recuperar últimas imágenes de este canal para consistencia
    recent_images = list_generated_images(folder_id=folder_id, limit=3) if folder_id else []

    return {
        "folder_id": folder_id,
        "channel_name": channel_name or "General",
        "folder_color": folder_color or "#F59E0B",
        "visual_rules": visual_rules,
        "recent_prompts": [img.get("enhanced_prompt") or img.get("prompt") for img in recent_images if img.get("prompt")]
    }


