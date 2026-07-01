from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session, joinedload

from app.dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from app.estoque.transferencia_parceiro_documents import _status_transferencia_parceiro
from app.estoque.transferencia_parceiro_schemas import (
    TransferenciaParceiroCompensacaoContaRequest,
    TransferenciaParceiroHistoricoMovItem,
    TransferenciaParceiroItemRequest,
)
from app.financeiro_models import (
    CategoriaFinanceira,
    ContaPagar,
    ContaReceber,
    FormaPagamento,
    Pagamento,
    Recebimento,
)
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote


def _texto_limpo(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE = "transf_parceiro"
_MOTIVO_TRANSFERENCIA_PARCEIRO_EXCLUSAO = "transf_exc"
_MOTIVO_TRANSFERENCIA_PARCEIRO_EDICAO = "transf_edit"
_REFERENCIA_TRANSFERENCIA_PARCEIRO_EXCLUSAO = "transf_excl"
_REFERENCIA_TRANSFERENCIA_PARCEIRO_EDICAO = "transf_edit"
_MODO_BAIXA_TRANSFERENCIA_LABELS = {
    "recebimento": "Recebimento",
    "acerto": "Acerto / Compensacao",
}


def _obter_dre_subcategoria_receita_padrao(db: Session, tenant_id) -> int:
    subcategoria = (
        db.query(DRESubcategoria)
        .join(DRECategoria, DRECategoria.id == DRESubcategoria.categoria_id)
        .filter(
            DRESubcategoria.tenant_id == str(tenant_id),
            DRECategoria.tenant_id == str(tenant_id),
            and_(DRESubcategoria.ativo.is_(True), DRECategoria.ativo.is_(True)),
            DRECategoria.natureza == NaturezaDRE.RECEITA,
        )
        .order_by(DRECategoria.ordem.asc(), DRESubcategoria.id.asc())
        .first()
    )
    return subcategoria.id if subcategoria else 1


def _obter_ou_criar_categoria_financeira_transferencia(
    db: Session,
    *,
    tenant_id,
    user_id: int,
) -> CategoriaFinanceira:
    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.tenant_id == str(tenant_id),
            CategoriaFinanceira.nome == "Transferencia para Parceiro",
            CategoriaFinanceira.tipo == "receita",
        )
        .first()
    )
    if categoria:
        return categoria

    categoria = CategoriaFinanceira(
        tenant_id=str(tenant_id),
        nome="Transferencia para Parceiro",
        tipo="receita",
        descricao="Ressarcimento de estoque transferido a parceiro sem gerar venda no PDV.",
        dre_subcategoria_id=_obter_dre_subcategoria_receita_padrao(db, tenant_id),
        ativo=True,
        user_id=user_id,
    )
    db.add(categoria)
    db.flush()
    return categoria


def _obter_ou_criar_forma_pagamento_acerto(
    db: Session,
    *,
    tenant_id,
    user_id: int,
) -> FormaPagamento:
    forma = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == str(tenant_id),
            FormaPagamento.nome.ilike("acerto%"),
        )
        .order_by(FormaPagamento.id.asc())
        .first()
    )
    if forma:
        if forma.ativo is False:
            forma.ativo = True
            db.add(forma)
            db.flush()
        return forma

    forma = FormaPagamento(
        tenant_id=str(tenant_id),
        nome="Acerto",
        tipo="transferencia",
        taxa_percentual=0,
        taxa_fixa=0,
        prazo_dias=0,
        prazo_recebimento=0,
        ativo=True,
        permite_parcelamento=False,
        max_parcelas=1,
        parcelas_maximas=1,
        gera_contas_receber=False,
        split_parcelas=False,
        user_id=user_id,
    )
    db.add(forma)
    db.flush()
    return forma


def _gerar_codigo_transferencia_parceiro() -> str:
    return f"TRP-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _normalizar_modo_baixa_transferencia(valor: str | None) -> str:
    texto = _texto_limpo(valor)
    modo = (texto or "recebimento").strip().lower()
    if modo not in _MODO_BAIXA_TRANSFERENCIA_LABELS:
        raise HTTPException(
            status_code=400,
            detail="Modo de baixa invalido. Use recebimento ou acerto.",
        )
    return modo


def _label_modo_baixa_transferencia(valor: str | None) -> str | None:
    texto = _texto_limpo(valor)
    if not texto:
        return None
    return _MODO_BAIXA_TRANSFERENCIA_LABELS.get(texto, texto.replace("_", " ").title())


def _buscar_forma_pagamento_transferencia(
    db: Session,
    *,
    tenant_id,
    forma_pagamento_id: int,
) -> FormaPagamento:
    forma = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.id == forma_pagamento_id,
            FormaPagamento.tenant_id == str(tenant_id),
        )
        .first()
    )
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento nao encontrada")
    return forma


def _saldo_conta_pagar(conta: ContaPagar) -> float:
    valor_final = float(conta.valor_final or 0)
    valor_pago = float(conta.valor_pago or 0)
    saldo = valor_final - valor_pago
    return round(max(saldo, 0.0), 2)


def _status_conta_pagar_compensacao(conta: ContaPagar) -> tuple[str, str]:
    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    saldo_aberto = _saldo_conta_pagar(conta)
    hoje = date.today()

    if status_atual in {"pago", "recebido"} or saldo_aberto <= 0:
        return "pago", "Paga"
    if status_atual in {"cancelado", "cancelada"}:
        return "cancelado", "Cancelada"
    if status_atual == "parcial":
        if conta.data_vencimento and conta.data_vencimento < hoje:
            return "vencido", "Vencida"
        return "parcial", "Parcial"
    if conta.data_vencimento and conta.data_vencimento < hoje:
        return "vencido", "Vencida"
    return "pendente", "Pendente"


def _origem_conta_pagar_compensacao(conta: ContaPagar) -> tuple[str, str]:
    canal = str(getattr(conta, "canal", "") or "").strip().lower()
    if canal == "transferencia_parceiro_entrada":
        return "entrada_parceiro", "Entrada do parceiro"
    if canal == "transferencia_parceiro":
        return "acerto_direto", "Acerto direto"
    return "financeiro", "Financeiro"


def _buscar_conta_transferencia_parceiro(
    db: Session,
    tenant_id: int | str,
    conta_receber_id: int,
) -> ContaReceber:
    conta = (
        db.query(ContaReceber)
        .options(
            joinedload(ContaReceber.cliente),
        )
        .filter(
            ContaReceber.id == conta_receber_id,
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.canal == "transferencia_parceiro",
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Transferencia nao encontrada")

    return conta


def _buscar_transferencias_parceiro_filtradas(
    db: Session,
    *,
    tenant_id: int | str,
    parceiro_id: Optional[int] = None,
    status_filtro: Optional[str] = None,
    busca: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    conta_receber_ids: Optional[list[int]] = None,
) -> list[ContaReceber]:
    termo_busca = (busca or "").strip()
    status_normalizado = (status_filtro or "").strip().lower()

    query = (
        db.query(ContaReceber)
        .options(
            joinedload(ContaReceber.cliente),
            joinedload(ContaReceber.recebimentos).joinedload(
                Recebimento.forma_pagamento
            ),
        )
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.canal == "transferencia_parceiro",
        )
    )

    if conta_receber_ids:
        query = query.filter(ContaReceber.id.in_(conta_receber_ids))

    if parceiro_id:
        query = query.filter(ContaReceber.cliente_id == parceiro_id)

    if data_inicio:
        query = query.filter(ContaReceber.data_emissao >= data_inicio)

    if data_fim:
        query = query.filter(ContaReceber.data_emissao <= data_fim)

    if termo_busca:
        busca_pattern = f"%{termo_busca}%"
        query = query.outerjoin(Cliente, Cliente.id == ContaReceber.cliente_id).filter(
            or_(
                ContaReceber.documento.ilike(busca_pattern),
                ContaReceber.descricao.ilike(busca_pattern),
                ContaReceber.observacoes.ilike(busca_pattern),
                Cliente.nome.ilike(busca_pattern),
                Cliente.codigo.ilike(busca_pattern),
            )
        )

    contas = query.order_by(
        desc(ContaReceber.data_emissao),
        desc(ContaReceber.id),
    ).all()

    if not status_normalizado:
        return contas

    return [
        conta
        for conta in contas
        if _status_transferencia_parceiro(conta)[0] == status_normalizado
    ]


def _buscar_contas_pagar_compensacao_transferencia(
    db: Session,
    *,
    tenant_id: int | str,
    cliente_id: int | None,
) -> list[ContaPagar]:
    if not cliente_id:
        return []

    contas = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.tenant_id == str(tenant_id),
            ContaPagar.fornecedor_id == cliente_id,
            ContaPagar.status.notin_(["pago", "cancelado", "cancelada"]),
        )
        .order_by(
            ContaPagar.data_vencimento.asc(),
            ContaPagar.id.asc(),
        )
        .all()
    )

    return [conta for conta in contas if _saldo_conta_pagar(conta) > 0.009]


def _formatar_resumo_compensacoes_transferencia(
    compensacoes_processadas: list[dict],
) -> str | None:
    if not compensacoes_processadas:
        return None

    partes = []
    for item in compensacoes_processadas:
        documento = (
            _texto_limpo(item.get("documento")) or f"Conta #{item['conta_pagar_id']}"
        )
        partes.append(f"{documento} (R$ {float(item['valor_compensado']):.2f})")

    return "Contas compensadas: " + ", ".join(partes)


def _aplicar_compensacoes_contas_pagar_transferencia(
    db: Session,
    *,
    conta_receber: ContaReceber,
    tenant_id: int | str,
    user_id: int,
    data_pagamento: date,
    forma_pagamento: FormaPagamento,
    compensacoes_payload: list[TransferenciaParceiroCompensacaoContaRequest],
) -> list[dict]:
    if not compensacoes_payload:
        return []

    cliente_id = getattr(conta_receber, "cliente_id", None)
    if not cliente_id:
        raise HTTPException(
            status_code=400,
            detail="Esta transferencia nao possui pessoa vinculada para compensacao.",
        )

    ids = [int(item.conta_pagar_id) for item in compensacoes_payload]
    contas = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.tenant_id == str(tenant_id),
            ContaPagar.fornecedor_id == cliente_id,
            ContaPagar.id.in_(ids),
        )
        .all()
    )
    contas_por_id = {conta.id: conta for conta in contas}

    compensacoes_processadas: list[dict] = []
    documento_transferencia = (
        _texto_limpo(conta_receber.documento) or f"TRP-{conta_receber.id:06d}"
    )

    for item in compensacoes_payload:
        conta_pagar = contas_por_id.get(int(item.conta_pagar_id))
        if not conta_pagar:
            raise HTTPException(
                status_code=404,
                detail=f"Conta a pagar #{item.conta_pagar_id} nao encontrada para essa pessoa.",
            )

        saldo_aberto = _saldo_conta_pagar(conta_pagar)
        valor_compensado = round(float(item.valor_compensado or 0), 2)
        if valor_compensado <= 0:
            raise HTTPException(
                status_code=400,
                detail="Informe um valor de compensacao maior que zero.",
            )
        if valor_compensado - saldo_aberto > 0.01:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"O valor compensado ultrapassa o saldo da conta a pagar #{conta_pagar.id}. "
                    f"Saldo atual: R$ {saldo_aberto:.2f}"
                ),
            )

        novo_valor_pago = round(
            float(conta_pagar.valor_pago or 0) + valor_compensado, 2
        )
        conta_pagar.valor_pago = Decimal(str(novo_valor_pago))
        conta_pagar.status = (
            "pago"
            if abs(float(conta_pagar.valor_final or 0) - novo_valor_pago) < 0.01
            else "parcial"
        )
        if conta_pagar.status == "pago":
            conta_pagar.data_pagamento = data_pagamento

        documento_conta = (
            _texto_limpo(conta_pagar.documento) or f"Conta #{conta_pagar.id}"
        )
        observacao_pagamento = (
            f"Compensacao via transferencia {documento_transferencia} "
            f"(conta a receber #{conta_receber.id}) - R$ {valor_compensado:.2f}"
        )
        pagamento = Pagamento(
            conta_pagar_id=conta_pagar.id,
            forma_pagamento_id=forma_pagamento.id,
            valor_pago=Decimal(str(valor_compensado)),
            data_pagamento=data_pagamento,
            observacoes=observacao_pagamento,
            user_id=user_id,
            tenant_id=str(tenant_id),
        )
        db.add(pagamento)

        conta_pagar.observacoes = (
            f"{conta_pagar.observacoes}\n\n{observacao_pagamento}".strip()
            if conta_pagar.observacoes
            else observacao_pagamento
        )

        compensacoes_processadas.append(
            {
                "conta_pagar_id": conta_pagar.id,
                "documento": documento_conta,
                "descricao": conta_pagar.descricao,
                "valor_compensado": valor_compensado,
                "saldo_restante": _saldo_conta_pagar(conta_pagar),
                "status": conta_pagar.status,
            }
        )

    return compensacoes_processadas


def _obter_ultimo_recebimento_transferencia(conta: ContaReceber) -> Recebimento | None:
    recebimentos = list(getattr(conta, "recebimentos", None) or [])
    if not recebimentos:
        return None

    return max(
        recebimentos,
        key=lambda item: (
            item.data_recebimento or date.min,
            getattr(item, "created_at", None) or datetime.min,
            getattr(item, "id", 0) or 0,
        ),
    )


def _detectar_modo_baixa_transferencia(
    recebimento: Recebimento | None,
) -> tuple[str | None, str | None]:
    if not recebimento:
        return None, None

    forma_nome = _texto_limpo(
        getattr(getattr(recebimento, "forma_pagamento", None), "nome", None)
    )
    observacoes = (_texto_limpo(recebimento.observacoes) or "").lower()

    if (
        (forma_nome and forma_nome.lower() == "acerto")
        or "acerto" in observacoes
        or "compens" in observacoes
    ):
        return "acerto", _label_modo_baixa_transferencia("acerto")

    return "recebimento", _label_modo_baixa_transferencia("recebimento")


def _movimentacao_para_historico_item(
    mov: EstoqueMovimentacao,
) -> TransferenciaParceiroHistoricoMovItem:
    produto = mov.produto
    return TransferenciaParceiroHistoricoMovItem(
        produto_id=mov.produto_id,
        produto_nome=produto.nome if produto else f"Produto #{mov.produto_id}",
        codigo=getattr(produto, "codigo", None) if produto else None,
        codigo_barras=getattr(produto, "codigo_barras", None) if produto else None,
        estoque_atual=float(getattr(produto, "estoque_atual", 0) or 0)
        if produto
        else 0,
        quantidade=float(mov.quantidade or 0),
        custo_unitario=float(mov.custo_unitario or 0),
        valor_total=float(mov.valor_total or 0),
        created_at=mov.created_at,
    )


def _listar_itens_por_conta_transferencia_parceiro(
    db: Session,
    tenant_id: int | str,
    conta_ids: list[int],
    *,
    ordem_desc: bool = False,
) -> dict[int, list[TransferenciaParceiroHistoricoMovItem]]:
    if not conta_ids:
        return {}

    ordenacao = (
        (EstoqueMovimentacao.created_at.desc(), EstoqueMovimentacao.id.desc())
        if ordem_desc
        else (EstoqueMovimentacao.created_at.asc(), EstoqueMovimentacao.id.asc())
    )
    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .options(joinedload(EstoqueMovimentacao.produto))
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id.in_(conta_ids),
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(*ordenacao)
        .all()
    )

    itens_por_conta: dict[int, list[TransferenciaParceiroHistoricoMovItem]] = (
        defaultdict(list)
    )
    for mov in movimentacoes:
        if mov.referencia_id is not None:
            itens_por_conta[int(mov.referencia_id)].append(
                _movimentacao_para_historico_item(mov)
            )
    return itens_por_conta


def _listar_itens_transferencia_parceiro(
    db: Session,
    tenant_id: int | str,
    conta_receber_id: int,
) -> list[TransferenciaParceiroHistoricoMovItem]:
    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .options(
            joinedload(EstoqueMovimentacao.produto),
        )
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id == conta_receber_id,
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(
            EstoqueMovimentacao.created_at.asc(),
            EstoqueMovimentacao.id.asc(),
        )
        .all()
    )

    return [_movimentacao_para_historico_item(mov) for mov in movimentacoes]


def _restaurar_lotes_consumidos_transferencia(
    db: Session,
    movimentacao: EstoqueMovimentacao,
) -> int:
    bruto = getattr(movimentacao, "lotes_consumidos", None)
    if not bruto:
        return 0

    try:
        lotes = json.loads(bruto) if isinstance(bruto, str) else bruto
    except Exception:
        lotes = []

    restaurados = 0
    for item_lote in lotes or []:
        lote_id = item_lote.get("lote_id")
        quantidade = float(item_lote.get("quantidade") or 0)
        if not lote_id or quantidade <= 0:
            continue

        lote = db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()
        if not lote:
            continue

        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        if lote.quantidade_disponivel > 0:
            lote.status = "ativo"
        db.add(lote)
        restaurados += 1

    return restaurados


def _resolver_valores_item_transferencia(
    produto: Produto,
    item: TransferenciaParceiroItemRequest,
) -> tuple[Decimal, Decimal]:
    quantidade = Decimal(str(float(item.quantidade or 0)))
    custo_padrao = Decimal(str(round(float(produto.preco_custo or 0), 2)))
    custo_informado = (
        Decimal(str(round(float(item.custo_unitario or 0), 2)))
        if item.custo_unitario is not None
        else None
    )
    total_informado = (
        Decimal(str(round(float(item.valor_total or 0), 2)))
        if item.valor_total is not None
        else None
    )

    if total_informado is not None:
        total_item = total_informado.quantize(Decimal("0.01"))
        custo_unitario = (
            (total_item / quantidade).quantize(Decimal("0.01"))
            if quantidade > 0
            else Decimal("0.00")
        )
    else:
        custo_unitario = (
            custo_informado if custo_informado is not None else custo_padrao
        ).quantize(Decimal("0.01"))
        total_item = (custo_unitario * quantidade).quantize(Decimal("0.01"))

    if custo_unitario < 0 or total_item < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Os valores do item '{produto.nome}' nao podem ser negativos",
        )

    return custo_unitario, total_item


def _preparar_itens_transferencia_parceiro(
    db: Session,
    *,
    tenant_id,
    itens_validos: list[TransferenciaParceiroItemRequest],
) -> tuple[list[dict], Decimal]:
    quantidades_por_produto: dict[int, float] = defaultdict(float)
    for item in itens_validos:
        quantidades_por_produto[int(item.produto_id)] += float(item.quantidade or 0)

    produto_ids = list(quantidades_por_produto.keys())
    produtos = (
        db.query(Produto)
        .filter(
            Produto.id.in_(produto_ids),
            Produto.tenant_id == tenant_id,
        )
        .all()
    )
    produtos_cache = {produto.id: produto for produto in produtos}

    for produto_id, quantidade in quantidades_por_produto.items():
        produto = produtos_cache.get(produto_id)
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto ID {produto_id} nao encontrado",
            )

        if produto.is_parent:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Produto '{produto.nome}' possui variacoes. "
                    "Selecione a variacao individual para transferir estoque."
                ),
            )

        if produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Produto '{produto.nome}' e um KIT VIRTUAL. "
                    "Use os componentes individuais na transferencia."
                ),
            )

        estoque_atual = float(produto.estoque_atual or 0)
        if estoque_atual < quantidade:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Estoque insuficiente para '{produto.nome}'. "
                    f"Disponivel: {estoque_atual}, solicitado: {quantidade}"
                ),
            )

    itens_processados = []
    total_transferencia = Decimal("0")
    for item in itens_validos:
        produto = produtos_cache.get(int(item.produto_id))
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto ID {item.produto_id} nao encontrado",
            )

        custo_unitario, total_item = _resolver_valores_item_transferencia(produto, item)
        total_transferencia += total_item

        itens_processados.append(
            {
                "produto_id": produto.id,
                "produto_nome": produto.nome,
                "codigo": getattr(produto, "codigo", None),
                "codigo_barras": getattr(produto, "codigo_barras", None),
                "quantidade": float(item.quantidade or 0),
                "custo_unitario": float(custo_unitario),
                "total_item": float(total_item),
                "estoque_anterior": float(produto.estoque_atual or 0),
            }
        )

    if total_transferencia <= 0:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com valor total maior que zero",
        )

    return itens_processados, total_transferencia


def _montar_observacoes_transferencia_parceiro(
    observacao: Optional[str],
    itens_processados: list[dict],
) -> str:
    observacoes_itens = "; ".join(
        f"{item['produto_nome']} x {item['quantidade']}" for item in itens_processados
    )
    observacao_limpa = _texto_limpo(observacao)
    if observacao_limpa:
        return f"{observacao_limpa}\n\nItens: {observacoes_itens}"
    return observacoes_itens
