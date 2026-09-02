"""Ajustes de estoque feitos durante a edição de uma venda aberta."""

import logging
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.empresa_grupo_estoque_compartilhado_service import (
    EmpresaGrupoEstoqueCompartilhadoService,
    ProdutoVendaResolvido,
    contexto_tenant_estoque,
    resolver_tenant_estoque_item,
)
from app.estoque.service import EstoqueService
from app.produtos_models import ProdutoKitComponente
from app.vendas.estoque_baixa import processar_baixa_estoque_item

logger = logging.getLogger(__name__)


def calcular_diferencas_estoque_edicao(itens_antigos, itens_novos) -> dict[int, float]:
    quantidades_antigas = defaultdict(float)
    quantidades_novas = defaultdict(float)
    for item in itens_antigos:
        if item.produto_id:
            quantidades_antigas[item.produto_id] += float(item.quantidade or 0)
    for item in itens_novos:
        if item.produto_id:
            quantidades_novas[item.produto_id] += float(item.quantidade or 0)

    return {
        produto_id: quantidades_novas[produto_id] - quantidades_antigas[produto_id]
        for produto_id in set(quantidades_antigas) | set(quantidades_novas)
        if abs(quantidades_novas[produto_id] - quantidades_antigas[produto_id]) > 1e-9
    }


def _estornar_quantidade_reduzida(
    *,
    produto,
    quantidade: float,
    venda,
    user_id: int,
    tenant_id,
    db: Session,
) -> None:
    if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
        componentes = (
            db.query(ProdutoKitComponente)
            .filter(ProdutoKitComponente.kit_id == produto.id)
            .all()
        )
        if not componentes:
            raise ValueError(
                f"KIT VIRTUAL '{produto.nome}' não possui componentes cadastrados"
            )
        for componente in componentes:
            EstoqueService.estornar_estoque(
                produto_id=componente.produto_componente_id,
                quantidade=quantidade * float(componente.quantidade),
                motivo="ajuste",
                referencia_id=venda.id,
                referencia_tipo="venda_editada",
                user_id=user_id,
                tenant_id=tenant_id,
                db=db,
                documento=venda.numero_venda,
                observacao=(
                    f"Componente devolvido na edição do KIT '{produto.nome}' "
                    f"na venda #{venda.id}"
                ),
            )
        return

    EstoqueService.estornar_estoque(
        produto_id=produto.id,
        quantidade=quantidade,
        motivo="ajuste",
        referencia_id=venda.id,
        referencia_tipo="venda_editada",
        user_id=user_id,
        tenant_id=tenant_id,
        db=db,
        documento=venda.numero_venda,
        observacao=f"Quantidade reduzida na venda #{venda.id}",
    )


def ajustar_estoque_edicao_venda(
    *,
    venda,
    itens_antigos,
    itens_novos,
    current_user,
    tenant_id,
    db: Session,
) -> dict[int, ProdutoVendaResolvido]:
    tenant_venda = str(tenant_id)
    antigos_por_produto = {
        int(item.produto_id): item for item in itens_antigos if item.produto_id
    }
    resolucoes_novas: dict[int, ProdutoVendaResolvido] = {}
    for item in itens_novos:
        if not item.produto_id:
            continue
        produto_id = int(item.produto_id)
        try:
            resolucao = EmpresaGrupoEstoqueCompartilhadoService.resolver_produto_venda(
                db, tenant_venda, produto_id
            )
        except HTTPException as error:
            antigo = antigos_por_produto.get(produto_id)
            if error.status_code != 404 or antigo is None:
                raise
            origem_antiga = getattr(antigo, "estoque_origem_tenant_id", None)
            if not origem_antiga:
                raise
            resolucao = (
                EmpresaGrupoEstoqueCompartilhadoService.carregar_produto_historico(
                    db,
                    produto_id=produto_id,
                    tenant_origem_id=origem_antiga,
                    compartilhamento_id=getattr(
                        antigo, "estoque_compartilhado_id", None
                    ),
                    empresa_origem_nome=getattr(antigo, "estoque_origem_nome", None),
                )
            )
        resolucoes_novas[produto_id] = resolucao

    quantidades_antigas = defaultdict(float)
    quantidades_novas = defaultdict(float)
    for item in itens_antigos:
        if item.produto_id:
            origem, _compartilhado = resolver_tenant_estoque_item(item, tenant_venda)
            quantidades_antigas[(int(item.produto_id), origem)] += float(
                item.quantidade or 0
            )
    for item in itens_novos:
        if item.produto_id:
            resolucao = resolucoes_novas[int(item.produto_id)]
            quantidades_novas[(int(item.produto_id), resolucao.tenant_origem_id)] += (
                float(item.quantidade or 0)
            )

    diferencas = {
        chave: quantidades_novas[chave] - quantidades_antigas[chave]
        for chave in set(quantidades_antigas) | set(quantidades_novas)
        if abs(quantidades_novas[chave] - quantidades_antigas[chave]) > 1e-9
    }
    for (produto_id, tenant_estoque), diferenca in diferencas.items():
        resolucao = resolucoes_novas.get(produto_id)
        if resolucao is None or resolucao.tenant_origem_id != tenant_estoque:
            antigo = antigos_por_produto.get(produto_id)
            resolucao = (
                EmpresaGrupoEstoqueCompartilhadoService.carregar_produto_historico(
                    db,
                    produto_id=produto_id,
                    tenant_origem_id=tenant_estoque,
                    compartilhamento_id=getattr(
                        antigo, "estoque_compartilhado_id", None
                    ),
                    empresa_origem_nome=getattr(antigo, "estoque_origem_nome", None),
                )
            )
        produto = resolucao.produto

        if not getattr(produto, "controlar_estoque", True):
            continue

        compartilhado = tenant_estoque != tenant_venda
        if diferenca > 0 and compartilhado and not resolucao.compartilhamento_ativo:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"O estoque compartilhado de '{produto.nome}' foi desativado. "
                    "Você pode reduzir ou remover o item, mas não aumentar a quantidade."
                ),
            )

        try:
            with contexto_tenant_estoque(
                tenant_estoque, tenant_venda
            ) as tenant_estoque_uuid:
                if diferenca < 0:
                    quantidade_estorno = abs(diferenca)
                    logger.info(
                        "Devolvendo estoque na edição: Produto %s +%s",
                        produto_id,
                        quantidade_estorno,
                    )
                    _estornar_quantidade_reduzida(
                        produto=produto,
                        quantidade=quantidade_estorno,
                        venda=venda,
                        user_id=0 if compartilhado else current_user.id,
                        tenant_id=tenant_estoque_uuid,
                        db=db,
                    )
                    detalhe = (
                        f"Estorno (+{quantidade_estorno}) - Quantidade reduzida "
                        f"na venda #{venda.id}"
                    )
                else:
                    logger.info(
                        "Baixando estoque na edição: Produto %s -%s",
                        produto_id,
                        diferenca,
                    )
                    processar_baixa_estoque_item(
                        produto=produto,
                        quantidade_vendida=diferenca,
                        venda_id=venda.id,
                        user_id=0 if compartilhado else current_user.id,
                        tenant_id=tenant_estoque_uuid,
                        db=db,
                        venda_codigo=venda.numero_venda,
                        observacao=(
                            f"Edição de venda em estoque compartilhado pelo tenant {tenant_venda}"
                            if compartilhado
                            else None
                        ),
                    )
                    detalhe = f"Baixa (-{diferenca}) - Quantidade adicionada na venda #{venda.id}"

            log_action(
                db=db,
                user_id=current_user.id,
                action="update",
                entity_type="produtos",
                entity_id=produto_id,
                details=detalhe,
                commit=False,
            )
        except ValueError as error:
            logger.error("Erro ao ajustar estoque na edição: %s", error)
            raise HTTPException(status_code=400, detail=str(error)) from error
    return resolucoes_novas
