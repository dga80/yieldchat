"""
Preloads today's strategic session and permanent business insights into YieldChat.
"""

import json
from datetime import datetime, timezone
import memory_manager

def seed():
    memory_manager.init_db()
    
    # 1. Precargar aprendizajes a largo plazo
    insights = [
        {
            "id": 1,
            "categoria": "CANAL_NUEVO",
            "regla": "Canal en desarrollo: 'Mente Kaizen'. Temática: Sabiduría y Filosofía Japonesa (Kaizen, Mottainai, Kakeibo, Bushido) cruzada con Dinero, Riqueza Silenciosa y Salarios Bajos.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": 2,
            "categoria": "FORMATO_GUION",
            "regla": "Duración de vídeo ideal: 22 a 26 minutos. Longitud de guion: 2.000 a 2.300 palabras (media de 2.263 palabras). Ritmo de voz pausado: 95-100 palabras por minuto con silencios meditativos.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": 3,
            "categoria": "MINIATURAS",
            "regla": "Estilo visual: Ilustración anime nostálgica estilo Studio Ghibli / Makoto Shinkai. Personaje humilde a la derecha, espacio despejado a la izquierda. Texto de 2 líneas (Línea 1 blanco, Línea 2 amarillo #FFD700) fiel a las palabras del título.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": 4,
            "categoria": "EDICION_VIDEO",
            "regla": "No usar animación total de vídeo con IA. Usar 100-130 imágenes estáticas de alta calidad (1 cada 10-12s) con zoom suave Ken Burns + capa de partículas de polvo zen + subtítulos palabra por palabra.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": 5,
            "categoria": "AUDIENCIA",
            "regla": "El 80% del éxito en este nicho es el Audio (guion narrativo + voz madura/cálida de ElevenLabs). Más del 60% de los usuarios escuchan el vídeo mientras descansan o duermen.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    memory_manager.save_all_insights(insights)
    
    # 2. Precargar sesión de conversación
    session_id = "estrategia-thewillwisdom-mentekaizen"
    existing = memory_manager.get_session(session_id)
    if not existing:
        memory_manager.create_session(session_id, "Estrategia @TheWillWisdom & Canal Mente Kaizen")
        
        messages = [
            ("user", "Hola, me gustaría saber si existen canales similares a @CosmoExplainsYT o en nichos de religión/filosofía para relajarse y aprender, y cómo analizarlos."),
            ("assistant", "Hola Dani. Analizamos el formato de documentales relajantes (docu-sleep / wisdom) y comprobamos la viabilidad en YouTube con Gemini y la YouTube API. Descubrimos que el nicho de historias bíblicas y sabiduría oriental cruzada con disciplina y dinero es un Océano Azul en español."),
            ("user", "Quiero analizar @TheWillWisdom y ver su rendimiento real, palabras de transcripción y cómo replicarlo bien."),
            ("assistant", "Auditamos los 48 vídeos de @TheWillWisdom en tiempo real con la YouTube API:\n\n1. **Top Outliers por Velocidad de Vistas/Día:**\n   - *Becoming Rich on a Low Salary*: 798K vistas (9.088 vistas/día, VR: 42x).\n   - *Building Wealth With Almost Nothing (Mottainai)*: 85K vistas (1.622 vistas/día).\n   - *Money Management for Low Income*: 75K vistas (1.134 vistas/día).\n\n2. **Métricas de Guion:**\n   - Media exacta de los 5 mejores vídeos: **2.263 palabras** (~22 a 25 minutos).\n   - Velocidad de locución: 95-100 palabras por minuto.\n\n3. **Estilo de Miniaturas:**\n   - Ilustración anime estilo Studio Ghibli con luz dorada, personaje modesto a la derecha y texto de 2 líneas (blanco/amarillo).\n\n4. **Nombre seleccionado para tu canal:** **Mente Kaizen**."),
            ("user", "¿Qué pasos seguimos ahora para empezar a producir los vídeos de Mente Kaizen?")
        ]
        
        for role, text in messages:
            memory_manager.add_message(session_id, role, text)
            
    print("Seed data cargado correctamente.")

if __name__ == "__main__":
    seed()
