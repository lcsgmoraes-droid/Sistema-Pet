"""
Rotas para gerenciamento de Notas Fiscais Eletrônicas
"""

from copy import deepcopy
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.db import get_session
from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.services.nfe_cache_service import (
    FONTES_NFE_LOCAIS,
    existe_nota_cache_no_intervalo,
    listar_notas_cache,
    obter_estado_cache_notas,
)
from app.services.bling_tenant_guard import tenant_pode_usar_bling_global
from app.services.nfe_pending_reconciliation_service import (
    reconciliar_nfes_pendentes_recentes,
)
from app.vendas_models import Venda
from app.intnfe.client import IntNFeClient
from app.intnfe.emission import (
    DirectEmissionError,
    cancel as cancel_intnfe,
    download_document as download_intnfe_document,
    issue as issue_intnfe,
    local_document_details as local_intnfe_details,
    preview as preview_intnfe,
    reconcile as reconcile_intnfe,
)
from app.intnfe.sharing import extrair_link_publico_nfce
from app.intnfe.repository import get_connection, get_tenant
from app.intnfe.numbering import NumberingError
from app.intnfe.recovery import repair_and_retry as repair_and_retry_intnfe
from app.bling_integration_fiscal import prevalidar_produtos_fiscais_venda
from app.nfe.operacional_routes import (
    CancelarNFeRequest as CancelarNFeRequest,
    CartaCorrecaoRequest as CartaCorrecaoRequest,
    baixar_danfe as baixar_danfe,
    baixar_xml as baixar_xml,
    cancelar_nfe as cancelar_nfe,
    carta_correcao as carta_correcao,
    consultar_nfe as consultar_nfe,
    excluir_nota as excluir_nota,
    reconciliar_fluxo_nfe as reconciliar_fluxo_nfe,
    router as operacional_router,
    sincronizar_status_nota as sincronizar_status_nota,
    sincronizar_todos_status as sincronizar_todos_status,
    testar_conexao as testar_conexao,
    webhook_bling as webhook_bling,
)
from app.nfe.listagem_rapida import router as listagem_rapida_router
from app.nfe.listagem import (
    _NFE_LIST_CACHE_SECONDS as _NFE_LIST_CACHE_SECONDS,
    _adicionar_notas_de_pedidos_integrados as _adicionar_notas_de_pedidos_integrados,
    _cache_key_detalhe_nfe as _cache_key_detalhe_nfe,
    _cache_key_listar_nfes as _cache_key_listar_nfes,
    _canal_label as _canal_label,
    _canal_slug as _canal_slug,
    _coerce_float as _coerce_float,
    _coerce_int as _coerce_int,
    _consultar_campos_fiscais_no_xml as _consultar_campos_fiscais_no_xml,
    _consultar_detalhe_nota_bling as _consultar_detalhe_nota_bling,
    _detalhe_nota_valido as _detalhe_nota_valido,
    _dict as _dict,
    _digitos as _digitos,
    _enriquecer_detalhe_com_xml_link as _enriquecer_detalhe_com_xml_link,
    _enriquecer_notas_com_detalhes_bling as _enriquecer_notas_com_detalhes_bling,
    _enriquecer_notas_com_pedidos_integrados as _enriquecer_notas_com_pedidos_integrados,
    _enriquecer_notas_com_vendas as _enriquecer_notas_com_vendas,
    _extrair_campo_texto as _extrair_campo_texto,
    _extrair_campos_fiscais_do_xml as _extrair_campos_fiscais_do_xml,
    _extrair_total_pedido_integrado as _extrair_total_pedido_integrado,
    _extrair_valor_nota as _extrair_valor_nota,
    _formatar_data_iso as _formatar_data_iso,
    _formatar_data_param_bling as _formatar_data_param_bling,
    _formatar_endereco as _formatar_endereco,
    _identificadores_pedido_integrado as _identificadores_pedido_integrado,
    _inferir_canal_por_loja_id as _inferir_canal_por_loja_id,
    _inferir_canal_por_numero as _inferir_canal_por_numero,
    _label_codigo as _label_codigo,
    _list as _list,
    _nfe_list_cache as _nfe_list_cache,
    _normalizar_detalhe_nota_bling as _normalizar_detalhe_nota_bling,
    _normalizar_item_nota as _normalizar_item_nota,
    _normalizar_nota_bling as _normalizar_nota_bling,
    _normalizar_nota_pedido_integrado as _normalizar_nota_pedido_integrado,
    _normalizar_nota_venda_local as _normalizar_nota_venda_local,
    _normalizar_parcela as _normalizar_parcela,
    _normalizar_resumo_canal as _normalizar_resumo_canal,
    _nota_autorizada_bling as _nota_autorizada_bling,
    _nota_cancelada_bling as _nota_cancelada_bling,
    _obter_detalhe_nfe_cache as _obter_detalhe_nfe_cache,
    _parse_data_referencia as _parse_data_referencia,
    _planejar_sincronizacao_bling_nfes as _planejar_sincronizacao_bling_nfes,
    _primeiro_preenchido as _primeiro_preenchido,
    _resumo_pedido_integrado as _resumo_pedido_integrado,
    _salvar_detalhe_nfe_cache as _salvar_detalhe_nfe_cache,
    _separar_data_hora as _separar_data_hora,
    _sincronizar_cache_nfes_com_bling as _sincronizar_cache_nfes_com_bling,
    _sincronizar_fontes_locais_nfe_em_cache as _sincronizar_fontes_locais_nfe_em_cache,
    _sincronizar_pedidos_integrados_em_cache as _sincronizar_pedidos_integrados_em_cache,
    _sincronizar_vendas_em_cache as _sincronizar_vendas_em_cache,
    _situacao_num as _situacao_num,
    _sort_key_nota_por_numero_desc as _sort_key_nota_por_numero_desc,
    _status_local_ultima_nf as _status_local_ultima_nf,
    _status_nota_bling as _status_nota_bling,
    _texto as _texto,
    _texto_generico_baixo_valor as _texto_generico_baixo_valor,
    _texto_relacionado as _texto_relacionado,
    _texto_situacao as _texto_situacao,
    _tipo_nota_label as _tipo_nota_label,
    _tipo_pessoa_label as _tipo_pessoa_label,
    _venda_usa_nfce as _venda_usa_nfce,
    upsert_nota_cache as upsert_nota_cache,
)
from app.utils.logger import logger

router = APIRouter(prefix="/nfe", tags=["NF-e"])


class EmitirNFeRequest(BaseModel):
    venda_id: int
    tipo_nota: str = "nfce"  # 'nfe' ou 'nfce'
    transmitir: bool = True
    autorizar_correcoes_fiscais: bool = False


class PrevalidarNFeRequest(BaseModel):
    venda_id: int
    tipo_nota: str = "nfce"  # 'nfe' ou 'nfce'


class CancelarIntNFeRequest(BaseModel):
    justificativa: str


def _normalizar_tipo_nota(tipo_nota: str | None) -> str:
    tipo = str(tipo_nota or "nfce").strip().lower()
    return "nfe" if tipo == "nfe" else "nfce"


def _buscar_venda_para_nfe(db: Session, venda_id: int, tenant_id):
    return (
        db.query(Venda)
        .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
        .first()
    )


def _exigir_bling_configurado_para_tenant(tenant_id) -> None:
    if not tenant_pode_usar_bling_global(tenant_id):
        raise HTTPException(
            status_code=403,
            detail="A integração Bling não está configurada para esta empresa",
        )


def _direct_failure(exc):
    detail = {
        "erro": exc.code or "intnfe_emissao",
        "mensagem": str(exc),
        "protocolo_suporte": exc.correlation,
    }
    if exc.validation:
        detail["validacao"] = exc.validation
    return HTTPException(
        exc.status,
        detail,
    )


def _intnfe_client():
    try:
        return IntNFeClient()
    except Exception as exc:
        raise HTTPException(503, "A integração IntNFe não está disponível.") from exc


@router.post("/prevalidar")
async def prevalidar_nfe(
    request: PrevalidarNFeRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Valida pendencias fiscais antes de emitir diretamente pela IntNFe."""
    current_user, tenant_id = user_and_tenant
    tipo_nota = _normalizar_tipo_nota(request.tipo_nota)
    venda = _buscar_venda_para_nfe(db, request.venda_id, tenant_id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")

    try:
        if venda.nfe_bling_id or venda.nfe_correlation_id:
            raise DirectEmissionError(
                "Esta venda já possui uma tentativa de nota fiscal. Consulte a situação existente.",
                status=409,
            )
        validacao = prevalidar_produtos_fiscais_venda(
            venda, db, exigir_documento_completo=True
        )
        if validacao["pode_emitir"]:
            validacao["resumo_emissao"] = preview_intnfe(
                db, get_tenant(db, tenant_id), venda, tipo_nota
            )
        validacao["provedor"] = "intnfe"
    except DirectEmissionError as exc:
        validacao = exc.validation or {
            "success": True,
            "pode_emitir": False,
            "requer_autorizacao": False,
            "correcoes": [],
            "bloqueios": [{"campo": "intnfe", "mensagem": str(exc)}],
        }
        validacao["provedor"] = "intnfe"
    validacao["tipo_nota"] = tipo_nota
    validacao["venda_id"] = venda.id
    validacao["tenant_id"] = str(tenant_id)
    validacao["usuario_id"] = getattr(current_user, "id", None)
    return validacao


@router.post("/emitir")
async def emitir_nfe(
    request: EmitirNFeRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Emite NF-e ou NFC-e exclusivamente pela IntNFe."""
    try:
        current_user, tenant_id = user_and_tenant
        tipo_nota = _normalizar_tipo_nota(request.tipo_nota)
        venda = _buscar_venda_para_nfe(db, request.venda_id, tenant_id)
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        if venda.nfe_bling_id and not venda.nfe_correlation_id:
            raise HTTPException(
                status_code=400,
                detail=f"Esta venda já possui nota fiscal no Bling (NF #{venda.nfe_numero}).",
            )
        if not request.transmitir:
            raise HTTPException(
                status_code=422,
                detail="A emissão direta pela IntNFe sempre transmite para o ambiente escolhido.",
            )

        api = _intnfe_client()
        try:
            connection = get_connection(db, tenant_id)
            log_action(
                db,
                user_id=current_user.id,
                tenant_id=tenant_id,
                action="intnfe_emitir_documento",
                entity_type="venda",
                entity_id=venda.id,
                new_value={
                    "tipo": tipo_nota,
                    "ambiente": (
                        "producao"
                        if connection and connection.emission_environment == 1
                        else "homologacao"
                    ),
                },
            )
            return issue_intnfe(db, get_tenant(db, tenant_id), venda, tipo_nota, api)
        except DirectEmissionError as exc:
            raise _direct_failure(exc) from None
        finally:
            api.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "emitir_nfe_intnfe_error",
            f"Falha inesperada na emissão IntNFe; error_type={type(e).__name__}",
        )
        raise HTTPException(
            status_code=500,
            detail="Não foi possível emitir a nota pela IntNFe. Tente novamente.",
        ) from e


@router.get("/vendas/{venda_id}/status")
def status_intnfe_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    venda = _buscar_venda_para_nfe(db, venda_id, tenant_id)
    if not venda:
        raise HTTPException(404, "Venda não encontrada")
    api = _intnfe_client()
    try:
        return reconcile_intnfe(db, venda, api)
    except DirectEmissionError as exc:
        raise _direct_failure(exc) from None
    finally:
        api.close()


@router.post("/vendas/{venda_id}/corrigir-reemitir")
def corrigir_reemitir_intnfe_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Aplica apenas correções comprováveis e refaz uma tentativa rejeitada."""
    current_user, tenant_id = user_and_tenant
    venda = _buscar_venda_para_nfe(db, venda_id, tenant_id)
    if not venda:
        raise HTTPException(404, "Venda não encontrada")

    def reset_audit(old_value, new_value):
        log_action(
            db,
            user_id=current_user.id,
            tenant_id=tenant_id,
            action="intnfe_corrigir_reemitir",
            entity_type="venda",
            entity_id=venda.id,
            old_value=old_value,
            new_value=new_value,
            commit=False,
        )

    def numbering_audit(connection_id, result, last, change, error=None):
        try:
            log_action(
                db,
                user_id=current_user.id,
                tenant_id=tenant_id,
                action="intnfe_numeracao_automatica",
                entity_type="intnfe_connection",
                entity_id=connection_id,
                old_value={"ultimoNumero": last},
                new_value={
                    **change,
                    "resultado": result,
                    "codigo": error.code if error else None,
                    "correlation_id": error.correlation if error else None,
                },
                commit=False,
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise NumberingError(
                "AuditoriaIndisponivel",
                "Não foi possível auditar o ajuste automático da numeração.",
                status=503,
            ) from None

    api = _intnfe_client()
    try:
        return repair_and_retry_intnfe(
            db,
            get_tenant(db, tenant_id),
            venda,
            api,
            reset_audit=reset_audit,
            numbering_audit=numbering_audit,
        )
    except DirectEmissionError as exc:
        raise _direct_failure(exc) from None
    except NumberingError as exc:
        raise HTTPException(
            exc.status,
            {
                "erro": exc.code,
                "mensagem": str(exc),
                "protocolo_suporte": exc.correlation,
            },
        ) from None
    finally:
        api.close()


@router.get("/vendas/{venda_id}/detalhes")
def detalhes_intnfe_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o documento fiscal usando a venda persistida no CorePet."""
    _user, tenant_id = user_and_tenant
    venda = _buscar_venda_para_nfe(db, venda_id, tenant_id)
    if not venda:
        raise HTTPException(404, "Venda não encontrada")
    if venda.nfe_provider != "intnfe" and not venda.nfe_correlation_id:
        raise HTTPException(404, "Esta venda não possui uma nota da IntNFe")
    return local_intnfe_details(db, get_tenant(db, tenant_id), venda)


@router.get("/vendas/{venda_id}/xml")
def xml_intnfe_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    venda = _buscar_venda_para_nfe(db, venda_id, tenant_id)
    if not venda:
        raise HTTPException(404, "Venda não encontrada")
    api = _intnfe_client()
    try:
        content = download_intnfe_document(db, venda, api, "xml")
        return Response(
            content=content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="nota-{venda_id}.xml"'
            },
        )
    except DirectEmissionError as exc:
        raise _direct_failure(exc) from None
    finally:
        api.close()


def _danfe_response_metadata(venda):
    is_nfce = venda.nfe_tipo == "nfce" or str(venda.nfe_modelo or "") == "65"
    if is_nfce:
        return "text/html", "html"
    return "application/pdf", "pdf"


@router.get("/vendas/{venda_id}/danfe")
def danfe_intnfe_venda(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    venda = _buscar_venda_para_nfe(db, venda_id, tenant_id)
    if not venda:
        raise HTTPException(404, "Venda não encontrada")
    api = _intnfe_client()
    try:
        content = download_intnfe_document(db, venda, api, "danfe")
        media_type, extension = _danfe_response_metadata(venda)
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="danfe-{venda_id}.{extension}"'
            },
        )
    except DirectEmissionError as exc:
        raise _direct_failure(exc) from None
    finally:
        api.close()


@router.get("/vendas/{venda_id}/compartilhar")
def preparar_compartilhamento_intnfe(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Prepara o link publico oficial da SEFAZ para uma NFC-e da IntNFe."""
    _user, tenant_id = user_and_tenant
    venda = _buscar_venda_para_nfe(db, venda_id, tenant_id)
    if not venda:
        raise HTTPException(404, "Venda não encontrada")
    if venda.nfe_provider != "intnfe" or not venda.nfe_correlation_id:
        raise HTTPException(404, "Esta venda não possui uma nota da IntNFe")
    if str(venda.nfe_status or "").strip().lower() != "autorizada":
        raise HTTPException(409, "Compartilhe a nota após a autorização.")

    is_nfce = venda.nfe_tipo == "nfce" or str(venda.nfe_modelo or "") == "65"
    if not is_nfce:
        raise HTTPException(
            409,
            "O compartilhamento por link está disponível para NFC-e. Para NF-e, baixe o PDF.",
        )

    xml = venda.nfe_xml
    if not xml:
        api = _intnfe_client()
        try:
            xml = download_intnfe_document(db, venda, api, "xml").decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                502, "O XML retornado pelo emissor é inválido."
            ) from None
        except DirectEmissionError as exc:
            raise _direct_failure(exc) from None
        finally:
            api.close()

    try:
        link = extrair_link_publico_nfce(xml)
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from None

    cliente = venda.cliente
    telefone = (
        getattr(cliente, "celular", None) or getattr(cliente, "telefone", None) or ""
    )
    nome_cliente = (
        getattr(cliente, "nome", None) or getattr(cliente, "razao_social", None) or ""
    )
    return {
        "link": link,
        "telefone": telefone,
        "cliente": nome_cliente,
        "numero": venda.nfe_numero,
        "modelo": venda.nfe_modelo or 65,
    }


@router.post("/vendas/{venda_id}/cancelar")
def cancel_intnfe_venda(
    venda_id: int,
    body: CancelarIntNFeRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _user, tenant_id = user_and_tenant
    venda = _buscar_venda_para_nfe(db, venda_id, tenant_id)
    if not venda:
        raise HTTPException(404, "Venda não encontrada")
    api = _intnfe_client()
    try:
        return cancel_intnfe(db, venda, api, body.justificativa)
    except DirectEmissionError as exc:
        raise _direct_failure(exc) from None
    finally:
        api.close()


@router.get("/")
async def listar_nfes(
    data_inicial: Optional[str] = None,
    data_final: Optional[str] = None,
    situacao: Optional[str] = None,
    force_refresh: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as NF-e/NFC-e emitidas — busca direto do Bling (inclui marketplace)"""
    current_user, tenant_id = user_and_tenant
    bling_remoto_permitido = tenant_pode_usar_bling_global(tenant_id)
    fontes_permitidas = None if bling_remoto_permitido else FONTES_NFE_LOCAIS
    cache_key = _cache_key_listar_nfes(tenant_id, data_inicial, data_final, situacao)
    cache_atual = _nfe_list_cache.get(cache_key)
    agora_cache = monotonic()

    if (
        not force_refresh
        and cache_atual
        and (agora_cache - cache_atual.get("ts_monotonic", 0))
        <= _NFE_LIST_CACHE_SECONDS
    ):
        payload_cache = deepcopy(cache_atual.get("payload", {}))
        payload_cache["cache_utilizado"] = True
        payload_cache["cache_idade_segundos"] = int(
            max(agora_cache - cache_atual.get("ts_monotonic", 0), 0)
        )
        return payload_cache

    estado_cache = obter_estado_cache_notas(
        db, tenant_id, fontes_permitidas=fontes_permitidas
    )
    _sincronizar_fontes_locais_nfe_em_cache(
        db,
        tenant_id,
        estado_cache=estado_cache,
        force_refresh=force_refresh,
    )
    db.commit()

    cache_intervalo_tem_dados = existe_nota_cache_no_intervalo(
        db,
        tenant_id,
        data_inicial=data_inicial,
        data_final=data_final,
        situacao=situacao,
        fontes_permitidas=fontes_permitidas,
    )
    estado_cache = obter_estado_cache_notas(
        db, tenant_id, fontes_permitidas=fontes_permitidas
    )

    if bling_remoto_permitido:
        deve_sincronizar_bling, sync_data_inicial, sync_data_final, estrategia_sync = (
            _planejar_sincronizacao_bling_nfes(
                force_refresh=force_refresh,
                data_inicial=data_inicial,
                data_final=data_final,
                cache_total=estado_cache.get("total", 0),
                cache_intervalo_tem_dados=cache_intervalo_tem_dados,
                ultimo_sync=estado_cache.get("ultimo_sync"),
                ultima_data_emissao=estado_cache.get("ultima_data_emissao"),
            )
        )
    else:
        deve_sincronizar_bling = False
        sync_data_inicial = None
        sync_data_final = None
        estrategia_sync = "somente_fontes_locais"

    bling_ok = False
    if deve_sincronizar_bling:
        bling_ok, _ = _sincronizar_cache_nfes_com_bling(
            db,
            tenant_id,
            data_inicial=sync_data_inicial,
            data_final=sync_data_final,
            situacao=situacao,
        )

    notas = listar_notas_cache(
        db,
        tenant_id,
        data_inicial=data_inicial,
        data_final=data_final,
        situacao=situacao,
        fontes_permitidas=fontes_permitidas,
    )

    if not notas:
        try:
            _adicionar_notas_de_pedidos_integrados(
                db,
                tenant_id,
                notas,
                situacao=situacao,
                data_inicial=data_inicial,
                data_final=data_final,
            )
        except Exception as e:
            logger.warning(
                "listar_nfes", f"Erro ao complementar NFs via pedidos integrados: {e}"
            )

    _enriquecer_notas_com_vendas(db, tenant_id, notas)
    _enriquecer_notas_com_pedidos_integrados(db, tenant_id, notas)
    notas.sort(key=_sort_key_nota_por_numero_desc, reverse=True)

    payload = {
        "success": True,
        "total": len(notas),
        "notas": notas,
        "fonte": "bling_cache_incremental" if bling_ok else "cache_local",
        "cache_utilizado": False,
        "cache_idade_segundos": 0,
        "sincronizacao": {
            "executada": deve_sincronizar_bling,
            "estrategia": estrategia_sync,
            "janela": {
                "data_inicial": sync_data_inicial,
                "data_final": sync_data_final,
            },
        },
    }
    _nfe_list_cache[cache_key] = {
        "ts_monotonic": monotonic(),
        "payload": deepcopy(payload),
    }
    return payload


@router.post("/reconciliar-pendentes")
async def reconciliar_pendentes_nfe(
    dias: int = Query(default=3, ge=1, le=15),
    limite_notas: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    _exigir_bling_configurado_para_tenant(tenant_id)
    try:
        resultado = reconciliar_nfes_pendentes_recentes(
            db,
            tenant_id,
            dias=dias,
            limite_notas=limite_notas,
        )
        return {
            "success": True,
            **resultado,
        }
    except Exception as exc:
        logger.warning(
            "reconciliar_pendentes_nfe", f"Falha ao reconciliar NFs pendentes: {exc}"
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao reconciliar NFs pendentes: {exc}"
        )


router.include_router(listagem_rapida_router)
router.include_router(operacional_router)
