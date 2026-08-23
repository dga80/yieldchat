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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import memory_manager
import gemini_agent

load_dotenv()

app = FastAPI(
    title="YieldChat API",
    description="Conversational YouTube Intelligence & Strategy Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Base de Datos al arrancar
@app.on_event("startup")
def on_startup():
    memory_manager.init_db()


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Nueva Conversación"

class UpdateSessionRequest(BaseModel):
    title: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class InsightRequest(BaseModel):
    categoria: str
    regla: str


# ── Rutas de Estado y Modelo ──────────────────────────────────────────────────

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


# ── Rutas de Sesiones de Chat ─────────────────────────────────────────────────

@app.get("/api/sessions")
def list_sessions():
    return memory_manager.list_sessions()


@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    new_id = f"chat-{uuid.uuid4().hex[:10]}"
    return memory_manager.create_session(new_id, req.title or "Nueva Conversación")


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


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    memory_manager.delete_session(session_id)
    return {"status": "deleted", "id": session_id}


# ── Ruta de Chat con Streaming (Server-Sent Events) ───────────────────────────

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    session = memory_manager.get_session(req.session_id)
    if not session:
        memory_manager.create_session(req.session_id, req.message[:30] + "...")

    async def event_generator():
        try:
            async for event in gemini_agent.stream_agent_chat(req.session_id, req.message):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
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


# ── Ruta de Sincronización con GitHub ─────────────────────────────────────────

@app.post("/api/sync/github")
def sync_github():
    import subprocess
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        # 1. Stage memory files
        subprocess.run(
            ["git", "add", "backend/learned_insights.json", "backend/chat_history.db"],
            cwd=repo_dir,
            check=True
        )
        
        # 2. Check if there are changes to commit
        status_res = subprocess.run(
            ["git", "status", "--porcelain", "backend/learned_insights.json", "backend/chat_history.db"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not status_res.stdout.strip():
            return {
                "status": "ok",
                "synced": False,
                "message": "GitHub ya está al día con la última memoria."
            }
            
        # 3. Commit and push
        subprocess.run(
            ["git", "commit", "-m", "sync: actualizar memoria a largo plazo e historial"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "status": "ok",
            "synced": True,
            "message": "¡Memoria y chats sincronizados con GitHub con éxito!"
        }
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else str(e)
        print(f"[Sync GitHub Error] {err_msg}")
        raise HTTPException(status_code=500, detail=f"Error Git: {err_msg}")
    except Exception as e:
        print(f"[Sync GitHub Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

