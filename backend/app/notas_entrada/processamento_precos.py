from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.notas_entrada.conferencia import (
    _resumir_conferencia_nota,
    _serializar_conferencia_item,
)
from app.notas_entrada.fiscal import (
    calcular_composicao_custos_nota,
    calcular_quantidade_custo_efetivos,
)
from app.notas_entrada.processamento_acoes import sugerir_acoes_processamento
from app.notas_entrada.produtos import (
    _montar_divergencia_codigo_barras_item,
    obter_detalhe_vinculo_item,
)
from app.notas_entrada.schemas import AtualizarPrecoRequest
from app.notas_entrada.xml_parser import parse_nfe_xml
from app.produtos_models import (
    NotaEntrada,
    NotaEntradaItem,
    Produto,
    ProdutoHistoricoPreco,
)

logger = logging.getLogger(__name__)
router = APIRouter()

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
# PREVIEW DE ENTRADA NO ESTOQUE - REVISÃƒÆ’O DE PREÃƒâ€¡OS
# ============================================================================


@router.get("/{nota_id}/preview-processamento")
def preview_processamento(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna preview da entrada com comparaÃƒÂ§ÃƒÂ£o de custos e preÃƒÂ§os atuais
    """
    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto))
        .filter(NotaEntrada.id == nota_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃƒÂ£o encontrada")

    if nota.produtos_nao_vinculados > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Existem {nota.produtos_nao_vinculados} produtos nÃƒÂ£o vinculados",
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

            # Calcular margem projetada mantendo o preÃ§o de venda atual e aplicando o novo custo
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
# ATUALIZAR PREÃƒâ€¡OS DOS PRODUTOS
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
    Atualiza preÃƒÂ§os de venda dos produtos antes de processar a nota
    Registra histÃƒÂ³rico de alteraÃƒÂ§ÃƒÂµes
    """
    current_user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nÃƒÂ£o encontrada")

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

            # Atualizar preÃƒÂ§o
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

            # Registrar histÃƒÂ³rico se houve alteraÃƒÂ§ÃƒÂ£o
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
                    variacao_custo_percentual=0,  # Custo nÃƒÂ£o mudou neste caso
                    variacao_venda_percentual=variacao_venda,
                    motivo="nfe_revisao_precos",
                    nota_entrada_id=nota.id,
                    referencia=f"NF-e {nota.numero_nota} - RevisÃƒÂ£o de PreÃƒÂ§os",
                    observacoes=f"PreÃƒÂ§o ajustado de R$ {preco_venda_anterior:.2f} para R$ {produto.preco_venda:.2f} (margem: {margem_anterior:.1f}% Ã¢â€ â€™ {margem_nova:.1f}%)",
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(historico)

                logger.info(
                    f"Ã°Å¸â€œÅ  HistÃƒÂ³rico registrado: {produto.nome} - "
                    f"PreÃƒÂ§o R$ {preco_venda_anterior:.2f} Ã¢â€ â€™ R$ {produto.preco_venda:.2f} "
                    f"({variacao_venda:+.2f}%)"
                )

    db.commit()

    return {"message": "PreÃƒÂ§os atualizados com sucesso"}
