#!/bin/bash
# ==============================================================================
# YieldChat Launcher — Asistente Estratégico de YouTube
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================"
echo "          Iniciando YieldChat (Gemini Flash)          "
echo "======================================================"

# Iniciar Backend FastAPI en puerto 8001
echo "[1/2] Iniciando Backend en puerto 8001..."
cd "$DIR/backend"
"$DIR/backend/.venv/bin/uvicorn" main:app --host 127.0.0.1 --port 8001 --reload &
BACKEND_PID=$!

# Iniciar Frontend Vite en puerto 5174
echo "[2/2] Iniciando Frontend en puerto 5174..."
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Esperar 2 segundos para que arranquen los servicios
sleep 2

# Abrir el navegador en la interfaz
open "http://localhost:5174"

echo ""
echo "-> YieldChat está activo en: http://localhost:5174"
echo "-> Presiona Ctrl+C para detener la aplicación."

# Capturar salida para apagar ambos procesos al cerrar la terminal
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM EXIT
wait
