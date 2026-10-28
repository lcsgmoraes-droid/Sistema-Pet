"""Uma transação de cartão não pode quitar operações diferentes."""

from fastapi import HTTPException
from sqlalchemy import func, or_

from app.financeiro_models import Recebimento
from app.operadoras_models import OperadoraCartao
from app.vendas_models import VendaBaixaLoteItem, VendaPagamento


def validar_nsu_recebimento(
    db,
    *,
    tenant_id,
    operadora_id,
    nsu,
    baixa_lote_id=None,
    recebimento_ids=(),
):
    nsu = str(nsu or "").strip()
    if not nsu or not operadora_id:
        return
    # Serializa as verificações entre PDV e baixas avulsas até o commit.
    operadora = (
        db.query(OperadoraCartao)
        .filter(
            OperadoraCartao.tenant_id == tenant_id,
            OperadoraCartao.id == operadora_id,
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if not operadora:
        raise HTTPException(400, "Operadora de cartão não encontrada.")
    pagamentos = db.query(VendaPagamento.id).filter(
        VendaPagamento.tenant_id == tenant_id,
        VendaPagamento.operadora_id == operadora_id,
        func.upper(func.trim(VendaPagamento.nsu_cartao)) == nsu.upper(),
    )
    excluidos = set(recebimento_ids)
    if baixa_lote_id is not None:
        # SessionLocal usa autoflush=False: o item do rateio anterior ainda pode
        # estar pendente na sessão, embora seu recibo já possua ID.
        db.flush()
        pagamentos = pagamentos.filter(
            or_(
                VendaPagamento.baixa_lote_id.is_(None),
                VendaPagamento.baixa_lote_id != baixa_lote_id,
            )
        )
        itens = (
            db.query(VendaBaixaLoteItem)
            .filter(
                VendaBaixaLoteItem.tenant_id == tenant_id,
                VendaBaixaLoteItem.lote_id == baixa_lote_id,
            )
            .all()
        )
        excluidos.update(
            i.efeitos.get("recebimento_id")
            for i in itens
            if isinstance(i.efeitos, dict)
        )
    recibos = db.query(Recebimento.id).filter(
        Recebimento.tenant_id == tenant_id,
        Recebimento.operadora_id == operadora_id,
        func.upper(func.trim(Recebimento.nsu_cartao)) == nsu.upper(),
    )
    if excluidos:
        recibos = recibos.filter(
            Recebimento.id.notin_([id for id in excluidos if id is not None])
        )
    if pagamentos.first() or recibos.first():
        raise HTTPException(
            400,
            f"NSU duplicado: '{nsu}' já foi utilizado em outro recebimento desta operadora. Confira a conciliação antes de registrar novamente.",
        )
