from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.notas_entrada.conferencia import (
    CONFERENCIA_STATUS_COM_DIVERGENCIA,
    CONFERENCIA_STATUS_SEM_DIVERGENCIA,
    _mapear_lotes_rastro_xml,
    _montar_lotes_entrada_item,
    _normalizar_custo_unitario_override,
    _obter_override_mapa,
    _resumir_conferencia_nota,
    _round_quantity,
    _serializar_conferencia_item,
)
from app.notas_entrada.financeiro import criar_contas_pagar_da_nota
from app.notas_entrada.fiscal import (
    calcular_composicao_custos_nota,
    calcular_quantidade_custo_efetivos,
)
from app.notas_entrada.processamento_acoes import (
    calcular_acoes_pendentes_processamento,
    carregar_acoes_processamento_salvas,
    detectar_contexto_processamento,
    detectar_acoes_realizadas_processamento,
    mesclar_acoes_realizadas_processamento,
    resolver_custo_operacional_entrada,
)
from app.notas_entrada.processamento_precos import (
    router as precos_router,
    _aplicar_precos_venda_processamento,
    _atualizar_custo_produto_entrada,
    _reverter_historicos_precos_nota,
    atualizar_precos_produtos,
    preview_processamento,
)
from app.notas_entrada.produtos import (
    _aplicar_codigos_barras_item_no_produto,
    _aplicar_dados_fiscais_item_no_produto,
)
from app.notas_entrada.schemas import ProcessarConfig
from app.notas_entrada.xml_parser import parse_nfe_xml
from app.produtos_models import (
    EstoqueMovimentacao,
    NotaEntrada,
    NotaEntradaItem,
    ProdutoFornecedor,
    ProdutoHistoricoPreco,
    ProdutoLote,
)

logger = logging.getLogger(__name__)
router = APIRouter()
router.include_router(precos_router)

__all__ = [
    "_acoes_processamento_dict",
    "_aplicar_precos_venda_processamento",
    "_atualizar_custo_produto_entrada",
    "_carregar_acoes_processamento_nota",
    "_reverter_historicos_precos_nota",
    "atualizar_precos_produtos",
    "preview_processamento",
    "processar_entrada_estoque",
    "router",
]


def _acoes_processamento_dict(config: ProcessarConfig) -> dict:
    return {
        "lancar_estoque": bool(config.lancar_estoque),
        "atualizar_custo": bool(config.atualizar_custo),
        "atualizar_preco_venda": bool(config.atualizar_preco_venda),
        "gerar_contas_pagar": bool(config.gerar_contas_pagar),
    }


def _carregar_acoes_processamento_nota(nota: NotaEntrada) -> dict:
    return carregar_acoes_processamento_salvas(nota)


# DAR ENTRADA NO ESTOQUE
# ============================================================================


@router.post("/{nota_id}/processar")
def processar_entrada_estoque(
    nota_id: int,
    config: ProcessarConfig = ProcessarConfig(),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Processa entrada no estoque de todos os itens vinculados.
    Aceita:
    - multiplicadores_override: {"item_id": multiplicador} para packs manuais
    - custos_override: {"item_id": custo_unitario} para custo manual de sistema
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"Ã°Å¸â€œÂ¦ Processando entrada no estoque - Nota {nota_id}")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    acoes_processamento = _acoes_processamento_dict(config)
    acoes_realizadas_antes = detectar_acoes_realizadas_processamento(
        db, nota, tenant_id
    )
    acoes_ja_lancadas_selecionadas = [
        acao
        for acao, selecionada in acoes_processamento.items()
        if selecionada and acoes_realizadas_antes.get(acao)
    ]
    if acoes_ja_lancadas_selecionadas:
        raise HTTPException(
            status_code=400,
            detail=(
                "Alguns movimentos ja foram lancados para esta NF: "
                + ", ".join(acoes_ja_lancadas_selecionadas)
            ),
        )

    acoes_pendentes_selecionadas = calcular_acoes_pendentes_processamento(
        acoes_processamento, acoes_realizadas_antes
    )
    if not any(acoes_pendentes_selecionadas.values()):
        raise HTTPException(
            status_code=400, detail="Nenhum movimento pendente selecionado"
        )

    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃƒÂ£o vinculados. "
            "Vincule todos os produtos antes de processar.",
        )

    try:
        dados_xml_processamento = parse_nfe_xml(nota.xml_content)
    except Exception:
        dados_xml_processamento = {
            "natureza_operacao": "",
            "valor_total": nota.valor_total,
            "itens": [
                {"cfop": getattr(item, "cfop", None), "valor_total": item.valor_total}
                for item in nota.itens
            ],
        }

    contexto_processamento = detectar_contexto_processamento(dados_xml_processamento)
    nota.processamento_contexto = contexto_processamento["contexto"]
    acoes_realizadas_finais = mesclar_acoes_realizadas_processamento(
        acoes_realizadas_antes, acoes_processamento
    )
    nota.processamento_acoes = json.dumps(acoes_realizadas_finais, sort_keys=True)

    precos_venda_atualizados = 0
    if config.atualizar_preco_venda and config.precos_venda_override:
        precos_venda_atualizados = _aplicar_precos_venda_processamento(
            nota=nota,
            precos=config.precos_venda_override,
            db=db,
            current_user=current_user,
            tenant_id=tenant_id,
        )

    itens_processados = []
    custos_atualizados = 0
    composicoes_custo = calcular_composicao_custos_nota(nota)
    lotes_rastro_por_item = _mapear_lotes_rastro_xml(nota.xml_content)

    # Processar cada item
    for item in nota.itens:
        if not item.produto_id:
            continue

        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_base_conferida = conferencia_item["quantidade_conferida"]

        # Verificar override manual antes de usar auto-deteccao
        override_raw = _obter_override_mapa(config.multiplicadores_override, item.id)
        try:
            override_mult = int(override_raw) if override_raw is not None else None
        except (ValueError, TypeError):
            override_mult = None
        custo_unitario_manual = _normalizar_custo_unitario_override(
            _obter_override_mapa(config.custos_override, item.id),
            item.id,
        )

        if override_mult is not None and 1 <= override_mult <= 200:
            multiplicador_pack = override_mult
            quantidade_total_efetiva_nf = (item.quantidade or 0) * override_mult
            quantidade_entrada = quantidade_base_conferida * override_mult
            custo_total_aquisicao = composicao_custo.get(
                "custo_aquisicao_total", item.valor_total
            )
            custo_unitario_entrada = (
                (custo_total_aquisicao / quantidade_total_efetiva_nf)
                if quantidade_total_efetiva_nf > 0
                else item.valor_unitario
            )
            logger.info(
                f"ðŸ“¦ Pack MANUAL no item {item.id}: x{override_mult} (qtd NF {item.quantidade} â†’ qtd entrada {quantidade_entrada})"
            )
        else:
            dados_pack = calcular_quantidade_custo_efetivos(
                item.descricao, item.quantidade, item.valor_unitario, item.valor_total
            )
            quantidade_entrada = (
                quantidade_base_conferida * dados_pack["multiplicador_pack"]
            )
            custo_unitario_entrada = composicao_custo.get(
                "custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]
            )
            multiplicador_pack = dados_pack["multiplicador_pack"]

        custo_unitario_calculado_nf = custo_unitario_entrada

        if custo_unitario_manual is not None and config.atualizar_custo:
            custo_unitario_entrada = custo_unitario_manual
            logger.info(
                f"ðŸ’° Custo manual aplicado no item {item.id}: "
                f"R$ {custo_unitario_entrada:.4f} por unidade"
            )

        if quantidade_entrada <= 0:
            item.status = "processado"
            itens_processados.append(
                {
                    "produto_id": item.produto.id,
                    "produto_nome": item.produto.nome,
                    "quantidade": 0,
                    "lote": None,
                    "estoque_atual": item.produto.estoque_atual or 0,
                    "pack_multiplicador": multiplicador_pack,
                    "status_conferencia": conferencia_item["status_conferencia"],
                }
            )
            logger.info(
                f"  âš ï¸ {item.produto.nome}: sem entrada em estoque "
                f"(conferida: {quantidade_base_conferida}, avariada: {conferencia_item['quantidade_avariada']}, "
                f"faltante: {conferencia_item['quantidade_faltante']})"
            )
            continue

        produto = item.produto
        if not config.atualizar_custo:
            custo_unitario_entrada = resolver_custo_operacional_entrada(
                custo_nf=custo_unitario_calculado_nf,
                custo_atual_sistema=produto.preco_custo,
                atualizar_custo=False,
            )

        # Ã¢Å“â€¦ REATIVAR produto se estiver inativo
        if not produto.ativo:
            produto.ativo = True
            logger.info(
                f"  Ã¢â„¢Â»Ã¯Â¸Â  Produto reativado: {produto.codigo} - {produto.nome}"
            )

        # Atualizar dados fiscais do produto com informacoes do XML quando vierem preenchidas.
        # Entradas PDF preservam o cadastro atual, pois o arquivo nao contem dados fiscais reais.
        _aplicar_dados_fiscais_item_no_produto(
            produto,
            item,
            sobrescrever=nota.serie != "PDF",
        )

        _aplicar_codigos_barras_item_no_produto(produto, item)

        # Ã¢Å“â€¦ VINCULAR ao fornecedor da nota
        if nota.fornecedor_id:
            vinculo_existente = (
                db.query(ProdutoFornecedor)
                .filter(
                    ProdutoFornecedor.produto_id == produto.id,
                    ProdutoFornecedor.fornecedor_id == nota.fornecedor_id,
                )
                .first()
            )

            if not vinculo_existente:
                novo_vinculo = ProdutoFornecedor(
                    produto_id=produto.id,
                    fornecedor_id=nota.fornecedor_id,
                    preco_custo=custo_unitario_entrada,
                    e_principal=True,
                    ativo=True,
                    tenant_id=tenant_id,
                )
                db.add(novo_vinculo)
                logger.info(
                    f"  Ã°Å¸â€â€” Produto {produto.codigo} vinculado ao fornecedor {nota.fornecedor_id}"
                )
            else:
                # Reativar vÃƒÂ­nculo se estiver inativo
                if not vinculo_existente.ativo:
                    vinculo_existente.ativo = True
                    logger.info(
                        f"  Ã¢â„¢Â»Ã¯Â¸Â  VÃƒÂ­nculo de fornecedor reativado: {produto.codigo}"
                    )
                # Atualizar preÃƒÂ§o de custo no vÃƒÂ­nculo
                if config.atualizar_custo:
                    vinculo_existente.preco_custo = custo_unitario_entrada

        if not config.lancar_estoque:
            if config.atualizar_custo and _atualizar_custo_produto_entrada(
                produto=produto,
                nota=nota,
                custo_unitario_entrada=custo_unitario_entrada,
                custo_unitario_manual=custo_unitario_manual,
                db=db,
                current_user=current_user,
                tenant_id=tenant_id,
            ):
                custos_atualizados += 1
            item.status = "processado"
            continue

        lotes_entrada = _montar_lotes_entrada_item(
            item,
            nota,
            quantidade_entrada,
            lotes_rastro_por_item,
        )
        if not lotes_entrada:
            continue

        lotes_criados = []
        ordem_base = int(datetime.utcnow().timestamp())
        for lote_index, lote_entrada in enumerate(lotes_entrada):
            quantidade_lote = _round_quantity(lote_entrada["quantidade"])
            if quantidade_lote <= 0:
                continue

            lote = ProdutoLote(
                produto_id=produto.id,
                nome_lote=lote_entrada["nome_lote"],
                quantidade_inicial=quantidade_lote,
                quantidade_disponivel=quantidade_lote,
                custo_unitario=float(custo_unitario_entrada),
                data_fabricacao=lote_entrada.get("data_fabricacao"),
                data_validade=lote_entrada.get("data_validade"),
                ordem_entrada=ordem_base + lote_index,
                tenant_id=tenant_id,
            )
            db.add(lote)
            db.flush()
            lotes_criados.append((lote, quantidade_lote))

        if not lotes_criados:
            continue

        # Atualizar estoque
        estoque_anterior = produto.estoque_atual or 0
        produto.estoque_atual = estoque_anterior + quantidade_entrada

        # Atualizar preÃƒÂ§o de custo e registrar histÃƒÂ³rico
        preco_custo_anterior = produto.preco_custo or 0
        preco_venda_anterior = produto.preco_venda or 0
        margem_anterior = (
            ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100)
            if preco_venda_anterior > 0
            else 0
        )

        alterou_custo = False
        if config.atualizar_custo and custo_unitario_entrada != preco_custo_anterior:
            produto.preco_custo = custo_unitario_entrada
            alterou_custo = True
            custos_atualizados += 1

        # Calcular margem nova
        preco_venda_novo = produto.preco_venda or 0
        margem_nova = (
            ((preco_venda_novo - (produto.preco_custo or 0)) / preco_venda_novo * 100)
            if preco_venda_novo > 0
            else 0
        )

        # Registrar histÃƒÂ³rico de preÃƒÂ§o se houve alteraÃƒÂ§ÃƒÂ£o
        if alterou_custo:
            variacao_custo = (
                (
                    (produto.preco_custo - preco_custo_anterior)
                    / preco_custo_anterior
                    * 100
                )
                if preco_custo_anterior > 0
                else 0
            )

            historico = ProdutoHistoricoPreco(
                produto_id=produto.id,
                preco_custo_anterior=preco_custo_anterior,
                preco_custo_novo=produto.preco_custo,
                preco_venda_anterior=preco_venda_anterior,
                preco_venda_novo=preco_venda_novo,
                margem_anterior=margem_anterior,
                margem_nova=margem_nova,
                variacao_custo_percentual=variacao_custo,
                variacao_venda_percentual=0,  # PreÃƒÂ§o de venda nÃƒÂ£o mudou
                motivo="nfe_entrada",
                nota_entrada_id=nota.id,
                referencia=f"NF-e {nota.numero_nota}",
                observacoes=(
                    f"Entrada via NF-e: custo alterado de R$ {preco_custo_anterior:.2f} "
                    f"para R$ {produto.preco_custo:.2f}"
                    f"{' (ajuste manual aplicado no processamento)' if custo_unitario_manual is not None else ''}"
                ),
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(historico)

            logger.info(
                f"  Ã°Å¸â€œÅ  HistÃƒÂ³rico registrado: {produto.nome} - "
                f"Custo R$ {preco_custo_anterior:.2f} Ã¢â€ â€™ R$ {produto.preco_custo:.2f} "
                f"({variacao_custo:+.2f}%)"
            )

        observacao_movimentacao = (
            (
                f"Entrada NF-e {nota.numero_nota} - {item.descricao}"
                if conferencia_item["status_conferencia"] == "ok"
                else (
                    f"Entrada NF-e {nota.numero_nota} - {item.descricao} | "
                    f"Conferida: {conferencia_item['quantidade_conferida']} | "
                    f"Avariada: {conferencia_item['quantidade_avariada']} | "
                    f"Faltante: {conferencia_item['quantidade_faltante']}"
                )
            )
            + (
                f" | Custo sistema manual: R$ {custo_unitario_entrada:.4f}"
                if custo_unitario_manual is not None and config.atualizar_custo
                else ""
            )
            + (
                " | Custo do cadastro preservado; entrada valorizada pelo custo atual do sistema"
                if not config.atualizar_custo
                else ""
            )
        )

        estoque_movimento_anterior = estoque_anterior
        for lote, quantidade_lote in lotes_criados:
            estoque_movimento_novo = _round_quantity(
                estoque_movimento_anterior + quantidade_lote
            )
            movimentacao = EstoqueMovimentacao(
                produto_id=produto.id,
                lote_id=lote.id,
                tipo="entrada",
                motivo="compra",
                quantidade=quantidade_lote,
                quantidade_anterior=estoque_movimento_anterior,
                quantidade_nova=estoque_movimento_novo,
                custo_unitario=float(custo_unitario_entrada),
                valor_total=float(quantidade_lote * custo_unitario_entrada),
                documento=nota.chave_acesso,
                referencia_tipo="nota_entrada",
                referencia_id=nota.id,
                observacao=observacao_movimentacao,
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(movimentacao)
            estoque_movimento_anterior = estoque_movimento_novo

        # Atualizar status do item
        item.status = "processado"

        itens_processados.append(
            {
                "produto_id": produto.id,
                "produto_nome": produto.nome,
                "quantidade": quantidade_entrada,
                "lote": ", ".join(lote.nome_lote for lote, _ in lotes_criados),
                "estoque_atual": produto.estoque_atual,
                "pack_multiplicador": multiplicador_pack,
                "status_conferencia": conferencia_item["status_conferencia"],
                "custo_unitario_aplicado": float(custo_unitario_entrada),
                "custo_manual_aplicado": (
                    custo_unitario_manual is not None and config.atualizar_custo
                ),
            }
        )

        logger.info(
            f"  Ã¢Å“â€¦ {produto.nome}: +{quantidade_entrada} unidades "
            f"em {len(lotes_criados)} lote(s) "
            f"(estoque: {estoque_anterior} Ã¢â€ â€™ {produto.estoque_atual})"
        )

        if multiplicador_pack > 1:
            logger.info(
                f"  Ã°Å¸â€œÂ¦ Pack detectado automaticamente no item {item.numero_item}: "
                f"x{multiplicador_pack} (qtd NF {item.quantidade} Ã¢â€ â€™ qtd entrada {quantidade_entrada})"
            )

    resumo_conferencia = _resumir_conferencia_nota(nota)
    if not nota.conferencia_realizada_em:
        nota.conferencia_realizada_em = datetime.utcnow()
        nota.conferencia_user_id = current_user.id
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo_conferencia["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    resumo_conferencia = _resumir_conferencia_nota(nota)

    # Atualizar nota
    nota.status = "processada"
    nota.entrada_estoque_realizada = bool(acoes_realizadas_finais["lancar_estoque"])
    nota.processada_em = datetime.utcnow()

    # CRIAR CONTAS A PAGAR apÃƒÂ³s processar estoque
    contas_ids = []
    if config.gerar_contas_pagar:
        try:
            # Buscar dados do XML salvos na nota para pegar duplicatas
            dados_xml = dados_xml_processamento
            contas_ids = criar_contas_pagar_da_nota(
                nota, dados_xml, db, current_user.id, tenant_id
            )
            logger.info(f"Ã°Å¸â€™Â° {len(contas_ids)} contas a pagar criadas")
        except Exception as exc:
            db.rollback()
            logger.exception("Erro ao criar contas a pagar da NF %s", nota.numero_nota)
            raise HTTPException(
                status_code=500,
                detail=(
                    "Erro ao gerar contas a pagar da NF. "
                    "Nenhum movimento foi confirmado."
                ),
            ) from exc
    else:
        logger.info("Geracao de contas a pagar desmarcada para NF %s", nota.numero_nota)

    db.commit()

    # SINCRONIZAR ESTOQUE COM BLING para todos os itens processados
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        for item_proc in itens_processados:
            sincronizar_bling_background(
                item_proc["produto_id"], item_proc["estoque_atual"], "entrada_nfe"
            )
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (entrada_nfe): {e_sync}")

    # VERIFICAR E NOTIFICAR PENDÃŠNCIAS DE ESTOQUE
    from app.services.pendencia_estoque_service import verificar_e_notificar_pendencias

    try:
        for item_proc in itens_processados:
            produto_id = item_proc["produto_id"]
            quantidade = item_proc["quantidade"]
            notificacoes = verificar_e_notificar_pendencias(
                db=db,
                tenant_id=tenant_id,
                produto_id=produto_id,
                quantidade_entrada=quantidade,
            )
            if notificacoes > 0:
                logger.info(
                    f"WhatsApp: {notificacoes} clientes notificados sobre {item_proc['produto']}"
                )
    except Exception as e:
        logger.error(f"Erro ao notificar pendencias: {str(e)}")
        # NÃ£o abortar, apenas logar o erro

    logger.info(f"Ã¢Å“â€¦ Entrada processada: {len(itens_processados)} produtos")

    return {
        "message": "Movimentos da NF processados com sucesso",
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "itens_processados": len(itens_processados),
        "contas_pagar_criadas": len(contas_ids),
        "custos_atualizados": custos_atualizados,
        "precos_venda_atualizados": precos_venda_atualizados,
        "acoes_processamento": acoes_processamento,
        "acoes_processamento_realizadas": acoes_realizadas_finais,
        "acoes_processamento_pendentes": {
            chave: not realizada for chave, realizada in acoes_realizadas_finais.items()
        },
        "conferencia": resumo_conferencia,
        "detalhes": itens_processados,
    }
