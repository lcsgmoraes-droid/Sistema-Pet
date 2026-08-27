"""Regras de gravação do atendimento sem venda."""

from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import Cliente
from app.nao_venda_models import NaoVenda, NaoVendaItem
from app.nao_venda_schemas import NaoVendaCreate
from app.pendencia_estoque_models import PendenciaEstoque
from app.produtos_models import Marca, Produto
from app.services.pendencia_estoque_service import STATUS_ATIVOS_LISTA_ESPERA


def _nome_fornecedor(fornecedor: Cliente | None) -> str | None:
    if not fornecedor:
        return None
    return (
        fornecedor.nome_fantasia or fornecedor.razao_social or fornecedor.nome or None
    )


def _mapa_por_id(db: Session, modelo, ids: set[int], tenant_id):
    if not ids:
        return {}
    registros = (
        db.query(modelo).filter(modelo.tenant_id == tenant_id, modelo.id.in_(ids)).all()
    )
    return {registro.id: registro for registro in registros}


def registrar_nao_venda(
    db: Session,
    *,
    tenant_id,
    usuario_id: int,
    dados: NaoVendaCreate,
) -> tuple[NaoVenda, int, int]:
    """Valida vínculos, cria snapshots e opcionalmente alimenta a lista de espera."""
    cliente = None
    if dados.cliente_id:
        cliente = (
            db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.id == dados.cliente_id)
            .first()
        )
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")

    produto_ids = {item.produto_id for item in dados.itens if item.produto_id}
    produtos = {}
    if produto_ids:
        encontrados = (
            db.query(Produto)
            .options(joinedload(Produto.marca), joinedload(Produto.fornecedor))
            .filter(Produto.tenant_id == tenant_id, Produto.id.in_(produto_ids))
            .all()
        )
        produtos = {produto.id: produto for produto in encontrados}
        if produto_ids - produtos.keys():
            raise HTTPException(status_code=404, detail="Produto não encontrado")

    marca_ids = {item.marca_id for item in dados.itens if item.marca_id}
    fornecedor_ids = {item.fornecedor_id for item in dados.itens if item.fornecedor_id}
    marcas = _mapa_por_id(db, Marca, marca_ids, tenant_id)
    fornecedores = _mapa_por_id(db, Cliente, fornecedor_ids, tenant_id)
    if marca_ids - marcas.keys():
        raise HTTPException(status_code=404, detail="Marca não encontrada")
    if fornecedor_ids - fornecedores.keys():
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    if dados.adicionar_lista_espera and not cliente:
        raise HTTPException(
            status_code=400,
            detail="Selecione um cliente cadastrado para usar a lista de espera",
        )
    if dados.adicionar_lista_espera and not produto_ids:
        raise HTTPException(
            status_code=400,
            detail="Selecione ao menos um produto cadastrado para usar a lista de espera",
        )

    registro = NaoVenda(
        tenant_id=tenant_id,
        cliente_id=cliente.id if cliente else None,
        usuario_registrou_id=usuario_id,
        cliente_nome=(cliente.nome if cliente else dados.cliente_nome),
        cliente_telefone=(
            (cliente.celular or cliente.telefone) if cliente else dados.cliente_telefone
        ),
        motivo=dados.motivo,
        observacoes=dados.observacoes,
        origem="pdv",
    )
    db.add(registro)
    db.flush()

    valor_total = Decimal("0")
    possui_valor = False
    itens_criados: list[tuple[NaoVendaItem, Produto | None]] = []
    for entrada in dados.itens:
        produto = produtos.get(entrada.produto_id)
        marca = getattr(produto, "marca", None) or marcas.get(entrada.marca_id)
        fornecedor = getattr(produto, "fornecedor", None) or fornecedores.get(
            entrada.fornecedor_id
        )
        valor_unitario = entrada.valor_unitario_estimado
        if valor_unitario is None and produto is not None:
            valor_unitario = Decimal(str(produto.preco_venda or 0))
        if valor_unitario is not None:
            possui_valor = True
            valor_total += entrada.quantidade * valor_unitario

        item = NaoVendaItem(
            tenant_id=tenant_id,
            nao_venda_id=registro.id,
            produto_id=produto.id if produto else None,
            marca_id=marca.id if marca else None,
            fornecedor_id=fornecedor.id if fornecedor else None,
            produto_nome=produto.nome if produto else entrada.produto_nome,
            sku=(produto.codigo if produto else entrada.sku),
            marca_nome=(marca.nome if marca else entrada.marca_nome),
            fornecedor_nome=(
                _nome_fornecedor(fornecedor) if fornecedor else entrada.fornecedor_nome
            ),
            quantidade=entrada.quantidade,
            valor_unitario_estimado=valor_unitario,
            adicionado_lista_espera=False,
        )
        db.add(item)
        itens_criados.append((item, produto))

    registro.valor_estimado_total = valor_total if possui_valor else None

    adicionados_lista_espera = 0
    ignorados_lista_espera = 0
    if dados.adicionar_lista_espera and cliente:
        for item, produto in itens_criados:
            if not produto:
                ignorados_lista_espera += 1
                continue
            if not getattr(produto, "controlar_estoque", True):
                ignorados_lista_espera += 1
                continue

            pendencia = (
                db.query(PendenciaEstoque)
                .filter(
                    PendenciaEstoque.tenant_id == tenant_id,
                    PendenciaEstoque.cliente_id == cliente.id,
                    PendenciaEstoque.produto_id == produto.id,
                    PendenciaEstoque.status.in_(STATUS_ATIVOS_LISTA_ESPERA),
                )
                .first()
            )
            if pendencia:
                pendencia.quantidade_desejada += float(item.quantidade)
            else:
                pendencia = PendenciaEstoque(
                    tenant_id=tenant_id,
                    cliente_id=cliente.id,
                    produto_id=produto.id,
                    usuario_registrou_id=usuario_id,
                    quantidade_desejada=float(item.quantidade),
                    valor_referencia=float(produto.preco_venda or 0),
                    observacoes="Incluído pelo registro rápido de não venda",
                    prioridade=0,
                    status="pendente",
                )
                db.add(pendencia)
            item.adicionado_lista_espera = True
            adicionados_lista_espera += 1

    db.commit()
    db.refresh(registro)
    return registro, adicionados_lista_espera, ignorados_lista_espera
