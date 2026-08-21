"""
Gemini Flash Agent with Auto-Update, Tool Calling, Multi-Model Fallback and Long-Term Memory
"""

import os
import json
from typing import AsyncGenerator, Dict, Any, List
import google.generativeai as genai
from dotenv import load_dotenv

import youtube_tools
import memory_manager

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

def herramienta_analizar_canal(handle_o_nombre: str) -> str:
    """Obtiene datos, suscriptores, vistas totales, fecha de creación y descripción de un canal."""
    res = youtube_tools.analizar_canal(handle_o_nombre)
    return json.dumps(res, ensure_ascii=False)

def herramienta_analizar_videos_velocidad(canal_identificador: str, max_videos: int = 25) -> str:
    """Analiza los vídeos de un canal calculando velocidad de vistas por día y Viral Ratio para encontrar los mejores Outliers."""
    res = youtube_tools.analizar_videos_velocidad(canal_identificador, max_videos)
    return json.dumps(res, ensure_ascii=False)

def herramienta_obtener_transcripcion(video_id: str) -> str:
    """Obtiene la transcripción, el conteo total de palabras y la velocidad de locución (palabras/minuto) de un vídeo."""
    res = youtube_tools.obtener_transcripcion(video_id)
    return json.dumps(res, ensure_ascii=False)

def herramienta_buscar_competencia_espanol(termino: str) -> str:
    """Busca vídeos y canales existentes en español para una temática o título dado para verificar competencia o brecha de mercado."""
    res = youtube_tools.buscar_competencia_espanol(termino)
    return json.dumps(res, ensure_ascii=False)

def herramienta_guardar_aprendizaje_en_memoria(categoria: str, regla_o_preferencia: str) -> str:
    """Guarda un aprendizaje o regla permanente en la memoria a largo plazo del agente."""
    res = memory_manager.add_insight(categoria, regla_o_preferencia)
    return json.dumps({"status": "guardado", "insight": res}, ensure_ascii=False)


AVAILABLE_TOOLS = [
    herramienta_analizar_canal,
    herramienta_analizar_videos_velocidad,
    herramienta_obtener_transcripcion,
    herramienta_buscar_competencia_espanol,
    herramienta_guardar_aprendizaje_en_memoria
]

TOOL_DISPATCH = {
    "herramienta_analizar_canal": herramienta_analizar_canal,
    "herramienta_analizar_videos_velocidad": herramienta_analizar_videos_velocidad,
    "herramienta_obtener_transcripcion": herramienta_obtener_transcripcion,
    "herramienta_buscar_competencia_espanol": herramienta_buscar_competencia_espanol,
    "herramienta_guardar_aprendizaje_en_memoria": herramienta_guardar_aprendizaje_en_memoria
}


def build_system_instruction() -> str:
    learned_memory = memory_manager.format_memory_for_system_prompt()
    
    return f"""Eres YieldChat, un Consultor y Estratega de Élite en Crecimiento de Canales de YouTube Faceless (Automatización de YouTube).
Tu objetivo es ayudar al usuario a descubrir nichos de océano azul, auditar canales competidores con métricas reales, analizar outliers por velocidad de vistas/día, diseñar guiones de alta retención, sugerir configuraciones de voz (TTS/ElevenLabs/Qwen) y generar prompts de imágenes y miniaturas de máxima conversión.

Tienes acceso directo a herramientas en tiempo real de la API de YouTube:
1. `herramienta_analizar_canal`: Para obtener radiografías completas de cualquier canal.
2. `herramienta_analizar_videos_velocidad`: Para analizar todos los vídeos y calcular velocidad (vistas/día) y Viral Ratio.
3. `herramienta_obtener_transcripcion`: Para contar palabras y velocidad de habla de un vídeo.
4. `herramienta_buscar_competencia_espanol`: Para comprobar si un formato ya está saturado o es un Océano Azul en español.
5. `herramienta_guardar_aprendizaje_en_memoria`: Para registrar automáticamente preferencias, canales o reglas clave del usuario.

### REGLAS DE RESPUESTA:
- Sé directo, analítico, estructurado y sin rodeos innecesarios.
- Usa tablas de Markdown para resumir métricas de vídeos y comparativas.
- Cuando sugieras miniaturas, indica siempre la composición, el prompt de IA para Midjourney/Flux y el texto exacto (Línea 1 en blanco / Línea 2 en amarillo).
- Cuando el usuario te pregunte por configuraciones técnicas (como voces TTS, prompts, o pacing de guiones), proporciona la configuración exacta lista para copiar y pegar.
- Cuando el usuario te pida investigar un canal o nicho, usa proactivamente tus herramientas para obtener datos 100% verídicos de YouTube antes de responder.

{learned_memory}
"""


async def stream_agent_chat(session_id: str, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Ejecuta el ciclo conversacional de Gemini con herramientas, fallback inteligente de modelos y streaming.
    """
    _configure_gemini()
    
    # 1. Recuperar historial de mensajes de la sesión
    session_data = memory_manager.get_session(session_id)
    history_messages = session_data.get("messages", []) if session_data else []
    
    # Guardar mensaje del usuario
    memory_manager.add_message(session_id, "user", user_message)
    
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

    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=build_system_instruction(),
                tools=AVAILABLE_TOOLS,
                generation_config=genai.GenerationConfig(temperature=0.7)
            )
            chat = model.start_chat(history=formatted_history)
            response = chat.send_message(user_message)
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
    
    # Bucle de llamadas a herramientas y respuesta final
    tool_calls_executed = []
    max_tool_iterations = 6
    iterations = 0
    
    while iterations < max_tool_iterations:
        iterations += 1
        
        # Comprobar si Gemini quiere ejecutar una herramienta
        function_calls = []
        for part in response.candidates[0].content.parts:
            if fn := getattr(part, "function_call", None):
                function_calls.append(fn)
                
        if not function_calls:
            # Respuesta final lista
            final_text = response.text
            memory_manager.add_message(session_id, "assistant", final_text, tool_calls=tool_calls_executed)
            yield {"type": "content", "content": final_text}
            yield {"type": "done"}
            return
            
        # Ejecutar cada herramienta solicitada
        tool_responses = {}
        for fn in function_calls:
            fn_name = fn.name
            fn_args = dict(fn.args)
            
            yield {"type": "tool_start", "tool": fn_name, "args": fn_args}
            tool_calls_executed.append({"tool": fn_name, "args": fn_args})
            
            tool_func = TOOL_DISPATCH.get(fn_name)
            if tool_func:
                try:
                    tool_res_str = tool_func(**fn_args)
                except Exception as e:
                    tool_res_str = json.dumps({"error": str(e)})
            else:
                tool_res_str = json.dumps({"error": f"Herramienta {fn_name} no encontrada"})
                
            yield {"type": "tool_done", "tool": fn_name}
            tool_responses[fn_name] = tool_res_str
            
        # Enviar resultado de herramientas a Gemini
        response = chat.send_message(
            genai.protos.Content(
                parts=[
                    genai.protos.Part.from_function_response(
                        name=name,
                        response={"result": res}
                    ) for name, res in tool_responses.items()
                ]
            )
        )

    # Fallback si alcanzó el límite de iteraciones de herramientas
    final_text = response.text if hasattr(response, "text") else "Análisis completado."
    memory_manager.add_message(session_id, "assistant", final_text, tool_calls=tool_calls_executed)
    yield {"type": "content", "content": final_text}
    yield {"type": "done"}
