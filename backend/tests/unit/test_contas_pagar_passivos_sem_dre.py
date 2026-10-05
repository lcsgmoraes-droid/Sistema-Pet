"""Passivos devem constar no contas a pagar sem virar despesa na DRE."""

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

from app.financeiro import contas_pagar_criacao_routes as routes
from app.financeiro import contas_pagar_pagamento_service as pagamento_service
from app.financeiro.contas_pagar_schemas import ContaPagarCreate
from app.financeiro_models import CategoriaFinanceira, ContaPagar, LancamentoManual


class FakeQuery:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *args):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, categoria=None):
        self.added = []
        self.categoria = categoria

    def add(self, item):
        self.added.append(item)

    def query(self, *args):
        return FakeQuery(self.categoria if args == (CategoriaFinanceira,) else None)

    def commit(self):
        pass


def test_criar_passivo_nao_exige_dre_e_mantem_previsao_de_caixa(monkeypatch):
    def nao_deve_chamar(*args, **kwargs):
        raise AssertionError("Passivo não deve ser classificado na DRE")

    monkeypatch.setattr(
        routes, "_resolver_dre_subcategoria_conta_pagar", nao_deve_chamar
    )
    monkeypatch.setattr(routes, "atualizar_dre_por_lancamento", nao_deve_chamar)
    monkeypatch.setattr(
        routes, "aplicar_classificacao_aprendida_conta_pagar", nao_deve_chamar
    )

    db = FakeSession()
    conta = ContaPagarCreate(
        descricao="Capital de giro - parcela 1/2",
        afeta_dre=False,
        valor_original=1000,
        data_emissao=date(2026, 10, 5),
        data_vencimento=date(2026, 11, 10),
    )

    resultado = asyncio.run(
        routes.criar_conta_pagar.__wrapped__(
            conta,
            request=SimpleNamespace(),
            db=db,
            user_and_tenant=(SimpleNamespace(id=7), 3),
        )
    )

    criadas = [item for item in db.added if isinstance(item, ContaPagar)]
    previsoes = [item for item in db.added if isinstance(item, LancamentoManual)]
    assert resultado["total_contas"] == 1
    assert len(criadas) == 1
    assert criadas[0].afeta_dre is False
    assert criadas[0].dre_subcategoria_id is None
    assert len(previsoes) == 1
    assert previsoes[0].valor == 1000


@pytest.mark.parametrize(
    "nome_categoria",
    ["DAS Simples Nacional", "INSS Patronal", "FGTS", "Folha de Pagamento"],
)
def test_passivo_com_categoria_na_api_nao_reconcilia_dre(monkeypatch, nome_categoria):
    def nao_deve_chamar(*args, **kwargs):
        raise AssertionError("Passivo não pode alterar impostos ou provisões da DRE")

    monkeypatch.setattr(routes, "reconciliar_das_simples", nao_deve_chamar)
    monkeypatch.setattr(routes, "reconciliar_provisao", nao_deve_chamar)
    monkeypatch.setattr(routes, "atualizar_dre_por_lancamento", nao_deve_chamar)
    monkeypatch.setattr(
        routes, "aplicar_classificacao_aprendida_conta_pagar", nao_deve_chamar
    )
    db = FakeSession(categoria=SimpleNamespace(id=19, nome=nome_categoria))
    conta = ContaPagarCreate(
        descricao="Obrigação sem competência na DRE",
        categoria_id=19,
        afeta_dre=False,
        valor_original=1000,
        data_emissao=date(2026, 10, 5),
        data_vencimento=date(2026, 11, 10),
    )

    resultado = asyncio.run(
        routes.criar_conta_pagar.__wrapped__(
            conta,
            request=SimpleNamespace(),
            db=db,
            user_and_tenant=(SimpleNamespace(id=7), 3),
        )
    )

    criada = next(item for item in db.added if isinstance(item, ContaPagar))
    assert resultado["total_contas"] == 1
    assert criada.categoria_id == 19
    assert criada.afeta_dre is False
    assert criada.dre_subcategoria_id is None


def test_recorrencia_de_passivo_pago_nao_sincroniza_dre(monkeypatch):
    def nao_deve_chamar(*args, **kwargs):
        raise AssertionError("Clone de passivo não pode sincronizar a DRE")

    monkeypatch.setattr(
        pagamento_service,
        "_garantir_janela_recorrencia_apos_pagamento",
        lambda **kwargs: [SimpleNamespace(id=20, afeta_dre=False)],
    )
    monkeypatch.setattr(
        pagamento_service, "atualizar_dre_por_lancamento", nao_deve_chamar
    )

    quantidade = pagamento_service._sincronizar_recorrencia_pos_pagamento(
        db=FakeSession(),
        tenant_id=3,
        conta=SimpleNamespace(status="pago"),
    )

    assert quantidade == 1
