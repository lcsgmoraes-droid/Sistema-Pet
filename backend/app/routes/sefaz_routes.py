"""
Rotas SEFAZ — Consulta de NF-e por chave de acesso.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.models import Tenant
from app.services.sefaz_service import SefazService
from app.services.sefaz_tenant_config_service import SefazTenantConfigService

router = APIRouter(prefix="/sefaz", tags=["sefaz"])


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
    importacao_intervalo_min: int = 15


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
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)

    data = SefazService.consultar_nfe_por_chave(chave, cfg)
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
        "importacao_intervalo_min": cfg.get("importacao_intervalo_min", 15),
        "ultimo_nsu": cfg.get("ultimo_nsu", "000000000000000"),
        "ultimo_sync_at": cfg.get("ultimo_sync_at"),
        "ultimo_sync_status": cfg.get("ultimo_sync_status", "nunca"),
        "ultimo_sync_mensagem": cfg.get("ultimo_sync_mensagem", "Ainda nao sincronizado."),
        "ultimo_sync_documentos": cfg.get("ultimo_sync_documentos", 0),
        "cnpj_configurado": status.cnpj_configurado,
        "cert_path_configurado": status.cert_path_configurado,
        "cert_existe": status.cert_existe,
        "cert_senha_configurada": status.cert_senha_configurada,
        "cert_ok": status.cert_ok,
        "mensagem": status.mensagem,
        "empresa": {
            "nome": tenant.name if tenant else None,
            "cnpj": SefazTenantConfigService.sanitize_cnpj(tenant.cnpj) if tenant else "",
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
):
    """Salva configuracao SEFAZ por tenant (sem upload de certificado)."""
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    atual = SefazTenantConfigService.merged_config(tenant_id, tenant)
    novo = {
        **atual,
        "enabled": payload.enabled,
        "modo": payload.modo.strip().lower(),
        "ambiente": payload.ambiente.strip().lower(),
        "uf": payload.uf.strip().upper(),
        "cnpj": SefazTenantConfigService.sanitize_cnpj(payload.cnpj),
        "importacao_automatica": payload.importacao_automatica,
        "importacao_intervalo_min": payload.importacao_intervalo_min,
    }

    if payload.cert_password is not None:
        novo["cert_password"] = payload.cert_password

    SefazTenantConfigService.save_config(tenant_id, novo)
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
):
    """Recebe e valida certificado A1 (.pfx) por tenant."""
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    cert_path = await SefazTenantConfigService.save_certificate(tenant_id, file)
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
    cfg["cert_path"] = cert_path
    cfg["cert_password"] = cert_password
    SefazTenantConfigService.save_config(tenant_id, cfg)

    # Valida o arquivo/senha do certificado de forma isolada.
    # Nao bloqueia upload quando o tenant ainda estiver em modo mock.
    cert_ok, cert_msg = SefazService._validar_certificado(cert_path, cert_password)
    if not cert_ok:
        raise HTTPException(status_code=422, detail=cert_msg)

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
        "ultimo_sync_mensagem": cfg.get("ultimo_sync_mensagem", "Ainda nao sincronizado."),
        "ultimo_sync_documentos": cfg.get("ultimo_sync_documentos", 0),
        "ultimo_nsu": cfg.get("ultimo_nsu", "000000000000000"),
    }


@router.post("/sync-now")
def sync_now(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Dispara sincronizacao manual.
    """
    from datetime import datetime, timezone

    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
    status = SefazService.status_configuracao(cfg)

    now_iso = datetime.now(timezone.utc).isoformat()

    if not status.enabled:
        cfg["ultimo_sync_at"] = now_iso
        cfg["ultimo_sync_status"] = "erro"
        cfg["ultimo_sync_mensagem"] = "SEFAZ desabilitado. Ative a integracao para sincronizar automaticamente."
        cfg["ultimo_sync_documentos"] = 0
        SefazTenantConfigService.save_config(tenant_id, cfg)
        raise HTTPException(status_code=422, detail=cfg["ultimo_sync_mensagem"])

    if cfg.get("modo") != "real":
        cfg["ultimo_sync_at"] = now_iso
        cfg["ultimo_sync_status"] = "pendente"
        cfg["ultimo_sync_mensagem"] = "Integracao pronta, mas em modo mock. Troque para modo real para sincronizacao oficial da SEFAZ SP."
        cfg["ultimo_sync_documentos"] = 0
        SefazTenantConfigService.save_config(tenant_id, cfg)
        return {
            "ok": True,
            "status": cfg["ultimo_sync_status"],
            "mensagem": cfg["ultimo_sync_mensagem"],
            "documentos": 0,
        }

    if not status.cert_ok:
        cfg["ultimo_sync_at"] = now_iso
        cfg["ultimo_sync_status"] = "erro"
        cfg["ultimo_sync_mensagem"] = f"Configuracao incompleta para sincronizacao: {status.mensagem}"
        cfg["ultimo_sync_documentos"] = 0
        SefazTenantConfigService.save_config(tenant_id, cfg)
        raise HTTPException(status_code=422, detail=cfg["ultimo_sync_mensagem"])

    try:
        resultado = SefazService.sincronizar_nsu(config=cfg, ultimo_nsu=cfg.get("ultimo_nsu", "000000000000000"))
        cfg["ultimo_sync_at"] = now_iso
        cfg["ultimo_sync_status"] = "ok"
        cfg["ultimo_sync_mensagem"] = resultado["mensagem"]
        cfg["ultimo_sync_documentos"] = int(resultado.get("documentos", 0))
        cfg["ultimo_nsu"] = resultado.get("ultimo_nsu", cfg.get("ultimo_nsu", "000000000000000"))
        SefazTenantConfigService.save_config(tenant_id, cfg)
        return {
            "ok": True,
            "status": cfg["ultimo_sync_status"],
            "mensagem": cfg["ultimo_sync_mensagem"],
            "documentos": cfg["ultimo_sync_documentos"],
            "ultimo_nsu": cfg["ultimo_nsu"],
            "max_nsu": resultado.get("max_nsu", cfg["ultimo_nsu"]),
            "c_stat": resultado.get("c_stat"),
            "x_motivo": resultado.get("x_motivo"),
        }
    except HTTPException as exc:
        cfg["ultimo_sync_at"] = now_iso
        cfg["ultimo_sync_status"] = "erro"
        cfg["ultimo_sync_mensagem"] = str(exc.detail)
        cfg["ultimo_sync_documentos"] = 0
        SefazTenantConfigService.save_config(tenant_id, cfg)
        raise
