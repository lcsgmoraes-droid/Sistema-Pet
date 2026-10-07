"""Reconcilia itens de venda aberta sem descartar o custo da baixa original."""

from collections import Counter
from decimal import Decimal

from fastapi import HTTPException

from app.grupo_comercial_estoque_compartilhado_service import resolver_tenant_estoque_item
from app.vendas.custo_original import registrar_custo_original_saida
from app.vendas.racao_previsao import validar_previsao_fim_racao
from app.vendas_models import VendaItem


def _chave_item(item, origem: str) -> tuple:
    """Preço e desconto podem mudar sem alterar a unidade retirada do estoque."""
    tipo = str(getattr(item, "tipo", "") or "").lower()
    produto_id = getattr(item, "produto_id", None)
    return (
        tipo,
        int(produto_id) if produto_id is not None else None,
        str(origem),
        Decimal(str(getattr(item, "quantidade", 0) or 0)),
        (
            str(getattr(item, "servico_descricao", "") or "")
            if tipo == "servico" and produto_id is None
            else None
        ),
    )


def _grupo_item(item, origem: str) -> tuple:
    chave = _chave_item(item, origem)
    return chave[0], chave[1], chave[2], chave[4]


def atualizar_itens_venda_aberta(
    *,
    venda_id: int,
    cliente_id: int | None,
    tenant_id,
    itens_antigos: list,
    itens_novos: list,
    resolucoes_produtos: dict,
    saidas_ajuste: dict,
    db,
) -> None:
    """Mantém ID e comprovante da linha quando o estoque físico não mudou.

    Uma quantidade alterada não herda o comprovante anterior. Novas baixas só
    vinculam custo quando o movimento de edição corresponde à linha inteira.
    """
    disponiveis = sorted(itens_antigos, key=lambda item: item.id)
    novos_criados = []
    antigos_por_id = {item.id: item for item in disponiveis}
    ids_reservados = {item.item_id for item in itens_novos if item.item_id is not None}
    antigos_sem_id_por_grupo = Counter(
        _grupo_item(item, resolver_tenant_estoque_item(item, tenant_id)[0])
        for item in disponiveis
        if item.id not in ids_reservados
    )
    sem_id_por_grupo = Counter()
    for item_data in itens_novos:
        if item_data.item_id is not None:
            continue
        produto_id = getattr(item_data, "produto_id", None)
        resolucao = resolucoes_produtos.get(int(produto_id)) if produto_id else None
        origem = str(resolucao.tenant_origem_id) if resolucao else str(tenant_id)
        sem_id_por_grupo[_grupo_item(item_data, origem)] += 1

    for item_data in itens_novos:
        produto_id = getattr(item_data, "produto_id", None)
        resolucao = resolucoes_produtos.get(int(produto_id)) if produto_id else None
        produto_catalogo = resolucao.produto if resolucao else None
        origem_nova = str(resolucao.tenant_origem_id) if resolucao else str(tenant_id)
        previsao = validar_previsao_fim_racao(
            item_data, produto=produto_catalogo, cliente_id=cliente_id
        )
        chave_nova = _chave_item(item_data, origem_nova)
        candidatos = [
            candidato
            for candidato in disponiveis
            if _chave_item(
                candidato,
                resolver_tenant_estoque_item(candidato, tenant_id)[0],
            )
            == chave_nova
            and (item_data.lote_id is None or item_data.lote_id == candidato.lote_id)
        ]
        if item_data.item_id is not None:
            identificado = antigos_por_id.get(item_data.item_id)
            if identificado is None or identificado not in disponiveis:
                raise HTTPException(
                    status_code=409,
                    detail="Item da venda mudou. Recarregue a venda antes de salvar.",
                )
            antigo = identificado if identificado in candidatos else None
        else:
            # Sem ID, linhas iguais podem ter custos/lotes diferentes.
            grupo = _grupo_item(item_data, origem_nova)
            candidatos_sem_id = [
                candidato
                for candidato in candidatos
                if candidato.id not in ids_reservados
            ]
            antigo = (
                candidatos_sem_id[0]
                if len(candidatos_sem_id) == 1
                and antigos_sem_id_por_grupo[grupo] == 1
                and sem_id_por_grupo[grupo] == 1
                else None
            )
        if antigo is not None:
            disponiveis.remove(antigo)
            item = antigo
        else:
            item = VendaItem(
                venda_id=venda_id,
                tenant_id=tenant_id,
                tipo=item_data.tipo,
                produto_id=produto_id,
                estoque_origem_tenant_id=(
                    resolucao.tenant_origem_id
                    if resolucao is not None and resolucao.compartilhado
                    else None
                ),
                estoque_compartilhado_id=(
                    resolucao.compartilhamento_id if resolucao is not None else None
                ),
                estoque_origem_nome=(
                    resolucao.empresa_origem_nome if resolucao is not None else None
                ),
            )
            db.add(item)
            novos_criados.append((item, origem_nova))

        item.servico_descricao = item_data.servico_descricao or (
            produto_catalogo.nome
            if resolucao is not None and resolucao.compartilhado
            else None
        )
        item.preco_unitario = item_data.preco_unitario
        item.desconto_item = item_data.desconto_item or 0
        item.subtotal = item_data.subtotal
        item.lote_id = item_data.lote_id or (
            getattr(item, "lote_id", None) if antigo is not None else None
        )
        item.pet_id = item_data.pet_id
        item.protocolo_recorrencia_id = (
            None
            if item_data.ignorar_recorrencia
            else item_data.protocolo_recorrencia_id
        )
        item.ignorar_recorrencia = item_data.ignorar_recorrencia
        item.racao_data_prevista_fim = previsao.data_prevista
        item.racao_prazo_estimado_dias = previsao.prazo_dias
        if antigo is None:
            item.quantidade = item_data.quantidade

    for antigo in disponiveis:
        db.delete(antigo)

    if novos_criados:
        db.flush()
        for item, origem in novos_criados:
            resultados = saidas_ajuste.get((item.produto_id, origem), [])
            registrar_custo_original_saida(item, resultados, origem)
