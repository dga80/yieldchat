"""
Image Tools for YieldChat — AI Image & Thumbnail Generator
Supports 16:9 (Thumbnails/B-roll), 9:16 (Shorts), 1:1 (Profiles) using Flux / Nano Banana aesthetic pipelines.
"""

import os
import ssl
import uuid
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional

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

def generar_imagen(
    prompt: str,
    aspect_ratio: str = "16:9",
    modelo: str = "flux",
    estilo_adicional: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera una imagen con IA en alta definición para miniaturas, escenas de guion o Shorts.
    Retorna la URL local o pública y el prompt utilizado.
    """
    width, height = RATIO_MAP.get(aspect_ratio, (1280, 720))
    
    # Enriquecer prompt según contexto si es necesario
    final_prompt = prompt
    if estilo_adicional:
        final_prompt = f"{prompt}, {estilo_adicional}"
        
    # Limpiar y codificar
    encoded_prompt = urllib.parse.quote(final_prompt)
    seed = uuid.uuid4().int % 1000000
    
    # URL de generación optimizada
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&model={modelo}&seed={seed}"
    
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
            }
        )
        
        filename = f"img_{uuid.uuid4().hex[:10]}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            img_data = response.read()
            with open(filepath, "wb") as f:
                f.write(img_data)
                
        # URL relativa para servir desde FastAPI
        image_url = f"/api/images/{filename}"
        
        return {
            "status": "success",
            "image_url": image_url,
            "external_url": url,
            "prompt_used": final_prompt,
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "filename": filename,
            "markdown": f"![{final_prompt[:40]}]({image_url})"
        }
    except Exception as e:
        print(f"[ImageTools] Error al generar imagen: {e}")
        return {
            "status": "success",
            "image_url": url,
            "external_url": url,
            "prompt_used": final_prompt,
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "markdown": f"![{final_prompt[:40]}]({url})"
        }
