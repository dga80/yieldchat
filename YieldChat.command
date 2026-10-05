#!/bin/bash
# ==============================================================================
# YieldChat Launcher — Asistente Estratégico de YouTube
# ==============================================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "======================================================"
echo "       YieldChat — Asistente Estratégico YouTube      "
echo "======================================================"
echo ""
echo "  [1] Iniciar Servidor Local en este Mac (Offline / Seguro / Permanente) [Por defecto en 2s]"
echo "  [2] Abrir Versión en la Nube (Compartido con Móvil)"
echo ""
read -t 2 -p "Selecciona una opción [1]: " OPTION || OPTION="1"
[ -z "$OPTION" ] && OPTION="1"
echo ""

if [ "$OPTION" = "1" ]; then
    echo "🔄 Comprobando sincronización con GitHub..."
    cd "$DIR" && git pull origin main --quiet 2>/dev/null || true

    # Detectar IP local para acceso móvil en la misma red Wi-Fi
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

    echo "[1/2] Iniciando Backend local en puerto 8001..."
    cd "$DIR/backend"
    "$DIR/backend/.venv/bin/uvicorn" main:app --host 0.0.0.0 --port 8001 --reload &
    BACKEND_PID=$!

    echo "[2/2] Iniciando Frontend local en puerto 5174..."
    cd "$DIR/frontend"
    npm run dev -- --host 0.0.0.0 --port 5174 &
    FRONTEND_PID=$!

    sleep 2
    open "http://localhost:5174"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💻 Mac (local):               http://localhost:5174"
    echo "📱 Móvil (en la misma Wi-Fi):   http://$LOCAL_IP:5174"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "-> Todas las conversaciones se guardan directamente en este Mac (chat_history.db y conversations/)."
    echo "-> Presiona Ctrl+C para detener la aplicación."
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM EXIT
    wait
else
    echo "Abriendo YieldChat en la nube (compartido con tu móvil)..."
    open "https://dga80.github.io/yieldchat/"
fi
