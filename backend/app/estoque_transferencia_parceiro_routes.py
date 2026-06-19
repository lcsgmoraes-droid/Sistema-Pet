"""Rotas de transferencia de estoque para parceiro."""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import io
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .bling_estoque_sync import sincronizar_bling_background
from .db import get_session
from .dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from .estoque.transferencia_parceiro_documents import (
    _gerar_pdf_transferencia_parceiro_bytes,
    _gerar_pdf_transferencias_parceiro_consolidado_bytes,
    _montar_email_transferencia_parceiro,
    _saldo_conta_receber,
    _status_transferencia_parceiro,
)
from .estoque.service import EstoqueService
from .financeiro_models import (
    CategoriaFinanceira,
    ContaPagar,
    ContaReceber,
    FormaPagamento,
    Pagamento,
    Recebimento,
)
from .models import Cliente
from .produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from .security.permissions_decorator import require_permission
from .services.email_service import is_email_configured, send_email
import logging


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/estoque", tags=["Estoque - Transferencia Parceiro"])


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


class TransferenciaParceiroItemRequest(BaseModel):
    """Item da transferencia de estoque para parceiro."""

    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unitario: Optional[float] = Field(default=None, ge=0)
    valor_total: Optional[float] = Field(default=None, ge=0)


class TransferenciaParceiroRequest(BaseModel):
    """Transferencia de estoque para parceiro com ressarcimento pelo custo."""

    parceiro_id: int
    data_vencimento: Optional[date] = None
    documento: Optional[str] = None
    observacao: Optional[str] = None
    itens: List[TransferenciaParceiroItemRequest] = Field(
        default_factory=list, min_items=1
    )


class TransferenciaParceiroEnviarEmailRequest(BaseModel):
    email: Optional[str] = None
    assunto: Optional[str] = None
    mensagem: Optional[str] = None
    mostrar_codigo: bool = True
    mostrar_descricao: bool = True
    mostrar_quantidade: bool = True
    mostrar_custo_unitario: bool = True
    mostrar_total_item: bool = True
    mostrar_totais: bool = True


class TransferenciaParceiroCompensacaoContaRequest(BaseModel):
    conta_pagar_id: int
    valor_compensado: float = Field(gt=0)


class TransferenciaParceiroRecebimentoRequest(BaseModel):
    valor_recebido: float = Field(gt=0)
    data_recebimento: date = Field(default_factory=date.today)
    modo_baixa: str = Field(default="recebimento")
    forma_pagamento_id: Optional[int] = None
    compensacoes: List[TransferenciaParceiroCompensacaoContaRequest] = Field(
        default_factory=list
    )
    observacao: Optional[str] = None


class TransferenciaParceiroHistoricoMovItem(BaseModel):
    produto_id: int
    produto_nome: str
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    estoque_atual: float = 0
    quantidade: float = 0
    custo_unitario: float = 0
    valor_total: float = 0
    created_at: Optional[datetime] = None


class TransferenciaParceiroContaPagarCompensacaoItem(BaseModel):
    conta_pagar_id: int
    descricao: str
    documento: Optional[str] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    status: str
    status_label: str
    valor_original: float = 0
    valor_pago: float = 0
    saldo_aberto: float = 0
    observacoes: Optional[str] = None


class TransferenciaParceiroContaPagarCompensacaoResponse(BaseModel):
    items: List[TransferenciaParceiroContaPagarCompensacaoItem] = Field(
        default_factory=list
    )
    total: int = 0
    total_disponivel: float = 0


class TransferenciaParceiroPdfConsolidadoRequest(BaseModel):
    conta_receber_ids: List[int] = Field(default_factory=list)
    parceiro_id: Optional[int] = None
    status_filtro: Optional[str] = None
    busca: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    mostrar_codigo: bool = True
    mostrar_descricao: bool = True
    mostrar_quantidade: bool = True
    mostrar_custo_unitario: bool = True
    mostrar_total_item: bool = True
    mostrar_totais: bool = True


class TransferenciaParceiroHistoricoItem(BaseModel):
    conta_receber_id: int
    documento: Optional[str] = None
    parceiro_id: Optional[int] = None
    parceiro_nome: str
    parceiro_codigo: Optional[str] = None
    parceiro_email: Optional[str] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    data_recebimento: Optional[date] = None
    status: str
    status_label: str
    valor_original: float = 0
    valor_recebido: float = 0
    saldo_aberto: float = 0
    modo_baixa: Optional[str] = None
    modo_baixa_label: Optional[str] = None
    forma_pagamento_id: Optional[int] = None
    forma_pagamento_nome: Optional[str] = None
    observacoes: Optional[str] = None
    itens: List[TransferenciaParceiroHistoricoMovItem] = Field(default_factory=list)


class TransferenciaParceiroHistoricoTotais(BaseModel):
    total_registros: int = 0
    valor_total: float = 0
    valor_recebido: float = 0
    saldo_aberto: float = 0
    pendentes: int = 0
    recebidas: int = 0
    vencidas: int = 0


class TransferenciaParceiroHistoricoResponse(BaseModel):
    items: List[TransferenciaParceiroHistoricoItem] = Field(default_factory=list)
    totais: TransferenciaParceiroHistoricoTotais
    total: int
    page: int
    page_size: int
    pages: int


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

    itens: list[TransferenciaParceiroHistoricoMovItem] = []
    for mov in movimentacoes:
        itens.append(
            TransferenciaParceiroHistoricoMovItem(
                produto_id=mov.produto_id,
                produto_nome=mov.produto.nome
                if mov.produto
                else f"Produto #{mov.produto_id}",
                codigo=getattr(mov.produto, "codigo", None) if mov.produto else None,
                codigo_barras=getattr(mov.produto, "codigo_barras", None)
                if mov.produto
                else None,
                estoque_atual=float(getattr(mov.produto, "estoque_atual", 0) or 0)
                if mov.produto
                else 0,
                quantidade=float(mov.quantidade or 0),
                custo_unitario=float(mov.custo_unitario or 0),
                valor_total=float(mov.valor_total or 0),
                created_at=mov.created_at,
            )
        )

    return itens


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


@router.post("/transferencia-parceiro", status_code=status.HTTP_201_CREATED)
@require_permission("produtos.editar")
def transferir_estoque_para_parceiro(
    payload: TransferenciaParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Transfere estoque para um parceiro pelo custo.

    Regras:
    - baixa estoque via FIFO/lotes;
    - nao cria venda nem entra no faturamento do PDV;
    - gera um contas a receber separado para o ressarcimento do parceiro.
    """
    current_user, tenant_id = user_and_tenant

    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == payload.parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    itens_validos = [item for item in payload.itens if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    quantidades_por_produto: dict[int, float] = defaultdict(float)
    for item in itens_validos:
        quantidades_por_produto[int(item.produto_id)] += float(item.quantidade or 0)

    codigo_transferencia = (
        _texto_limpo(payload.documento) or _gerar_codigo_transferencia_parceiro()
    )
    conta_existente = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.documento == codigo_transferencia,
        )
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um registro financeiro com este documento",
        )

    itens_processados = []
    total_transferencia = Decimal("0")

    try:
        produtos_cache: dict[int, Produto] = {}

        for produto_id, quantidade in quantidades_por_produto.items():
            produto = (
                db.query(Produto)
                .filter(
                    Produto.id == produto_id,
                    Produto.tenant_id == tenant_id,
                )
                .first()
            )
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

            produtos_cache[produto.id] = produto

        for item in itens_validos:
            produto = produtos_cache.get(int(item.produto_id))
            if not produto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Produto ID {item.produto_id} nao encontrado",
                )

            custo_unitario, total_item = _resolver_valores_item_transferencia(
                produto, item
            )
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

        categoria_financeira = _obter_ou_criar_categoria_financeira_transferencia(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
        dre_subcategoria_id = (
            categoria_financeira.dre_subcategoria_id
            or _obter_dre_subcategoria_receita_padrao(db, tenant_id)
        )

        observacoes_itens = "; ".join(
            f"{item['produto_nome']} x {item['quantidade']}"
            for item in itens_processados
        )
        observacoes_conta = observacoes_itens
        if payload.observacao:
            observacoes_conta = f"{payload.observacao}\n\nItens: {observacoes_itens}"

        conta_receber = ContaReceber(
            tenant_id=str(tenant_id),
            descricao=f"Transferencia para parceiro - {parceiro.nome}",
            cliente_id=parceiro.id,
            categoria_id=categoria_financeira.id,
            dre_subcategoria_id=dre_subcategoria_id,
            canal="transferencia_parceiro",
            valor_original=total_transferencia,
            valor_recebido=Decimal("0"),
            valor_final=total_transferencia,
            data_emissao=date.today(),
            data_vencimento=payload.data_vencimento or date.today(),
            status="pendente",
            documento=codigo_transferencia,
            observacoes=observacoes_conta,
            user_id=current_user.id,
        )
        db.add(conta_receber)
        db.flush()

        for item in itens_processados:
            observacao_item = (
                f"Transferencia para parceiro {parceiro.nome} pelo custo. "
                f"Conta a receber #{conta_receber.id}."
            )
            if payload.observacao:
                observacao_item = f"{observacao_item} {payload.observacao}"

            resultado_baixa = EstoqueService.baixar_estoque(
                produto_id=item["produto_id"],
                quantidade=item["quantidade"],
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                referencia_id=conta_receber.id,
                referencia_tipo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=codigo_transferencia,
                observacao=observacao_item,
                custo_unitario_override=item["custo_unitario"],
                valor_total_override=item["total_item"],
            )
            item["movimentacao_id"] = resultado_baixa["movimentacao_id"]
            item["estoque_novo"] = resultado_baixa["estoque_novo"]

        db.commit()

        for item in itens_processados:
            try:
                sincronizar_bling_background(
                    item["produto_id"],
                    item["estoque_novo"],
                    "transferencia_parceiro",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "documento": codigo_transferencia,
            "conta_receber_id": conta_receber.id,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "codigo": getattr(parceiro, "codigo", None),
                "email": getattr(parceiro, "email", None),
            },
            "data_vencimento": conta_receber.data_vencimento.isoformat()
            if conta_receber.data_vencimento
            else None,
            "total_ressarcimento": float(total_transferencia),
            "itens": itens_processados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao registrar transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel registrar a transferencia para parceiro",
        )


@router.put("/transferencia-parceiro/{conta_receber_id}")
@require_permission("produtos.editar")
def editar_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Edita uma transferencia ainda sem baixa, preservando estoque e financeiro."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)

    if float(conta.valor_recebido or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta transferencia ja possui recebimento registrado. "
                "Remova ou trate a baixa financeira antes de editar o lancamento."
            ),
        )

    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    if status_atual in {"cancelado", "cancelada"}:
        raise HTTPException(
            status_code=400,
            detail="Transferencia cancelada nao pode ser editada.",
        )

    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == payload.parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    itens_validos = [item for item in payload.itens if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero",
        )

    codigo_transferencia = (
        _texto_limpo(payload.documento)
        or _texto_limpo(conta.documento)
        or _gerar_codigo_transferencia_parceiro()
    )
    conta_existente = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == str(tenant_id),
            ContaReceber.documento == codigo_transferencia,
            ContaReceber.id != conta.id,
        )
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe um registro financeiro com este documento",
        )

    movimentacoes_anteriores = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id == conta.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )

    try:
        estoques_finais: dict[int, float] = {}
        produtos_tocados: set[int] = set()
        lotes_restaurados = 0

        for movimentacao in movimentacoes_anteriores:
            produtos_tocados.add(int(movimentacao.produto_id))
            lotes_restaurados += _restaurar_lotes_consumidos_transferencia(
                db, movimentacao
            )
            resultado_estorno = EstoqueService.estornar_estoque(
                produto_id=movimentacao.produto_id,
                quantidade=float(movimentacao.quantidade or 0),
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_EDICAO,
                referencia_id=conta.id,
                referencia_tipo=_REFERENCIA_TRANSFERENCIA_PARCEIRO_EDICAO,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=conta.documento,
                observacao=(
                    f"Estorno temporario para edicao da transferencia "
                    f"{conta.documento or conta.id}"
                ),
                custo_unitario_override=float(movimentacao.custo_unitario or 0),
                valor_total_override=float(movimentacao.valor_total or 0),
            )
            estoques_finais[int(movimentacao.produto_id)] = resultado_estorno[
                "estoque_novo"
            ]
            db.delete(movimentacao)

        db.flush()

        itens_processados, total_transferencia = _preparar_itens_transferencia_parceiro(
            db,
            tenant_id=tenant_id,
            itens_validos=itens_validos,
        )

        categoria_financeira = None
        if not conta.categoria_id or not conta.dre_subcategoria_id:
            categoria_financeira = _obter_ou_criar_categoria_financeira_transferencia(
                db,
                tenant_id=tenant_id,
                user_id=current_user.id,
            )

        if not conta.categoria_id and categoria_financeira:
            conta.categoria_id = categoria_financeira.id
        if not conta.dre_subcategoria_id:
            conta.dre_subcategoria_id = (
                categoria_financeira.dre_subcategoria_id
                if categoria_financeira
                else None
            ) or _obter_dre_subcategoria_receita_padrao(db, tenant_id)

        conta.descricao = f"Transferencia para parceiro - {parceiro.nome}"
        conta.cliente_id = parceiro.id
        conta.canal = "transferencia_parceiro"
        conta.valor_original = total_transferencia
        conta.valor_final = total_transferencia
        conta.valor_recebido = Decimal("0")
        conta.data_vencimento = (
            payload.data_vencimento or conta.data_vencimento or date.today()
        )
        conta.status = "pendente"
        conta.documento = codigo_transferencia
        conta.observacoes = _montar_observacoes_transferencia_parceiro(
            payload.observacao,
            itens_processados,
        )
        db.add(conta)
        db.flush()

        for item in itens_processados:
            produtos_tocados.add(int(item["produto_id"]))
            observacao_item = (
                f"Transferencia para parceiro {parceiro.nome} pelo custo. "
                f"Conta a receber #{conta.id}. Editada."
            )
            if payload.observacao:
                observacao_item = f"{observacao_item} {payload.observacao}"

            resultado_baixa = EstoqueService.baixar_estoque(
                produto_id=item["produto_id"],
                quantidade=item["quantidade"],
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                referencia_id=conta.id,
                referencia_tipo=_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=codigo_transferencia,
                observacao=observacao_item,
                custo_unitario_override=item["custo_unitario"],
                valor_total_override=item["total_item"],
            )
            item["movimentacao_id"] = resultado_baixa["movimentacao_id"]
            item["estoque_novo"] = resultado_baixa["estoque_novo"]
            estoques_finais[int(item["produto_id"])] = resultado_baixa["estoque_novo"]

        db.commit()

        for produto_id in produtos_tocados:
            estoque_novo = estoques_finais.get(produto_id)
            if estoque_novo is None:
                continue
            try:
                sincronizar_bling_background(
                    produto_id,
                    estoque_novo,
                    "transferencia_parceiro_edicao",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (edicao transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "editado": True,
            "documento": codigo_transferencia,
            "conta_receber_id": conta.id,
            "parceiro": {
                "id": parceiro.id,
                "nome": parceiro.nome,
                "codigo": getattr(parceiro, "codigo", None),
                "email": getattr(parceiro, "email", None),
            },
            "data_vencimento": conta.data_vencimento.isoformat()
            if conta.data_vencimento
            else None,
            "total_ressarcimento": float(total_transferencia),
            "lotes_restaurados": lotes_restaurados,
            "itens": itens_processados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao editar transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel editar a transferencia para parceiro",
        )


@router.get(
    "/transferencia-parceiro/historico",
    response_model=TransferenciaParceiroHistoricoResponse,
)
@require_permission("produtos.visualizar")
def listar_transferencias_para_parceiro(
    page: int = 1,
    page_size: int = 20,
    parceiro_id: Optional[int] = None,
    status_filtro: Optional[str] = None,
    busca: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista historico operacional e financeiro das transferencias para parceiro."""
    _current_user, tenant_id = user_and_tenant
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    contas = _buscar_transferencias_parceiro_filtradas(
        db,
        tenant_id=tenant_id,
        parceiro_id=parceiro_id,
        status_filtro=status_filtro,
        busca=busca,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    if not contas:
        return TransferenciaParceiroHistoricoResponse(
            items=[],
            totais=TransferenciaParceiroHistoricoTotais(),
            total=0,
            page=page,
            page_size=page_size,
            pages=0,
        )

    conta_ids = [conta.id for conta in contas]
    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .options(
            joinedload(EstoqueMovimentacao.produto),
        )
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id.in_(conta_ids),
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(
            EstoqueMovimentacao.created_at.desc(),
            EstoqueMovimentacao.id.desc(),
        )
        .all()
    )

    itens_por_conta: dict[int, list[TransferenciaParceiroHistoricoMovItem]] = (
        defaultdict(list)
    )
    for mov in movimentacoes:
        if mov.referencia_id is None:
            continue
        itens_por_conta[int(mov.referencia_id)].append(
            TransferenciaParceiroHistoricoMovItem(
                produto_id=mov.produto_id,
                produto_nome=mov.produto.nome
                if mov.produto
                else f"Produto #{mov.produto_id}",
                codigo=getattr(mov.produto, "codigo", None) if mov.produto else None,
                codigo_barras=getattr(mov.produto, "codigo_barras", None)
                if mov.produto
                else None,
                estoque_atual=float(getattr(mov.produto, "estoque_atual", 0) or 0)
                if mov.produto
                else 0,
                quantidade=float(mov.quantidade or 0),
                custo_unitario=float(mov.custo_unitario or 0),
                valor_total=float(mov.valor_total or 0),
                created_at=mov.created_at,
            )
        )

    registros_filtrados: list[TransferenciaParceiroHistoricoItem] = []
    totais = {
        "total_registros": 0,
        "valor_total": 0.0,
        "valor_recebido": 0.0,
        "saldo_aberto": 0.0,
        "pendentes": 0,
        "recebidas": 0,
        "vencidas": 0,
    }

    for conta in contas:
        status_resolvido, status_label = _status_transferencia_parceiro(conta)
        valor_original = float(conta.valor_original or 0)
        valor_recebido = float(conta.valor_recebido or 0)
        saldo_aberto = _saldo_conta_receber(conta)

        totais["total_registros"] += 1
        totais["valor_total"] += valor_original
        totais["valor_recebido"] += valor_recebido
        totais["saldo_aberto"] += saldo_aberto
        if status_resolvido == "recebido":
            totais["recebidas"] += 1
        elif status_resolvido == "vencido":
            totais["vencidas"] += 1
        elif status_resolvido != "cancelado":
            totais["pendentes"] += 1

        cliente = conta.cliente
        ultimo_recebimento = _obter_ultimo_recebimento_transferencia(conta)
        modo_baixa, modo_baixa_label = _detectar_modo_baixa_transferencia(
            ultimo_recebimento
        )
        forma_pagamento = (
            getattr(ultimo_recebimento, "forma_pagamento", None)
            if ultimo_recebimento
            else None
        )
        registros_filtrados.append(
            TransferenciaParceiroHistoricoItem(
                conta_receber_id=conta.id,
                documento=conta.documento,
                parceiro_id=cliente.id if cliente else None,
                parceiro_nome=cliente.nome if cliente else "Parceiro nao encontrado",
                parceiro_codigo=getattr(cliente, "codigo", None) if cliente else None,
                parceiro_email=getattr(cliente, "email", None) if cliente else None,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                data_recebimento=conta.data_recebimento,
                status=status_resolvido,
                status_label=status_label,
                valor_original=valor_original,
                valor_recebido=valor_recebido,
                saldo_aberto=saldo_aberto,
                modo_baixa=modo_baixa,
                modo_baixa_label=modo_baixa_label,
                forma_pagamento_id=getattr(
                    ultimo_recebimento, "forma_pagamento_id", None
                ),
                forma_pagamento_nome=_texto_limpo(
                    getattr(forma_pagamento, "nome", None)
                ),
                observacoes=conta.observacoes,
                itens=itens_por_conta.get(conta.id, []),
            )
        )

    total = len(registros_filtrados)
    pages = (total + page_size - 1) // page_size if total else 0
    offset = (page - 1) * page_size
    pagina_items = registros_filtrados[offset : offset + page_size]

    return TransferenciaParceiroHistoricoResponse(
        items=pagina_items,
        totais=TransferenciaParceiroHistoricoTotais(
            total_registros=int(totais["total_registros"]),
            valor_total=float(totais["valor_total"]),
            valor_recebido=float(totais["valor_recebido"]),
            saldo_aberto=float(totais["saldo_aberto"]),
            pendentes=int(totais["pendentes"]),
            recebidas=int(totais["recebidas"]),
            vencidas=int(totais["vencidas"]),
        ),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/transferencia-parceiro/{conta_receber_id}/pdf")
@require_permission("produtos.visualizar")
def gerar_pdf_transferencia_parceiro(
    conta_receber_id: int,
    mostrar_codigo: bool = True,
    mostrar_descricao: bool = True,
    mostrar_quantidade: bool = True,
    mostrar_custo_unitario: bool = True,
    mostrar_total_item: bool = True,
    mostrar_totais: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera PDF operacional da transferencia com ressarcimento."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    parceiro = conta.cliente
    itens = _listar_itens_transferencia_parceiro(db, tenant_id, conta_receber_id)
    pdf_bytes = _gerar_pdf_transferencia_parceiro_bytes(
        conta,
        parceiro,
        itens,
        {
            "mostrar_codigo": mostrar_codigo,
            "mostrar_descricao": mostrar_descricao,
            "mostrar_quantidade": mostrar_quantidade,
            "mostrar_custo_unitario": mostrar_custo_unitario,
            "mostrar_total_item": mostrar_total_item,
            "mostrar_totais": mostrar_totais,
        },
    )
    nome_documento = (conta.documento or f"TRP-{conta.id:06d}").replace("/", "-")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transferencia_{nome_documento}.pdf"'
        },
    )


@router.post("/transferencia-parceiro/pdf-consolidado")
@require_permission("produtos.visualizar")
def gerar_pdf_transferencias_parceiro_consolidado(
    payload: TransferenciaParceiroPdfConsolidadoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera um PDF unico com varias transferencias selecionadas ou filtradas."""
    _current_user, tenant_id = user_and_tenant
    contas = _buscar_transferencias_parceiro_filtradas(
        db,
        tenant_id=tenant_id,
        parceiro_id=payload.parceiro_id,
        status_filtro=payload.status_filtro,
        busca=payload.busca,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        conta_receber_ids=payload.conta_receber_ids or None,
    )

    if not contas:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma transferencia encontrada para gerar o PDF consolidado",
        )

    conta_ids = [conta.id for conta in contas]
    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .options(
            joinedload(EstoqueMovimentacao.produto),
        )
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id.in_(conta_ids),
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

    itens_por_conta: dict[int, list[TransferenciaParceiroHistoricoMovItem]] = (
        defaultdict(list)
    )
    for mov in movimentacoes:
        if mov.referencia_id is None:
            continue
        itens_por_conta[int(mov.referencia_id)].append(
            TransferenciaParceiroHistoricoMovItem(
                produto_id=mov.produto_id,
                produto_nome=mov.produto.nome
                if mov.produto
                else f"Produto #{mov.produto_id}",
                codigo=getattr(mov.produto, "codigo", None) if mov.produto else None,
                codigo_barras=getattr(mov.produto, "codigo_barras", None)
                if mov.produto
                else None,
                estoque_atual=float(getattr(mov.produto, "estoque_atual", 0) or 0)
                if mov.produto
                else 0,
                quantidade=float(mov.quantidade or 0),
                custo_unitario=float(mov.custo_unitario or 0),
                valor_total=float(mov.valor_total or 0),
                created_at=mov.created_at,
            )
        )

    pdf_bytes = _gerar_pdf_transferencias_parceiro_consolidado_bytes(
        contas,
        itens_por_conta,
        {
            "mostrar_codigo": payload.mostrar_codigo,
            "mostrar_descricao": payload.mostrar_descricao,
            "mostrar_quantidade": payload.mostrar_quantidade,
            "mostrar_custo_unitario": payload.mostrar_custo_unitario,
            "mostrar_total_item": payload.mostrar_total_item,
            "mostrar_totais": payload.mostrar_totais,
        },
    )
    data_ref = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="transferencias_consolidadas_{data_ref}.pdf"'
        },
    )


@router.post("/transferencia-parceiro/{conta_receber_id}/enviar-email")
@require_permission("produtos.visualizar")
def enviar_email_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroEnviarEmailRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Envia por e-mail o PDF da transferencia usando o cadastro da pessoa."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    parceiro = conta.cliente
    email_destino = _texto_limpo(payload.email) or _texto_limpo(
        getattr(parceiro, "email", None)
    )

    if not email_destino:
        raise HTTPException(
            status_code=400,
            detail="A pessoa selecionada nao possui e-mail cadastrado",
        )

    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="O envio de e-mail nao esta configurado no servidor",
        )

    itens = _listar_itens_transferencia_parceiro(db, tenant_id, conta_receber_id)
    opcoes_documento = {
        "mostrar_codigo": payload.mostrar_codigo,
        "mostrar_descricao": payload.mostrar_descricao,
        "mostrar_quantidade": payload.mostrar_quantidade,
        "mostrar_custo_unitario": payload.mostrar_custo_unitario,
        "mostrar_total_item": payload.mostrar_total_item,
        "mostrar_totais": payload.mostrar_totais,
    }
    pdf_bytes = _gerar_pdf_transferencia_parceiro_bytes(
        conta,
        parceiro,
        itens,
        opcoes_documento,
    )
    assunto_padrao, html_body, text_body = _montar_email_transferencia_parceiro(
        conta,
        parceiro,
        itens,
        mensagem_extra=payload.mensagem,
        opcoes_documento=opcoes_documento,
    )

    enviado = send_email(
        to=email_destino,
        subject=_texto_limpo(payload.assunto) or assunto_padrao,
        html_body=html_body,
        text_body=text_body,
        attachments=[
            {
                "filename": f"transferencia_{(conta.documento or f'TRP-{conta.id:06d}').replace('/', '-')}.pdf",
                "content": pdf_bytes,
                "mime_subtype": "pdf",
            }
        ],
        simulate_if_unconfigured=False,
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Nao foi possivel enviar o e-mail. Revise a configuracao SMTP.",
        )

    return {
        "sucesso": True,
        "email": email_destino,
        "documento": conta.documento or f"TRP-{conta.id:06d}",
    }


@router.get(
    "/transferencia-parceiro/{conta_receber_id}/contas-pagar-compensacao",
    response_model=TransferenciaParceiroContaPagarCompensacaoResponse,
)
@require_permission("produtos.visualizar")
def listar_contas_pagar_compensacao_transferencia(
    conta_receber_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista contas a pagar em aberto da mesma pessoa para realizar compensacao."""
    _current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    contas = _buscar_contas_pagar_compensacao_transferencia(
        db,
        tenant_id=tenant_id,
        cliente_id=getattr(conta, "cliente_id", None),
    )

    items = []
    total_disponivel = 0.0
    for conta_pagar in contas:
        saldo_aberto = _saldo_conta_pagar(conta_pagar)
        status_conta, status_label = _status_conta_pagar_compensacao(conta_pagar)
        total_disponivel += saldo_aberto
        items.append(
            TransferenciaParceiroContaPagarCompensacaoItem(
                conta_pagar_id=conta_pagar.id,
                descricao=conta_pagar.descricao,
                documento=conta_pagar.documento,
                data_emissao=conta_pagar.data_emissao,
                data_vencimento=conta_pagar.data_vencimento,
                status=status_conta,
                status_label=status_label,
                valor_original=float(conta_pagar.valor_original or 0),
                valor_pago=float(conta_pagar.valor_pago or 0),
                saldo_aberto=saldo_aberto,
                observacoes=conta_pagar.observacoes,
            )
        )

    return TransferenciaParceiroContaPagarCompensacaoResponse(
        items=items,
        total=len(items),
        total_disponivel=round(total_disponivel, 2),
    )


@router.post("/transferencia-parceiro/{conta_receber_id}/receber")
@require_permission("produtos.editar")
def registrar_recebimento_transferencia_parceiro(
    conta_receber_id: int,
    payload: TransferenciaParceiroRecebimentoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registra baixa financeira de uma transferencia com ressarcimento."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)
    modo_baixa = _normalizar_modo_baixa_transferencia(payload.modo_baixa)
    compensacoes_payload = [
        item
        for item in (payload.compensacoes or [])
        if round(float(item.valor_compensado or 0), 2) > 0
    ]

    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    if status_atual in {"cancelado", "cancelada"}:
        raise HTTPException(
            status_code=400,
            detail="Transferencia cancelada nao pode receber baixa",
        )

    saldo_aberto = _saldo_conta_receber(conta)
    valor_recebido = round(float(payload.valor_recebido or 0), 2)

    if valor_recebido <= 0:
        raise HTTPException(
            status_code=400,
            detail="Informe um valor recebido maior que zero",
        )

    if valor_recebido - saldo_aberto > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"O valor recebido ultrapassa o saldo da transferencia. "
                f"Saldo atual: R$ {saldo_aberto:.2f}"
            ),
        )

    total_compensado = round(
        sum(float(item.valor_compensado or 0) for item in compensacoes_payload),
        2,
    )
    if compensacoes_payload and abs(total_compensado - valor_recebido) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                "O total compensado nas contas a pagar deve ser igual ao valor da baixa "
                "quando houver titulos selecionados para compensacao."
            ),
        )

    valor_recebido_total = round(float(conta.valor_recebido or 0) + valor_recebido, 2)
    conta.valor_recebido = Decimal(str(valor_recebido_total))
    conta.data_recebimento = payload.data_recebimento or date.today()
    conta.status = (
        "recebido"
        if abs(float(conta.valor_final or 0) - valor_recebido_total) < 0.01
        else "parcial"
    )

    forma_pagamento = None
    if modo_baixa == "acerto":
        forma_pagamento = _obter_ou_criar_forma_pagamento_acerto(
            db,
            tenant_id=tenant_id,
            user_id=current_user.id,
        )
    elif payload.forma_pagamento_id:
        forma_pagamento = _buscar_forma_pagamento_transferencia(
            db,
            tenant_id=tenant_id,
            forma_pagamento_id=payload.forma_pagamento_id,
        )

    if forma_pagamento:
        conta.forma_pagamento_id = forma_pagamento.id

    observacao_recebimento = _texto_limpo(payload.observacao)
    modo_label = _label_modo_baixa_transferencia(modo_baixa) or "Recebimento"
    compensacoes_processadas: list[dict] = []
    if modo_baixa == "acerto" and compensacoes_payload:
        compensacoes_processadas = _aplicar_compensacoes_contas_pagar_transferencia(
            db,
            conta_receber=conta,
            tenant_id=tenant_id,
            user_id=current_user.id,
            data_pagamento=conta.data_recebimento,
            forma_pagamento=forma_pagamento,
            compensacoes_payload=compensacoes_payload,
        )

    detalhe_forma = (
        f" | Forma: {forma_pagamento.nome}"
        if forma_pagamento and _texto_limpo(forma_pagamento.nome)
        else ""
    )
    detalhe_compensacao = ""
    resumo_compensacao = _formatar_resumo_compensacoes_transferencia(
        compensacoes_processadas
    )
    if resumo_compensacao:
        detalhe_compensacao = f" | {resumo_compensacao}"
    detalhe_observacao = (
        f" - {observacao_recebimento}" if observacao_recebimento else ""
    )
    historico = (
        f"{modo_label} {conta.data_recebimento.strftime('%d/%m/%Y')}: "
        f"R$ {valor_recebido:.2f}{detalhe_forma}{detalhe_compensacao}{detalhe_observacao}"
    )
    conta.observacoes = (
        f"{conta.observacoes}\n\n{historico}".strip()
        if conta.observacoes
        else historico
    )

    recebimento = Recebimento(
        conta_receber_id=conta.id,
        forma_pagamento_id=forma_pagamento.id if forma_pagamento else None,
        valor_recebido=Decimal(str(valor_recebido)),
        data_recebimento=conta.data_recebimento,
        observacoes=historico,
        user_id=current_user.id,
        tenant_id=str(tenant_id),
    )
    db.add(recebimento)
    db.commit()
    db.refresh(conta)

    status_resolvido, status_label = _status_transferencia_parceiro(conta)

    return {
        "sucesso": True,
        "conta_receber_id": conta.id,
        "status": status_resolvido,
        "status_label": status_label,
        "valor_recebido": float(conta.valor_recebido or 0),
        "saldo_aberto": _saldo_conta_receber(conta),
        "data_recebimento": conta.data_recebimento.isoformat()
        if conta.data_recebimento
        else None,
        "modo_baixa": modo_baixa,
        "modo_baixa_label": modo_label,
        "forma_pagamento_id": forma_pagamento.id if forma_pagamento else None,
        "forma_pagamento_nome": _texto_limpo(getattr(forma_pagamento, "nome", None)),
        "compensacoes": compensacoes_processadas,
    }


@router.delete("/transferencia-parceiro/{conta_receber_id}")
@require_permission("produtos.editar")
def excluir_transferencia_parceiro(
    conta_receber_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exclui uma transferencia ainda sem baixa, estornando o estoque."""
    current_user, tenant_id = user_and_tenant
    conta = _buscar_conta_transferencia_parceiro(db, tenant_id, conta_receber_id)

    if float(conta.valor_recebido or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Esta transferencia ja possui recebimento registrado. "
                "Remova ou trate a baixa financeira antes de excluir o lancamento."
            ),
        )

    movimentacoes = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id == conta.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.motivo.in_(
                [_MOTIVO_TRANSFERENCIA_PARCEIRO_ESTOQUE, "transferencia_parceiro"]
            ),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )

    try:
        estoques_finais: dict[int, float] = {}
        lotes_restaurados = 0

        for movimentacao in movimentacoes:
            lotes_restaurados += _restaurar_lotes_consumidos_transferencia(
                db, movimentacao
            )
            resultado_estorno = EstoqueService.estornar_estoque(
                produto_id=movimentacao.produto_id,
                quantidade=float(movimentacao.quantidade or 0),
                motivo=_MOTIVO_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
                referencia_id=conta.id,
                referencia_tipo=_REFERENCIA_TRANSFERENCIA_PARCEIRO_EXCLUSAO,
                user_id=current_user.id,
                db=db,
                tenant_id=str(tenant_id),
                documento=conta.documento,
                observacao=(
                    f"Estorno por exclusao da transferencia "
                    f"{conta.documento or conta.id}"
                ),
                custo_unitario_override=float(movimentacao.custo_unitario or 0),
                valor_total_override=float(movimentacao.valor_total or 0),
            )
            estoques_finais[movimentacao.produto_id] = resultado_estorno["estoque_novo"]
            db.delete(movimentacao)

        recebimentos = (
            db.query(Recebimento)
            .filter(
                Recebimento.conta_receber_id == conta.id,
                Recebimento.tenant_id == str(tenant_id),
            )
            .all()
        )
        for recebimento in recebimentos:
            db.delete(recebimento)

        db.delete(conta)
        db.commit()

        for produto_id, estoque_novo in estoques_finais.items():
            try:
                sincronizar_bling_background(
                    produto_id,
                    estoque_novo,
                    "transferencia_parceiro_exclusao",
                )
            except Exception as e_sync:
                logger.warning(
                    f"[BLING-SYNC] Erro ao agendar sync (exclusao transferencia-parceiro): {e_sync}"
                )

        return {
            "sucesso": True,
            "conta_receber_id": conta_receber_id,
            "documento": conta.documento,
            "lotes_restaurados": lotes_restaurados,
        }
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Erro ao excluir transferencia para parceiro: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel excluir a transferencia para parceiro",
        )
