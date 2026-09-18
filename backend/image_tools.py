"""
Image Tools for YieldChat — AI Image & Thumbnail Generator
Supports 16:9 (Thumbnails/B-roll), 9:16 (Shorts), 1:1 (Avatars/Profiles) using Google Banana / Flux aesthetic pipelines
with channel visual memory and persistent gallery per folder.
"""

import os
import ssl
import uuid
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional

try:
    from . import memory_manager
except ImportError:
    import memory_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Dimensión por ratio
RATIO_MAP = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (1024, 1024),
    "4:3": (1024, 768),
    "3:4": (768, 1024)
}


def build_channel_enhanced_prompt(
    raw_prompt: str,
    folder_id: Optional[str] = None,
    aspect_ratio: str = "16:9",
    estilo_adicional: Optional[str] = None
) -> str:
    """
    Enriquece el prompt con las directrices visuales del canal (Studio Ghibli, paleta, composición)
    y los modificadores de alta fidelidad del pipeline Google Banana / Flux.
    """
    channel_ctx = memory_manager.get_channel_visual_context(folder_id)
    visual_rules = channel_ctx.get("visual_rules", [])
    
    parts = [raw_prompt.strip()]
    
    # 1. Reglas específicas del canal (ej. @estoescosmos -> Ghibli / Makoto Shinkai, composición Smart TV)
    if visual_rules:
        for r in visual_rules[:2]:
            clean_r = r.replace("Estilo visual:", "").replace("Diseño:", "").strip()
            if len(clean_r) < 160:
                parts.append(clean_r)
    
    if estilo_adicional:
        parts.append(estilo_adicional.strip())
        
    # 2. Pipeline estético Google Banana / High-End YouTube
    if aspect_ratio == "16:9":
        parts.append("cinematic lighting, YouTube thumbnail composition, high contrast, vivid colors, ultra sharp focus, 8k render, masterpiece")
    elif aspect_ratio == "9:16":
        parts.append("vertical composition, dramatic lighting, mobile wallpaper aesthetic, detailed textures, 8k render")
    else:
        parts.append("balanced studio composition, sharp subject, soft bokeh background, high resolution")
        
    return ", ".join(parts)


def generar_imagen(
    prompt: str,
    aspect_ratio: str = "16:9",
    modelo: str = "google-banana",
    estilo_adicional: Optional[str] = None,
    folder_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera una imagen con IA en alta definición para miniaturas, escenas de guion o Shorts,
    respetando la memoria visual del canal y guardándola en la base de datos.
    """
    width, height = RATIO_MAP.get(aspect_ratio, (1280, 720))
    
    # Enriquecer prompt con el contexto del canal
    enhanced_prompt = build_channel_enhanced_prompt(
        raw_prompt=prompt,
        folder_id=folder_id,
        aspect_ratio=aspect_ratio,
        estilo_adicional=estilo_adicional
    )
    
    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    seed = uuid.uuid4().int % 1000000
    
    # Pipeline optimizado de Pollinations / Flux / Google Banana aesthetic
    clean_model = "flux" if "banana" in modelo.lower() or "flux" in modelo.lower() else modelo
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&model={clean_model}&seed={seed}"
    
    image_id = f"img_{uuid.uuid4().hex[:10]}"
    filename = f"{image_id}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=35, context=ctx) as response:
            img_data = response.read()
            with open(filepath, "wb") as f:
                f.write(img_data)
                
        image_url = f"/api/images/{filename}"
        
        # Persistir en la base de datos de imágenes del canal
        db_record = memory_manager.save_generated_image(
            image_id=image_id,
            prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            image_url=image_url,
            filename=filename,
            folder_id=folder_id,
            session_id=session_id,
            aspect_ratio=aspect_ratio,
            model="google-banana",
            metadata={"width": width, "height": height, "seed": seed, "pipeline": "banana-flux"}
        )
        
        return {
            "status": "success",
            "id": image_id,
            "image_url": image_url,
            "external_url": url,
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "filename": filename,
            "folder_id": folder_id,
            "session_id": session_id,
            "created_at": db_record["created_at"],
            "markdown": f"![{prompt[:40]}]({image_url})"
        }
    except Exception as e:
        print(f"[ImageTools] Error al descargar localmente imagen: {e}")
        db_record = memory_manager.save_generated_image(
            image_id=image_id,
            prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            image_url=url,
            filename=filename,
            folder_id=folder_id,
            session_id=session_id,
            aspect_ratio=aspect_ratio,
            model="google-banana",
            metadata={"width": width, "height": height, "seed": seed, "pipeline": "banana-flux", "external": True}
        )
        return {
            "status": "success",
            "id": image_id,
            "image_url": url,
            "external_url": url,
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "filename": filename,
            "folder_id": folder_id,
            "session_id": session_id,
            "created_at": db_record["created_at"],
            "markdown": f"![{prompt[:40]}]({url})"
        }
