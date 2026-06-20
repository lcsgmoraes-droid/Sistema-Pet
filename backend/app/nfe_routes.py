"""
Rotas para gerenciamento de Notas Fiscais Eletrônicas
"""

from copy import deepcopy
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.services.nfe_cache_service import (
    existe_nota_cache_no_intervalo,
    listar_notas_cache,
    obter_estado_cache_notas,
)
from app.services.nfe_pending_reconciliation_service import (
    reconciliar_nfes_pendentes_recentes,
)
from app.vendas_models import Venda
from app.bling_integration import (
    BlingAPI,
    aplicar_correcoes_fiscais_venda,
    prevalidar_fiscal_venda,
)
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


def _normalizar_tipo_nota(tipo_nota: str | None) -> str:
    tipo = str(tipo_nota or "nfce").strip().lower()
    return "nfe" if tipo == "nfe" else "nfce"


def _buscar_venda_para_nfe(db: Session, venda_id: int, tenant_id):
    return (
        db.query(Venda)
        .filter(Venda.id == venda_id, Venda.tenant_id == tenant_id)
        .first()
    )


@router.post("/prevalidar")
async def prevalidar_nfe(
    request: PrevalidarNFeRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Valida pendencias fiscais antes de criar a nota no Bling."""
    current_user, tenant_id = user_and_tenant
    tipo_nota = _normalizar_tipo_nota(request.tipo_nota)
    venda = _buscar_venda_para_nfe(db, request.venda_id, tenant_id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")

    validacao = prevalidar_fiscal_venda(venda, tipo_nota, db)
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
    """Emite NF-e ou NFC-e para uma venda"""
    import traceback

    try:
        current_user, tenant_id = user_and_tenant
        tipo_nota = _normalizar_tipo_nota(request.tipo_nota)
        venda = _buscar_venda_para_nfe(db, request.venda_id, tenant_id)
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        # Verificar se venda já tem NF emitida
        if venda.nfe_bling_id:
            raise HTTPException(
                status_code=400,
                detail=f"Esta venda já possui nota fiscal emitida (NF #{venda.nfe_numero}). Cancele a nota existente antes de emitir uma nova.",
            )

        logger.info("emitir_nfe", "\n=== EMITINDO NF-e ===")
        logger.info("emitir_nfe", f"Venda ID: {venda.id}")
        logger.info("emitir_nfe", f"Tipo: {tipo_nota}")

        validacao_fiscal = prevalidar_fiscal_venda(venda, tipo_nota, db)
        pendencias_fiscais = validacao_fiscal.get("bloqueios") or validacao_fiscal.get(
            "correcoes"
        )
        if pendencias_fiscais:
            if request.autorizar_correcoes_fiscais and not validacao_fiscal.get(
                "bloqueios"
            ):
                aplicar_correcoes_fiscais_venda(
                    venda,
                    tipo_nota,
                    db,
                    user_id=getattr(current_user, "id", None),
                )
                db.flush()
                logger.info(
                    "emitir_nfe",
                    f"Correcoes fiscais autorizadas antes da emissao da venda {venda.id}",
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "erro": "pendencias_fiscais",
                        "mensagem": "Existem dados fiscais para conferir antes de emitir a nota.",
                        "validacao": validacao_fiscal,
                    },
                )

        bling = BlingAPI()
        resultado = bling.emitir_nota_fiscal(
            venda,
            tipo_nota,
            db,
            transmitir=request.transmitir,
        )

        logger.info("emitir_nfe", f"DEBUG: Resultado Bling: {resultado}")

        # Extrair dados da resposta (Bling retorna em 'data')
        dados_nota = (
            resultado.get("data", resultado) if isinstance(resultado, dict) else {}
        )

        # Atualizar venda com dados da nota
        # IMPORTANTE: tipo deve ser INTEGER (0=NF-e, 1=NFC-e) para consultas funcionarem
        venda.nfe_tipo = tipo_nota
        venda.nfe_modelo = "55" if tipo_nota == "nfe" else "65"
        venda.nfe_numero = dados_nota.get("numero")
        venda.nfe_serie = dados_nota.get("serie")
        venda.nfe_chave = dados_nota.get("chaveAcesso")

        # Mapear situacao (número) para texto
        venda.nfe_status = _status_nota_bling(dados_nota)

        venda.nfe_bling_id = dados_nota.get("id")
        venda.nfe_data_emissao = datetime.now()

        logger.info(
            "emitir_nfe",
            f"✅ Rastreamento: Venda #{venda.id} → Bling #{venda.nfe_bling_id} (Tipo {venda.nfe_tipo}, Modelo {venda.nfe_modelo})",
        )

        logger.info(
            "emitir_nfe",
            f"DEBUG: Salvando - nfe_bling_id={venda.nfe_bling_id}, numero={venda.nfe_numero}, status={venda.nfe_status}",
        )

        # Mudar status para 'pago_nf' quando a nota for emitida
        venda.status = "pago_nf"

        db.commit()
        db.refresh(venda)

        logger.info(
            "emitir_nfe",
            f"DEBUG: Após commit - nfe_bling_id={venda.nfe_bling_id}, venda_id={venda.id}",
        )

        return {
            "success": True,
            "message": f"{'NF-e' if tipo_nota == 'nfe' else 'NFC-e'} emitida com sucesso",
            "nfe_id": dados_nota.get("id"),
            "numero": dados_nota.get("numero"),
            "serie": dados_nota.get("serie"),
            "chave_acesso": dados_nota.get("chaveAcesso"),
            "situacao": dados_nota.get("situacao", "Pendente"),
            "transmissao": resultado.get("transmissao")
            if isinstance(resultado, dict)
            else None,
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("emitir_nfe_error", f"❌ ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        erro_msg = str(e)
        erro_upper = erro_msg.upper()
        if (
            "TOO_MANY_REQUESTS" in erro_upper
            or "HTTP 429" in erro_upper
            or "TOO MANY REQUESTS" in erro_upper
            or "LIMITE TEMPORARIO DE REQUISICOES DO BLING" in erro_upper
        ):
            logger.warning(
                "emitir_nfe_rate_limit",
                f"Bling limitou a emissao da venda {getattr(request, 'venda_id', None)}: {erro_msg}",
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "erro": "bling_rate_limit",
                    "mensagem": (
                        "O Bling limitou temporariamente as emissoes. "
                        "Aguarde alguns segundos e tente novamente."
                    ),
                    "retry_after_seconds": 30,
                    "detalhe": erro_msg,
                },
            )
        logger.error("emitir_nfe_error", "❌ ERRO AO EMITIR NF-e:")
        logger.error("emitir_nfe_error", f"Erro: {str(e)}")
        logger.error("emitir_nfe_error", "Traceback completo:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao emitir NF-e: {str(e)}")


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

    estado_cache = obter_estado_cache_notas(db, tenant_id)
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
    )
    estado_cache = obter_estado_cache_notas(db, tenant_id)

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


router.include_router(operacional_router)
