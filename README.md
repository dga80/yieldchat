# ⚡ YieldChat — Asistente Estratégico Autónomo de YouTube

YieldChat es un consultor conversacional inteligente diseñado para la **investigación, auditoría y estrategia de canales de YouTube Faceless**, impulsado por **Gemini Flash (con auto-actualización)** y conectado en tiempo real a la **YouTube Data API v3**.

---

## ✨ Características

* 🤖 **Gemini Flash Auto-Actualizable:** Descubre y utiliza dinámicamente la versión más reciente de Gemini Flash (`gemini-3.7-flash` / `gemini-flash-latest`).
* 🛠️ **Herramientas de YouTube (Function Calling):**
  * Radiografía y auditoría completa de canales (@handle, suscriptores, vistas, fecha de creación).
  * Análisis de **Outliers por Velocidad (Vistas/Día)** y **Viral Ratio**.
  * Extracción de transcripciones con cálculo de palabras y ritmo de locución (ppm).
  * Detección de brechas de mercado y competencia en español.
* 🧠 **Memoria a Largo Plazo Evolutiva:** Almacén permanente de aprendizajes, canales en producción y reglas de negocio inyectadas en cada conversación.
* 💾 **Persistencia SQLite:** Historial multi-sesión de chats persistente en local.
* 🎨 **Renderizado Visual:** Markdown enriquecido, tablas de rendimiento y botón de 1 clic para **Copiar Prompts de Imagen**.

---

## 🚀 Inicio Rápido

### En macOS (Un solo clic)
Haz doble clic en el archivo **`YieldChat.command`**. Arrancará el backend, el frontend y abrirá el navegador en `http://localhost:5174`.

### Manualmente

1. **Configurar claves en `backend/.env`:**
   ```env
   YOUTUBE_API_KEY=tu_clave_de_youtube
   GEMINI_API_KEY=tu_clave_de_gemini
   ```

2. **Iniciar Backend:**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --host 127.0.0.1 --port 8001 --reload
   ```

3. **Iniciar Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
