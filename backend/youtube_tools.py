"""
YouTube Intelligence Tools for YieldChat Agent
Connects directly to YouTube Data API v3 and YouTube Transcript API
"""

import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

def _get_youtube_client():
    if not API_KEY or API_KEY == "your_youtube_api_key_here":
        raise ValueError("YOUTUBE_API_KEY no está configurada en .env")
    return build("youtube", "v3", developerKey=API_KEY)


def analizar_canal(identificador: str) -> Dict[str, Any]:
    """
    Obtiene la radiografía completa de un canal de YouTube a partir de su @handle, URL, ID o nombre.
    """
    yt = _get_youtube_client()
    clean_id = identificador.strip()
    
    # Si viene como URL completa de YouTube (ej. https://youtube.com/@mrwealthlab?si=...)
    if "youtube.com" in clean_id or "youtu.be" in clean_id:
        handle_match = re.search(r'(@[a-zA-Z0-9_.-]+)', clean_id)
        if handle_match:
            clean_id = handle_match.group(1)
        else:
            ch_match = re.search(r'/(channel/)?(UC[a-zA-Z0-9_-]{22})', clean_id)
            if ch_match:
                clean_id = ch_match.group(2)
            else:
                clean_id = clean_id.split("?")[0].rstrip("/").split("/")[-1]

    # 1. Si es handle (@...)
    if clean_id.startswith("@") or not clean_id.startswith("UC"):
        handle = clean_id.lstrip("@")
        try:
            res = yt.channels().list(forHandle=handle, part="snippet,statistics,contentDetails").execute()
            if res.get("items"):
                item = res["items"][0]
                return _format_channel_data(item)
        except Exception:
            pass
            
    # 2. Si es ID directo (UC...)
    if clean_id.startswith("UC"):
        try:
            res = yt.channels().list(id=clean_id, part="snippet,statistics,contentDetails").execute()
            if res.get("items"):
                return _format_channel_data(res["items"][0])
        except Exception:
            pass

    # 3. Búsqueda por término
    res = yt.search().list(q=clean_id, type="channel", part="snippet", maxResults=1).execute()
    if res.get("items"):
        ch_id = res["items"][0]["snippet"]["channelId"]
        ch_res = yt.channels().list(id=ch_id, part="snippet,statistics,contentDetails").execute()
        if ch_res.get("items"):
            return _format_channel_data(ch_res["items"][0])
            
    return {"error": f"No se encontró ningún canal para '{identificador}'"}


def _format_channel_data(item: Dict[str, Any]) -> Dict[str, Any]:
    sn = item["snippet"]
    st = item["statistics"]
    cd = item.get("contentDetails", {})
    uploads_id = cd.get("relatedPlaylists", {}).get("uploads", "")
    
    subs = int(st.get("subscriberCount", 0))
    views = int(st.get("viewCount", 0))
    video_count = int(st.get("videoCount", 0))
    
    return {
        "channel_id": item["id"],
        "title": sn.get("title", ""),
        "handle": sn.get("customUrl", ""),
        "description": sn.get("description", "")[:400] + ("..." if len(sn.get("description", "")) > 400 else ""),
        "subscribers": subs,
        "total_views": views,
        "video_count": video_count,
        "created_at": sn.get("publishedAt", "")[:10],
        "country": sn.get("country", "Desconocido"),
        "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
        "uploads_playlist_id": uploads_id
    }


def analizar_videos_velocidad(canal_identificador: str, max_videos: int = 30) -> Dict[str, Any]:
    """
    Analiza todos los vídeos recientes de un canal y los ordena por su velocidad de vistas por día,
    Viral Ratio y engagement para detectar los verdaderos Outliers.
    """
    yt = _get_youtube_client()
    ch_info = analizar_canal(canal_identificador)
    if "error" in ch_info:
        return ch_info
        
    uploads_id = ch_info.get("uploads_playlist_id")
    if not uploads_id:
        uploads_id = "UU" + ch_info["channel_id"][2:]
        
    sub_count = max(ch_info.get("subscribers", 1), 1)
    now = datetime.now(timezone.utc)
    
    videos = []
    next_page = None
    
    while len(videos) < max_videos:
        batch_size = min(max_videos - len(videos), 50)
        pl_res = yt.playlistItems().list(
            playlistId=uploads_id,
            part="snippet",
            maxResults=batch_size,
            pageToken=next_page
        ).execute()
        
        v_ids = [it["snippet"]["resourceId"]["videoId"] for it in pl_res.get("items", [])]
        if not v_ids:
            break
            
        v_details = yt.videos().list(id=",".join(v_ids), part="snippet,statistics,contentDetails").execute()
        for v in v_details.get("items", []):
            sn = v["snippet"]
            st = v["statistics"]
            cd = v["contentDetails"]
            
            pub_date = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
            days_old = max((now - pub_date).total_seconds() / 86400.0, 0.5)
            views = int(st.get("viewCount", 0))
            likes = int(st.get("likeCount", 0))
            comments = int(st.get("commentCount", 0))
            
            views_per_day = views / days_old
            viral_ratio = views / sub_count
            eng_rate = ((likes + comments) / views * 100) if views > 0 else 0
            
            # Format duration ISO8601
            dur_str = cd.get("duration", "")
            
            videos.append({
                "video_id": v["id"],
                "title": sn.get("title", ""),
                "published_at": sn.get("publishedAt", "")[:10],
                "days_old": round(days_old, 1),
                "views": views,
                "likes": likes,
                "comments": comments,
                "views_per_day": round(views_per_day, 1),
                "viral_ratio": round(viral_ratio, 2),
                "engagement_pct": round(eng_rate, 2),
                "duration": dur_str,
                "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
                "url": f"https://www.youtube.com/watch?v={v['id']}"
            })
            
        next_page = pl_res.get("nextPageToken")
        if not next_page:
            break

    # Ordenar por velocidad de vistas diarias (momentum real)
    videos_by_velocity = sorted(videos, key=lambda x: x["views_per_day"], reverse=True)
    videos_by_views = sorted(videos, key=lambda x: x["views"], reverse=True)
    
    return {
        "channel_title": ch_info["title"],
        "channel_handle": ch_info["handle"],
        "subscribers": ch_info["subscribers"],
        "total_videos_analyzed": len(videos),
        "top_by_velocity": videos_by_velocity[:8],
        "top_by_views": videos_by_views[:8]
    }


def obtener_transcripcion(video_id: str) -> Dict[str, Any]:
    """
    Obtiene la transcripción oficial de un vídeo, calcula el conteo exacto de palabras,
    la duración y la velocidad de habla (palabras por minuto).
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi()
        transcript_obj = ytt.fetch(video_id, languages=['es', 'en', 'es-ES', 'es-419', 'en-US'])
        
        full_text = " ".join([item.text for item in transcript_obj])
        words = re.findall(r'\b\w+\b', full_text)
        word_count = len(words)
        
        # Estimate duration from timestamps
        last_snippet = transcript_obj[-1] if len(transcript_obj) > 0 else None
        duration_sec = (last_snippet.start + last_snippet.duration) if last_snippet else 0
        duration_min = round(duration_sec / 60.0, 1)
        wpm = round(word_count / duration_min, 1) if duration_min > 0 else 0
        
        # Summary snippet
        preview = full_text[:600] + ("..." if len(full_text) > 600 else "")
        
        return {
            "video_id": video_id,
            "total_words": word_count,
            "duration_minutes": duration_min,
            "words_per_minute": wpm,
            "preview_text": preview,
            "full_text": full_text
        }
    except Exception as e:
        return {"error": f"No se pudo obtener la transcripción del vídeo {video_id}: {str(e)}"}


def buscar_competencia_espanol(termino: str, max_resultados: int = 6) -> Dict[str, Any]:
    """
    Busca competidores y vídeos existentes en español para una temática o título dado.
    """
    yt = _get_youtube_client()
    res = yt.search().list(
        q=termino,
        part="snippet",
        maxResults=max_resultados,
        type="video",
        relevanceLanguage="es"
    ).execute()
    
    items = []
    v_ids = [it["id"]["videoId"] for it in res.get("items", [])]
    if v_ids:
        v_details = yt.videos().list(id=",".join(v_ids), part="snippet,statistics,contentDetails").execute()
        for v in v_details.get("items", []):
            sn = v["snippet"]
            st = v["statistics"]
            items.append({
                "video_id": v["id"],
                "title": sn.get("title", ""),
                "channel_title": sn.get("channelTitle", ""),
                "published_at": sn.get("publishedAt", "")[:10],
                "views": int(st.get("viewCount", 0)),
                "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url", ""),
                "url": f"https://www.youtube.com/watch?v={v['id']}"
            })
            
    return {
        "query": termino,
        "total_found": len(items),
        "results": items
    }


def evaluar_packaging_3_elementos(titulo: str, thumbnail_url: str = "") -> Dict[str, Any]:
    """
    Audita el empaque (Packaging) de un vídeo aplicando la metodología de Tim Danilov:
    - Regla de los 3 elementos en la miniatura (Sujeto, Contexto, Curiosidad/Contraste).
    - Longitud del título (<50 caracteres para Smart TV y dispositivos móviles).
    - Detección de Brecha de Curiosidad (Curiosity Gap) vs Título descriptivo aburrido.
    """
    title_clean = titulo.strip()
    title_length = len(title_clean)
    word_count = len(title_clean.split())
    
    # Análisis de longitud
    length_verdict = "Óptimo (<50 caracteres)" if title_length <= 50 else ("Aceptable (50-65 caracteres)" if title_length <= 65 else "Demasiado largo (>65 caracteres, se corta en móviles y TV)")
    
    # Análisis de brecha de curiosidad (palabras detonantes vs estilo manual)
    curiosity_triggers = ["por qué", "la verdad", "el secreto", "nunca", "nadie", "cómo", "el error", "regla", "lo que pasa", "why", "secret", "never", "truth", "how", "what happens"]
    boring_triggers = ["tutorial", "curso", "guía completa", "paso a paso", "introducción", "parte 1", "episodio", "guide", "step by step"]
    
    title_lower = title_clean.lower()
    has_curiosity = any(trig in title_lower for trig in curiosity_triggers)
    is_boring_manual = any(trig in title_lower for trig in boring_triggers)
    
    packaging_score = 70
    if title_length <= 50:
        packaging_score += 15
    elif title_length > 65:
        packaging_score -= 15
        
    if has_curiosity:
        packaging_score += 15
    if is_boring_manual:
        packaging_score -= 20
        
    packaging_score = max(20, min(100, packaging_score))
    
    return {
        "titulo": title_clean,
        "thumbnail_url": thumbnail_url,
        "caracteres": title_length,
        "palabras": word_count,
        "evaluacion_longitud": length_verdict,
        "tiene_brecha_curiosidad": has_curiosity,
        "es_estilo_manual_seo": is_boring_manual,
        "danilov_score": packaging_score,
        "regla_3_elementos": {
            "elemento_1_sujeto": "Elemento o personaje focal nítido (a la derecha o centro).",
            "elemento_2_contexto": "Entorno o fondo limpio con alto contraste que sitúa la historia.",
            "elemento_3_curiosidad": "Elemento visual paradójico o de contraste que obliga a hacer clic.",
            "regla_texto": "Máximo 2 a 3 palabras gigantes. Si es Smart TV: Línea 1 blanco, Línea 2 amarillo #FFD700."
        },
        "recomendacion_optimizacion": "Hacer el título más corto e intrigante. Asegurar que la miniatura complemente el título pero NO repita las mismas palabras exactas." if title_length > 50 or not has_curiosity else "Excelente empaque para Browse Features (Página de Inicio / Sugeridos)."
    }


def diseccionar_hook_30_segundos(video_id: str) -> Dict[str, Any]:
    """
    Extrae y analiza los primeros 30-40 segundos de la transcripción de un vídeo.
    Evalúa si cumple los 3 requisitos de Danilov:
    1. Reconfirmar la promesa del título de inmediato (evitar rebote).
    2. Elevar las apuestas (The Stakes) / introducir el conflicto.
    3. Abrir bucles narrativos (Open Loops) sin intros ni saludos largos.
    """
    clean_id = video_id.strip()
    if "watch?v=" in clean_id:
        clean_id = clean_id.split("watch?v=")[-1].split("&")[0]
    elif "youtu.be/" in clean_id:
        clean_id = clean_id.split("youtu.be/")[-1].split("?")[0]
        
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(clean_id, languages=['es', 'en', 'ja', 'pt', 'de'])
        
        hook_snippets = []
        full_hook_text = []
        for snip in transcript_list:
            start_sec = snip.get("start", 0)
            text = snip.get("text", "").strip()
            hook_snippets.append(text)
            full_hook_text.append(text)
            if start_sec >= 35.0 or len(" ".join(full_hook_text).split()) >= 100:
                break
                
        hook_text = " ".join(full_hook_text)
        words_in_hook = len(hook_text.split())
        
        # Detección de errores típicos en los primeros 30s
        intro_fluff_words = ["hola a todos", "bienvenidos a mi canal", "en el video de hoy", "suscríbete", "dale like", "hey guys", "welcome back", "in this video", "today we are going to"]
        has_intro_fluff = any(fluff in hook_text.lower() for fluff in intro_fluff_words)
        
        return {
            "video_id": clean_id,
            "palabras_primeros_35s": words_in_hook,
            "texto_del_gancho": hook_text,
            "diagnostico": {
                "tiene_relleno_o_saludo_innecesario": has_intro_fluff,
                "velocidad_arranque": "Lenta (presentación/saludo detectado)" if has_intro_fluff else "Rápida y directa al tema",
                "ritmo_estimado_ppm": round((words_in_hook / 35.0) * 60, 1)
            },
            "principios_hook_danilov": [
                "Segundo 0-5: Validar visualmente y verbalmente lo prometido en la miniatura.",
                "Segundo 6-15: Mostrar la consecuencia extrema o paradoja (las apuestas).",
                "Segundo 16-30: Abrir el bucle de curiosidad principal antes de arrancar la cronología."
            ]
        }
    except Exception as e:
        return {
            "video_id": clean_id,
            "error": f"No se pudo extraer la transcripción para analizar el gancho: {str(e)}",
            "consejo": "Para analizar el gancho manualmente, transcribe los primeros 30 segundos y verifica que no tenga intros vacías."
        }


def generar_matriz_niche_bending(nicho_origen: str, formato_probado: str, categoria_alto_rpm: str) -> Dict[str, Any]:
    """
    Aplica el método de 'Niche Bending' de Tim Danilov:
    Cruza un formato narrativo de probada tracción viral con un micronicho de alto RPM/demanda.
    """
    FORMATOS_ESTRELLA = {
        "mini_doc_misterio": "Mini-documental de investigación oscura (pacing tenso, estilo MagnatesMedia/Moon).",
        "timeline_auge_caida": "Línea temporal cinematográfica 'El ascenso y colapso de...' (Rise and Fall).",
        "animacion_zen_seinen": "Ilustración Seinen/Ghibli contemplativa con narrativa reflexiva (estilo Mente Kaizen / Frugalismo).",
        "simulacion_3d_mapas": "Animación geográfica y mapas geopolíticos 3D con datos estratégicos.",
        "paradoja_regla_oculta": "Desmitificación de paradojas: 'Por qué la regla del 99% te mantiene atrapado'."
    }
    
    formato_desc = FORMATOS_ESTRELLA.get(formato_probado.lower().strip(), formato_probado)
    
    return {
        "concepto": f"Niche Bending: {nicho_origen} ➔ {categoria_alto_rpm}",
        "formato_base": formato_desc,
        "nicho_objetivo": categoria_alto_rpm,
        "tesis_estrategica": f"Tomar la estructura de retención y diseño visual de '{nicho_origen}' y aplicarla a '{categoria_alto_rpm}', donde la competencia utiliza formatos monótonos o anticuados.",
        "pasos_accion": [
            "1. Localizar 3 vídeos virales en el nicho de origen para extraer sus arcos de tensión y hooks.",
            "2. Reemplazar la temática central por el dolor/tema del micronicho de alto RPM.",
            "3. Diseñar miniatura con la regla de 3 elementos adaptada al nuevo avatar.",
            "4. Comprobar competencia en español (Océano Azul)."
        ]
    }

