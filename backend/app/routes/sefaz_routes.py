"""
Rotas SEFAZ — Consulta de NF-e por chave de acesso.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import logging

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.models import Tenant
from app.produtos_models import NotaEntrada
from app.services.sefaz_service import SefazService
from app.services.sefaz_tenant_config_service import SefazTenantConfigService

router = APIRouter(prefix="/sefaz", tags=["sefaz"])
logger = logging.getLogger(__name__)


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
        "proximo_sync_permitido_at": cfg.get("_proximo_sync_permitido_at"),
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
    Usa o mesmo coordinator do scheduler para garantir exclusividade.
    """
    from datetime import datetime, timezone

    current_user, tenant_id = auth
    logger.info(f"[SEFAZ] [manual] Pedido de sync manual — tenant {tenant_id} user {current_user.id}")
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)

    now_dt = datetime.now(timezone.utc)

    # ── Verificar penalidade 656 (bloqueia sync manual) ──────────────────────
    proximo_str = cfg.get("_proximo_sync_permitido_at")
    if proximo_str and cfg.get("_sync_bloqueado_656"):
        try:
            from datetime import timezone as _tz_check
            proximo_dt = datetime.fromisoformat(proximo_str)
            if proximo_dt.tzinfo is None:
                proximo_dt = proximo_dt.replace(tzinfo=_tz_check.utc)
            if now_dt < proximo_dt:
                faltam = int((proximo_dt - now_dt).total_seconds() / 60) + 1
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"SEFAZ em cooldown por bloqueio anterior (cStat 656). "
                        f"Proxima tentativa permitida em ~{faltam} minuto(s). "
                        f"Aguarde antes de sincronizar novamente."
                    ),
                )
        except HTTPException:
            raise
        except Exception:
            pass

    # ── Anti-spam: mínimo 20 minutos entre sincronizações manuais ────────────
    ultimo_sync_str = cfg.get("ultimo_sync_at")
    if ultimo_sync_str:
        try:
            from datetime import timezone as _tz_spam
            ultimo_dt = datetime.fromisoformat(ultimo_sync_str)
            if ultimo_dt.tzinfo is None:
                ultimo_dt = ultimo_dt.replace(tzinfo=_tz_spam.utc)
            segundos = (now_dt - ultimo_dt).total_seconds()
            min_segundos = 20 * 60
            if segundos < min_segundos:
                faltam_min = int((min_segundos - segundos) / 60) + 1
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Uma sincronizacao foi executada ha {int(segundos)} segundos. "
                        f"Aguarde cerca de {faltam_min} minuto(s) antes de tentar novamente."
                    ),
                )
        except HTTPException:
            raise
        except Exception:
            pass

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
    from app.services.sefaz_sync_coordinator import sefaz_coordinator

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
        "ultimo_nsu": result.get("ultimo_nsu", cfg.get("ultimo_nsu", "000000000000000")),
        "proximo_permitido_at": result.get("proximo_permitido_at", cfg.get("_proximo_sync_permitido_at")),
        "max_nsu": result.get("ultimo_nsu", ""),
        "c_stat": None,
        "x_motivo": None,
    }



@router.get("/nsu-status")
def get_nsu_status(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Retorna o ultimo_nsu armazenado e o maxNSU atual da SEFAZ,
    permitindo ver quantos documentos ainda faltam ser alcançados.
    """
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
    status_cfg = SefazService.status_configuracao(cfg)

    ultimo_nsu = cfg.get("ultimo_nsu", "000000000000000")

    max_nsu = None
    gap_estimado = None
    erro_consulta = None

    if status_cfg.enabled and cfg.get("modo") == "real" and status_cfg.cert_ok:
        # Proteção 656: não chamar SEFAZ enquanto estiver em cooldown
        proximo_str = cfg.get("_proximo_sync_permitido_at")
        em_cooldown_656 = False
        if proximo_str and cfg.get("_sync_bloqueado_656"):
            try:
                from datetime import timezone as _tz
                from datetime import datetime as _dt
                proximo_dt = _dt.fromisoformat(proximo_str)
                if proximo_dt.tzinfo is None:
                    proximo_dt = proximo_dt.replace(tzinfo=_tz.utc)
                em_cooldown_656 = _dt.now(_tz.utc) < proximo_dt
            except Exception:
                pass

        if not em_cooldown_656:
            try:
                # Faz uma chamada leve com o NSU atual só para capturar o maxNSU
                resultado = SefazService.sincronizar_nsu(config=cfg, ultimo_nsu=ultimo_nsu)
                max_nsu = resultado.get("max_nsu")
                novo_nsu = resultado.get("ultimo_nsu", ultimo_nsu)

                # Salva docs se vieram
                docs_lista = resultado.get("docs_list", [])
                if docs_lista:
                    from app.notas_entrada_routes import importar_docs_sefaz
                    from app.db import SessionLocal as _SL
                    _db = _SL()
                    try:
                        importar_docs_sefaz(docs_lista, str(tenant_id), _db)
                    finally:
                        _db.close()
                    # Atualiza NSU
                    cfg["ultimo_nsu"] = novo_nsu
                    SefazTenantConfigService.save_config(tenant_id, cfg)
                    ultimo_nsu = novo_nsu

                if max_nsu and ultimo_nsu:
                    try:
                        gap_estimado = int(max_nsu) - int(ultimo_nsu)
                    except ValueError:
                        gap_estimado = None
            except Exception as exc:
                erro_consulta = str(exc)

    return {
        "ultimo_nsu": ultimo_nsu,
        "max_nsu_sefaz": max_nsu,
        "gap_documentos": gap_estimado,
        "documentos_por_lote": 50,
        "lotes_restantes": (gap_estimado // 50 + 1) if gap_estimado and gap_estimado > 0 else 0,
        "atualizado": max_nsu is not None,
        "erro": erro_consulta,
    }


class ResetNsuRequest(BaseModel):
    nsu: str = "000000000000000"


@router.post("/reset-nsu")
def reset_nsu(
    payload: ResetNsuRequest,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Redefine o ultimo_nsu para o valor informado.
    Use '000000000000000' para reiniciar do zero (busca todas as NFs disponíveis).
    Use um valor específico para começar de um ponto determinado.
    ATENÇÃO: notas já importadas não serão duplicadas pois há verificação por chave de acesso.
    """
    nsu = payload.nsu.strip().zfill(15)
    if not nsu.isdigit() or len(nsu) != 15:
        raise HTTPException(status_code=422, detail="NSU deve ter 15 dígitos numéricos.")

    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)

    nsu_anterior = cfg.get("ultimo_nsu", "000000000000000")
    cfg["ultimo_nsu"] = nsu
    cfg["ultimo_sync_status"] = "nunca"
    cfg["ultimo_sync_mensagem"] = f"NSU redefinido de {nsu_anterior} para {nsu}. Próxima sincronização buscará a partir deste ponto."
    SefazTenantConfigService.save_config(tenant_id, cfg)

    return {
        "ok": True,
        "nsu_anterior": nsu_anterior,
        "novo_nsu": nsu,
        "mensagem": f"NSU redefinido. O próximo ciclo de sincronização buscará documentos a partir do NSU {nsu}.",
    }


@router.post("/pular-para-hoje")
def pular_para_hoje(
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Marca a configuração para pular documentos antigos na próxima sincronização.
    Na próxima janela disponível (após o cooldown atual), o sistema avança o NSU
    para o ponto atual da SEFAZ sem importar nenhum documento antigo.
    Útil quando o CNPJ ficou muito atrás no NSU e há risco de cStat 656.
    """
    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)

    cfg["comecar_do_hoje"] = True
    SefazTenantConfigService.save_config(tenant_id, cfg)

    proximo_str = cfg.get("_proximo_sync_permitido_at")
    aviso_cooldown = ""
    if proximo_str and cfg.get("_sync_bloqueado_656"):
        try:
            from datetime import timezone as _tz
            proximo_dt = __import__("datetime").datetime.fromisoformat(proximo_str)
            if proximo_dt.tzinfo is None:
                proximo_dt = proximo_dt.replace(tzinfo=_tz.utc)
            from datetime import datetime as _dt
            faltam = int((_dt.now(_tz.utc) - proximo_dt).total_seconds() / -60) + 1
            if faltam > 0:
                aviso_cooldown = f" O sistema está em cooldown por ~{faltam} minuto(s) — o pulo será executado automaticamente após esse período."
        except Exception:
            pass

    return {
        "ok": True,
        "mensagem": (
            "Configurado com sucesso. Na próxima sincronização disponível, "
            "documentos antigos serão ignorados e o sistema começará do ponto atual da SEFAZ."
            + aviso_cooldown
        ),
    }


@router.post("/sync-diagnostico")
def sync_diagnostico(
    max_lotes: int = 5,
    auth=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Busca documentos da SEFAZ em lote (até max_lotes chamadas de 50 docs cada)
    e retorna diagnóstico detalhado: tipo de cada documento, o que foi importado,
    pulado (duplicado), descartado (NF de saída) ou ignorado (só resumo resNFe).

    Útil para entender por que poucos documentos foram importados numa sincronização.
    NÃO avança o ultimo_nsu globalmente — apenas lê e relata.
    """
    from datetime import datetime, timezone
    import time as _time

    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
    status_cfg = SefazService.status_configuracao(cfg)

    # Bloquear se em penalidade 656
    now_dt = datetime.now(timezone.utc)
    proximo_str = cfg.get("_proximo_sync_permitido_at")
    if proximo_str and cfg.get("_sync_bloqueado_656"):
        try:
            proximo_dt = datetime.fromisoformat(proximo_str)
            if proximo_dt.tzinfo is None:
                proximo_dt = proximo_dt.replace(tzinfo=timezone.utc)
            if now_dt < proximo_dt:
                faltam = int((proximo_dt - now_dt).total_seconds() / 60) + 1
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"SEFAZ em cooldown por bloqueio (cStat 656). "
                        f"Aguarde ~{faltam} minuto(s) antes de executar o diagnóstico."
                    ),
                )
        except HTTPException:
            raise
        except Exception:
            pass

    if not status_cfg.enabled or cfg.get("modo") != "real":
        raise HTTPException(
            status_code=422,
            detail="SEFAZ precisa estar habilitado e em modo real para executar o diagnóstico.",
        )
    if not status_cfg.cert_ok:
        raise HTTPException(
            status_code=422,
            detail=f"Certificado não está válido: {status_cfg.mensagem}",
        )

    from app.notas_entrada_routes import importar_docs_sefaz
    from app.services.sefaz_tenant_config_service import SefazTenantConfigService as _Cfg

    tenant_cnpj = "".join(c for c in str(cfg.get("cnpj", "")) if c.isdigit())

    nsu_atual = cfg.get("ultimo_nsu", "000000000000000")
    lotes_executados = 0
    relatorio_docs: list[dict] = []
    total_importadas = 0
    total_duplicadas = 0
    total_saidas = 0
    total_resumos = 0
    total_erros = 0
    novo_ultimo_nsu = nsu_atual
    max_nsu_global = nsu_atual

    for _ in range(max(1, min(max_lotes, 20))):  # Limite de segurança: máx 20 lotes
        try:
            resultado = SefazService.sincronizar_nsu(config=cfg, ultimo_nsu=nsu_atual)
        except HTTPException as exc:
            relatorio_docs.append({
                "lote": lotes_executados + 1,
                "erro": str(exc.detail),
                "nsu_inicio": nsu_atual,
            })
            total_erros += 1
            break

        lotes_executados += 1
        docs = resultado.get("docs_list", [])
        novo_ultimo_nsu = resultado.get("ultimo_nsu", nsu_atual)
        max_nsu_global = resultado.get("max_nsu", novo_ultimo_nsu)

        for doc in docs:
            nsu = doc.get("nsu", "?")
            schema = doc.get("schema", "")
            xml_str = doc.get("xml", "")

            entry: dict = {
                "nsu": nsu,
                "schema": schema,
                "tipo": "",
                "resultado": "",
                "chave": None,
                "fornecedor": None,
                "numero_nf": None,
                "valor_total": None,
            }

            # Resumo apenas (sem XML completo)
            if "procNFe" not in schema and "nfeProc" not in xml_str[:200]:
                entry["tipo"] = "resNFe (resumo)"
                entry["resultado"] = "ignorado — sem XML completo, não é possível importar itens"

                # Tentar extrair info básica do resNFe para ajudar no diagnóstico
                try:
                    import xml.etree.ElementTree as _ET
                    _root = _ET.fromstring(xml_str)
                    def _txt(tag):
                        for el in _root.iter():
                            if el.tag.split("}")[-1] == tag:
                                return el.text
                        return None
                    entry["chave"] = _txt("chNFe")
                    entry["fornecedor"] = _txt("xNome")
                    entry["numero_nf"] = _txt("nNF")
                    v = _txt("vNF")
                    entry["valor_total"] = float(v) if v else None
                except Exception:
                    pass

                total_resumos += 1
                relatorio_docs.append(entry)
                continue

            # NF-e completa — tentar parsear
            try:
                from app.notas_entrada_routes import parse_nfe_xml
                dados = parse_nfe_xml(xml_str)
            except Exception as exc_parse:
                entry["tipo"] = "procNFe"
                entry["resultado"] = f"erro_parse — {exc_parse}"
                total_erros += 1
                relatorio_docs.append(entry)
                continue

            entry["tipo"] = "procNFe (completa)"
            entry["chave"] = dados.get("chave_acesso")
            entry["fornecedor"] = dados.get("fornecedor_nome")
            entry["numero_nf"] = dados.get("numero_nota")
            entry["valor_total"] = dados.get("valor_total")

            # Verificar NF de saída
            cnpj_emit = "".join(c for c in str(dados.get("fornecedor_cnpj", "")) if c.isdigit())
            if tenant_cnpj and cnpj_emit == tenant_cnpj:
                entry["resultado"] = "descartada — NF de saída (emitida pela própria empresa)"
                total_saidas += 1
                relatorio_docs.append(entry)
                continue

            # Verificar duplicata
            chave = dados.get("chave_acesso", "")
            if chave:
                existente = db.query(NotaEntrada).filter(
                    NotaEntrada.chave_acesso == chave
                ).first()
                if existente:
                    entry["resultado"] = f"duplicada — já existe no sistema (id={existente.id}, status={existente.status})"
                    total_duplicadas += 1
                    relatorio_docs.append(entry)
                    continue

            entry["resultado"] = "importada com sucesso"
            total_importadas += 1
            relatorio_docs.append(entry)

        # Importar de verdade os documentos deste lote
        if docs:
            try:
                importar_docs_sefaz(docs, str(tenant_id), db)
            except Exception as exc_import:
                relatorio_docs.append({"erro_importacao_lote": str(exc_import)})

        # Avança NSU para próximo lote
        nsu_atual = novo_ultimo_nsu

        # Se não há mais documentos novos, para
        if novo_ultimo_nsu >= max_nsu_global or not docs:
            break

        # Pausa entre lotes para evitar bloqueio 656 da SEFAZ
        _time.sleep(15)

    # Atualiza o ultimo_nsu na config se avançou
    if novo_ultimo_nsu != cfg.get("ultimo_nsu"):
        cfg["ultimo_nsu"] = novo_ultimo_nsu
        cfg["ultimo_sync_at"] = datetime.now(timezone.utc).isoformat()
        cfg["ultimo_sync_status"] = "ok"
        cfg["ultimo_sync_mensagem"] = (
            f"Diagnóstico em lote: {total_importadas} importada(s), "
            f"{total_duplicadas} duplicada(s), {total_resumos} resumo(s) ignorado(s), "
            f"{total_saidas} NF(s) de saída descartada(s)."
        )
        SefazTenantConfigService.save_config(tenant_id, cfg)

    return {
        "ok": True,
        "lotes_executados": lotes_executados,
        "nsu_inicio": cfg.get("ultimo_nsu", "000000000000000"),
        "novo_ultimo_nsu": novo_ultimo_nsu,
        "max_nsu_sefaz": max_nsu_global,
        "ha_mais_documentos": novo_ultimo_nsu < max_nsu_global,
        "resumo": {
            "total_documentos_analisados": len(relatorio_docs),
            "importadas": total_importadas,
            "duplicadas": total_duplicadas,
            "resumos_sem_xml": total_resumos,
            "nfs_de_saida_descartadas": total_saidas,
            "erros": total_erros,
        },
        "explicacao": (
            "resNFe = resumo enviado pela SEFAZ sem XML completo. "
            "O XML completo (procNFe) chega depois, quando o emitente transmite a NF. "
            "Execute o diagnóstico novamente para buscar os XMLs completos que ainda não chegaram."
        ),
        "documentos": relatorio_docs,
    }
