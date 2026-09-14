"""
YieldChat API Server — Autonomous YouTube Intelligence Chat
FastAPI backend powering the conversational strategy interface.
"""

import os
import json
import uuid
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import asyncio
from datetime import datetime, timezone
import subprocess

import memory_manager
import gemini_agent

load_dotenv()

app = FastAPI(
    title="YieldChat API",
    description="Conversational YouTube Intelligence & Strategy Assistant",
    version="1.0.0"
)

CORS_ORIGINS = [
    "https://dga80.github.io",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorios de imágenes
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated_images")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ── Estado de Sincronización y Tarea de Fondo ─────────────────────────────────
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTO_SYNC_INTERVAL_MINUTES = int(os.getenv("AUTO_SYNC_INTERVAL_MINUTES", "5"))

sync_state = {
    "last_synced_at": datetime.now(timezone.utc).isoformat(),
    "last_status": "ok",
    "last_message": "Sincronizado con GitHub",
    "is_syncing": False
}


def perform_git_sync(commit_msg: str = "auto-sync: actualizar memoria a largo plazo e historial") -> dict:
    """Ejecuta la sincronización Git de memoria y chats."""
    try:
        # 1. Stage memory files
        subprocess.run(
            ["git", "add", "backend/learned_insights.json", "backend/chat_history.db"],
            cwd=REPO_DIR,
            check=True
        )
        
        # 2. Check if there are changes to commit
        status_res = subprocess.run(
            ["git", "status", "--porcelain", "backend/learned_insights.json", "backend/chat_history.db"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not status_res.stdout.strip():
            sync_state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
            sync_state["last_status"] = "ok"
            sync_state["last_message"] = "Al día con GitHub"
            return {"status": "ok", "synced": False, "message": "GitHub ya está al día con la última memoria."}
            
        # 3. Commit and push
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        
        sync_state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        sync_state["last_status"] = "ok"
        sync_state["last_message"] = "Sincronizado con éxito"
        return {"status": "ok", "synced": True, "message": "¡Memoria y chats sincronizados con GitHub con éxito!"}
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else str(e)
        sync_state["last_status"] = "error"
        sync_state["last_message"] = f"Error Git: {err_msg}"
        raise RuntimeError(err_msg)
    except Exception as e:
        sync_state["last_status"] = "error"
        sync_state["last_message"] = str(e)
        raise e


async def background_auto_sync_worker():
    """Bucle autónomo que sincroniza cada X minutos si hay cambios pendientes."""
    print(f"[AutoSync] Bucle autónomo iniciado (cada {AUTO_SYNC_INTERVAL_MINUTES} minutos).")
    while True:
        await asyncio.sleep(AUTO_SYNC_INTERVAL_MINUTES * 60)
        try:
            # Comprobar si hay cambios pendientes antes de ejecutar
            status_res = subprocess.run(
                ["git", "status", "--porcelain", "backend/learned_insights.json", "backend/chat_history.db"],
                cwd=REPO_DIR,
                capture_output=True,
                text=True
            )
            if status_res.stdout.strip():
                print("[AutoSync] Detectados cambios en la memoria. Sincronizando con GitHub de forma autónoma...")
                sync_state["is_syncing"] = True
                res = perform_git_sync("auto-sync: actualización autónoma de memoria e historial")
                print(f"[AutoSync] Resultado: {res.get('message')}")
        except Exception as e:
            print(f"[AutoSync] Error en sincronización autónoma: {e}")
        finally:
            sync_state["is_syncing"] = False


# Inicializar Base de Datos y Tarea de Fondo al arrancar
@app.on_event("startup")
async def on_startup():
    memory_manager.init_db()
    asyncio.create_task(background_auto_sync_worker())



# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Nueva Conversación"
    folder_id: Optional[str] = None

class UpdateSessionRequest(BaseModel):
    title: str

class CreateFolderRequest(BaseModel):
    name: str
    color: Optional[str] = "#F59E0B"

class UpdateFolderRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class SetSessionFolderRequest(BaseModel):
    folder_id: Optional[str] = None

class AttachedFile(BaseModel):
    name: str
    type: str  # 'text', 'pdf', 'image'
    data: Optional[str] = None
    text: Optional[str] = None
    size: Optional[str] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str
    images: Optional[List[str]] = None
    files: Optional[List[AttachedFile]] = None

class InsightRequest(BaseModel):
    categoria: str
    regla: str


# ── Rutas de Estado y Modelo ──────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "YieldChat API Server is running",
        "version": "1.0.0"
    }

@app.get("/api/status")
def get_status():
    active_model = gemini_agent.get_active_model_name()
    has_yt_key = bool(os.getenv("YOUTUBE_API_KEY") and os.getenv("YOUTUBE_API_KEY") != "your_youtube_api_key_here")
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here")
    
    return {
        "status": "online",
        "active_gemini_model": active_model,
        "youtube_api_configured": has_yt_key,
        "gemini_api_configured": has_gemini_key,
        "app_name": "YieldChat"
    }


@app.get("/api/diag")
def get_diag():
    active_model = gemini_agent.get_active_model_name()
    key = os.getenv("GEMINI_API_KEY", "")
    key_info = {
        "configured": bool(key and key != "your_gemini_api_key_here"),
        "length": len(key),
        "prefix": key[:8] if key else "",
        "suffix": key[-4:] if key else "",
        "has_newline": "\n" in key or "\r" in key,
        "has_quotes": key.startswith(('"', "'"))
    }
    
    test_results = {}
    try:
        client = gemini_agent._get_client()
        for m in ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]:
            try:
                chat = client.chats.create(model=m)
                resp = chat.send_message("ping")
                test_results[m] = {"status": "ok", "text": resp.text[:30] if hasattr(resp, 'text') else "ok"}
                break
            except Exception as ex:
                test_results[m] = {"status": "error", "type": type(ex).__name__, "message": str(ex)[:200]}
    except Exception as e:
        return {"key_info": key_info, "client_error": str(e), "active_model": active_model}
        
    import google.genai as gai
    return {
        "key_info": key_info,
        "test_results": test_results,
        "active_model": active_model,
        "google_genai_version": getattr(gai, "__version__", "unknown")
    }
@app.get("/api/test-chat")
async def test_chat_endpoint(q: str = "hola"):
    test_session_id = f"test-diag-{uuid.uuid4().hex[:6]}"
    memory_manager.create_session(test_session_id, "Test Diag")
    events = []
    try:
        async for ev in gemini_agent.stream_agent_chat(test_session_id, q):
            events.append(ev)
        return {"status": "ok", "events": events}
    except Exception as e:
        import traceback
        return {"status": "exception", "error": str(e), "traceback": traceback.format_exc(), "events": events}


@app.get("/api/test-yt")
def test_yt_endpoint(url: str = "https://youtube.com/@mrwealthlab?si=br5c24WMQllrm_2b"):
    import youtube_tools
    try:
        ch = youtube_tools.analizar_canal(url)
        return {"status": "ok", "channel": ch}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Rutas de Archivos e Imágenes ──────────────────────────────────────────────

@app.get("/api/images/{filename}")
def get_generated_image(filename: str):
    filepath = os.path.join(GENERATED_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(filepath, media_type="image/jpeg")


@app.get("/api/uploads/{filename}")
def get_uploaded_image(filename: str):
    filepath = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(filepath)


# ── Rutas de Carpetas / Temas ─────────────────────────────────────────────────

@app.get("/api/folders")
def list_folders():
    return memory_manager.list_folders()


@app.post("/api/folders")
def create_folder(req: CreateFolderRequest):
    new_id = f"folder-{uuid.uuid4().hex[:8]}"
    return memory_manager.create_folder(new_id, req.name.strip(), req.color or "#F59E0B")


@app.patch("/api/folders/{folder_id}")
def update_folder(folder_id: str, req: UpdateFolderRequest):
    updated = memory_manager.update_folder(folder_id, req.name.strip() if req.name else None, req.color)
    if not updated:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    return updated


@app.delete("/api/folders/{folder_id}")
def delete_folder(folder_id: str):
    memory_manager.delete_folder(folder_id)
    return {"status": "deleted", "id": folder_id}


# ── Rutas de Sesiones de Chat ─────────────────────────────────────────────────

@app.get("/api/sessions")
def list_sessions():
    return memory_manager.list_sessions()


@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    new_id = f"chat-{uuid.uuid4().hex[:10]}"
    return memory_manager.create_session(new_id, req.title or "Nueva Conversación", req.folder_id)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    session = memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return session


@app.patch("/api/sessions/{session_id}")
def update_session(session_id: str, req: UpdateSessionRequest):
    memory_manager.update_session_title(session_id, req.title)
    return {"status": "updated", "id": session_id, "title": req.title}


@app.patch("/api/sessions/{session_id}/folder")
def set_session_folder(session_id: str, req: SetSessionFolderRequest):
    session = memory_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    memory_manager.assign_session_folder(session_id, req.folder_id)
    return {"status": "updated", "id": session_id, "folder_id": req.folder_id}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    memory_manager.delete_session(session_id)
    return {"status": "deleted", "id": session_id}


# ── Ruta de Chat con Streaming (Server-Sent Events) ───────────────────────────

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    session = memory_manager.get_session(req.session_id)
    if not session:
        memory_manager.create_session(req.session_id, req.message[:30] + "...")

    files_list = [f.model_dump() for f in req.files] if req.files else None

    async def event_generator():
        try:
            async for event in gemini_agent.stream_agent_chat(
                session_id=req.session_id,
                user_message=req.message,
                images=req.images,
                files=files_list
            ):
                if await request.is_disconnected():
                    print(f"[Chat] Cliente canceló o se desconectó de la sesión {req.session_id}")
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            print(f"[Chat] Tarea cancelada por el cliente para la sesión {req.session_id}")
        except Exception as e:
            err_payload = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )



# ── Rutas de Memoria a Largo Plazo (Aprendizajes) ─────────────────────────────

@app.get("/api/memory")
def get_memory():
    return memory_manager.get_all_insights()


@app.post("/api/memory")
def add_memory(req: InsightRequest):
    return memory_manager.add_insight(req.categoria, req.regla)


# ── Rutas de Sincronización con GitHub ─────────────────────────────────────────

@app.get("/api/sync/status")
def get_sync_status():
    # Comprobar cambios pendientes
    status_res = subprocess.run(
        ["git", "status", "--porcelain", "backend/learned_insights.json", "backend/chat_history.db"],
        cwd=REPO_DIR,
        capture_output=True,
        text=True
    )
    has_pending = bool(status_res.stdout.strip())
    
    return {
        "is_synced": not has_pending and sync_state["last_status"] == "ok",
        "has_pending_changes": has_pending,
        "is_syncing": sync_state["is_syncing"],
        "last_synced_at": sync_state["last_synced_at"],
        "status": "pending" if has_pending else sync_state["last_status"],
        "message": "Cambios locales pendientes" if has_pending else sync_state["last_message"],
        "auto_sync_interval_minutes": AUTO_SYNC_INTERVAL_MINUTES
    }


@app.post("/api/sync/github")
def sync_github():
    sync_state["is_syncing"] = True
    try:
        res = perform_git_sync("sync: actualizar memoria a largo plazo e historial")
        return res
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Error Git: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        sync_state["is_syncing"] = False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)


