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
import re
from contextvars import ContextVar
from typing import AsyncGenerator, Dict, Any, List, Optional
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

import youtube_tools
import memory_manager

load_dotenv()

_current_session_id: ContextVar[str] = ContextVar("_current_session_id", default="")
_session_created_notes: Dict[str, List[Dict[str, Any]]] = {}

FLASH_CANDIDATES = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite"
]

API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_REQUEST_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "40000"))  # 40s timeout HTTP por defecto
_key_round_robin_index: int = 0


def get_all_api_keys() -> List[str]:
    """Retorna todas las claves API disponibles configuradas en .env o entorno."""
    keys: List[str] = []

    # 1. Comprobar GEMINI_API_KEYS (lista separada por comas)
    multi = (os.getenv("GEMINI_API_KEYS") or "").strip()
    if multi:
        for k in multi.split(","):
            k = k.strip()
            if k and k != "your_gemini_api_key_here" and k not in keys:
                keys.append(k)

    # 2. Comprobar variables individuales
    for var in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_SECONDARY"]:
        k = (os.getenv(var) or "").strip()
        if k and k != "your_gemini_api_key_here" and k not in keys:
            keys.append(k)

    if not keys and API_KEY and API_KEY != "your_gemini_api_key_here":
        keys.append(API_KEY)

    return keys


def get_next_api_key() -> str:
    """Retorna la siguiente clave de la lista aplicando rotación Round-Robin."""
    global _key_round_robin_index
    keys = get_all_api_keys()
    if not keys:
        raise ValueError("No hay ninguna clave GEMINI_API_KEY configurada en .env")
    key = keys[_key_round_robin_index % len(keys)]
    _key_round_robin_index = (_key_round_robin_index + 1) % len(keys)
    return key


def _get_client(api_key: Optional[str] = None, timeout_ms: int = DEFAULT_REQUEST_TIMEOUT_MS) -> genai.Client:
    key = api_key or get_next_api_key()
    return genai.Client(
        api_key=key,
        http_options=types.HttpOptions(timeout=timeout_ms)
    )


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

def herramienta_evaluar_packaging_danilov(titulo: str, thumbnail_url: str = "") -> dict:
    """Audita el empaque (título y miniatura) aplicando la regla de los 3 elementos de Tim Danilov y la brecha de curiosidad para Smart TV y móviles."""
    return youtube_tools.evaluar_packaging_3_elementos(titulo, thumbnail_url)

def herramienta_diseccionar_hook_30s(video_id: str) -> dict:
    """Analiza los primeros 30-40 segundos de la transcripción de un vídeo para verificar promesa del título, elevación de apuestas y ausencia de intros vacías."""
    return youtube_tools.diseccionar_hook_30_segundos(video_id)

def herramienta_niche_bending_generator(nicho_origen: str, formato_probado: str, categoria_alto_rpm: str) -> dict:
    """Aplica la metodología Niche Bending cruzando un formato viral probado con un micronicho de alto RPM para crear conceptos de canal únicos."""
    return youtube_tools.generar_matriz_niche_bending(nicho_origen, formato_probado, categoria_alto_rpm)

def herramienta_crear_nota_sesion(titulo: str, contenido: str, categoria: str = "Estrategia") -> dict:
    """Crea y guarda una nota o cápsula estratégica en la columna lateral de la conversación actual. Usa esta herramienta cuando el usuario te pida crear una nota, archivar un resumen, guardar ideas o estructurar apuntes para su panel lateral."""
    s_id = _current_session_id.get()
    if not s_id:
        return {"status": "error", "message": "No hay sesión activa"}
    cat = categoria.strip() if categoria and categoria.strip() else "Estrategia"
    note = memory_manager.create_note(s_id, titulo, contenido, cat)
    if s_id not in _session_created_notes:
        _session_created_notes[s_id] = []
    _session_created_notes[s_id].append(note)
    return {"status": "nota_creada", "nota": note}

def herramienta_generar_imagen(prompt: str, aspect_ratio: str = "16:9", estilo: str = "") -> dict:
    """Genera una imagen o miniatura de alta definición con IA usando el pipeline Google Banana / Flux, respetando la memoria visual y estilo del canal (16:9 para YouTube, 9:16 para Shorts, 1:1 para perfil)."""
    s_id = _current_session_id.get()
    folder_id = None
    if s_id:
        try:
            import sqlite3
            conn = sqlite3.connect(memory_manager.DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT folder_id FROM sessions WHERE id = ?", (s_id,))
            row = cur.fetchone()
            if row:
                folder_id = row[0]
            conn.close()
        except Exception:
            pass

    import image_tools
    res = image_tools.generar_imagen(
        prompt=prompt,
        aspect_ratio=aspect_ratio or "16:9",
        modelo="google-banana",
        estilo_adicional=estilo,
        folder_id=folder_id,
        session_id=s_id
    )
    return res


def herramienta_consultar_conversacion_carpeta(identificador_o_titulo: str) -> dict:
    """Consulta y lee el contenido íntegro y detallado (todos los mensajes y notas) de otra conversación de la misma carpeta actual. Pasa el ID de la conversación (ej: chat-12345) o palabras de su título."""
    s_id = _current_session_id.get()
    if not s_id:
        return {"status": "error", "message": "No hay sesión activa"}

    session_data = memory_manager.get_session(s_id)
    if not session_data or not session_data.get("folder_id"):
        return {"status": "error", "message": "La conversación actual no pertenece a ninguna carpeta temática."}

    folder_id = session_data["folder_id"]
    return memory_manager.get_full_session_in_folder(folder_id, identificador_o_titulo)


AVAILABLE_TOOLS = [
    herramienta_analizar_canal,
    herramienta_analizar_videos_velocidad,
    herramienta_obtener_transcripcion,
    herramienta_buscar_competencia_espanol,
    herramienta_guardar_aprendizaje_en_memoria,
    herramienta_evaluar_packaging_danilov,
    herramienta_diseccionar_hook_30s,
    herramienta_niche_bending_generator,
    herramienta_crear_nota_sesion,
    herramienta_generar_imagen,
    herramienta_consultar_conversacion_carpeta
]


def clean_script_chunk(text: str) -> str:
    """Elimina acotaciones de fin de parte, esperas de confirmación o preguntas para locución limpia."""
    cleaned = text.rstrip()
    
    # 1. Eliminar acotaciones entre paréntesis o asteriscos sobre fin de parte, espera de confirmación, etc.
    cleaned = re.sub(
        r'[\*\_\s]*\(?(?:fin de la parte|fin parte|parte \d+ finalizada|quedo a la espera|a la espera|espero tu confirmaci[óo]n).*?\)?[\*\_\s]*$',
        '',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL
    ).rstrip()
    
    # 2. Eliminar preguntas conversacionales de continuación
    patterns = [
        r'(?:¿|¡)?(?:quieres|deseas|te gustaría)\s+que\s+(?:continúe|siga|redacte).*$',
        r'(?:dime|avísame|indícame)\s+(?:si|cuando)\s+(?:quieres|deseas)\s+que\s+(?:continúe|siga).*$',
        r'(?:¿|¡)?pasamos\s+a\s+la\s+(?:siguiente|próxima)\s+parte\??.*$',
        r'(?:¿|¡)?quieres\s+hacer\s+algún\s+ajuste\s+antes\s+de\s+seguir\??.*$',
        r'(?:quedo a la espera|a la espera)\s+de\s+tu\s+confirmaci[óo]n.*$',
        r'\(?fin de la parte \d+.*?\)?$'
    ]
    for p in patterns:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE | re.MULTILINE).rstrip()
        
    # 3. Eliminar líneas finales de asteriscos, guiones o separadores residuales
    cleaned = re.sub(r'(\n\s*[\*\-_]{3,}\s*)+$', '', cleaned).rstrip()
    return cleaned


def find_last_script_part_in_history(history_messages: List[Dict[str, Any]]) -> Optional[int]:
    """Busca en el historial el número de la última parte de guion generada previamente."""
    if not history_messages:
        return None
    for msg in reversed(history_messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            matches = re.findall(r"(?:##\s*PARTE|Parte)\s*(\d+)", content, re.IGNORECASE)
            if matches:
                try:
                    return int(matches[-1])
                except ValueError:
                    pass
    return None


def detect_multi_part_request(user_message: str, history_messages: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, int]]:
    """
    Detecta si el mensaje del usuario solicita redactar un guion en múltiples partes o bucle autónomo.
    Retorna un diccionario con {'start': X, 'total': Y} o None.
    """
    msg = user_message.lower().strip()
    
    script_indicators = [
        'guion', 'guión', 'script', 'redacta', 'escribe', 'desarrolla', 
        'historia', 'narracion', 'narración', 'locucion', 'locución', 
        'video', 'vídeo', 'bucle autónomo', 'bucle autonomo', 'partes seguidas',
        'continua', 'continúa', 'sigue'
    ]
    is_script = any(ind in msg for ind in script_indicators)
    
    auto_indicators = [
        'sigue tú solo', 'sigue tu solo', 'sigue solo', 'sin parar', 
        'sin preguntarme', 'sin que yo te pida', 'sin que te lo pida', 
        'sin orden', 'sin que te dé la orden', 'sin que te de la orden',
        'sin que yo le de', 'sin que yo le dé', 'sin que yo te diga',
        'del tirón', 'del tiron', 'de un tirón', 'de un tiron',
        'bucle autónomo', 'bucle autonomo', 'de forma continua', 'ininterrumpid',
        'todas las partes', 'las 9 partes', 'partes seguidas', 'completo en',
        'todas seguidas', 'una detrás de otra', 'una detras de otra',
        'siguientes partes', 'partes que faltan', 'termina el guion',
        'completa el guion', 'sigue con el guion', 'continúa el guion', 'continua el guion',
        'crea las partes en bucle', 'en bucle'
    ]
    is_auto = any(ind in msg for ind in auto_indicators)
    
    # 1. Rango explícito: 'de la parte 3 a la 9', 'partes 2 a 9', 'parte 2 hasta 9'
    range_match = re.search(r'(?:de la\s+|de las\s+|las\s+)?partes?\s+(\d+)\s+(?:a|hasta|al)\s+(?:la\s+|las\s+)?(?:partes?\s+)?(\d+)', msg)
    if range_match:
        start_p = int(range_match.group(1))
        end_p = int(range_match.group(2))
        if 1 <= start_p < end_p <= 20:
            return {'start': start_p, 'total': end_p}
            
    # 2. Conteo de partes: '9 partes', 'en 9 partes', 'nueve partes'
    part_match = re.search(r'(\d+)\s*(?:partes|bloques|secciones|capítulos|capitulos)', msg)
    num_map = {'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10, 'once': 11, 'doce': 12}
    words_match = re.search(r'\b(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)\s*(?:partes|bloques|secciones)', msg)
    
    parts_count = None
    if part_match:
        parts_count = int(part_match.group(1))
    elif words_match:
        parts_count = num_map.get(words_match.group(1))
        
    if parts_count and (is_script or is_auto):
        if 2 <= parts_count <= 20:
            if any(q in msg for q in ['cuáles son', 'cuales son', 'qué son', 'que son', 'cuantas partes', 'cuántas partes']):
                return None
            return {'start': 1, 'total': parts_count}
            
    # 3. Solicitud de bucle autónomo o continuación automática
    if is_auto:
        last_part = find_last_script_part_in_history(history_messages or [])
        if last_part and last_part < 9:
            return {'start': last_part + 1, 'total': 9}
        if is_script or 'bucle' in msg:
            return {'start': 1, 'total': 9}
            
    return None


def build_system_instruction(folder_id: Optional[str] = None, current_session_id: Optional[str] = None) -> str:
    learned_memory = memory_manager.format_memory_for_system_prompt()
    folder_context = ""
    if folder_id and current_session_id:
        folder_context = memory_manager.format_folder_context_for_prompt(folder_id, current_session_id)

    return f"""Eres YieldChat, un Consultor y Estratega de Élite en Crecimiento de Canales de YouTube Faceless (Automatización de YouTube).
Tu objetivo es ayudar al usuario a descubrir nichos de océano azul, auditar canales competidores con métricas reales, analizar outliers por velocidad de vistas/día, diseñar guiones de alta retención, sugerir configuraciones de voz (TTS/ElevenLabs/Qwen), analizar imágenes de referencia con visión artificial y redactar prompts profesionales de imágenes y miniaturas de máxima conversión (para Midjourney v6, Flux y Nano Banana).

Tienes acceso directo a herramientas en tiempo real de la API de YouTube y de gestión de notas:
1. `herramienta_analizar_canal`: Para obtener radiografías completas de cualquier canal.
2. `herramienta_analizar_videos_velocidad`: Para analizar todos los vídeos y calcular velocidad (vistas/día) y Viral Ratio.
3. `herramienta_obtener_transcripcion`: Para contar palabras y velocidad de habla de un vídeo.
4. `herramienta_buscar_competencia_espanol`: Para comprobar si un formato ya está saturado o es un Océano Azul en español.
5. `herramienta_guardar_aprendizaje_en_memoria`: Para registrar automáticamente preferencias, canales o reglas clave del usuario.
6. `herramienta_evaluar_packaging_danilov`: Para auditar la regla de 3 elementos de miniatura y curiosidad del título.
7. `herramienta_diseccionar_hook_30s`: Para analizar la retención y estructura de los primeros 30 segundos de un guion.
8. `herramienta_niche_bending_generator`: Para generar conceptos de Niche Bending cruzando formatos probados con categorías de alto RPM.
9. `herramienta_crear_nota_sesion`: Para crear y archivar notas en la columna lateral de la conversación. SI EL USUARIO PIDE 'crea una nota sobre...', 'guarda esto en una nota' o pide archivar una síntesis, LLAMA SIEMPRE a esta herramienta con un título claro, el contenido estructurado en Markdown y su categoría ('Estrategia', 'Packaging', 'Guion', 'Outliers', etc.).
10. `herramienta_consultar_conversacion_carpeta`: Para leer el contenido íntegro y exhaustivo (todos los mensajes y notas) de otra conversación de la misma carpeta actual si necesitas consultar a fondo un guion largo o detalles específicos.

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
- Si el usuario solicita crear una nota, además de llamar a `herramienta_crear_nota_sesion`, confirma en tu respuesta que la nota ha sido creada y guardada en su columna lateral.
- Cuando el usuario te pida **unir respuestas, compilar partes de la conversación o generar un archivo .txt**:
  * Revisa con precisión el historial de la conversación para extraer las partes solicitadas.
  * Organiza el texto unificado con separadores limpios (ej. `=== TÍTULO DE LA SECCIÓN ===`) y estructura profesional.
  * Encapsula el documento consolidado en un bloque de código markdown especificando el nombre del archivo con `txt:nombre_descriptivo.txt` (ej: ````txt:guion_y_outliers_cosmos.txt ... ````) para habilitar su descarga en 1 clic desde el chat.

### REGLAS PARA GUIONES Y LOCUCIÓN TTS (QWEN 1.7 / ELEVENLABS):
- Cuando redactes guiones para YouTube:
  * Estructura cada sección con encabezado claro: `## PARTE X: [TÍTULO DESCRIPTIVO]`.
  * Redacta prosa limpia, envolvente y lista para ser leída por voz artificial: **NUNCA incluyas marcas de tiempo** (ej: `[00:00]`, `(2:15)`), ni acotaciones de sonido o música innecesarias que interrumpan el audio.
  * Mantén el ritmo narrativo elevado, con tensión, ganchos de curiosidad continuos y preguntas abiertas que obliguen a seguir escuchando.
  * En modo de generación de guion o bucle, redacta directamente la narración sin saludos iniciales ni preguntas de cierre como "¿Quieres que continúe?".

{learned_memory}
{folder_context}
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

        # Filtrar mensajes de error del sistema o avisos de cuota guardados en el historial
        if role == "model" and any(err_kw in content for err_kw in [
            "El servicio de Gemini no respondió",
            "503 UNAVAILABLE",
            "alcanzó el límite de cuota",
            "RESOURCE_EXHAUSTED",
            "is currently experiencing high demand"
        ]):
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
    files: Optional[List[Dict[str, Any]]] = None,
    is_disconnected: Optional[Any] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Ejecuta el ciclo conversacional de Gemini con herramientas nativas automáticas,
    soporte multimodal, bucle autónomo multi-paso para guiones, y streaming no bloqueante.
    """
    _current_session_id.set(session_id)
    _session_created_notes[session_id] = []
    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # 1. Recuperar historial de mensajes PREVIOS de la sesión (antes de agregar el actual)
    session_data = memory_manager.get_session(session_id)
    history_messages = session_data.get("messages", []) if session_data else []
    
    # Detectar si el usuario pide redactar un guion en múltiples partes o bucle autónomo
    multi_part_info = detect_multi_part_request(user_message, history_messages)
    
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
                    # Normalizar imagen (convertir RGBA PNG, WebP a RGB JPEG optimizado)
                    try:
                        pil_img = Image.open(io.BytesIO(img_bytes))
                        if pil_img.mode != "RGB":
                            pil_img = pil_img.convert("RGB")
                        if max(pil_img.size) > 1920:
                            pil_img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        pil_img.save(buf, format="JPEG", quality=88, optimize=True)
                        img_bytes = buf.getvalue()
                    except Exception as p_ex:
                        print(f"[GeminiAgent] Aviso normalizando imagen: {p_ex}")

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
                try:
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    if pil_img.mode != "RGB":
                        pil_img = pil_img.convert("RGB")
                    if max(pil_img.size) > 1920:
                        pil_img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=88, optimize=True)
                    img_bytes = buf.getvalue()
                except Exception as p_ex:
                    print(f"[GeminiAgent] Aviso normalizando imagen legacy: {p_ex}")

                ref_filename = f"ref_{uuid.uuid4().hex[:8]}.jpg"
                ref_filepath = os.path.join(uploads_dir, ref_filename)
                with open(ref_filepath, "wb") as imf:
                    imf.write(img_bytes)
                stored_user_content += f"![Referencia](/api/uploads/{ref_filename})\n\n"
                payload_parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
            except Exception as e:
                print(f"[GeminiAgent] Error processing attached legacy image {idx}: {e}")
                
    # Agregar texto del usuario al almacenamiento de la conversación
    stored_user_content += user_message
    memory_manager.add_message(session_id, "user", stored_user_content)
    
    if user_message:
        payload_parts.append(types.Part.from_text(text=user_message))
        
    send_payload = payload_parts if len(payload_parts) > 1 else (payload_parts[0] if payload_parts else user_message)
    
    # Formatear y sanitizar historial previo para google-genai
    formatted_history = _sanitize_history_for_genai(history_messages)

    folder_id = session_data.get("folder_id") if session_data else None

    # Configuración de generación optimizada con 8192 max tokens y contexto de carpeta
    config = types.GenerateContentConfig(
        system_instruction=build_system_instruction(folder_id=folder_id, current_session_id=session_id),
        tools=AVAILABLE_TOOLS,
        max_output_tokens=8192,
        temperature=0.7
    )

    # Lista de modelos con fallback automático
    env_model = os.getenv("GEMINI_MODEL")
    candidate_models = [env_model] if env_model else FLASH_CANDIDATES
    
    selected_model_name = None
    chat = None
    first_response = None
    failed_attempts = []

    # Ajustar payload inicial si se entra en bucle multi-parte
    initial_payload = send_payload
    if multi_part_info:
        start_part = multi_part_info["start"]
        total_parts = multi_part_info["total"]
        if start_part == 1:
            directive = (
                f"\n\n[DIRECTIVA DE BUCLE AUTÓNOMO ININTERRUMPIDO]: El usuario ha solicitado redactar las {total_parts} partes de forma continua. "
                f"Redacta de inmediato la PARTE 1 de {total_parts}. "
                f"REGLA OBLIGATORIA: NO te despidas, NO digas 'fin de la parte', NO digas 'quedo a la espera de confirmación', "
                f"NO hagas preguntas ni pidas confirmación, NO incluyas marcas de tiempo (ej. [00:00]). "
                f"Empieza directamente con '## PARTE 1: [TÍTULO]' y termina la narración limpiamente sin acotaciones finales."
            )
        else:
            directive = (
                f"\n\n[DIRECTIVA DE BUCLE AUTÓNOMO ININTERRUMPIDO]: Continúa el guion redactando la PARTE {start_part} de {total_parts}. "
                f"REGLA OBLIGATORIA: NO te despidas, NO digas 'fin de la parte', NO digas 'quedo a la espera de confirmación', "
                f"NO hagas preguntas ni pidas confirmación, NO incluyas marcas de tiempo (ej. [00:00]). "
                f"Empieza directamente con '## PARTE {start_part}: [TÍTULO]' y termina la narración limpiamente sin acotaciones finales."
            )

        if isinstance(initial_payload, list):
            initial_payload = list(initial_payload) + [types.Part.from_text(text=directive)]
        elif isinstance(initial_payload, types.Part):
            initial_payload = [initial_payload, types.Part.from_text(text=directive)]
        else:
            initial_payload = f"{initial_payload}{directive}"

    MODEL_TIMEOUT_SECONDS = float(os.getenv("GEMINI_MODEL_TIMEOUT", "22.0"))

    # Recuperar claves API configuradas y rotar Round-Robin para balancear cuotas
    all_keys = get_all_api_keys()
    if not all_keys:
        all_keys = [API_KEY or ""]

    global _key_round_robin_index
    start_k = _key_round_robin_index % len(all_keys)
    _key_round_robin_index = (_key_round_robin_index + 1) % len(all_keys)
    ordered_keys = all_keys[start_k:] + all_keys[:start_k]

    selected_model_name = None
    chat = None
    first_response = None
    failed_attempts = []

    for key_attempt_idx, current_api_key in enumerate(ordered_keys, 1):
        client = _get_client(api_key=current_api_key)
        real_key_num = all_keys.index(current_api_key) + 1
        key_label = f" [Key #{real_key_num}]" if len(all_keys) > 1 else ""

        for model_name in candidate_models:
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    curr_chat = client.chats.create(model=model_name, config=config, history=formatted_history)
                    if multi_part_info:
                        yield {
                            "type": "tool_start",
                            "tool": f"Redactando Parte {multi_part_info['start']} de {multi_part_info['total']}...",
                            "message": f"Redactando Parte {multi_part_info['start']} de {multi_part_info['total']}..."
                        }
                    else:
                        if attempt > 0:
                            yield {
                                "type": "tool_start",
                                "tool": f"Reintentando {model_name}{key_label}...",
                                "message": f"Reintentando {model_name}{key_label}..."
                            }
                        else:
                            yield {
                                "type": "tool_start",
                                "tool": f"Conectando con {model_name}{key_label}...",
                                "message": f"Conectando con {model_name}{key_label}..."
                            }

                    task = asyncio.create_task(asyncio.to_thread(curr_chat.send_message, initial_payload))
                    elapsed = 0.0
                    is_503 = False

                    while not task.done():
                        done, _ = await asyncio.wait([task], timeout=2.0)
                        elapsed += 2.0
                        if done:
                            try:
                                first_response = task.result()
                                chat = curr_chat
                                selected_model_name = model_name
                            except Exception as ex:
                                ex_str = str(ex)
                                print(f"[GeminiAgent] Error ejecutando send_message con modelo {model_name}{key_label}: {ex}")
                                failed_attempts.append(f"{model_name}{key_label}: {ex_str[:100]}")
                                if any(k in ex_str for k in ["503", "UNAVAILABLE", "high demand"]):
                                    is_503 = True
                            break
                        else:
                            if is_disconnected:
                                try:
                                    if await is_disconnected():
                                        print(f"[GeminiAgent] Cliente desconectado. Cancelando llamada a {model_name}.")
                                        task.cancel()
                                        break
                                except Exception:
                                    pass

                            if elapsed >= MODEL_TIMEOUT_SECONDS:
                                print(f"[GeminiAgent] Timeout de {int(elapsed)}s alcanzado para modelo {model_name}{key_label}. Cancelando y probando fallback...")
                                task.cancel()
                                failed_attempts.append(f"{model_name}{key_label}: Sin respuesta tras {int(elapsed)}s (timeout)")
                                yield {
                                    "type": "tool_start",
                                    "tool": f"Tiempo de espera agotado con {model_name} ({int(elapsed)}s). Probando modelo alternativo...",
                                    "message": f"Tiempo de espera agotado con {model_name} ({int(elapsed)}s). Probando modelo alternativo..."
                                }
                                break

                            # Enviar pista visual de tiempo transcurrido en tiempo real
                            if not multi_part_info:
                                yield {
                                    "type": "tool_start",
                                    "tool": f"Pensando con {model_name}{key_label} ({int(elapsed)}s)...",
                                    "message": f"Pensando con {model_name}{key_label} ({int(elapsed)}s)..."
                                }
                            yield {"type": "ping"}

                    if chat and first_response:
                        break

                    # Si hubo un pico de saturación 503 y queda reintento, pausar 1.5s antes del reintento
                    if is_503 and attempt < max_retries - 1:
                        yield {
                            "type": "tool_start",
                            "tool": f"{model_name} saturado momentáneamente. Reintentando...",
                            "message": f"{model_name} saturado momentáneamente. Reintentando..."
                        }
                        await asyncio.sleep(1.5)
                    else:
                        break

                except Exception as e:
                    failed_attempts.append(f"{model_name}{key_label}: {type(e).__name__} - {str(e)[:100]}")
                    print(f"[GeminiAgent] Fallo con modelo {model_name}{key_label}: {e}")
                    break

            if chat and first_response:
                break

        if chat and first_response:
            break

        # Si fallaron los modelos con esta clave y disponemos de otra clave, pivotar
        if key_attempt_idx < len(ordered_keys):
            next_key_num = all_keys.index(ordered_keys[key_attempt_idx]) + 1
            yield {
                "type": "tool_start",
                "tool": f"Pivotando automáticamente a clave API de respaldo (Key #{next_key_num})...",
                "message": f"Pivotando automáticamente a clave API de respaldo (Key #{next_key_num})..."
            }
            print(f"[GeminiAgent] Clave API agotada/saturada. Pivotando a clave #{next_key_num} ({key_attempt_idx + 1}/{len(ordered_keys)})...")

    if not chat or not first_response:
        all_failures = " | ".join(failed_attempts)
        print(f"[GeminiAgent] Todos los modelos fallaron: {all_failures}")
        err_msg = f"El servicio de Gemini no respondió a tiempo o los modelos están saturados ({all_failures[:300]}). Por favor, intenta de nuevo en unos segundos."
        # No persistir mensajes de fallo del sistema como respuestas para no contaminar el historial
        yield {"type": "tool_done"}
        yield {"type": "content", "content": err_msg}
        yield {"type": "done"}
        return

    # Limpiar indicador de herramienta activa antes de continuar
    yield {"type": "tool_done"}

    # Notificar modelo activo utilizado
    yield {"type": "model_info", "model": selected_model_name}

    # ── MODO ESTÁNDAR (UN SOLO TURNO) ─────────────────────────────────────────
    if not multi_part_info:
        # Emitir notas creadas durante el turno
        created_notes = _session_created_notes.pop(session_id, [])
        for n in created_notes:
            yield {"type": "note_created", "note": n}
        
        try:
            final_text = first_response.text if hasattr(first_response, "text") else "Análisis completado."
        except Exception:
            final_text = "Análisis completado."
            
        memory_manager.add_message(session_id, "assistant", final_text)
        yield {"type": "content", "content": final_text}
        yield {"type": "done"}
        return

    # ── MODO BUCLE AUTÓNOMO (MULTI-PARTE SCRIPTING) ───────────────────────────
    start_p = multi_part_info["start"]
    total_p = multi_part_info["total"]

    first_text = first_response.text if hasattr(first_response, "text") else ""
    first_text_cleaned = clean_script_chunk(first_text)
    
    accumulated_parts: List[str] = [first_text_cleaned]
    full_assistant_content = first_text_cleaned
    
    yield {"type": "content", "content": first_text_cleaned}
    yield {"type": "tool_done"}

    created_notes = _session_created_notes.pop(session_id, [])
    for n in created_notes:
        yield {"type": "note_created", "note": n}

    # Bucle autónomo continuo hasta total_p
    for part_idx in range(start_p + 1, total_p + 1):
        if is_disconnected:
            try:
                if await is_disconnected():
                    print(f"[GeminiAgent] Bucle autónomo detenido por cancelación del cliente en parte {part_idx}/{total_p}")
                    break
            except Exception:
                pass

        yield {
            "type": "tool_start",
            "tool": f"Redactando Parte {part_idx} de {total_p} autónomamente...",
            "message": f"Redactando Parte {part_idx} de {total_p} autónomamente..."
        }

        cont_prompt = (
            f"Continúa de inmediato con la PARTE {part_idx} de {total_p}. "
            f"Escribe la narración completa, fluida y con máxima profundidad para esta sección del vídeo. "
            f"REGLA OBLIGATORIA: NO te detengas, NO digas 'fin de la parte', NO digas 'quedo a la espera de confirmación', "
            f"NO pidas confirmación ni hagas preguntas (como '¿quieres que siga?'). "
            f"NUNCA incluyas marcas de tiempo (ej. [00:00]). "
            f"Empieza directamente con el encabezado '## PARTE {part_idx}: [TÍTULO]' y el texto de locución sin despedidas."
        )

        cleaned_chunk = ""
        max_retries = 2
        for attempt in range(max_retries):
            task = asyncio.create_task(asyncio.to_thread(chat.send_message, cont_prompt))
            next_resp = None
            client_disconnected = False
            elapsed_part = 0.0
            PART_TIMEOUT_SECONDS = float(os.getenv("GEMINI_PART_TIMEOUT", "45.0"))

            while not task.done():
                done, _ = await asyncio.wait([task], timeout=2.5)
                elapsed_part += 2.5
                if done:
                    try:
                        next_resp = task.result()
                    except Exception as ex:
                        print(f"[GeminiAgent] Error en send_message de parte {part_idx} (intento {attempt+1}): {ex}")
                    break
                else:
                    if is_disconnected:
                        try:
                            if await is_disconnected():
                                print(f"[GeminiAgent] Cliente desconectado durante generación de parte {part_idx}")
                                task.cancel()
                                client_disconnected = True
                                break
                        except Exception:
                            pass

                    if elapsed_part >= PART_TIMEOUT_SECONDS:
                        print(f"[GeminiAgent] Timeout de {int(elapsed_part)}s en parte {part_idx}. Cancelando intento...")
                        task.cancel()
                        yield {
                            "type": "tool_start",
                            "tool": f"Tiempo agotado en Parte {part_idx} ({int(elapsed_part)}s). Reintentando...",
                            "message": f"Tiempo agotado en Parte {part_idx} ({int(elapsed_part)}s). Reintentando..."
                        }
                        break

                    yield {
                        "type": "tool_start",
                        "tool": f"Redactando Parte {part_idx} de {total_p} ({int(elapsed_part)}s)...",
                        "message": f"Redactando Parte {part_idx} de {total_p} ({int(elapsed_part)}s)..."
                    }
                    yield {"type": "ping"}

            if client_disconnected:
                break

            if next_resp:
                raw_chunk = next_resp.text if hasattr(next_resp, "text") else ""
                cleaned_chunk = clean_script_chunk(raw_chunk)
                if cleaned_chunk:
                    break
            
            if attempt < max_retries - 1:
                print(f"[GeminiAgent] Reintentando parte {part_idx} en 3 segundos...")
                await asyncio.sleep(3.0)

        if not cleaned_chunk:
            print(f"[GeminiAgent] Parte {part_idx} no devolvió contenido tras reintentos. Deteniendo bucle.")
            yield {"type": "tool_done"}
            break

        accumulated_parts.append(cleaned_chunk)
        formatted_chunk = f"\n\n---\n\n{cleaned_chunk}"
        full_assistant_content += formatted_chunk
        yield {"type": "content", "content": formatted_chunk}
        yield {"type": "tool_done"}

        created_notes = _session_created_notes.pop(session_id, [])
        for n in created_notes:
            yield {"type": "note_created", "note": n}

    # Empaquetado final unificado y tarjeta descargable
    if accumulated_parts:
        full_script = "\n\n---\n\n".join(accumulated_parts)
        num_generated = len(accumulated_parts)
        
        if num_generated < total_p:
            note_title = f"Guion Parcial ({num_generated} de {total_p} Partes)"
            note = memory_manager.create_note(session_id, note_title, full_script, "Guion")
            yield {"type": "note_created", "note": note}
            
            txt_filename = f"guion_parcial_{num_generated}_de_{total_p}_partes.txt"
            download_card = (
                f"\n\n---\n\n"
                f"### 📄 Guion ({num_generated} de {total_p} Partes Generadas)\n\n"
                f"````txt:{txt_filename}\n{full_script}\n````\n\n"
                f"*📌 Se ha guardado como nota en tu panel lateral. Puedes pedir 'continúa el guion desde la parte {num_generated + 1}' para redactar las partes restantes.*"
            )
        else:
            note_title = f"Guion Completo ({total_p} Partes)"
            note = memory_manager.create_note(session_id, note_title, full_script, "Guion")
            yield {"type": "note_created", "note": note}
            
            txt_filename = f"guion_completo_{total_p}_partes.txt"
            download_card = (
                f"\n\n---\n\n"
                f"### 📄 Guion Completo ({total_p} Partes) Unificado\n\n"
                f"````txt:{txt_filename}\n{full_script}\n````\n\n"
                f"*📌 El guion completo se ha guardado automáticamente en tu panel lateral de Notas.*"
            )

        full_assistant_content += download_card
        yield {"type": "content", "content": download_card}

    memory_manager.add_message(session_id, "assistant", full_assistant_content)
    yield {"type": "done"}
