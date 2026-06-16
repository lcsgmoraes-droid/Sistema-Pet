"""
Decorator de Idempotência para FastAPI
Garante que endpoints críticos não sejam executados mais de uma vez

USO:
    from app.idempotency import idempotent

    @router.post("/vendas/")
    @idempotent()  # ← Adiciona proteção de idempotência
    async def criar_venda(request: CriarVendaRequest, ...):
        ...

HEADER OPCIONAL:
    Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

    ⚠️ Se o header NÃO for enviado:
    - Uma chave UUID será gerada automaticamente
    - Log de warning será registrado
    - Idempotência continua ativa

COMPORTAMENTO:
    - Se a chave já foi processada → retorna resposta anterior (HTTP 200)
    - Se a chave está sendo processada → aguarda/retorna 409 Conflict
    - Se é nova → processa normalmente e armazena resultado
    - Se header ausente → gera UUID automático e processa
"""

import hashlib
import json
import logging
import uuid
from functools import wraps
from typing import Optional, Callable
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.idempotency_models import IdempotencyKey
from app.tenancy.context import get_current_tenant

logger = logging.getLogger(__name__)

# Configurações
IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_EXPIRATION_HOURS = 24


def _compute_request_hash(body: dict, path_params: dict) -> str:
    """
    Calcula hash SHA256 da requisição para detectar mudanças
    Inclui: body JSON + path parameters (ex: venda_id)
    """
    content = {"body": body, "path_params": path_params}
    serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _normalize_tenant_id(value):
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _extract_user_tenant_pair(value):
    if not isinstance(value, tuple) or len(value) < 2:
        return None, None

    user = value[0]
    tenant_id = _normalize_tenant_id(value[1])
    if user is None or tenant_id is None or not hasattr(user, "id"):
        return None, None
    return user, tenant_id


def _cleanup_expired_keys(
    db: Session, user_id: int, tenant_id, now: datetime | None = None
):
    """
    Remove chaves de idempotência expiradas (mais de 24h)
    Executado automaticamente antes de criar nova chave
    """
    try:
        resolved_tenant_id = _normalize_tenant_id(tenant_id)
        expiration_time = (now or datetime.utcnow()) - timedelta(
            hours=IDEMPOTENCY_EXPIRATION_HOURS
        )
        deleted = (
            db.query(IdempotencyKey)
            .filter(
                and_(
                    IdempotencyKey.user_id == user_id,
                    IdempotencyKey.tenant_id == resolved_tenant_id,
                    IdempotencyKey.created_at < expiration_time,
                )
            )
            .delete(synchronize_session=False)
        )

        if deleted > 0:
            db.commit()
            logger.info(
                f"🧹 Limpeza: removidas {deleted} chaves expiradas do user {user_id}"
            )
    except Exception as e:
        logger.error(f"❌ Erro na limpeza de chaves expiradas: {e}")
        db.rollback()


def idempotent(require_key: bool = True):
    """
    Decorator para tornar endpoints idempotentes

    Args:
        require_key: Se True (padrão), gera chave automática quando header ausente
                     Se False, a idempotência é completamente opcional

    Exemplo:
        @router.post("/vendas/")
        @idempotent()  # Idempotency-Key opcional (gera automático se ausente)
        async def criar_venda(...):
            pass

        @router.post("/vendas/{venda_id}/cancelar")
        @idempotent(require_key=False)  # Idempotência completamente opcional
        async def cancelar_venda(...):
            pass

    Comportamento:
        - Header fornecido → usa a chave do cliente
        - Header ausente + require_key=True → gera UUID automático
        - Header ausente + require_key=False → executa sem idempotência
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extrair dependências injetadas
            request: Optional[Request] = None
            db: Optional[Session] = None
            current_user = None
            tenant_id = None

            # Buscar Request, Session e User nos kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, Session):
                    db = arg

            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                elif isinstance(value, Session):
                    db = value
                elif key in ("current_user", "user"):
                    current_user = value
                elif key in ("user_and_tenant", "current_user_and_tenant"):
                    extracted_user, extracted_tenant = _extract_user_tenant_pair(value)
                    if extracted_user is not None:
                        current_user = extracted_user
                    if extracted_tenant is not None:
                        tenant_id = extracted_tenant

                if current_user is None or tenant_id is None:
                    extracted_user, extracted_tenant = _extract_user_tenant_pair(value)
                    if current_user is None and extracted_user is not None:
                        current_user = extracted_user
                    if tenant_id is None and extracted_tenant is not None:
                        tenant_id = extracted_tenant

            # Se não temos os componentes necessários, executa normalmente
            tenant_id = _normalize_tenant_id(tenant_id or get_current_tenant())

            if not request or not db or not current_user or tenant_id is None:
                logger.warning(
                    "⚠️ Idempotência: componentes não encontrados, executando sem proteção"
                )
                return await func(*args, **kwargs)

            # Verificar se há header de idempotência
            idempotency_key = request.headers.get(IDEMPOTENCY_HEADER)
            auto_generated = False

            if not idempotency_key:
                if require_key:
                    # Gerar chave automática em vez de retornar erro
                    idempotency_key = str(uuid.uuid4())
                    auto_generated = True
                    logger.warning(
                        f"⚠️ Idempotency-Key não fornecida. Gerando chave automática para segurança: {idempotency_key[:8]}..."
                    )
                else:
                    # Idempotência opcional, executa normalmente
                    return await func(*args, **kwargs)

            # Validar formato da chave (mínimo 16 caracteres) - apenas se não foi auto-gerada
            if not auto_generated and len(idempotency_key) < 16:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{IDEMPOTENCY_HEADER}' deve ter no mínimo 16 caracteres",
                )

            # Extrair informações da requisição
            endpoint = f"{request.method} {request.url.path}"
            user_id = current_user.id

            # Processar body da requisição
            try:
                body = (
                    await request.json()
                    if request.method in ["POST", "PUT", "PATCH"]
                    else {}
                )
            except Exception:
                body = {}

            # Path parameters (ex: venda_id)
            path_params = request.path_params

            # Calcular hash da requisição
            request_hash = _compute_request_hash(body, path_params)

            # Limpar chaves expiradas (otimização)
            _cleanup_expired_keys(db, user_id, tenant_id)

            # Buscar chave existente
            existing_key = (
                db.query(IdempotencyKey)
                .filter(
                    and_(
                        IdempotencyKey.user_id == user_id,
                        IdempotencyKey.tenant_id == tenant_id,
                        IdempotencyKey.chave_idempotencia == idempotency_key,
                    )
                )
                .first()
            )

            # Cenário 1: Chave já existe
            if existing_key:
                # Verificar se é a mesma requisição (mesmo hash)
                if existing_key.request_hash != request_hash:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"A chave de idempotência '{idempotency_key}' já foi usada "
                            f"para uma requisição diferente. Use uma chave única."
                        ),
                    )

                # Status: processing (ainda processando)
                if existing_key.status == "processing":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Requisição ainda está sendo processada. Tente novamente em alguns instantes.",
                    )

                # Status: failed (falhou anteriormente)
                if existing_key.status == "failed":
                    logger.info(
                        "♻️ Idempotência: reprocessando requisição que falhou anteriormente"
                    )
                    # Permite reprocessamento de requisições que falharam
                    existing_key.status = "processing"
                    existing_key.completed_at = None
                    existing_key.error_message = None
                    db.commit()
                    # Continua para processar...

                # Status: completed (já processado com sucesso)
                elif existing_key.status == "completed":
                    logger.info(
                        f"✅ Idempotência: retornando resposta anterior "
                        f"[{existing_key.endpoint}] key={idempotency_key[:8]}..."
                    )

                    # Retornar resposta armazenada
                    response_body = (
                        json.loads(existing_key.response_body)
                        if existing_key.response_body
                        else {}
                    )
                    return Response(
                        content=json.dumps(response_body, ensure_ascii=False),
                        status_code=existing_key.response_status_code or 200,
                        media_type="application/json",
                    )

            # Cenário 2: Nova chave - criar registro
            else:
                new_key = IdempotencyKey(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    endpoint=endpoint,
                    chave_idempotencia=idempotency_key,
                    request_hash=request_hash,
                    status="processing",
                )
                db.add(new_key)
                db.commit()
                db.refresh(new_key)
                existing_key = new_key

                key_origin = (
                    "auto-gerada" if auto_generated else "fornecida pelo cliente"
                )
                logger.info(
                    f"🔑 Idempotência: nova chave criada ({key_origin}) "
                    f"[{endpoint}] key={idempotency_key[:8]}... user={user_id}"
                )

            # Processar requisição
            try:
                # Executar função original
                result = await func(*args, **kwargs)

                # Armazenar resultado
                existing_key.status = "completed"
                existing_key.completed_at = datetime.utcnow()

                # Serializar resposta
                if isinstance(result, dict):
                    existing_key.response_status_code = 200
                    existing_key.response_body = json.dumps(
                        result, ensure_ascii=False, default=str
                    )
                elif isinstance(result, Response):
                    existing_key.response_status_code = result.status_code
                    existing_key.response_body = (
                        result.body.decode("utf-8") if result.body else None
                    )
                else:
                    # Tentar serializar qualquer objeto
                    existing_key.response_status_code = 200
                    existing_key.response_body = json.dumps(
                        result, ensure_ascii=False, default=str
                    )

                db.commit()

                logger.info(
                    f"✅ Idempotência: requisição processada com sucesso "
                    f"[{endpoint}] key={idempotency_key[:8]}..."
                )

                return result

            except Exception as e:
                # Registrar falha
                existing_key.status = "failed"
                existing_key.completed_at = datetime.utcnow()
                existing_key.error_message = str(e)
                db.commit()

                logger.error(
                    f"❌ Idempotência: requisição falhou "
                    f"[{endpoint}] key={idempotency_key[:8]}... erro={str(e)}"
                )

                # Re-raise para o FastAPI tratar
                raise

        return wrapper

    return decorator
