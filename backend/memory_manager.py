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
CONVERSATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conversations")
FOLDERS_FILE = os.path.join(CONVERSATIONS_DIR, "folders.json")


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

    # Sincronizar y restaurar carpetas y conversaciones desde archivos de disco si faltan en SQLite
    sync_from_disk_on_startup()


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
        "INSERT OR REPLACE INTO folders (id, name, color, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (folder_id, name, color, now, now)
    )
    conn.commit()
    conn.close()
    export_folders_to_file()
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
    export_folders_to_file()
    return {"id": folder_id, "name": new_name, "color": new_color, "updated_at": now}


def delete_folder(folder_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Desvincular las sesiones de esta carpeta
    cursor.execute("UPDATE sessions SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
    cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    conn.commit()
    conn.close()
    export_folders_to_file()


def assign_session_folder(session_id: str, folder_id: Optional[str]):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET folder_id = ?, updated_at = ? WHERE id = ?", (folder_id, now, session_id))
    conn.commit()
    conn.close()
    export_session_to_file(session_id)
    export_folders_to_file()


def get_folder_details(folder_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve los detalles de una carpeta por su ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, color, created_at, updated_at FROM folders WHERE id = ?", (folder_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None



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
    export_session_to_file(session_id)
    export_folders_to_file()
    return {"id": session_id, "title": title, "folder_id": folder_id, "created_at": now, "updated_at": now, "messages": []}


def restore_session(
    session_id: str,
    title: str,
    folder_id: Optional[str] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    c_at = created_at or now
    u_at = updated_at or now
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO sessions (id, title, folder_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, title, folder_id, c_at, u_at))

    if messages:
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        for m in messages:
            m_role = m.get("role", "user")
            m_content = m.get("content", "")
            m_time = m.get("created_at", now)
            m_tools = json.dumps(m.get("tool_calls"), ensure_ascii=False) if m.get("tool_calls") else None
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, m_role, m_content, m_tools, m_time)
            )
    conn.commit()
    conn.close()
    export_session_to_file(session_id)
    return get_session(session_id) or {"id": session_id, "title": title}


def update_session_title(session_id: str, title: str):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title, now, session_id))
    conn.commit()
    conn.close()
    export_session_to_file(session_id)


def delete_session(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    remove_session_file(session_id)
    export_folders_to_file()


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
    export_session_to_file(session_id)


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
    export_session_to_file(session_id)
    
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
    if updated and updated["session_id"]:
        export_session_to_file(updated["session_id"])
    return dict(updated) if updated else None


def delete_note(note_id: str) -> bool:
    """Elimina una nota por su ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    session_id = row[0] if row else None

    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if session_id:
        export_session_to_file(session_id)
    return deleted


# ── Persistencia Espejo en Disco (conversations/*.json y folders.json) ────────

def export_folders_to_file():
    """Exporta todas las carpetas a conversations/folders.json para respaldo permanente."""
    try:
        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
        folders = list_folders()
        with open(FOLDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(folders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Export] Error guardando folders.json: {e}")


def export_session_to_file(session_id: str):
    """Exporta una sesión con todos sus mensajes y notas a conversations/{id}.json."""
    try:
        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
        session = get_session(session_id)
        if not session:
            return
        session["notes"] = list_notes(session_id)
        fpath = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Export] Error guardando sesión {session_id} en archivo: {e}")


def remove_session_file(session_id: str):
    """Elimina el archivo JSON de una sesión si fue eliminada."""
    try:
        fpath = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)
    except Exception:
        pass


def sync_from_disk_on_startup():
    """Restaura carpetas y conversaciones desde los archivos JSON en conversations/ si faltan en SQLite."""
    try:
        if not os.path.exists(CONVERSATIONS_DIR):
            return

        # 1. Restaurar carpetas si existen en folders.json
        if os.path.exists(FOLDERS_FILE):
            try:
                with open(FOLDERS_FILE, "r", encoding="utf-8") as f:
                    saved_folders = json.load(f)
                if isinstance(saved_folders, list):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    now = datetime.now(timezone.utc).isoformat()
                    for folder in saved_folders:
                        fid = folder.get("id")
                        fname = folder.get("name")
                        fcolor = folder.get("color", "#F59E0B")
                        fc_at = folder.get("created_at") or now
                        fu_at = folder.get("updated_at") or fc_at
                        if fid and fname:
                            cursor.execute("""
                                INSERT OR REPLACE INTO folders (id, name, color, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (fid, fname, fcolor, fc_at, fu_at))
                    conn.commit()
                    conn.close()
            except Exception as ex:
                print(f"[InitDB] Error restaurando carpetas desde {FOLDERS_FILE}: {ex}")

        # 2. Restaurar sesiones desde los archivos JSON individuales
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sessions")
        existing_sids = {row[0] for row in cursor.fetchall()}
        conn.close()

        for fname in os.listdir(CONVERSATIONS_DIR):
            if fname.endswith(".json") and fname != "folders.json":
                sid = fname[:-5]
                fpath = os.path.join(CONVERSATIONS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "id" in data:
                        if data["id"] not in existing_sids:
                            print(f"[InitDB] Resucitando sesión {data['id']} desde archivo local...")
                            restore_session(
                                session_id=data["id"],
                                title=data.get("title", "Conversación"),
                                folder_id=data.get("folder_id"),
                                created_at=data.get("created_at"),
                                updated_at=data.get("updated_at"),
                                messages=data.get("messages", [])
                            )
                            # Restaurar notas
                            if data.get("notes"):
                                for n in data["notes"]:
                                    create_note(
                                        session_id=data["id"],
                                        title=n.get("title", ""),
                                        content=n.get("content", ""),
                                        category=n.get("category", "Estrategia")
                                    )
                except Exception as ex:
                    print(f"[InitDB] Error leyendo archivo {fname}: {ex}")
    except Exception as e:
        print(f"[InitDB] Error global en sync_from_disk_on_startup: {e}")


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


# ── Contexto Compartido entre Conversaciones de una Misma Carpeta ─────────────

def get_sibling_sessions_context(folder_id: str, exclude_session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene las demás conversaciones pertenecientes a la misma carpeta,
    incluyendo sus notas y sus mensajes para alimentar el contexto compartido del agente.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if exclude_session_id:
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE folder_id = ? AND id != ?
            ORDER BY updated_at DESC
        """, (folder_id, exclude_session_id))
    else:
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE folder_id = ?
            ORDER BY updated_at DESC
        """, (folder_id,))

    session_rows = cursor.fetchall()
    siblings = []

    for s in session_rows:
        s_id = s["id"]
        # Notas asociadas a esta conversación hermana
        cursor.execute("""
            SELECT id, title, category, content, updated_at
            FROM notes
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (s_id,))
        notes = [dict(n) for n in cursor.fetchall()]

        # Mensajes de esta conversación hermana
        cursor.execute("""
            SELECT id, role, content, tool_calls, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
        """, (s_id,))
        msgs = [dict(m) for m in cursor.fetchall()]

        siblings.append({
            "id": s_id,
            "title": s["title"],
            "created_at": s["created_at"],
            "updated_at": s["updated_at"],
            "notes": notes,
            "messages": msgs,
            "message_count": len(msgs)
        })

    conn.close()
    return siblings


def get_full_session_in_folder(folder_id: str, identifier: str) -> Dict[str, Any]:
    """
    Busca y devuelve una conversación completa dentro de una carpeta por ID exacto
    o por coincidencia en el título.
    """
    clean_id = identifier.strip()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Búsqueda exacta por ID
    cursor.execute("""
        SELECT id, title, created_at, updated_at
        FROM sessions
        WHERE folder_id = ? AND id = ?
    """, (folder_id, clean_id))
    row = cursor.fetchone()

    # 2. Si no, búsqueda por coincidencia parcial en el título
    if not row:
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM sessions
            WHERE folder_id = ? AND LOWER(title) LIKE ?
            ORDER BY updated_at DESC
        """, (folder_id, f"%{clean_id.lower()}%"))
        row = cursor.fetchone()

    if not row:
        cursor.execute("SELECT id, title FROM sessions WHERE folder_id = ?", (folder_id,))
        available = [{"id": r["id"], "title": r["title"]} for r in cursor.fetchall()]
        conn.close()
        return {
            "status": "not_found",
            "message": f"No se encontró ninguna conversación que coincida con '{clean_id}' en esta carpeta.",
            "conversaciones_disponibles_en_carpeta": available
        }

    target_id = row["id"]
    target_title = row["title"]

    cursor.execute("""
        SELECT id, title, category, content, updated_at
        FROM notes
        WHERE session_id = ?
        ORDER BY created_at ASC
    """, (target_id,))
    notes = [dict(n) for n in cursor.fetchall()]

    cursor.execute("""
        SELECT id, role, content, created_at
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
    """, (target_id,))
    messages = [dict(m) for m in cursor.fetchall()]
    conn.close()

    return {
        "status": "ok",
        "id": target_id,
        "title": target_title,
        "notes": notes,
        "messages": messages,
        "total_messages": len(messages)
    }


def _clean_msg_for_context(content: str, max_chars: int = 500) -> str:
    """Limpia el contenido de un mensaje para el prompt eliminando URLs de imágenes pesadas y recortando si es largo."""
    import re
    # Reemplazar imágenes markdown por etiqueta concisa
    cleaned = re.sub(r'!\[.*?\]\(.*?\)', '[Imagen/Referencia visual]', content)
    cleaned = cleaned.strip().replace('\r', '')
    if len(cleaned) > max_chars:
        return cleaned[:max_chars] + "... [continúa]"
    return cleaned


def format_folder_context_for_prompt(folder_id: Optional[str], current_session_id: str) -> str:
    """
    Construye la sección de contexto compartido de la carpeta para ser inyectada
    en la directiva de sistema de Gemini.
    """
    if not folder_id:
        return ""

    folder = get_folder_details(folder_id)
    if not folder:
        return ""

    folder_name = folder.get("name", "Carpeta")
    siblings = get_sibling_sessions_context(folder_id, exclude_session_id=current_session_id)

    if not siblings:
        return (
            f"\n### CONTEXTO DE LA CARPETA TEMÁTICA ('{folder_name}'):\n"
            f"- Esta conversación pertenece a la carpeta temática o canal **'{folder_name}'**.\n"
            f"- Actualmente es la primera o única conversación en esta carpeta.\n"
        )

    lines = [
        f"\n### CONTEXTO COMPARTIDO DE LA CARPETA TEMÁTICA: \"{folder_name}\"",
        f"Esta conversación comparte carpeta temática y línea de proyecto con otras **{len(siblings)} conversación(es)** vinculadas.",
        "TIENES ACCESO COMPLETO AL CONTEXTO DE TODAS ELLAS para mantener plena coherencia, recordar los canales y vídeos analizados,",
        "las métricas de outliers, ideas de empaque (título/miniatura), guiones en desarrollo y notas estratégicas acordadas:",
        ""
    ]

    for idx, sib in enumerate(siblings, start=1):
        lines.append(f"#### 📁 Conversación Relacionada #{idx}: \"{sib['title']}\" (ID: `{sib['id']}`)")

        # Notas estratégicas de la conversación hermana
        if sib["notes"]:
            lines.append("  📌 **Notas estratégicas guardadas en este chat:**")
            for n in sib["notes"]:
                cat = n.get('category', 'Estrategia')
                title = n.get('title', '')
                content = n.get('content', '').replace('\n', ' ')
                if len(content) > 300:
                    content = content[:300] + "..."
                lines.append(f"    - [{cat}] **{title}**: {content}")

        # Mensajes de la conversación hermana
        msgs = sib["messages"]
        if not msgs:
            lines.append("  *(Sin mensajes registrados aún)*")
        elif len(msgs) <= 6:
            lines.append("  💬 **Historial de la conversación:**")
            for m in msgs:
                role = "USUARIO" if m["role"] == "user" else "ASISTENTE"
                text = _clean_msg_for_context(m["content"], max_chars=600)
                lines.append(f"    * {role}: {text}")
        else:
            lines.append(f"  💬 **Historial resumido ({len(msgs)} mensajes en total):**")
            lines.append("    -- [Inicio de la charla / Objetivo] --")
            for m in msgs[:2]:
                role = "USUARIO" if m["role"] == "user" else "ASISTENTE"
                text = _clean_msg_for_context(m["content"], max_chars=400)
                lines.append(f"    * {role}: {text}")

            lines.append(f"    -- [... {len(msgs) - 6} mensajes intermedios omitidos ...] --")
            lines.append("    -- [Últimos intercambios y estado actual] --")
            for m in msgs[-4:]:
                role = "USUARIO" if m["role"] == "user" else "ASISTENTE"
                text = _clean_msg_for_context(m["content"], max_chars=500)
                lines.append(f"    * {role}: {text}")

        lines.append("")

    lines.append(
        "💡 **DIRECTIVA DE COHERENCIA ENTRE CHATS DE LA CARPETA:**\n"
        "- Si el usuario hace referencia a 'la otra conversación', 'los canales que vimos', "
        "'el guion anterior' o cualquier temática tratada en esta carpeta, usa directamente este contexto.\n"
        "- Si necesitas consultar el texto íntegro, palabra por palabra, de cualquiera de estas conversaciones "
        "o sus notas completas, puedes invocar la herramienta `herramienta_consultar_conversacion_carpeta` pasando su ID o título."
    )
    lines.append("")

    return "\n".join(lines)



