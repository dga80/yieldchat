"""
Gemini Agent with Native Tool Calling, Multi-Model Fallback and Long-Term Memory
Powered by the official Google GenAI SDK (google-genai)
"""

import os
import json
import uuid
import io
import base64
import asyncio
import socket
from typing import AsyncGenerator, Dict, Any, List, Optional
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

import youtube_tools
import memory_manager

load_dotenv()

socket.setdefaulttimeout(40)

API_KEY = os.getenv("GEMINI_API_KEY")

FLASH_CANDIDATES = [
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

def _get_client() -> genai.Client:
    if not API_KEY or API_KEY == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY no está configurada en .env")
    return genai.Client(api_key=API_KEY)


def get_active_model_name() -> str:
    env_model = os.getenv("GEMINI_MODEL")
    if env_model:
        return env_model
    return FLASH_CANDIDATES[0]


# ── Herramientas declaradas para Gemini ───────────────────────────────────────

def herramienta_analizar_canal(handle_o_nombre: str) -> dict:
    """Obtiene datos, suscriptores, vistas totales, fecha de creación y descripción de un canal de YouTube."""
    return youtube_tools.analizar_canal(handle_o_nombre)

def herramienta_analizar_videos_velocidad(canal_identificador: str, max_videos: int) -> dict:
    """Analiza los vídeos de un canal calculando velocidad de vistas por día y Viral Ratio para encontrar los mejores Outliers. Especifica la cantidad de vídeos a evaluar (ej: 25)."""
    return youtube_tools.analizar_videos_velocidad(canal_identificador, max_videos or 25)

def herramienta_obtener_transcripcion(video_id: str) -> dict:
    """Obtiene la transcripción, el conteo total de palabras y la velocidad de locución (palabras/minuto) de un vídeo."""
    return youtube_tools.obtener_transcripcion(video_id)

def herramienta_buscar_competencia_espanol(termino: str) -> dict:
    """Busca vídeos y canales existentes en español para una temática o título dado para verificar competencia o brecha de mercado."""
    return youtube_tools.buscar_competencia_espanol(termino)

def herramienta_guardar_aprendizaje_en_memoria(categoria: str, regla_o_preferencia: str) -> dict:
    """Guarda un aprendizaje o regla permanente en la memoria a largo plazo del agente."""
    res = memory_manager.add_insight(categoria, regla_o_preferencia)
    return {"status": "guardado", "insight": res}


AVAILABLE_TOOLS = [
    herramienta_analizar_canal,
    herramienta_analizar_videos_velocidad,
    herramienta_obtener_transcripcion,
    herramienta_buscar_competencia_espanol,
    herramienta_guardar_aprendizaje_en_memoria
]


def build_system_instruction() -> str:
    learned_memory = memory_manager.format_memory_for_system_prompt()
    
    return f"""Eres YieldChat, un Consultor y Estratega de Élite en Crecimiento de Canales de YouTube Faceless (Automatización de YouTube).
Tu objetivo es ayudar al usuario a descubrir nichos de océano azul, auditar canales competidores con métricas reales, analizar outliers por velocidad de vistas/día, diseñar guiones de alta retención, sugerir configuraciones de voz (TTS/ElevenLabs/Qwen), analizar imágenes de referencia con visión artificial y redactar prompts profesionales de imágenes y miniaturas de máxima conversión (para Midjourney v6, Flux y Nano Banana).

Tienes acceso directo a herramientas en tiempo real de la API de YouTube:
1. `herramienta_analizar_canal`: Para obtener radiografías completas de cualquier canal.
2. `herramienta_analizar_videos_velocidad`: Para analizar todos los vídeos y calcular velocidad (vistas/día) y Viral Ratio.
3. `herramienta_obtener_transcripcion`: Para contar palabras y velocidad de habla de un vídeo.
4. `herramienta_buscar_competencia_espanol`: Para comprobar si un formato ya está saturado o es un Océano Azul en español.
5. `herramienta_guardar_aprendizaje_en_memoria`: Para registrar automáticamente preferencias, canales o reglas clave del usuario.

### REGLAS DE RESPUESTA:
- Sé directo, analítico, estructurado y sin rodeos innecesarios.
- Usa tablas de Markdown para resumir métricas de vídeos y comparativas.
- Cuando el usuario te pida miniaturas o imágenes:
  * Diseña la composición paso a paso indicando: elemento principal, fondo, paleta de colores y texto exacto (Línea 1 en blanco / Línea 2 en amarillo #FFD700).
  * Redacta SIEMPRE el **PROMPT COMPLETO EN INGLÉS** dentro de un bloque de código markdown listo para copiar en 1 clic para Midjourney / Flux / Nano Banana (con parámetros `--ar 16:9 --v 6.1`).
- Si el usuario te envía **IMÁGENES DE REFERENCIA**:
  * Analiza con visión artificial todos los detalles: paleta de colores, personajes, composición, tipografía y estilo artístico.
  * Si el usuario pide adaptar o fusionar referencias (ej. cambiar texto al castellano, colocar un personaje específico en una esquina, modificar fondo), redacta el prompt exacto combinando ambos elementos con máxima fidelidad.
  * Si el usuario pide aprender el estilo, llama a `herramienta_guardar_aprendizaje_en_memoria` con categoría 'MINIATURAS' o 'ESTILO_VISUAL'.
- Cuando el usuario te pida investigar un canal o nicho, usa proactivamente tus herramientas para obtener datos 100% verídicos de YouTube antes de responder.

{learned_memory}
"""


def _sanitize_history_for_genai(raw_messages: List[Dict[str, Any]]) -> List[types.Content]:
    """
    Garantiza que el historial cumpla estrictamente las reglas de Gemini:
    - Alternancia estricta entre 'user' y 'model'.
    - Comienza siempre con 'user'.
    - Mensajes consecutivos del mismo rol se concatenan.
    - El historial DEBE terminar con 'model' para que la siguiente llamada chat.send_message() sea el nuevo turno de 'user'.
    """
    if not raw_messages:
        return []
        
    sanitized: List[types.Content] = []
    for msg in raw_messages:
        role = "user" if msg.get("role") == "user" else "model"
        content = msg.get("content", "").strip()
        if not content:
            continue
            
        if not sanitized:
            if role == "user":
                sanitized.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
        else:
            if sanitized[-1].role == role:
                # Merge into previous turn text
                prev_text = sanitized[-1].parts[0].text or ""
                sanitized[-1].parts = [types.Part.from_text(text=f"{prev_text}\n\n{content}")]
            else:
                sanitized.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
                
    # Si termina en 'user', lo retiramos porque el nuevo mensaje se enviará en chat.send_message()
    if sanitized and sanitized[-1].role == "user":
        sanitized.pop()
        
    return sanitized


def _execute_chat_turn(client: genai.Client, model_name: str, config: types.GenerateContentConfig, history: List[types.Content], payload: Any):
    """Ejecuta una ronda de chat completa con soporte automático de herramientas y tipos de partes."""
    chat = client.chats.create(model=model_name, config=config, history=history)
    return chat.send_message(payload)


async def stream_agent_chat(
    session_id: str, 
    user_message: str, 
    images: Optional[List[str]] = None,
    files: Optional[List[Dict[str, Any]]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Ejecuta el ciclo conversacional de Gemini con herramientas nativas automáticas, soporte multimodal de imágenes, archivos de texto y PDFs, fallback inteligente y streaming no bloqueante.
    """
    client = _get_client()
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # 1. Recuperar historial de mensajes PREVIOS de la sesión (antes de agregar el actual)
    session_data = memory_manager.get_session(session_id)
    history_messages = session_data.get("messages", []) if session_data else []
    
    # Preparar contenido guardado en BD y partes del payload de Gemini
    stored_user_content = ""
    payload_parts = []
    
    # 2. Procesar archivos adjuntos (texto, PDFs, imágenes)
    if files and len(files) > 0:
        for idx, f in enumerate(files):
            f_name = f.get("name", f"archivo_{idx}")
            f_type = f.get("type", "text")
            f_size = f.get("size", "")
            size_label = f" *({f_size})*" if f_size else ""

            if f_type == "text" or f.get("text"):
                txt_content = f.get("text", "")
                stored_user_content += f"📄 **Archivo adjunto:** `{f_name}`{size_label}\n\n"
                payload_parts.append(types.Part.from_text(text=f"=== Archivo Adjunto: {f_name} ===\n{txt_content}\n=== Fin del Archivo ==="))
            elif f_type == "pdf":
                raw_b64 = f.get("data", "")
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                try:
                    pdf_bytes = base64.b64decode(raw_b64)
                    pdf_filename = f"doc_{uuid.uuid4().hex[:8]}.pdf"
                    pdf_filepath = os.path.join(uploads_dir, pdf_filename)
                    with open(pdf_filepath, "wb") as pf:
                        pf.write(pdf_bytes)
                    stored_user_content += f"📑 **Documento PDF adjunto:** [{f_name}](/api/uploads/{pdf_filename})\n\n"
                    payload_parts.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
                except Exception as ex:
                    print(f"[GeminiAgent] Error processing PDF {f_name}: {ex}")
            elif f_type == "image":
                raw_b64 = f.get("data", "")
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                try:
                    img_bytes = base64.b64decode(raw_b64)
                    ref_filename = f"ref_{uuid.uuid4().hex[:8]}.jpg"
                    ref_filepath = os.path.join(uploads_dir, ref_filename)
                    with open(ref_filepath, "wb") as imgf:
                        imgf.write(img_bytes)
                    stored_user_content += f"![Referencia](/api/uploads/{ref_filename})\n\n"
                    payload_parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
                except Exception as ex:
                    print(f"[GeminiAgent] Error processing image {f_name}: {ex}")

    # 3. Procesar imágenes del array legacy si existen
    if images and len(images) > 0:
        for idx, img_b64 in enumerate(images):
            try:
                raw_b64 = img_b64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(raw_b64)
                ref_filename = f"ref_{uuid.uuid4().hex[:8]}.jpg"
                ref_filepath = os.path.join(uploads_dir, ref_filename)
                with open(ref_filepath, "wb") as imf:
                    imf.write(img_bytes)
                stored_user_content += f"![Referencia](/api/uploads/{ref_filename})\n\n"
                payload_parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
            except Exception as e:
                print(f"[GeminiAgent] Error processing attached legacy image {idx}: {e}")
                
    # Agregar texto del usuario al almacenamiento y al payload
    stored_user_content += user_message
    memory_manager.add_message(session_id, "user", stored_user_content)
    
    if user_message:
        payload_parts.append(types.Part.from_text(text=user_message))
        
    send_payload = payload_parts if len(payload_parts) > 1 else (payload_parts[0] if payload_parts else user_message)
    
    # Formatear y sanitizar historial para google-genai
    formatted_history = _sanitize_history_for_genai(history_messages)

    # Configuración de generación
    config = types.GenerateContentConfig(
        system_instruction=build_system_instruction(),
        tools=AVAILABLE_TOOLS,
        temperature=0.7
    )

    # Lista de modelos con fallback automático
    env_model = os.getenv("GEMINI_MODEL")
    candidate_models = [env_model] if env_model else FLASH_CANDIDATES
    
    selected_model_name = None
    response = None

    failed_attempts = []
    for model_name in candidate_models:
        try:
            # Ejecutar de forma no bloqueante en hilo con timeout de 70s
            response = await asyncio.wait_for(
                asyncio.to_thread(_execute_chat_turn, client, model_name, config, formatted_history, send_payload),
                timeout=70.0
            )
            selected_model_name = model_name
            break
        except asyncio.TimeoutError:
            print(f"[GeminiAgent] Timeout (70s) excedido con modelo {model_name}. Intentando fallback...")
            failed_attempts.append(f"{model_name}: Timeout")
            continue
        except Exception as e:
            failed_attempts.append(f"{model_name}: {type(e).__name__} - {str(e)[:100]}")
            print(f"[GeminiAgent] Fallo con modelo {model_name}: {e}")
            continue

    if not response:
        all_failures = " | ".join(failed_attempts)
        print(f"[GeminiAgent] Todos los modelos fallaron: {all_failures}")
        err_msg = f"El servicio de Gemini no respondió en el tiempo límite o alcanzó el límite de cuota ({all_failures[:300]}). Por favor, intenta de nuevo en unos segundos."
        memory_manager.add_message(session_id, "assistant", err_msg)
        yield {"type": "content", "content": err_msg}
        yield {"type": "done"}
        return

    # Notificar modelo activo utilizado
    yield {"type": "model_info", "model": selected_model_name}
    
    # Enviar respuesta final
    try:
        final_text = response.text if hasattr(response, "text") else "Análisis completado."
    except Exception:
        final_text = "Análisis completado."
        
    memory_manager.add_message(session_id, "assistant", final_text)
    yield {"type": "content", "content": final_text}
    yield {"type": "done"}
