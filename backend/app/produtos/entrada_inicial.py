"""Entrada de estoque registrada junto com o primeiro cadastro do produto."""

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote


class EntradaInicialProduto(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    quantidade: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=9, decimal_places=3
    )
    numero_lote: str | None = Field(default=None, max_length=50)
    data_validade: date | None = None
    data_fabricacao: date | None = None

    @model_validator(mode="after")
    def validar_entrada(self):
        if self.quantidade == 0 and (
            self.numero_lote or self.data_validade or self.data_fabricacao
        ):
            raise ValueError("Informe a quantidade para registrar lote ou datas.")
        if (
            self.data_fabricacao
            and self.data_validade
            and self.data_fabricacao > self.data_validade
        ):
            raise ValueError("A fabricacao nao pode ser posterior a validade.")
        return self


def registrar_entrada_inicial(
    db: Session,
    *,
    produto: Produto,
    entrada: EntradaInicialProduto,
    user_id: int,
    tenant_id,
    origem: str,
) -> None:
    """Prepara saldo, lote e histórico na mesma transação do cadastro."""
    if entrada.quantidade == 0:
        return
    if (
        not produto.controlar_estoque
        or produto.tipo_produto == "PAI"
        or produto.is_parent
        or (
            produto.tipo_produto in {"KIT", "VARIACAO"}
            and produto.tipo_kit == "VIRTUAL"
        )
    ):
        raise ValueError("Este tipo de produto nao permite entrada inicial de estoque.")

    quantidade = float(entrada.quantidade)
    produto.estoque_atual = quantidade
    lote_id = None
    if entrada.numero_lote or entrada.data_validade or entrada.data_fabricacao:
        produto.controle_lote = True
        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=entrada.numero_lote
            or f"CAD-{produto.id}-{datetime.utcnow():%Y%m%d%H%M%S}",
            quantidade_inicial=quantidade,
            quantidade_disponivel=quantidade,
            quantidade_reservada=0,
            data_fabricacao=(
                datetime.combine(entrada.data_fabricacao, time.min)
                if entrada.data_fabricacao
                else None
            ),
            data_validade=(
                datetime.combine(entrada.data_validade, time.max).replace(microsecond=0)
                if entrada.data_validade
                else None
            ),
            custo_unitario=float(produto.preco_custo or 0),
            ordem_entrada=int(datetime.utcnow().timestamp()),
            status="ativo",
            apenas_identificacao=False,
            tenant_id=tenant_id,
        )
        db.add(lote)
        db.flush()
        lote_id = lote.id

    custo = float(produto.preco_custo or 0)
    db.add(
        EstoqueMovimentacao(
            produto_id=produto.id,
            tipo="entrada",
            motivo="cadastro_produto",
            quantidade=quantidade,
            quantidade_anterior=0,
            quantidade_nova=quantidade,
            custo_unitario=custo,
            valor_total=quantidade * custo,
            lote_id=lote_id,
            observacao=f"Entrada inicial no cadastro pelo {origem}",
            user_id=user_id,
            tenant_id=tenant_id,
        )
    )
