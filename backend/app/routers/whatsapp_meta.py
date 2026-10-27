"""Vinculo da loja com a API oficial do WhatsApp (Meta Cloud API).

Alimenta a pagina de apoio "Conectar o WhatsApp oficial": guarda as credenciais da
loja, testa a conexao passo a passo e so entao troca o provedor de envio.
Credenciais e provedor atual so mudam por acao explicita da loja.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session as get_db
from app.security.permissions_decorator import require_permission_dependency
from app.whatsapp.meta_cloud import MetaCloudClient, MetaCloudError, versao_da_api
from app.whatsapp.models import TenantWhatsAppConfig
from app.whatsapp.tenant_context import whatsapp_tenant_context

logger = logging.getLogger(__name__)

PROVEDOR_META = "meta_cloud"
STATUS_AGUARDANDO = "aguardando_teste"
STATUS_CONECTADO = "conectado"
STATUS_ERRO = "erro"

router = APIRouter(
    prefix="/whatsapp/config/meta",
    tags=["WhatsApp API oficial (Meta)"],
    dependencies=[Depends(require_permission_dependency("crm.configurar"))],
)


class Credenciais(BaseModel):
    waba_id: str = Field(min_length=5, max_length=40)
    phone_number_id: str = Field(min_length=5, max_length=40)
    # Em branco = manter o que ja esta salvo (o segredo nunca volta para a tela).
    access_token: str | None = Field(default=None, max_length=1000)
    app_secret: str | None = Field(default=None, max_length=200)


def _so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def _config(
    db: Session, tenant_id: Any, criar: bool = False
) -> TenantWhatsAppConfig | None:
    config = (
        db.query(TenantWhatsAppConfig)
        .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
        .first()
    )
    if config is None and criar:
        # Mantem o provedor que a loja ja usa (inclusive o padrao do ambiente):
        # criar a linha nao pode trocar o envio de ninguem.
        config = TenantWhatsAppConfig(
            tenant_id=tenant_id,
            provider=os.getenv("WHATSAPP_DEFAULT_PROVIDER", "waha").lower(),
        )
        db.add(config)
        db.flush()
    return config


def _url_do_webhook(tenant_id: Any) -> str:
    base = str(settings.COREPET_PUBLIC_API_URL).rstrip("/")
    return f"{base}/webhook/whatsapp/{tenant_id}"


def _iso(valor: datetime | None) -> str | None:
    return valor.isoformat() if valor else None


def montar_estado(
    config: TenantWhatsAppConfig | None, tenant_id: Any
) -> dict[str, Any]:
    """Estado do vinculo para a tela (nunca devolve token nem segredo)."""
    return {
        "webhook_url": _url_do_webhook(tenant_id),
        "verify_token": (config.webhook_secret if config else "") or None,
        "versao_da_api": versao_da_api(),
        "credenciais": {
            "waba_id": getattr(config, "meta_waba_id", None),
            "phone_number_id": getattr(config, "meta_phone_number_id", None),
            "tem_token": bool(config and config.meta_access_token),
            "tem_app_secret": bool(config and config.meta_app_secret),
        },
        "status": {
            "codigo": getattr(config, "meta_status", None),
            "detalhe": getattr(config, "meta_status_detalhe", None),
            "verificado_em": _iso(getattr(config, "meta_verificado_em", None)),
            "numero": getattr(config, "meta_numero_exibicao", None),
            "nome_verificado": getattr(config, "meta_nome_verificado", None),
            "qualidade": getattr(config, "meta_qualidade", None),
            "ultimo_webhook_em": _iso(getattr(config, "meta_ultimo_webhook_em", None)),
        },
        "provedor_atual": (config.provider if config else None),
        "ativo": bool(config and (config.provider or "").lower() == PROVEDOR_META),
    }


def _cliente(config: TenantWhatsAppConfig) -> MetaCloudClient:
    if not (config.meta_access_token and config.meta_phone_number_id):
        raise HTTPException(
            status_code=422,
            detail="Salve primeiro o token e o ID do número de telefone.",
        )
    return MetaCloudClient(
        access_token=config.meta_access_token,
        phone_number_id=config.meta_phone_number_id,
        waba_id=config.meta_waba_id,
    )


@router.get("/estado")
async def estado(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        config = _config(db, tenant_id)
        return montar_estado(config, tenant_id)


@router.post("/token-de-verificacao")
async def gerar_token_de_verificacao(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria o 'token de verificação' que a loja cola no webhook do app da Meta."""
    _, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        config = _config(db, tenant_id, criar=True)
        if not config.webhook_secret:
            config.webhook_secret = secrets.token_urlsafe(24)
            db.commit()
        return montar_estado(config, tenant_id)


@router.put("/credenciais")
async def salvar_credenciais(
    dados: Credenciais,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    waba = _so_digitos(dados.waba_id)
    numero_id = _so_digitos(dados.phone_number_id)
    if len(waba) < 5 or len(numero_id) < 5:
        raise HTTPException(
            status_code=422,
            detail="Os IDs da Meta têm só números. Copie de novo da tela de configuração da API.",
        )
    with whatsapp_tenant_context(tenant_id):
        config = _config(db, tenant_id, criar=True)
        config.meta_waba_id = waba
        config.meta_phone_number_id = numero_id
        if dados.access_token and dados.access_token.strip():
            config.meta_access_token = dados.access_token.strip()
        if dados.app_secret and dados.app_secret.strip():
            config.meta_app_secret = dados.app_secret.strip()
        if not config.webhook_secret:
            config.webhook_secret = secrets.token_urlsafe(24)
        # Dados mudaram: o teste anterior nao vale mais. O provedor NAO muda aqui.
        config.meta_status = STATUS_AGUARDANDO
        config.meta_status_detalhe = "Dados salvos. Falta testar a conexão."
        config.meta_verificado_em = None
        db.commit()
        return montar_estado(config, tenant_id)


def _passo(identificador: str, ok: bool, mensagem: str, **extra: Any) -> dict[str, Any]:
    return {"id": identificador, "ok": ok, "mensagem": mensagem, **extra}


@router.post("/testar")
async def testar(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Confere token, número, conta e webhook. Não altera o provedor de envio."""
    _, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        config = _config(db, tenant_id)
        if config is None:
            raise HTTPException(
                status_code=422, detail="Salve as credenciais antes de testar."
            )
        cliente = _cliente(config)
        passos: list[dict[str, Any]] = []
        conectado = False
        try:
            numero = await cliente.consultar_numero()
            config.meta_numero_exibicao = numero.get("display_phone_number")
            config.meta_nome_verificado = numero.get("verified_name")
            config.meta_qualidade = numero.get("quality_rating")
            passos.append(
                _passo(
                    "numero",
                    True,
                    f"Número {numero.get('display_phone_number') or ''} encontrado"
                    + (
                        f" ({numero.get('verified_name')})"
                        if numero.get("verified_name")
                        else ""
                    ),
                )
            )
            conta = await cliente.consultar_conta()
            passos.append(
                _passo(
                    "conta",
                    True,
                    f"Conta do WhatsApp “{conta.get('name', '')}” encontrada",
                )
            )
            apps = await cliente.apps_inscritos()
            passos.append(
                _passo(
                    "app_inscrito",
                    bool(apps),
                    "O app recebe os eventos da conta."
                    if apps
                    else "O app ainda não está inscrito na conta, então as respostas dos tutores não chegam.",
                    pode_corrigir=not apps,
                )
            )
            conectado = True
            config.meta_status = STATUS_CONECTADO
            config.meta_status_detalhe = None
        except MetaCloudError as erro:
            config.meta_status = STATUS_ERRO
            config.meta_status_detalhe = erro.mensagem[:300]
            passos.append(
                _passo("erro", False, erro.mensagem, passo_do_guia=erro.passo)
            )
        config.meta_verificado_em = datetime.utcnow()
        db.commit()
        recebeu = bool(config.meta_ultimo_webhook_em)
        passos.append(
            _passo(
                "webhook",
                recebeu,
                "A Meta já enviou um evento para o webhook."
                if recebeu
                else "Ainda não chegou nenhum evento pelo webhook. Envie uma mensagem para o número "
                "e teste de novo.",
            )
        )
        return {
            "conectado": conectado,
            "passos": passos,
            "estado": montar_estado(config, tenant_id),
        }


@router.post("/inscrever-app")
async def inscrever_app(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Inscreve o app na conta do WhatsApp (passo que faz o webhook receber eventos)."""
    _, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        config = _config(db, tenant_id)
        if config is None:
            raise HTTPException(
                status_code=422, detail="Salve as credenciais primeiro."
            )
        try:
            await _cliente(config).inscrever_app()
        except MetaCloudError as erro:
            raise HTTPException(status_code=422, detail=erro.mensagem) from erro
        return {"ok": True}


@router.post("/ativar")
async def ativar(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Passa a enviar e receber pela API oficial. Só depois de um teste bem-sucedido."""
    _, tenant_id = user_and_tenant
    with whatsapp_tenant_context(tenant_id):
        config = _config(db, tenant_id)
        if config is None or config.meta_status != STATUS_CONECTADO:
            raise HTTPException(
                status_code=409,
                detail="Teste a conexão com sucesso antes de ativar.",
            )
        if not config.meta_app_secret:
            raise HTTPException(
                status_code=409,
                detail="Informe o segredo do app (App Secret): sem ele não dá para confirmar que "
                "as mensagens recebidas vêm da Meta.",
            )
        config.provider = PROVEDOR_META
        db.commit()
        logger.info("Tenant %s passou a usar a API oficial da Meta", tenant_id)
        return montar_estado(config, tenant_id)
