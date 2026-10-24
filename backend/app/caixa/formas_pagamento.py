"""Nomes das formas cadastradas, sem confundir o cadastro com o tipo financeiro."""

from collections import Counter

from app.financeiro_models import FormaPagamento


def carregar_nomes_formas_pagamento(db, *, tenant_id, forma_ids):
    ids = {forma_id for forma_id in forma_ids if forma_id is not None}
    if not ids:
        return {}
    # Inclui desativadas e considera nomes repetidos em todo o cadastro da loja,
    # para o rótulo não mudar conforme o caixa ou o período consultado.
    nomes = {
        forma_id: nome.strip()
        for forma_id, nome in db.query(FormaPagamento.id, FormaPagamento.nome)
        .filter(FormaPagamento.tenant_id == tenant_id)
        .all()
        if nome and nome.strip()
    }
    repetidos = Counter(nome.casefold() for nome in nomes.values())
    return {
        forma_id: f"{nome} (forma #{forma_id})"
        if repetidos[nome.casefold()] > 1
        else nome
        for forma_id, nome in nomes.items()
        if forma_id in ids
    }


def nome_forma_pagamento(pagamento, nomes):
    # Registros legados sem vínculo seguro mantêm a descrição original.
    return nomes.get(
        getattr(pagamento, "forma_pagamento_id", None), pagamento.forma_pagamento
    )
