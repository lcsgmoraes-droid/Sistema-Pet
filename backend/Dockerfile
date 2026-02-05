# ============================================================================
# DOCKERFILE - BACKEND (FastAPI + SQLAlchemy)
# Sistema Pet Shop Pro - Backend API
# FASE 8.4 - Docker Endurecido (production-ready)
# ============================================================================

# Usar Python 3.11 slim (menor, mais seguro)
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Variáveis de ambiente para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copiar requirements primeiro (cache de layers do Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código da aplicação
COPY --chown=appuser:appuser . .

# Criar diretório para uploads e dados com permissões corretas
RUN mkdir -p /app/uploads /app/data && \
    chown -R appuser:appuser /app

# Mudar para usuário não-root
USER appuser

# Expor porta 8000 (FastAPI/Uvicorn)
EXPOSE 8000

# Healthcheck usando endpoint /health (FASE 8.1)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para rodar a aplicação
# SEM --reload em produção (performance)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

