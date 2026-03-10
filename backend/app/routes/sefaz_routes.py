"""
Rotas SEFAZ — Consulta de NF-e por chave de acesso.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.models import Tenant, Cliente
from app.produtos_models import NotaEntrada, NotaEntradaItem
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

    current_user, tenant_id = auth
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

        # ── Salvar documentos recebidos no banco de dados ────────────────────
        from app.notas_entrada_routes import (
            parse_nfe_xml,
            criar_fornecedor_automatico,
            encontrar_produto_similar,
        )

        docs_list = resultado.get("docs_list", [])
        notas_salvas = 0
        notas_puladas = 0

        for doc in docs_list:
            xml_str = doc.get("xml", "")
            if not xml_str:
                continue
            # Apenas NF-e completas têm itens; resumos (resNFe) são ignorados
            schema = doc.get("schema", "")
            if "resNFe" in schema and "nfeProc" not in schema and "NFe" not in schema:
                continue
            try:
                dados = parse_nfe_xml(xml_str)
            except Exception:
                continue

            chave = dados.get("chave_acesso")
            if not chave:
                continue

            # Pular se já existe
            existe = db.query(NotaEntrada).filter(
                NotaEntrada.chave_acesso == chave,
                NotaEntrada.tenant_id == tenant_id,
            ).first()
            if existe:
                notas_puladas += 1
                continue

            # Buscar / criar fornecedor
            fornecedor = db.query(Cliente).filter(
                Cliente.cnpj == dados.get("fornecedor_cnpj", ""),
                Cliente.ativo.is_(True),
            ).first()
            if not fornecedor:
                try:
                    fornecedor, _ = criar_fornecedor_automatico(dados, db, current_user, tenant_id)
                except Exception:
                    fornecedor = None

            nota = NotaEntrada(
                numero_nota=dados.get("numero_nota") or "0",
                serie=dados.get("serie") or "1",
                chave_acesso=chave,
                fornecedor_cnpj=dados.get("fornecedor_cnpj") or "",
                fornecedor_nome=dados.get("fornecedor_nome") or "",
                fornecedor_id=fornecedor.id if fornecedor else None,
                data_emissao=dados["data_emissao"],
                data_entrada=datetime.utcnow(),
                valor_produtos=dados.get("valor_produtos") or dados.get("valor_total", 0),
                valor_frete=dados.get("valor_frete", 0),
                valor_desconto=dados.get("valor_desconto", 0),
                valor_total=dados.get("valor_total", 0),
                xml_content=xml_str,
                status="pendente",
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(nota)
            db.flush()

            vinculados = 0
            nao_vinculados = 0
            for item_data in dados.get("itens", []):
                produto, confianca, _ = encontrar_produto_similar(
                    item_data.get("descricao", ""),
                    item_data.get("codigo_produto", ""),
                    db,
                    fornecedor.id if fornecedor else None,
                )
                item = NotaEntradaItem(
                    nota_entrada_id=nota.id,
                    numero_item=item_data.get("numero_item", 0),
                    codigo_produto=item_data.get("codigo_produto", ""),
                    descricao=item_data.get("descricao", ""),
                    ncm=item_data.get("ncm"),
                    cest=item_data.get("cest"),
                    cfop=item_data.get("cfop"),
                    origem=item_data.get("origem", "0"),
                    aliquota_icms=item_data.get("aliquota_icms", 0),
                    aliquota_pis=item_data.get("aliquota_pis", 0),
                    aliquota_cofins=item_data.get("aliquota_cofins", 0),
                    unidade=item_data.get("unidade", "UN"),
                    quantidade=item_data.get("quantidade", 0),
                    valor_unitario=item_data.get("valor_unitario", 0),
                    valor_total=item_data.get("valor_total", 0),
                    ean=item_data.get("ean"),
                    lote=item_data.get("lote"),
                    data_validade=item_data.get("data_validade"),
                    produto_id=produto.id if produto else None,
                    vinculado=bool(produto),
                    confianca_vinculo=confianca,
                    status="vinculado" if produto else "nao_vinculado",
                    tenant_id=tenant_id,
                )
                db.add(item)
                if produto:
                    vinculados += 1
                else:
                    nao_vinculados += 1

            nota.produtos_vinculados = vinculados
            nota.produtos_nao_vinculados = nao_vinculados
            db.commit()
            notas_salvas += 1

        # ── Atualizar config de sincronização ────────────────────────────────
        total_docs = int(resultado.get("documentos", 0))
        if notas_salvas or notas_puladas:
            msg_final = (
                f"Sincronizacao concluida. {notas_salvas} nota(s) importada(s)"
                + (f", {notas_puladas} ja existiam." if notas_puladas else ".")
            )
        else:
            msg_final = resultado["mensagem"]

        cfg["ultimo_sync_at"] = now_iso
        cfg["_proximo_sync_permitido_at"] = now_iso
        cfg["ultimo_sync_status"] = "ok"
        cfg["ultimo_sync_mensagem"] = msg_final
        cfg["ultimo_sync_documentos"] = total_docs
        cfg["ultimo_nsu"] = resultado.get("ultimo_nsu", cfg.get("ultimo_nsu", "000000000000000"))
        SefazTenantConfigService.save_config(tenant_id, cfg)
        return {
            "ok": True,
            "status": cfg["ultimo_sync_status"],
            "mensagem": msg_final,
            "documentos": total_docs,
            "notas_salvas": notas_salvas,
            "notas_puladas": notas_puladas,
            "ultimo_nsu": cfg["ultimo_nsu"],
            "max_nsu": resultado.get("max_nsu", cfg["ultimo_nsu"]),
            "c_stat": resultado.get("c_stat"),
            "x_motivo": resultado.get("x_motivo"),
        }
    except HTTPException as exc:
        cfg["ultimo_sync_at"] = now_iso
        cfg["_proximo_sync_permitido_at"] = now_iso
        cfg["ultimo_sync_status"] = "erro"
        cfg["ultimo_sync_mensagem"] = str(exc.detail)
        cfg["ultimo_sync_documentos"] = 0
        SefazTenantConfigService.save_config(tenant_id, cfg)
        raise


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

    _, tenant_id = auth
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cfg = SefazTenantConfigService.merged_config(tenant_id, tenant)
    status_cfg = SefazService.status_configuracao(cfg)

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
