"""Passivos devem constar no contas a pagar sem virar despesa na DRE."""

import asyncio
from datetime import date
from types import SimpleNamespace

from app.financeiro import contas_pagar_criacao_routes as routes
from app.financeiro.contas_pagar_schemas import ContaPagarCreate
from app.financeiro_models import ContaPagar, LancamentoManual


class FakeQuery:
    def filter(self, *args):
        return self

    def first(self):
        return None


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)

    def query(self, *args):
        return FakeQuery()

    def commit(self):
        pass


def test_criar_passivo_nao_exige_dre_e_mantem_previsao_de_caixa(monkeypatch):
    def nao_deve_chamar(*args, **kwargs):
        raise AssertionError("Passivo não deve ser classificado na DRE")

    monkeypatch.setattr(routes, "_resolver_dre_subcategoria_conta_pagar", nao_deve_chamar)
    monkeypatch.setattr(routes, "atualizar_dre_por_lancamento", nao_deve_chamar)
    monkeypatch.setattr(routes, "aplicar_classificacao_aprendida_conta_pagar", nao_deve_chamar)

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
