FROM python:3.11-slim

# Crear usuario estándar para Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Instalar dependencias
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copiar el código del backend
COPY --chown=user . .

# Puerto estándar de Hugging Face Spaces
EXPOSE 7860

# Iniciar FastAPI en el puerto 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
