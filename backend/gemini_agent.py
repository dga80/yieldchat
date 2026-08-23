"""
Gemini Flash Agent with Auto-Update, Native Tool Calling, Multi-Model Fallback and Long-Term Memory
"""

import os
import json
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

import youtube_tools
import memory_manager
import image_tools
from PIL import Image
import io
import base64


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

FLASH_CANDIDATES = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest"
]

def _configure_gemini():
    if not API_KEY or API_KEY == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY no está configurada en .env")
    genai.configure(api_key=API_KEY)


def get_active_model_name() -> str:
    env_model = os.getenv("GEMINI_MODEL")
    if env_model:
        return env_model
    return "gemini-3.6-flash"


# ── Herramientas declaradas para Gemini ───────────────────────────────────────

def herramienta_analizar_canal(handle_o_nombre: str) -> dict:
    """Obtiene datos, suscriptores, vistas totales, fecha de creación y descripción de un canal de YouTube."""
    return youtube_tools.analizar_canal(handle_o_nombre)

def herramienta_analizar_videos_velocidad(canal_identificador: str, max_videos: int = 25) -> dict:
    """Analiza los vídeos de un canal calculando velocidad de vistas por día y Viral Ratio para encontrar los mejores Outliers."""
    return youtube_tools.analizar_videos_velocidad(canal_identificador, max_videos)

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

def herramienta_generar_imagen(prompt_visual: str, aspect_ratio: str = "16:9", estilo: str = "cinematic aesthetic, 8k") -> dict:
    """Genera una imagen/miniatura real en alta definición con IA (Nano Banana / Flux) y la incrusta en el chat.
    aspect_ratio puede ser '16:9' (YouTube / Miniaturas / B-roll), '9:16' (Shorts / Vertical) o '1:1' (Foto Perfil).
    Retorna el enlace a la imagen y el bloque Markdown para mostrarla en el chat."""
    return image_tools.generar_imagen(prompt=prompt_visual, aspect_ratio=aspect_ratio, estilo_adicional=estilo)


AVAILABLE_TOOLS = [
    herramienta_analizar_canal,
    herramienta_analizar_videos_velocidad,
    herramienta_obtener_transcripcion,
    herramienta_buscar_competencia_espanol,
    herramienta_guardar_aprendizaje_en_memoria,
    herramienta_generar_imagen
]


def build_system_instruction() -> str:
    learned_memory = memory_manager.format_memory_for_system_prompt()
    
    return f"""Eres YieldChat, un Consultor y Estratega de Élite en Crecimiento de Canales de YouTube Faceless (Automatización de YouTube).
Tu objetivo es ayudar al usuario a descubrir nichos de océano azul, auditar canales competidores con métricas reales, analizar outliers por velocidad de vistas/día, diseñar guiones de alta retención, sugerir configuraciones de voz (TTS/ElevenLabs/Qwen), generar imágenes y miniaturas con IA y aprender estilos visuales a partir de imágenes de referencia.

Tienes acceso directo a herramientas en tiempo real:
1. `herramienta_analizar_canal`: Para obtener radiografías completas de cualquier canal.
2. `herramienta_analizar_videos_velocidad`: Para analizar todos los vídeos y calcular velocidad (vistas/día) y Viral Ratio.
3. `herramienta_obtener_transcripcion`: Para contar palabras y velocidad de habla de un vídeo.
4. `herramienta_buscar_competencia_espanol`: Para comprobar si un formato ya está saturado o es un Océano Azul en español.
5. `herramienta_guardar_aprendizaje_en_memoria`: Para registrar automáticamente preferencias, canales o reglas clave del usuario.
6. `herramienta_generar_imagen`: Para generar imágenes y miniaturas reales directamente en el chat usando Nano Banana / Flux. Úsala SIEMPRE que el usuario te pida crear, generar o diseñar una miniatura o imagen visual. Cuando la herramienta retorne la imagen, asegúrate de incluir el enlace markdown ![descripción](url) y los detalles del prompt en tu respuesta.

### REGLAS DE RESPUESTA:
- Sé directo, analítico, estructurado y sin rodeos innecesarios.
- Usa tablas de Markdown para resumir métricas de vídeos y comparativas.
- Cuando el usuario te pida una miniatura o imagen, INVOCA `herramienta_generar_imagen` con un prompt visual detallado (en inglés, con iluminación cinematográfica, composición clara y estilo definido).
- Si el usuario te envía una o varias IMÁGENES DE REFERENCIA:
  1. Analiza con visión artificial su estilo (paleta de colores, trazo, iluminación, ángulo, disposición del personaje y texto).
  2. Si el usuario te pide aprender el estilo, llama a `herramienta_guardar_aprendizaje_en_memoria` con categoría 'MINIATURAS' o 'ESTILO_VISUAL' guardando la fórmula estética exacta.
  3. Si el usuario te pide generar una imagen basada en la referencia, usa los mismos parámetros estilísticos detectados.

{learned_memory}
"""


async def stream_agent_chat(
    session_id: str, 
    user_message: str, 
    images: Optional[List[str]] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Ejecuta el ciclo conversacional de Gemini con herramientas nativas automáticas, soporte multimodal de imágenes, fallback inteligente y streaming.
    """
    _configure_gemini()
    
    # 1. Recuperar historial de mensajes de la sesión
    session_data = memory_manager.get_session(session_id)
    history_messages = session_data.get("messages", []) if session_data else []
    
    # Preparar contenido guardado en BD
    stored_user_content = user_message
    
    # Procesar imágenes adjuntas para Gemini
    pil_images = []
    if images and len(images) > 0:
        for idx, img_b64 in enumerate(images):
            try:
                # Quitar prefijo data:image/...;base64, si existe
                raw_b64 = img_b64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(raw_b64)
                
                # Guardar imagen localmente como referencia
                uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
                os.makedirs(uploads_dir, exist_ok=True)
                ref_filename = f"ref_{uuid.uuid4().hex[:8]}.jpg"
                ref_filepath = os.path.join(uploads_dir, ref_filename)
                with open(ref_filepath, "wb") as f:
                    f.write(img_bytes)
                
                # Inyectar markdown de la referencia en el mensaje del usuario
                img_md = f"![Referencia](/api/uploads/{ref_filename})\n\n"
                stored_user_content = img_md + stored_user_content
                
                # PIL Image para Gemini Vision
                pil_img = Image.open(io.BytesIO(img_bytes))
                pil_images.append(pil_img)
            except Exception as e:
                print(f"[GeminiAgent] Error processing attached image {idx}: {e}")
                
    # Guardar mensaje del usuario en SQLite
    memory_manager.add_message(session_id, "user", stored_user_content)
    
    # Formatear historial para google-generativeai
    formatted_history = []
    for msg in history_messages:
        role = "user" if msg["role"] == "user" else "model"
        formatted_history.append({
            "role": role,
            "parts": [msg["content"]]
        })

    # Lista de modelos con fallback automático
    env_model = os.getenv("GEMINI_MODEL")
    candidate_models = [env_model] if env_model else FLASH_CANDIDATES
    
    chat = None
    selected_model_name = None
    response = None

    # Contenido de la consulta actual (multimodal si hay imágenes)
    send_payload = pil_images + [user_message] if pil_images else user_message

    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=build_system_instruction(),
                tools=AVAILABLE_TOOLS,
                generation_config=genai.GenerationConfig(temperature=0.7)
            )
            # Habilitar function calling automático nativo
            chat = model.start_chat(history=formatted_history, enable_automatic_function_calling=True)
            response = chat.send_message(send_payload)
            selected_model_name = model_name
            break
        except Exception as e:
            err_str = str(e).lower()
            print(f"[GeminiAgent] Fallback from {model_name}: {e}")
            if "quota" in err_str or "429" in err_str or "not found" in err_str or "404" in err_str:
                continue
            else:
                # Error fatal
                raise e

    if not chat or not response:
        err_msg = "Todos los modelos de Gemini alcanzaron su cuota de peticiones. Por favor, espera 1 minuto o revisa tu cuota en Google AI Studio."
        memory_manager.add_message(session_id, "assistant", err_msg)
        yield {"type": "content", "content": err_msg}
        yield {"type": "done"}
        return

    # Notificar modelo activo utilizado
    yield {"type": "model_info", "model": selected_model_name}
    
    # Enviar respuesta final
    final_text = response.text if hasattr(response, "text") else "Análisis completado."
    memory_manager.add_message(session_id, "assistant", final_text)
    yield {"type": "content", "content": final_text}
    yield {"type": "done"}

