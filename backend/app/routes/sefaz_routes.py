"""
Rotas SEFAZ — Consulta de NF-e por chave de acesso.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import logging

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.models import Tenant
from app.produtos_compras_models import SefazDocumentoDistribuido
from app.security.permissions_decorator import require_permission_dependency
from app.services.sefaz_service import SefazConsumoIndevidoError, SefazService
from app.services.sefaz_tenant_config_service import SefazTenantConfigService
from app.services.sefaz_sync_coordinator import (
    SefazLockBusy,
    bloqueio_656_ate,
    proximo_sync_permitido,
    sefaz_coordinator,
)

router = APIRouter(prefix="/sefaz", tags=["sefaz"])
logger = logging.getLogger(__name__)
can_configure_sefaz = require_permission_dependency("configuracoes.editar")


class ConsultaNFeRequest(BaseModel):
    chave_acesso: str  # 44 dígitos


class ItemNFe(BaseModel):
    numero_item: int
    codigo_produto: str
    descricao: str
    ncm: Optional[str] = None
    cfop: Optional[str] = None
    quantidade: float
    unidade: str
    valor_unitario: float
    valor_total: float


class ConsultaNFeResponse(BaseModel):
    chave_acesso: str
    numero_nf: str
    serie: str
    data_emissao: str
    emitente_cnpj: str
    emitente_nome: str
    destinatario_cnpj: Optional[str] = None
    destinatario_nome: Optional[str] = None
    valor_total_nf: float
    itens: List[ItemNFe]
    aviso: str
    xml_nfe: Optional[str] = None


class SefazConfigUpdateRequest(BaseModel):
    enabled: bool = False
    modo: str = "mock"
    ambiente: str = "homologacao"
    uf: str = "SP"
    cnpj: str = ""
    cert_password: Optional[str] = None
    importacao_automatica: bool = False
    importacao_intervalo_min: int = 60


@router.post("/consultar", response_model=ConsultaNFeResponse)
async def consultar_nfe(
    payload: ConsultaNFeRequest,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Consulta uma NF-e na SEFAZ pela chave de acesso (44 dígitos).
    """
    chave = payload.chave_acesso.replace(" ", "").replace(".", "")

    if len(chave) != 44 or not chave.isdigit():
        raise HTTPException(
            status_code=422,
            detail="Chave de acesso inválida. Deve conter exatamente 44 dígitos numéricos.",
        )

    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    try:
        with sefaz_coordinator.config_guard():
            cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
            agora = datetime.now(timezone.utc)
            bloqueio = bloqueio_656_ate(cfg)
            if bloqueio is not None and bloqueio > agora:
                espera = int((bloqueio - agora).total_seconds()) + 1
                raise HTTPException(
                    status_code=429,
                    detail="SEFAZ bloqueou as consultas (cStat 656). Aguarde o horário indicado.",
                    headers={"Retry-After": str(espera)},
                )

            SefazService.garantir_pronto_para_consulta_real(cfg)
            janela = []
            for valor in cfg.get("consultas_chave_timestamps", []):
                try:
                    momento = datetime.fromisoformat(valor)
                    if momento.tzinfo is None:
                        momento = momento.replace(tzinfo=timezone.utc)
                    if momento > agora - timedelta(hours=1):
                        janela.append(momento)
                except (TypeError, ValueError):
                    continue
            # Reserva margem para outras modalidades no limite combinado de 20/h.
            if len(janela) >= 18:
                espera = (
                    int((janela[0] + timedelta(hours=1) - agora).total_seconds()) + 1
                )
                raise HTTPException(
                    status_code=429,
                    detail="Limite de consultas por chave atingido. Aguarde uma hora.",
                    headers={"Retry-After": str(max(1, espera))},
                )

            cfg["consultas_chave_timestamps"] = [
                momento.isoformat() for momento in (*janela, agora)
            ]
            SefazTenantConfigService.save_config(tenant_id, cfg)
            try:
                data = SefazService.consultar_nfe_por_chave(chave, cfg)
            except SefazConsumoIndevidoError as exc:
                bloqueio = datetime.now(timezone.utc) + timedelta(minutes=65)
                cfg["dfe_656_bloqueado_ate"] = bloqueio.isoformat()
                SefazTenantConfigService.save_config(tenant_id, cfg)
                raise HTTPException(
                    status_code=429,
                    detail="SEFAZ bloqueou as consultas (cStat 656). Tente novamente após a espera indicada.",
                    headers={"Retry-After": str(65 * 60)},
                ) from exc
    except SefazLockBusy as exc:
        raise HTTPException(
            status_code=409,
            detail="Outra consulta SEFAZ está em andamento. Aguarde alguns instantes.",
        ) from exc
    return ConsultaNFeResponse(**data)


@router.get("/config")
def get_config(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Retorna configuracao e status da SEFAZ por tenant sem expor segredo completo."""
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
    status = SefazService.status_configuracao(cfg)

    return {
        "enabled": status.enabled,
        "modo": cfg.get("modo", "mock"),
        "ambiente": cfg.get("ambiente", "homologacao"),
        "uf": cfg.get("uf", "SP"),
        "cnpj": cfg.get("cnpj", ""),
        "importacao_automatica": cfg.get("importacao_automatica", False),
        "importacao_automatica_status": (
            "desativada"
            if not cfg.get("importacao_automatica")
            else "configuracao_pendente"
            if not status.enabled or cfg.get("modo") != "real" or not status.cert_ok
            else "configurada"
        ),
        "importacao_intervalo_min": cfg.get("importacao_intervalo_min", 15),
        "ultimo_nsu": cfg.get("ultimo_nsu", "000000000000000"),
        "ultimo_sync_at": cfg.get("ultimo_sync_at"),
        "ultimo_sync_status": cfg.get("ultimo_sync_status", "nunca"),
        "ultimo_sync_mensagem": cfg.get(
            "ultimo_sync_mensagem", "Ainda nao sincronizado."
        ),
        "ultimo_sync_documentos": cfg.get("ultimo_sync_documentos", 0),
        "ultimo_sync_cstat": cfg.get("ultimo_sync_cstat"),
        "ultimo_sync_xmotivo": cfg.get("ultimo_sync_xmotivo"),
        "ultimo_sync_ult_nsu_retorno": cfg.get("ultimo_sync_ult_nsu_retorno"),
        "ultimo_sync_max_nsu_retorno": cfg.get("ultimo_sync_max_nsu_retorno"),
        "ultimo_max_nsu_confirmado": cfg.get("ultimo_max_nsu_confirmado"),
        "proximo_sync_permitido_at": (
            proximo_sync_permitido(cfg).isoformat()
            if proximo_sync_permitido(cfg)
            else None
        ),
        "cnpj_configurado": status.cnpj_configurado,
        "cert_path_configurado": status.cert_path_configurado,
        "cert_existe": status.cert_existe,
        "cert_senha_configurada": status.cert_senha_configurada,
        "cert_ok": status.cert_ok,
        "mensagem": status.mensagem,
        "pendencias": SefazService.pendencias_configuracao_real(cfg),
        "empresa": {
            "nome": tenant.name if tenant else None,
            "cnpj": SefazTenantConfigService.sanitize_cnpj(tenant.cnpj)
            if tenant
            else "",
            "uf": (tenant.uf or "").upper() if tenant and tenant.uf else "",
        },
    }


@router.get("/status-config")
def status_config_compat(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Compatibilidade com endpoint antigo."""
    return get_config(auth=auth, db=db)


@router.post("/config")
def update_config(
    payload: SefazConfigUpdateRequest,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
    _permission=Depends(can_configure_sefaz),
):
    """Salva configuracao SEFAZ por tenant (sem upload de certificado)."""
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    try:
        with sefaz_coordinator.config_guard():
            atual = SefazTenantConfigService.merged_config(tenant_id, tenant)
            novo_cnpj = SefazTenantConfigService.sanitize_cnpj(payload.cnpj)
            novo_ambiente = payload.ambiente.strip().lower()
            houve_sync = (
                bool(atual.get("ultimo_sync_at"))
                or str(atual.get("ultimo_nsu", "000000000000000")) != "000000000000000"
            )
            if houve_sync and (
                novo_cnpj != atual.get("cnpj") or novo_ambiente != atual.get("ambiente")
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "CNPJ e ambiente nao podem ser alterados apos iniciar a "
                        "distribuicao. Solicite migracao auditada do checkpoint NSU."
                    ),
                )
            novo = {
                **atual,
                "enabled": payload.enabled,
                "modo": payload.modo.strip().lower(),
                "ambiente": novo_ambiente,
                "uf": payload.uf.strip().upper(),
                "cnpj": novo_cnpj,
                "importacao_automatica": payload.importacao_automatica,
                "importacao_intervalo_min": payload.importacao_intervalo_min,
            }
            if payload.cert_password is not None:
                novo["cert_password"] = payload.cert_password
            SefazTenantConfigService.save_config(tenant_id, novo)
    except SefazLockBusy as exc:
        raise HTTPException(
            status_code=409, detail="Sincronizacao SEFAZ em andamento. Tente novamente."
        ) from exc
    status = SefazService.status_configuracao(novo)
    return {
        "ok": True,
        "mensagem": "Configuracao salva com sucesso.",
        "status": {
            "cert_ok": status.cert_ok,
            "mensagem": status.mensagem,
            "cert_existe": status.cert_existe,
            "cnpj_configurado": status.cnpj_configurado,
        },
    }


@router.post("/upload-certificado")
async def upload_certificado(
    file: UploadFile = File(...),
    cert_password: str = Form(...),
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
    _permission=Depends(can_configure_sefaz),
):
    """Recebe e valida certificado A1 (.pfx) por tenant."""
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    cert_path = await SefazTenantConfigService.save_certificate(tenant_id, file)
    cert_ok, cert_msg = SefazService._validar_certificado(cert_path, cert_password)
    if not cert_ok:
        Path(cert_path).unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=cert_msg)

    try:
        with sefaz_coordinator.config_guard():
            cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
            cfg["cert_path"] = cert_path
            cfg["cert_password"] = cert_password
            SefazTenantConfigService.save_config(tenant_id, cfg)
    except SefazLockBusy as exc:
        Path(cert_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=409, detail="Sincronizacao SEFAZ em andamento. Tente novamente."
        ) from exc

    status = SefazService.status_configuracao(cfg)

    return {
        "ok": True,
        "mensagem": "Certificado salvo e validado com sucesso.",
        "status": {
            "enabled": status.enabled,
            "modo": status.modo,
            "ambiente": status.ambiente,
            "cert_ok": True,
            "mensagem": status.mensagem,
        },
        "cert_path": cert_path,
    }


@router.get("/sync-status")
def get_sync_status(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Retorna status da ultima tentativa de sincronizacao automatica/manual."""
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)

    return {
        "ultimo_sync_at": cfg.get("ultimo_sync_at"),
        "ultimo_sync_status": cfg.get("ultimo_sync_status", "nunca"),
        "ultimo_sync_mensagem": cfg.get(
            "ultimo_sync_mensagem", "Ainda nao sincronizado."
        ),
        "ultimo_sync_documentos": cfg.get("ultimo_sync_documentos", 0),
        "ultimo_nsu": cfg.get("ultimo_nsu", "000000000000000"),
    }


@router.post("/sync-now")
def sync_now(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
    _permission=Depends(can_configure_sefaz),
):
    """
    Dispara sincronizacao manual.
    Usa o mesmo coordinator do scheduler para garantir exclusividade.
    """
    from datetime import datetime, timezone

    current_user, tenant_id = auth
    logger.info("[SEFAZ] [manual] Pedido de sync manual recebido")
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)

    now_dt = datetime.now(timezone.utc)

    # Respeita a proxima janela tambem no fluxo manual. Repetir o mesmo
    # ultNSU antes da hora pode provocar cStat 656.
    proximo_dt = proximo_sync_permitido(cfg)
    if proximo_dt is not None and now_dt < proximo_dt:
        faltam = int((proximo_dt - now_dt).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=429,
            detail=(
                f"Proxima consulta SEFAZ permitida em ~{faltam} minuto(s). "
                "Aguarde antes de sincronizar novamente."
            ),
        )

    # ── Verificar configuração ────────────────────────────────────────────────
    status = SefazService.status_configuracao(cfg)

    if not status.enabled:
        raise HTTPException(
            status_code=422,
            detail="SEFAZ desabilitado. Ative a integracao para sincronizar.",
        )

    if cfg.get("modo") != "real":
        return {
            "ok": True,
            "status": "pendente",
            "mensagem": "Integracao em modo mock. Troque para modo real para sincronizacao oficial.",
            "documentos": 0,
            "notas_salvas": 0,
            "notas_puladas": 0,
            "ultimo_nsu": cfg.get("ultimo_nsu", "000000000000000"),
        }

    if not status.cert_ok:
        raise HTTPException(
            status_code=422,
            detail=f"Configuracao incompleta: {status.mensagem}",
        )

    # ── Executar via coordinator ──────────────────────────────────────────────
    # Garante exclusividade: scheduler e sync-now nunca chamam SEFAZ ao mesmo tempo.
    config_path = SefazTenantConfigService._config_path(tenant_id)
    result = sefaz_coordinator.try_sync(
        tenant_id_str=str(tenant_id),
        config_path=config_path,
        cfg=cfg,
        reason="manual",
    )
    logger.info(
        f"[SEFAZ] [manual] Resultado sync manual — tenant {tenant_id} "
        f"status={result.get('status')} docs={result.get('documentos', 0)} "
        f"importadas={result.get('importadas', 0)}"
    )

    r_status = result.get("status")

    if r_status in ("already_running", "lock_busy"):
        raise HTTPException(
            status_code=409,
            detail="Sincronizacao SEFAZ ja esta em execucao. Aguarde alguns instantes.",
        )

    if r_status == "cooldown":
        raise HTTPException(
            status_code=429,
            detail="Aguarde o proximo horario de consulta SEFAZ antes de sincronizar.",
        )

    if r_status == "disabled":
        raise HTTPException(status_code=422, detail=result.get("mensagem"))

    if r_status == "erro_656":
        raise HTTPException(
            status_code=429,
            detail=result.get("mensagem", "SEFAZ bloqueou a requisicao (cStat 656)."),
        )

    if r_status == "error":
        raise HTTPException(
            status_code=502,
            detail=result.get("mensagem", "Erro interno na sincronizacao SEFAZ."),
        )

    return {
        "ok": True,
        "status": "ok",
        "mensagem": result.get("mensagem", "Sincronizacao concluida."),
        "documentos": result.get("documentos", 0),
        "notas_salvas": result.get("importadas", 0),
        "notas_puladas": result.get("duplicadas", 0),
        "ultimo_nsu": result.get(
            "ultimo_nsu", cfg.get("ultimo_nsu", "000000000000000")
        ),
        "proximo_permitido_at": result.get(
            "proximo_permitido_at", cfg.get("_proximo_sync_permitido_at")
        ),
        "max_nsu": result.get("max_nsu", ""),
        "c_stat": None,
        "x_motivo": None,
    }


@router.get("/nsu-status")
def get_nsu_status(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Retorna o checkpoint e o ultimo maxNSU observado em uma sincronizacao.
    Nao faz chamada extra a SEFAZ; a distancia entre NSUs nao e contagem de NFs.
    """
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)

    ultimo_nsu = cfg.get("ultimo_nsu", "000000000000000")
    max_nsu_observado = cfg.get("ultimo_max_nsu_confirmado")
    if not max_nsu_observado and cfg.get("ultimo_sync_status") == "ok":
        max_nsu_observado = cfg.get("ultimo_sync_max_nsu_retorno")
    if max_nsu_observado == "000000000000000":
        max_nsu_observado = None

    return {
        "ultimo_nsu": ultimo_nsu,
        "max_nsu_sefaz": max_nsu_observado,
        "gap_documentos": None,
        "documentos_por_lote": 50,
        "lotes_restantes": None,
        "atualizado": bool(max_nsu_observado),
        "ultimo_sync_at": cfg.get("ultimo_sync_at"),
        "ultimo_sync_status": cfg.get("ultimo_sync_status", "nunca"),
        "ultimo_sync_cstat": cfg.get("ultimo_sync_cstat"),
        "proximo_sync_permitido_at": (
            proximo_sync_permitido(cfg).isoformat()
            if proximo_sync_permitido(cfg)
            else None
        ),
        "erro": None,
    }


@router.get("/documentos")
def listar_documentos_distribuidos(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    status: Optional[str] = None,
    tipos: Optional[str] = None,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Lista metadados dos documentos recebidos, sem expor o XML armazenado."""
    _, tenant_id = auth
    consulta = db.query(SefazDocumentoDistribuido).filter(
        SefazDocumentoDistribuido.tenant_id == str(tenant_id)
    )
    if status:
        consulta = consulta.filter(SefazDocumentoDistribuido.status == status)
    if tipos:
        tipos_solicitados = [item.strip() for item in tipos.split(",") if item.strip()]
        tipos_permitidos = {"resNFe", "procNFe", "evento", "outro"}
        if not tipos_solicitados or any(
            item not in tipos_permitidos for item in tipos_solicitados
        ):
            raise HTTPException(status_code=422, detail="Tipo de documento inválido.")
        consulta = consulta.filter(
            SefazDocumentoDistribuido.tipo.in_(tipos_solicitados)
        )

    total = consulta.count()
    documentos = (
        consulta.order_by(
            SefazDocumentoDistribuido.nsu.desc(),
            SefazDocumentoDistribuido.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    campos = (
        "id",
        "nsu",
        "schema",
        "tipo",
        "chave_acesso",
        "emitente_cnpj",
        "emitente_nome",
        "numero_nota",
        "data_emissao",
        "valor_total",
        "status",
        "nota_entrada_id",
        "processado_em",
        "created_at",
        "updated_at",
    )
    return {
        "items": [
            {
                **{campo: getattr(doc, campo) for campo in campos},
                "erro_mensagem": (
                    "Falha ao processar o XML salvo; nova tentativa será feita automaticamente."
                    if doc.status == "erro_processamento"
                    else None
                ),
            }
            for doc in documentos
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/reset-nsu")
def reset_nsu(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
    _permission=Depends(can_configure_sefaz),
):
    """Alterações manuais do cursor exigem procedimento auditado fora da API."""
    raise HTTPException(
        status_code=409,
        detail=(
            "A redefinição manual do NSU foi desativada para evitar perda de NF-e "
            "ou bloqueio por consumo indevido."
        ),
    )


@router.post("/pular-para-hoje")
def pular_para_hoje(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
    _permission=Depends(can_configure_sefaz),
):
    """Bloqueia avanço artificial do NSU, que poderia ocultar notas ainda não salvas."""
    raise HTTPException(
        status_code=409,
        detail=(
            "Não é seguro pular para o NSU atual: isso pode deixar NF-e fora do sistema. "
            "Use a sincronização sequencial para importar os documentos disponíveis."
        ),
    )


@router.post("/sync-diagnostico")
def sync_diagnostico(
    max_lotes: int = 5,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
    _permission=Depends(can_configure_sefaz),
):
    """
    Endpoint legado desativado. Ele fazia novas consultas e modificava o NSU,
    apesar de se apresentar como diagnostico somente de leitura.
    """
    raise HTTPException(
        status_code=409,
        detail=(
            "O diagnóstico em lote foi desativado para proteger o NSU. "
            "Consulte /sefaz/config ou /sefaz/nsu-status para ver o último estado salvo."
        ),
    )
