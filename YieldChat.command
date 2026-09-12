#!/bin/bash
# ==============================================================================
# YieldChat Launcher — Asistente Estratégico de YouTube
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "======================================================"
echo "       YieldChat — Asistente Estratégico YouTube      "
echo "======================================================"
echo ""
echo "  [1] Abrir YieldChat en la Nube (Compartido con Móvil) [Por defecto en 4s]"
echo "  [2] Iniciar Servidor Local en este Mac (Offline)"
echo ""
read -t 4 -p "Selecciona una opción [1]: " OPTION || OPTION="1"
[ -z "$OPTION" ] && OPTION="1"
echo ""

if [ "$OPTION" = "2" ]; then
    echo "[1/2] Iniciando Backend local en puerto 8001..."
    cd "$DIR/backend"
    "$DIR/backend/.venv/bin/uvicorn" main:app --host 127.0.0.1 --port 8001 --reload &
    BACKEND_PID=$!

    echo "[2/2] Iniciando Frontend local en puerto 5174..."
    cd "$DIR/frontend"
    npm run dev &
    FRONTEND_PID=$!

    sleep 2
    open "http://localhost:5174"
    echo ""
    echo "-> YieldChat Local activo en: http://localhost:5174"
    echo "-> Presiona Ctrl+C para detener la aplicación."
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM EXIT
    wait
else
    echo "Abriendo YieldChat en la nube (compartido con tu móvil)..."
    open "https://dga80.github.io/yieldchat/"
fi
