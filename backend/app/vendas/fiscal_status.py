"""Regras de venda compartilhadas pelos fluxos de situação fiscal."""

from fastapi import HTTPException


def nota_fiscal_cancelada(venda) -> bool:
    return str(getattr(venda, "nfe_status", "") or "").strip().lower() in {
        "cancelada",
        "cancelado",
    }


def sincronizar_venda_apos_cancelamento_fiscal(db, venda) -> None:
    # O cancelamento fiscal não cancela a venda nem movimenta estoque/financeiro.
    # Apenas remove a trava fiscal, preservando cancelamentos e devoluções.
    if not nota_fiscal_cancelada(venda):
        return
    # A consulta externa terminou; outra transação pode ter cancelado/devolvido
    # a venda enquanto aguardávamos. Relê somente o estado comercial com lock,
    # sem enviar os campos fiscais ainda pendentes antes de obter a linha atual.
    with db.no_autoflush:
        db.refresh(venda, attribute_names=["status"], with_for_update=True)
        if venda.status == "pago_nf":
            venda.status = "finalizada"


def validar_cancelamento_fiscal_venda(venda) -> None:
    if nota_fiscal_cancelada(venda):
        return

    situacao = str(getattr(venda, "nfe_status", "") or "").strip().lower()
    if situacao in {"rejeitada", "rascunho", "denegada", "inutilizada"} and not getattr(
        venda, "nfe_data_autorizacao", None
    ):
        return
    if venda.status == "pago_nf" or situacao in {
        "autorizada",
        "emitida",
        "emitida_danfe",
        "aguardando",
        "pendente",
        "enviando",
        "processando",
        "inconclusiva",
        "contingencia",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cancele a nota fiscal e aguarde a confirmação do emissor "
                "antes de cancelar a venda."
            ),
        )
