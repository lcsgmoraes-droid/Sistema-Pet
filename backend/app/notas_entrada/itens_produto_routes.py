"""Rotas de vinculo e criacao de produtos a partir de itens de NF-e."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.fiscal_patterns import aplicar_inteligencia_fiscal
from app.notas_entrada.fiscal import calcular_composicao_custos_nota
from app.notas_entrada.produtos import (
    _aplicar_dados_fiscais_item_no_produto,
    _buscar_produto_por_codigo_global,
    _codigos_barras_nf,
    _montar_sugestao_sku_produto,
)
from app.notas_entrada.schemas import CriarProdutoRequest
from app.produtos_models import NotaEntrada, NotaEntradaItem, Produto, ProdutoFornecedor
from app.services.produto_service import normalizar_sku_produto

logger = logging.getLogger(__name__)

router = APIRouter()


def _buscar_nota_item_por_tenant(
    nota_id: int,
    item_id: int,
    tenant_id,
    db: Session,
) -> tuple[NotaEntrada, NotaEntradaItem]:
    nota = (
        db.query(NotaEntrada)
        .filter(
            NotaEntrada.id == nota_id,
            NotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    item = (
        db.query(NotaEntradaItem)
        .filter(
            NotaEntradaItem.id == item_id,
            NotaEntradaItem.nota_entrada_id == nota_id,
            NotaEntradaItem.tenant_id == tenant_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item nao encontrado")

    return nota, item


@router.post("/{nota_id}/itens/{item_id}/vincular")
def vincular_produto(
    nota_id: int,
    item_id: int,
    produto_id: int = Query(..., description="ID do produto a vincular"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Vincula item a um produto manualmente."""
    _, tenant_id = user_and_tenant
    item = (
        db.query(NotaEntradaItem)
        .filter(
            NotaEntradaItem.id == item_id,
            NotaEntradaItem.nota_entrada_id == nota_id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item nao encontrado")

    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    foi_nao_vinculado = not item.vinculado

    item.produto_id = produto_id
    item.vinculado = True
    item.confianca_vinculo = 1.0
    item.status = "vinculado"

    atualizar_fiscal = _aplicar_dados_fiscais_item_no_produto(produto, item)
    if atualizar_fiscal:
        logger.info(
            "Dados fiscais do produto %s atualizados com informacoes da NF", produto.id
        )

    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    custo_item_vinculo = item.valor_unitario
    if nota:
        composicao_custo = calcular_composicao_custos_nota(nota).get(item.id, {})
        custo_item_vinculo = composicao_custo.get(
            "custo_aquisicao_unitario", item.valor_unitario
        )

    if nota and nota.fornecedor_id:
        vinculo_principal = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.e_principal.is_(True),
            )
            .first()
        )

        if not vinculo_principal:
            novo_vinculo = ProdutoFornecedor(
                produto_id=produto_id,
                fornecedor_id=nota.fornecedor_id,
                preco_custo=custo_item_vinculo,
                e_principal=True,
                ativo=True,
                tenant_id=tenant_id,
            )
            db.add(novo_vinculo)
            logger.info(
                "Produto %s vinculado ao fornecedor %s como principal",
                produto_id,
                nota.fornecedor_id,
            )
        elif vinculo_principal.fornecedor_id == nota.fornecedor_id:
            vinculo_principal.preco_custo = custo_item_vinculo
            vinculo_principal.ativo = True
            logger.info(
                "Preco do fornecedor principal do produto %s atualizado", produto_id
            )
        else:
            vinculo_principal.fornecedor_id = nota.fornecedor_id
            vinculo_principal.preco_custo = custo_item_vinculo
            vinculo_principal.ativo = True
            logger.info(
                "Fornecedor principal do produto %s alterado para %s",
                produto_id,
                nota.fornecedor_id,
            )

    if foi_nao_vinculado:
        nota.produtos_vinculados += 1
        nota.produtos_nao_vinculados -= 1

    db.commit()

    logger.info("Item %s vinculado manualmente ao produto %s", item_id, produto.nome)

    return {
        "message": "Produto vinculado com sucesso",
        "item_id": item.id,
        "produto_id": produto.id,
        "produto_nome": produto.nome,
    }


@router.post("/{nota_id}/itens/{item_id}/desvincular")
def desvincular_produto(
    nota_id: int,
    item_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Remove vinculacao de um item com produto."""
    _ = user_and_tenant
    item = (
        db.query(NotaEntradaItem)
        .filter(
            NotaEntradaItem.id == item_id,
            NotaEntradaItem.nota_entrada_id == nota_id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item nao encontrado")

    if not item.produto_id:
        raise HTTPException(
            status_code=400, detail="Item nao esta vinculado a nenhum produto"
        )

    item.produto_id = None
    item.vinculado = False
    item.confianca_vinculo = None
    item.status = "pendente"

    nota = db.query(NotaEntrada).filter(NotaEntrada.id == nota_id).first()
    nota.produtos_vinculados -= 1
    nota.produtos_nao_vinculados += 1

    db.commit()

    logger.info("Item %s desvinculado", item_id)

    return {
        "message": "Produto desvinculado com sucesso",
        "item_id": item.id,
    }


@router.get("/{nota_id}/itens/{item_id}/sugerir-sku")
def sugerir_sku(
    nota_id: int,
    item_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Sugere SKU para produto novo usando o SKU do fornecedor como primeira opcao."""
    current_user, tenant_id = user_and_tenant
    nota, item = _buscar_nota_item_por_tenant(nota_id, item_id, tenant_id, db)
    return _montar_sugestao_sku_produto(
        nota=nota,
        item=item,
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
    )


@router.post("/{nota_id}/itens/{item_id}/criar-produto")
def criar_produto_from_item(
    nota_id: int,
    item_id: int,
    dados: CriarProdutoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo produto a partir do item da nota."""
    current_user, tenant_id = user_and_tenant

    logger.info("Criando produto: %s - %s", dados.sku, dados.nome)

    nota, item = _buscar_nota_item_por_tenant(nota_id, item_id, tenant_id, db)

    sku_solicitado = (dados.sku or "").strip()
    sku_final = sku_solicitado
    sku_ajustado_automaticamente = False

    if not sku_final:
        sugestao = _montar_sugestao_sku_produto(
            nota=nota,
            item=item,
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        sugestao_recomendada = next(
            (sug for sug in sugestao["sugestoes"] if sug.get("padrao")),
            sugestao["sugestoes"][0] if sugestao["sugestoes"] else None,
        )
        if not sugestao_recomendada:
            raise HTTPException(
                status_code=409,
                detail="Nao foi possivel gerar um SKU para o novo produto",
            )
        sku_final = normalizar_sku_produto(sugestao_recomendada["sku"])
        sku_ajustado_automaticamente = True

    sku_final = normalizar_sku_produto(sku_final)
    produto_existente = _buscar_produto_por_codigo_global(db, sku_final)
    if produto_existente:
        sugestao = _montar_sugestao_sku_produto(
            nota=nota,
            item=item,
            db=db,
            tenant_id=tenant_id,
            user_id=current_user.id,
            sku_base_customizado=sku_final,
        )
        sugestao_recomendada = next(
            (sug for sug in sugestao["sugestoes"] if sug.get("padrao")),
            sugestao["sugestoes"][0] if sugestao["sugestoes"] else None,
        )
        if not sugestao_recomendada:
            raise HTTPException(
                status_code=409,
                detail="O SKU informado ja existe e nao foi possivel gerar alternativa",
            )
        sku_final = normalizar_sku_produto(sugestao_recomendada["sku"])
        sku_ajustado_automaticamente = True
        logger.info(
            "SKU ajustado automaticamente para criar novo produto: %s -> %s",
            sku_solicitado or "<vazio>",
            sku_final,
        )

    try:
        descricao_texto = dados.descricao or item.descricao or ""
        descricao_curta = descricao_texto[:100] if descricao_texto else ""
        descricao_completa = descricao_texto

        dados_produto = {
            "nome": dados.nome,
            "descricao": descricao_texto,
            "ncm": item.ncm if hasattr(item, "ncm") else None,
            "cfop": item.cfop if hasattr(item, "cfop") else None,
            "cest": item.cest if hasattr(item, "cest") else None,
            "origem": item.origem if hasattr(item, "origem") else None,
            "aliquota_icms": item.aliquota_icms
            if hasattr(item, "aliquota_icms")
            else None,
            "aliquota_pis": item.aliquota_pis
            if hasattr(item, "aliquota_pis")
            else None,
            "aliquota_cofins": item.aliquota_cofins
            if hasattr(item, "aliquota_cofins")
            else None,
        }

        dados_fiscais = aplicar_inteligencia_fiscal(
            dados_produto,
            {
                "ncm": item.ncm if hasattr(item, "ncm") else None,
                "cfop": item.cfop if hasattr(item, "cfop") else None,
                "cest": item.cest if hasattr(item, "cest") else None,
                "origem": item.origem if hasattr(item, "origem") else None,
                "aliquota_icms": item.aliquota_icms
                if hasattr(item, "aliquota_icms")
                else None,
                "aliquota_pis": item.aliquota_pis
                if hasattr(item, "aliquota_pis")
                else None,
                "aliquota_cofins": item.aliquota_cofins
                if hasattr(item, "aliquota_cofins")
                else None,
            },
        )

        if dados_fiscais.get("padrao_fiscal_motivo"):
            logger.info(
                "%s (confianca: %.0f%%)",
                dados_fiscais["padrao_fiscal_motivo"],
                dados_fiscais.get("padrao_fiscal_confianca", 0) * 100,
            )

        codigos_barras_nf = _codigos_barras_nf(item)

        novo_produto = Produto(
            codigo=sku_final,
            nome=dados.nome,
            descricao_curta=descricao_curta,
            descricao_completa=descricao_completa,
            preco_custo=dados.preco_custo,
            preco_venda=dados.preco_venda,
            categoria_id=dados.categoria_id,
            marca_id=dados.marca_id,
            ncm=dados_fiscais.get("ncm"),
            cfop=dados_fiscais.get("cfop"),
            cest=dados_fiscais.get("cest"),
            origem=dados_fiscais.get("origem", "0"),
            aliquota_icms=dados_fiscais.get("aliquota_icms", 0),
            aliquota_pis=dados_fiscais.get("aliquota_pis", 0),
            aliquota_cofins=dados_fiscais.get("aliquota_cofins", 0),
            codigo_barras=codigos_barras_nf["principal"] or None,
            gtin_ean=codigos_barras_nf["ean"] or None,
            gtin_ean_tributario=codigos_barras_nf["ean_tributario"] or None,
            estoque_minimo=dados.estoque_minimo,
            estoque_maximo=dados.estoque_maximo,
            estoque_atual=0,
            unidade=item.unidade,
            controle_lote=True,
            ativo=True,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )

        db.add(novo_produto)
        db.flush()

        item.produto_id = novo_produto.id
        item.vinculado = True
        item.confianca_vinculo = 1.0
        item.status = "vinculado"

        if nota.fornecedor_id:
            novo_vinculo = ProdutoFornecedor(
                produto_id=novo_produto.id,
                fornecedor_id=nota.fornecedor_id,
                preco_custo=dados.preco_custo,
                e_principal=True,
                ativo=True,
                tenant_id=tenant_id,
            )
            db.add(novo_vinculo)
            logger.info(
                "Novo produto %s vinculado ao fornecedor %s",
                novo_produto.id,
                nota.fornecedor_id,
            )

        db.flush()

        nota.produtos_vinculados = (
            db.query(NotaEntradaItem)
            .filter(
                NotaEntradaItem.nota_entrada_id == nota_id,
                NotaEntradaItem.produto_id.isnot(None),
            )
            .count()
        )

        nota.produtos_nao_vinculados = (
            db.query(NotaEntradaItem)
            .filter(
                NotaEntradaItem.nota_entrada_id == nota_id,
                NotaEntradaItem.produto_id.is_(None),
            )
            .count()
        )

        db.commit()
        db.refresh(novo_produto)
        db.refresh(item)
        db.refresh(nota)

    except Exception as e:
        db.rollback()
        logger.error("Erro ao criar produto: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {str(e)}")

    logger.info(
        "Produto criado a partir da nota: %s - %s",
        novo_produto.codigo,
        novo_produto.nome,
    )

    return {
        "message": (
            f"Produto criado e vinculado com sucesso com SKU ajustado para {novo_produto.codigo}"
            if sku_ajustado_automaticamente
            else "Produto criado e vinculado com sucesso"
        ),
        "produto": {
            "id": novo_produto.id,
            "codigo": novo_produto.codigo,
            "nome": novo_produto.nome,
            "descricao_curta": novo_produto.descricao_curta,
            "descricao_completa": novo_produto.descricao_completa,
            "preco_custo": novo_produto.preco_custo,
            "preco_venda": novo_produto.preco_venda,
        },
        "item_vinculado": True,
        "sku_ajustado_automaticamente": sku_ajustado_automaticamente,
    }
