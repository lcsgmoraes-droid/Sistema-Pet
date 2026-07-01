from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.bling_estoque_sync import sincronizar_bling_background
from app.financeiro_models import ContaPagar
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao, Produto


CENTAVO = Decimal("0.01")
MOTIVO_ENTRADA_PARCEIRO = "transf_parceiro_entrada"
CANAL_ENTRADA_PARCEIRO = "transferencia_parceiro_entrada"


def _texto_limpo(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _decimal_monetario(valor) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _data_ref(valor):
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        return date.fromisoformat(valor)
    return None


def _saldo_conta_pagar_decimal(conta) -> Decimal:
    valor_final = _decimal_monetario(getattr(conta, "valor_final", 0))
    valor_pago = _decimal_monetario(getattr(conta, "valor_pago", 0))
    saldo = valor_final - valor_pago
    return max(saldo, Decimal("0.00")).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _status_entrada_parceiro(conta, *, hoje=None) -> tuple[str, str]:
    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    saldo_aberto = _saldo_conta_pagar_decimal(conta)
    data_hoje = _data_ref(hoje) or date.today()
    data_vencimento = _data_ref(getattr(conta, "data_vencimento", None))

    if status_atual in {"pago", "recebido"} or saldo_aberto <= 0:
        return "pago", "Paga"
    if status_atual in {"cancelado", "cancelada"}:
        return "cancelado", "Cancelada"
    if data_vencimento and data_vencimento < data_hoje:
        return "vencido", "Vencida"
    if status_atual == "parcial":
        return "parcial", "Parcial"
    return "pendente", "Pendente"


def normalizar_status_filtro_entrada(status_filtro: str | None) -> str:
    status_normalizado = (status_filtro or "").strip().lower()
    if status_normalizado in {"recebido", "recebida", "paga"}:
        return "pago"
    return status_normalizado


def serializar_entrada_parceiro(conta, *, hoje=None) -> dict:
    parceiro = getattr(conta, "fornecedor", None)
    status, status_label = _status_entrada_parceiro(conta, hoje=hoje)
    saldo_aberto = _saldo_conta_pagar_decimal(conta)
    observacoes = _texto_limpo(getattr(conta, "observacoes", None))

    return {
        "conta_pagar_id": int(conta.id),
        "documento": _texto_limpo(getattr(conta, "documento", None)),
        "parceiro_id": getattr(conta, "fornecedor_id", None),
        "parceiro_nome": getattr(parceiro, "nome", None)
        or getattr(conta, "descricao", "Parceiro nao encontrado"),
        "parceiro_codigo": getattr(parceiro, "codigo", None),
        "descricao": getattr(conta, "descricao", ""),
        "data_emissao": _data_ref(getattr(conta, "data_emissao", None)),
        "data_vencimento": _data_ref(getattr(conta, "data_vencimento", None)),
        "data_pagamento": _data_ref(getattr(conta, "data_pagamento", None)),
        "status": status,
        "status_label": status_label,
        "valor_original": float(_decimal_monetario(getattr(conta, "valor_original", 0))),
        "valor_pago": float(_decimal_monetario(getattr(conta, "valor_pago", 0))),
        "saldo_aberto": float(saldo_aberto),
        "estoque_atualizado": "estoque atualizado: sim" in (observacoes or "").lower(),
        "observacoes": observacoes,
    }


def _gerar_documento_entrada_parceiro() -> str:
    return f"TRP-ENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _validar_produto_entrada_parceiro(produto, *, entrar_estoque: bool) -> None:
    if entrar_estoque and getattr(produto, "is_parent", False):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Produto '{produto.nome}' possui variacoes. "
                "Selecione a variacao individual para entrar no estoque."
            ),
        )
    if (
        entrar_estoque
        and getattr(produto, "tipo_produto", None) == "KIT"
        and getattr(produto, "tipo_kit", None) == "VIRTUAL"
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Produto '{produto.nome}' e um KIT VIRTUAL e nao recebe estoque manual.",
        )


def preparar_itens_entrada_parceiro(
    produtos_cache: dict[int, object],
    itens,
    *,
    entrar_estoque: bool = True,
) -> tuple[list[dict], Decimal]:
    itens_validos = [item for item in (itens or []) if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero.",
        )

    processados: list[dict] = []
    total_divida = Decimal("0.00")

    for item in itens_validos:
        produto_id = int(item.produto_id)
        produto = produtos_cache.get(produto_id)
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto ID {produto_id} nao encontrado.",
            )
        _validar_produto_entrada_parceiro(produto, entrar_estoque=entrar_estoque)

        quantidade = Decimal(str(float(item.quantidade or 0)))
        total_informado = (
            _decimal_monetario(item.valor_total)
            if getattr(item, "valor_total", None) is not None
            else None
        )
        if total_informado is not None:
            total_item = total_informado
            custo_unitario = (
                (total_item / quantidade).quantize(CENTAVO, rounding=ROUND_HALF_UP)
                if quantidade > 0
                else Decimal("0.00")
            )
        else:
            custo_base = (
                getattr(item, "custo_unitario", None)
                if getattr(item, "custo_unitario", None) is not None
                else getattr(produto, "preco_custo", 0)
            )
            custo_unitario = _decimal_monetario(custo_base)
            total_item = (custo_unitario * quantidade).quantize(
                CENTAVO, rounding=ROUND_HALF_UP
            )

        if total_item <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Informe valor total maior que zero para o item "
                    f"'{getattr(produto, 'nome', produto_id)}'."
                ),
            )

        total_divida += total_item
        processados.append(
            {
                "produto_id": produto_id,
                "produto_nome": getattr(produto, "nome", f"Produto #{produto_id}"),
                "codigo": getattr(produto, "codigo", None),
                "codigo_barras": getattr(produto, "codigo_barras", None),
                "quantidade": float(quantidade),
                "custo_unitario": float(custo_unitario),
                "total_item": float(total_item),
                "estoque_anterior": float(getattr(produto, "estoque_atual", 0) or 0),
            }
        )

    return processados, total_divida.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _montar_observacoes_entrada_parceiro(
    observacao: str | None,
    itens_processados: list[dict],
    *,
    entrou_estoque: bool,
) -> str:
    itens_texto = "; ".join(
        f"{item['produto_nome']} x {item['quantidade']}" for item in itens_processados
    )
    partes = [
        "Entrada de parceiro com conta a pagar.",
        f"Estoque atualizado: {'sim' if entrou_estoque else 'nao'}.",
        f"Itens: {itens_texto}",
    ]
    observacao_limpa = _texto_limpo(observacao)
    if observacao_limpa:
        partes.insert(0, observacao_limpa)
    return "\n\n".join(partes)


def _buscar_parceiro_entrada(db: Session, tenant_id, parceiro_id: int):
    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada.")
    return parceiro


def _buscar_produtos_entrada(db: Session, tenant_id, produto_ids: list[int]):
    produtos = (
        db.query(Produto)
        .filter(
            Produto.id.in_(produto_ids),
            Produto.tenant_id == tenant_id,
        )
        .all()
    )
    return {int(produto.id): produto for produto in produtos}


def _registrar_movimentacoes_entrada(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    conta_pagar: ContaPagar,
    parceiro,
    documento: str,
    itens_processados: list[dict],
    produtos_cache: dict[int, Produto],
) -> list[int]:
    movimentacao_ids: list[int] = []
    for item in itens_processados:
        produto = produtos_cache[int(item["produto_id"])]
        estoque_anterior = float(produto.estoque_atual or 0)
        produto.estoque_atual = estoque_anterior + float(item["quantidade"])

        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            tipo="entrada",
            motivo=MOTIVO_ENTRADA_PARCEIRO,
            quantidade=float(item["quantidade"]),
            quantidade_anterior=estoque_anterior,
            quantidade_nova=float(produto.estoque_atual or 0),
            custo_unitario=float(item["custo_unitario"]),
            valor_total=float(item["total_item"]),
            documento=documento,
            referencia_id=conta_pagar.id,
            referencia_tipo=MOTIVO_ENTRADA_PARCEIRO,
            observacao=(
                f"Entrada de produto recebido do parceiro {parceiro.nome}. "
                f"Conta a pagar #{conta_pagar.id}."
            ),
            user_id=user_id,
            tenant_id=str(tenant_id),
        )
        db.add(produto)
        db.add(movimentacao)
        db.flush()
        movimentacao_ids.append(movimentacao.id)

    return movimentacao_ids


def registrar_entrada_parceiro(db: Session, *, tenant_id, user_id: int, payload) -> dict:
    parceiro = _buscar_parceiro_entrada(db, tenant_id, int(payload.parceiro_id))
    documento = _texto_limpo(payload.documento) or _gerar_documento_entrada_parceiro()

    conta_existente = (
        db.query(ContaPagar)
        .filter(ContaPagar.tenant_id == str(tenant_id), ContaPagar.documento == documento)
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe uma conta a pagar com este documento.",
        )

    produto_ids = sorted({int(item.produto_id) for item in payload.itens or []})
    produtos_cache = _buscar_produtos_entrada(db, tenant_id, produto_ids)
    itens_processados, total_divida = preparar_itens_entrada_parceiro(
        produtos_cache,
        payload.itens,
        entrar_estoque=bool(payload.entrar_estoque),
    )

    data_emissao = payload.data_emissao or date.today()
    data_vencimento = payload.data_vencimento or data_emissao
    conta_pagar = ContaPagar(
        tenant_id=str(tenant_id),
        descricao=f"Entrada de parceiro - {parceiro.nome}",
        fornecedor_id=parceiro.id,
        canal=CANAL_ENTRADA_PARCEIRO,
        valor_original=total_divida,
        valor_pago=Decimal("0.00"),
        valor_final=total_divida,
        data_emissao=data_emissao,
        data_vencimento=data_vencimento,
        status="pendente",
        documento=documento,
        observacoes=_montar_observacoes_entrada_parceiro(
            payload.observacao,
            itens_processados,
            entrou_estoque=bool(payload.entrar_estoque),
        ),
        user_id=user_id,
    )
    db.add(conta_pagar)
    db.flush()

    movimentacao_ids: list[int] = []
    if payload.entrar_estoque:
        movimentacao_ids = _registrar_movimentacoes_entrada(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            conta_pagar=conta_pagar,
            parceiro=parceiro,
            documento=documento,
            itens_processados=itens_processados,
            produtos_cache=produtos_cache,
        )

    db.commit()

    if payload.entrar_estoque:
        for item in itens_processados:
            produto = produtos_cache.get(int(item["produto_id"]))
            if not produto:
                continue
            try:
                sincronizar_bling_background(
                    produto.id,
                    float(produto.estoque_atual or 0),
                    "transferencia_parceiro_entrada",
                )
            except Exception:
                pass

    return {
        "sucesso": True,
        "documento": documento,
        "conta_pagar_id": conta_pagar.id,
        "parceiro_id": parceiro.id,
        "total_divida": float(total_divida),
        "entrar_estoque": bool(payload.entrar_estoque),
        "movimentacoes_estoque": movimentacao_ids,
    }


def listar_entradas_parceiro(
    db: Session,
    *,
    tenant_id,
    page: int = 1,
    page_size: int = 20,
    parceiro_id: int | None = None,
    status_filtro: str | None = None,
    busca: str | None = None,
    data_inicio=None,
    data_fim=None,
) -> dict:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    termo_busca = (busca or "").strip()
    status_normalizado = normalizar_status_filtro_entrada(status_filtro)

    query = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.fornecedor))
        .filter(
            ContaPagar.tenant_id == str(tenant_id),
            ContaPagar.canal == CANAL_ENTRADA_PARCEIRO,
        )
    )

    if parceiro_id:
        query = query.filter(ContaPagar.fornecedor_id == int(parceiro_id))
    if data_inicio:
        query = query.filter(ContaPagar.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(ContaPagar.data_emissao <= data_fim)
    if termo_busca:
        busca_pattern = f"%{termo_busca}%"
        query = query.outerjoin(Cliente, Cliente.id == ContaPagar.fornecedor_id).filter(
            or_(
                ContaPagar.documento.ilike(busca_pattern),
                ContaPagar.descricao.ilike(busca_pattern),
                ContaPagar.observacoes.ilike(busca_pattern),
                Cliente.nome.ilike(busca_pattern),
                Cliente.codigo.ilike(busca_pattern),
            )
        )

    contas = query.order_by(desc(ContaPagar.data_emissao), desc(ContaPagar.id)).all()
    registros = [serializar_entrada_parceiro(conta) for conta in contas]
    if status_normalizado:
        registros = [item for item in registros if item["status"] == status_normalizado]

    totais = {
        "total_registros": len(registros),
        "valor_total": round(sum(item["valor_original"] for item in registros), 2),
        "valor_pago": round(sum(item["valor_pago"] for item in registros), 2),
        "saldo_aberto": round(sum(item["saldo_aberto"] for item in registros), 2),
        "pendentes": sum(1 for item in registros if item["status"] in {"pendente", "parcial"}),
        "pagas": sum(1 for item in registros if item["status"] == "pago"),
        "vencidas": sum(1 for item in registros if item["status"] == "vencido"),
    }
    total = len(registros)
    pages = (total + page_size - 1) // page_size if total else 0
    offset = (page - 1) * page_size

    return {
        "items": registros[offset : offset + page_size],
        "totais": totais,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
