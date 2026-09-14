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
