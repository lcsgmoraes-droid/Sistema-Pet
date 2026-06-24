from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List

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
    detectar_contexto_processamento,
    resolver_custo_operacional_entrada,
    sugerir_acoes_processamento,
)
from app.notas_entrada.produtos import (
    _aplicar_codigos_barras_item_no_produto,
    _aplicar_dados_fiscais_item_no_produto,
    _montar_divergencia_codigo_barras_item,
    obter_detalhe_vinculo_item,
)
from app.notas_entrada.schemas import AtualizarPrecoRequest, ProcessarConfig
from app.notas_entrada.xml_parser import parse_nfe_xml
from app.produtos_models import (
    EstoqueMovimentacao,
    NotaEntrada,
    NotaEntradaItem,
    Produto,
    ProdutoFornecedor,
    ProdutoHistoricoPreco,
    ProdutoLote,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _acoes_processamento_dict(config: ProcessarConfig) -> dict:
    return {
        "lancar_estoque": bool(config.lancar_estoque),
        "atualizar_custo": bool(config.atualizar_custo),
        "atualizar_preco_venda": bool(config.atualizar_preco_venda),
        "gerar_contas_pagar": bool(config.gerar_contas_pagar),
    }


def _carregar_acoes_processamento_nota(nota: NotaEntrada) -> dict:
    if getattr(nota, "processamento_acoes", None):
        try:
            dados = json.loads(nota.processamento_acoes)
            if isinstance(dados, dict):
                return {
                    "lancar_estoque": bool(dados.get("lancar_estoque")),
                    "atualizar_custo": bool(dados.get("atualizar_custo")),
                    "atualizar_preco_venda": bool(dados.get("atualizar_preco_venda")),
                    "gerar_contas_pagar": bool(dados.get("gerar_contas_pagar")),
                }
        except (TypeError, ValueError):
            pass

    legado_processado = bool(getattr(nota, "entrada_estoque_realizada", False))
    return {
        "lancar_estoque": legado_processado,
        "atualizar_custo": legado_processado,
        "atualizar_preco_venda": legado_processado,
        "gerar_contas_pagar": legado_processado,
    }


def _reverter_historicos_precos_nota(
    *, produto: Produto, nota: NotaEntrada, db: Session, tenant_id
) -> int:
    historicos = (
        db.query(ProdutoHistoricoPreco)
        .filter(
            ProdutoHistoricoPreco.produto_id == produto.id,
            ProdutoHistoricoPreco.nota_entrada_id == nota.id,
            ProdutoHistoricoPreco.motivo.in_(["nfe_entrada", "nfe_revisao_precos"]),
            ProdutoHistoricoPreco.tenant_id == tenant_id,
        )
        .order_by(ProdutoHistoricoPreco.id.desc())
        .all()
    )

    for historico in historicos:
        produto.preco_custo = float(historico.preco_custo_anterior or 0)
        produto.preco_venda = float(historico.preco_venda_anterior or 0)
        db.delete(historico)

    return len(historicos)


def _atualizar_custo_produto_entrada(
    *,
    produto: Produto,
    nota: NotaEntrada,
    custo_unitario_entrada: float,
    custo_unitario_manual: float | None,
    db: Session,
    current_user,
    tenant_id,
) -> bool:
    preco_custo_anterior = produto.preco_custo or 0
    if custo_unitario_entrada == preco_custo_anterior:
        return False

    preco_venda_anterior = produto.preco_venda or 0
    margem_anterior = (
        ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100)
        if preco_venda_anterior > 0
        else 0
    )

    produto.preco_custo = custo_unitario_entrada
    preco_venda_novo = produto.preco_venda or 0
    margem_nova = (
        ((preco_venda_novo - produto.preco_custo) / preco_venda_novo * 100)
        if preco_venda_novo > 0
        else 0
    )
    variacao_custo = (
        ((produto.preco_custo - preco_custo_anterior) / preco_custo_anterior * 100)
        if preco_custo_anterior > 0
        else 0
    )

    db.add(
        ProdutoHistoricoPreco(
            produto_id=produto.id,
            preco_custo_anterior=preco_custo_anterior,
            preco_custo_novo=produto.preco_custo,
            preco_venda_anterior=preco_venda_anterior,
            preco_venda_novo=preco_venda_novo,
            margem_anterior=margem_anterior,
            margem_nova=margem_nova,
            variacao_custo_percentual=variacao_custo,
            variacao_venda_percentual=0,
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
    )
    return True


# ============================================================================
# PREVIEW DE ENTRADA NO ESTOQUE - REVISÃƒO DE PREÃ‡OS
# ============================================================================


@router.get("/{nota_id}/preview-processamento")
def preview_processamento(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna preview da entrada com comparaÃ§Ã£o de custos e preÃ§os atuais
    """
    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados",
        )

    composicoes_custo = calcular_composicao_custos_nota(nota)
    preview_itens = []

    for item in nota.itens:
        composicao_custo = composicoes_custo.get(item.id, {})
        conferencia_item = _serializar_conferencia_item(item)
        # Dados do item da NF (sempre presente)
        dados_pack = calcular_quantidade_custo_efetivos(
            item.descricao, item.quantidade, item.valor_unitario, item.valor_total
        )

        item_nf = {
            "item_id": item.id,
            "codigo_produto_nf": item.codigo_produto,
            "descricao_nf": item.descricao,
            "quantidade_nf": item.quantidade,
            "valor_unitario_nf": item.valor_unitario,
            "quantidade_efetiva_nf": dados_pack["quantidade_efetiva"],
            "custo_unitario_efetivo_nf": dados_pack["custo_unitario_efetivo"],
            "custo_aquisicao_unitario_nf": composicao_custo.get(
                "custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]
            ),
            "custo_aquisicao_total_nf": composicao_custo.get(
                "custo_aquisicao_total", item.valor_total
            ),
            "composicao_custo": composicao_custo,
            "pack_detectado_automatico": dados_pack["pack_detectado"],
            "pack_multiplicador_detectado": dados_pack["multiplicador_pack"],
            "ean_nf": item.ean,
            "ean_tributario_nf": getattr(item, "ean_tributario", None),
            "ncm_nf": item.ncm,
            "vinculado": item.vinculado,
            "confianca_vinculo": item.confianca_vinculo,
            "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(item),
            **conferencia_item,
        }

        detalhe_vinculo = obter_detalhe_vinculo_item(item)
        item_nf["origem_vinculo_automatico"] = detalhe_vinculo["origem"]
        item_nf["referencia_vinculo"] = detalhe_vinculo["referencia"]

        # Dados do produto vinculado (se houver)
        produto_vinculado = None
        if item.produto_id:
            produto = item.produto
            custo_atual = produto.preco_custo or 0
            custo_novo = composicao_custo.get(
                "custo_aquisicao_unitario", dados_pack["custo_unitario_efetivo"]
            )
            variacao_custo = (
                ((custo_novo - custo_atual) / custo_atual * 100)
                if custo_atual > 0
                else 0
            )

            # Calcular margem de referencia (com custo atual do cadastro)
            preco_venda_atual = produto.preco_venda or 0
            if preco_venda_atual > 0 and custo_atual > 0:
                margem_atual = (
                    (preco_venda_atual - custo_atual) / preco_venda_atual
                ) * 100
            else:
                margem_atual = 0

            # Calcular margem projetada mantendo o preço de venda atual e aplicando o novo custo
            if preco_venda_atual > 0 and custo_novo > 0:
                margem_projetada = (
                    (preco_venda_atual - custo_novo) / preco_venda_atual
                ) * 100
            else:
                margem_projetada = 0

            produto_vinculado = {
                "produto_id": produto.id,
                "produto_codigo": produto.codigo,
                "produto_nome": produto.nome,
                "produto_ean": produto.codigo_barras,
                "produto_codigo_barras": produto.codigo_barras,
                "produto_gtin_ean": produto.gtin_ean,
                "produto_ean_tributario": produto.gtin_ean_tributario,
                "divergencia_codigo_barras": _montar_divergencia_codigo_barras_item(
                    item
                ),
                "custo_anterior": custo_atual,
                "custo_novo": custo_novo,
                "variacao_custo_percentual": round(variacao_custo, 2),
                "preco_venda_atual": preco_venda_atual,
                "margem_atual": round(margem_atual, 2),
                "margem_projetada_custo_novo": round(margem_projetada, 2),
                "estoque_atual": produto.estoque_atual or 0,
            }

        preview_itens.append({**item_nf, "produto_vinculado": produto_vinculado})

    try:
        dados_xml = parse_nfe_xml(nota.xml_content)
    except Exception:
        dados_xml = {
            "natureza_operacao": "",
            "valor_total": nota.valor_total,
            "itens": [
                {"cfop": getattr(item, "cfop", None), "valor_total": item.valor_total}
                for item in nota.itens
            ],
        }
    sugestao_acoes = sugerir_acoes_processamento(dados_xml)

    return {
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "data_emissao": nota.data_emissao.isoformat() if nota.data_emissao else None,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "valor_total": nota.valor_total,
        "conferencia": _resumir_conferencia_nota(nota),
        "acoes_processamento_sugeridas": sugestao_acoes["acoes"],
        "processamento_contexto": sugestao_acoes["contexto"],
        "processamento_mensagem": sugestao_acoes["mensagem"],
        "itens": preview_itens,
    }


# ============================================================================
# ATUALIZAR PREÃ‡OS DOS PRODUTOS
# ============================================================================


def _aplicar_precos_venda_processamento(
    *,
    nota: NotaEntrada,
    precos: List[AtualizarPrecoRequest],
    db: Session,
    current_user,
    tenant_id,
) -> int:
    atualizados = 0
    for preco_data in precos:
        produto = (
            db.query(Produto)
            .filter(Produto.id == preco_data.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if not produto:
            continue

        preco_venda_anterior = produto.preco_venda or 0
        preco_custo_anterior = produto.preco_custo or 0
        if preco_venda_anterior == preco_data.preco_venda:
            continue

        margem_anterior = (
            ((preco_venda_anterior - preco_custo_anterior) / preco_venda_anterior * 100)
            if preco_venda_anterior > 0
            else 0
        )
        produto.preco_venda = preco_data.preco_venda
        margem_nova = (
            (
                (produto.preco_venda - (produto.preco_custo or 0))
                / produto.preco_venda
                * 100
            )
            if produto.preco_venda > 0
            else 0
        )
        variacao_venda = (
            ((produto.preco_venda - preco_venda_anterior) / preco_venda_anterior * 100)
            if preco_venda_anterior > 0
            else 0
        )

        db.add(
            ProdutoHistoricoPreco(
                produto_id=produto.id,
                preco_custo_anterior=preco_custo_anterior,
                preco_custo_novo=produto.preco_custo,
                preco_venda_anterior=preco_venda_anterior,
                preco_venda_novo=produto.preco_venda,
                margem_anterior=margem_anterior,
                margem_nova=margem_nova,
                variacao_custo_percentual=0,
                variacao_venda_percentual=variacao_venda,
                motivo="nfe_revisao_precos",
                nota_entrada_id=nota.id,
                referencia=f"NF-e {nota.numero_nota} - Revisao de precos",
                observacoes=(
                    f"Preco ajustado de R$ {preco_venda_anterior:.2f} "
                    f"para R$ {produto.preco_venda:.2f}"
                ),
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
        )
        atualizados += 1

    return atualizados


@router.post("/{nota_id}/atualizar-precos")
def atualizar_precos_produtos(
    nota_id: int,
    precos: List[AtualizarPrecoRequest],
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza preÃ§os de venda dos produtos antes de processar a nota
    Registra histÃ³rico de alteraÃ§Ãµes
    """
    current_user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    for preco_data in precos:
        produto = (
            db.query(Produto)
            .filter(Produto.id == preco_data.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if produto:
            # Capturar valores anteriores
            preco_venda_anterior = produto.preco_venda
            preco_custo_anterior = produto.preco_custo
            margem_anterior = (
                (
                    (preco_venda_anterior - preco_custo_anterior)
                    / preco_venda_anterior
                    * 100
                )
                if preco_venda_anterior > 0
                else 0
            )

            # Atualizar preÃ§o
            produto.preco_venda = preco_data.preco_venda

            # Calcular nova margem
            margem_nova = (
                (
                    (produto.preco_venda - produto.preco_custo)
                    / produto.preco_venda
                    * 100
                )
                if produto.preco_venda > 0
                else 0
            )

            # Registrar histÃ³rico se houve alteraÃ§Ã£o
            if preco_venda_anterior != produto.preco_venda:
                variacao_venda = (
                    (
                        (produto.preco_venda - preco_venda_anterior)
                        / preco_venda_anterior
                        * 100
                    )
                    if preco_venda_anterior > 0
                    else 0
                )

                historico = ProdutoHistoricoPreco(
                    produto_id=produto.id,
                    preco_custo_anterior=preco_custo_anterior,
                    preco_custo_novo=produto.preco_custo,
                    preco_venda_anterior=preco_venda_anterior,
                    preco_venda_novo=produto.preco_venda,
                    margem_anterior=margem_anterior,
                    margem_nova=margem_nova,
                    variacao_custo_percentual=0,  # Custo nÃ£o mudou neste caso
                    variacao_venda_percentual=variacao_venda,
                    motivo="nfe_revisao_precos",
                    nota_entrada_id=nota.id,
                    referencia=f"NF-e {nota.numero_nota} - RevisÃ£o de PreÃ§os",
                    observacoes=f"PreÃ§o ajustado de R$ {preco_venda_anterior:.2f} para R$ {produto.preco_venda:.2f} (margem: {margem_anterior:.1f}% â†’ {margem_nova:.1f}%)",
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(historico)

                logger.info(
                    f"ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                    f"PreÃ§o R$ {preco_venda_anterior:.2f} â†’ R$ {produto.preco_venda:.2f} "
                    f"({variacao_venda:+.2f}%)"
                )

    db.commit()

    return {"message": "PreÃ§os atualizados com sucesso"}


# ============================================================================
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
    logger.info(f"ðŸ“¦ Processando entrada no estoque - Nota {nota_id}")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃ£o encontrada")

    if nota.entrada_estoque_realizada or nota.status == "processada":
        raise HTTPException(
            status_code=400, detail="Entrada no estoque jÃ¡ foi realizada"
        )

    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃ£o vinculados. "
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

    acoes_processamento = _acoes_processamento_dict(config)
    contexto_processamento = detectar_contexto_processamento(dados_xml_processamento)
    nota.processamento_contexto = contexto_processamento["contexto"]
    nota.processamento_acoes = json.dumps(acoes_processamento, sort_keys=True)

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
                f"📦 Pack MANUAL no item {item.id}: x{override_mult} (qtd NF {item.quantidade} → qtd entrada {quantidade_entrada})"
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
                f"💰 Custo manual aplicado no item {item.id}: "
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
                f"  ⚠️ {item.produto.nome}: sem entrada em estoque "
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

        # âœ… REATIVAR produto se estiver inativo
        if not produto.ativo:
            produto.ativo = True
            logger.info(
                f"  â™»ï¸  Produto reativado: {produto.codigo} - {produto.nome}"
            )

        # Atualizar dados fiscais do produto com informacoes do XML quando vierem preenchidas.
        # Entradas PDF preservam o cadastro atual, pois o arquivo nao contem dados fiscais reais.
        _aplicar_dados_fiscais_item_no_produto(
            produto,
            item,
            sobrescrever=nota.serie != "PDF",
        )

        _aplicar_codigos_barras_item_no_produto(produto, item)

        # âœ… VINCULAR ao fornecedor da nota
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
                    f"  ðŸ”— Produto {produto.codigo} vinculado ao fornecedor {nota.fornecedor_id}"
                )
            else:
                # Reativar vÃ­nculo se estiver inativo
                if not vinculo_existente.ativo:
                    vinculo_existente.ativo = True
                    logger.info(
                        f"  â™»ï¸  VÃ­nculo de fornecedor reativado: {produto.codigo}"
                    )
                # Atualizar preÃ§o de custo no vÃ­nculo
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

        # Atualizar preÃ§o de custo e registrar histÃ³rico
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

        # Registrar histÃ³rico de preÃ§o se houve alteraÃ§Ã£o
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
                variacao_venda_percentual=0,  # PreÃ§o de venda nÃ£o mudou
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
                f"  ðŸ“Š HistÃ³rico registrado: {produto.nome} - "
                f"Custo R$ {preco_custo_anterior:.2f} â†’ R$ {produto.preco_custo:.2f} "
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
            f"  âœ… {produto.nome}: +{quantidade_entrada} unidades "
            f"em {len(lotes_criados)} lote(s) "
            f"(estoque: {estoque_anterior} â†’ {produto.estoque_atual})"
        )

        if multiplicador_pack > 1:
            logger.info(
                f"  ðŸ“¦ Pack detectado automaticamente no item {item.numero_item}: "
                f"x{multiplicador_pack} (qtd NF {item.quantidade} â†’ qtd entrada {quantidade_entrada})"
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
    nota.entrada_estoque_realizada = bool(config.lancar_estoque)
    nota.processada_em = datetime.utcnow()

    # CRIAR CONTAS A PAGAR apÃ³s processar estoque
    contas_ids = []
    try:
        # Buscar dados do XML salvos na nota para pegar duplicatas
        dados_xml = dados_xml_processamento

        contas_ids = (
            criar_contas_pagar_da_nota(nota, dados_xml, db, current_user.id, tenant_id)
            if config.gerar_contas_pagar
            else []
        )
        logger.info(f"ðŸ’° {len(contas_ids)} contas a pagar criadas")
    except Exception as e:
        logger.error(f"âš ï¸ Erro ao criar contas a pagar: {str(e)}")
        # NÃ£o abortar o processo, apenas avisar

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

    # VERIFICAR E NOTIFICAR PENDÊNCIAS DE ESTOQUE
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
        # Não abortar, apenas logar o erro

    logger.info(f"âœ… Entrada processada: {len(itens_processados)} produtos")

    return {
        "message": "Entrada no estoque realizada com sucesso",
        "nota_id": nota.id,
        "numero_nota": nota.numero_nota,
        "itens_processados": len(itens_processados),
        "contas_pagar_criadas": len(contas_ids),
        "custos_atualizados": custos_atualizados,
        "precos_venda_atualizados": precos_venda_atualizados,
        "acoes_processamento": acoes_processamento,
        "conferencia": resumo_conferencia,
        "detalhes": itens_processados,
    }
