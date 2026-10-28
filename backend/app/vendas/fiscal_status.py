"""Regras de venda compartilhadas pelos fluxos de situação fiscal."""


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
    venda.nfe_cancelamento_status = "confirmado"
    venda.nfe_cancelamento_codigo = None
    venda.nfe_cancelamento_motivo = None
    # A consulta externa terminou; outra transação pode ter cancelado/devolvido
    # a venda enquanto aguardávamos. Relê somente o estado comercial com lock,
    # sem enviar os campos fiscais ainda pendentes antes de obter a linha atual.
    with db.no_autoflush:
        db.refresh(venda, attribute_names=["status"], with_for_update=True)
        if venda.status == "pago_nf":
            venda.status = "finalizada"


def nota_fiscal_requer_regularizacao(venda) -> bool:
    """Identifica documento ainda ativo sem confundir a venda com a nota.

    Cancelar comercialmente a venda estorna estoque e financeiro, mas não
    equivale ao registro de um evento fiscal pelo emissor.
    """
    if nota_fiscal_cancelada(venda):
        return False

    situacao = str(getattr(venda, "nfe_status", "") or "").strip().lower()
    if situacao in {"rejeitada", "rascunho", "denegada", "inutilizada"} and not getattr(
        venda, "nfe_data_autorizacao", None
    ):
        return False
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
        return True
    return bool(
        getattr(venda, "nfe_data_autorizacao", None)
        or getattr(venda, "nfe_correlation_id", None)
        or getattr(venda, "nfe_bling_id", None)
        or getattr(venda, "nfe_protocolo", None)
    )


def pendencia_fiscal_cancelamento(venda) -> bool:
    return str(
        getattr(venda, "status", "") or ""
    ).strip().lower() == "cancelada" and nota_fiscal_requer_regularizacao(venda)
