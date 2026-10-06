"""Passivos devem constar no contas a pagar sem virar despesa na DRE."""

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.financeiro import contas_pagar_criacao_routes as routes
from app.financeiro import contas_pagar_manutencao_routes as manutencao_routes
from app.financeiro import contas_pagar_pagamento_service as pagamento_service
from app.financeiro import contas_pagar_recorrencia as recorrencia
from app.financeiro.contas_pagar_schemas import ContaPagarCreate, ContaPagarUpdate
from app.financeiro_models import CategoriaFinanceira, ContaPagar, LancamentoManual


class FakeQuery:
    def __init__(self, result=None, rows=None):
        self.result = result
        self.rows = rows or []

    def filter(self, *args):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, categoria=None, conta=None, filhas=None):
        self.added = []
        self.categoria = categoria
        self.conta = conta
        self.filhas = filhas or []

    def add(self, item):
        self.added.append(item)

    def query(self, *args):
        result = self.categoria if args == (CategoriaFinanceira,) else None
        if args == (ContaPagar,):
            result = self.conta
        return FakeQuery(result, self.filhas)

    def commit(self):
        pass

    def refresh(self, item):
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


def test_editar_conta_para_passivo_preserva_categoria_e_retira_classificacao_dre():
    conta = ContaPagar(
        id=21,
        tenant_id=3,
        descricao="Principal emprestimo",
        categoria_id=19,
        dre_subcategoria_id=8,
        afeta_dre=True,
        valor_original=1000,
        valor_pago=0,
        valor_juros=0,
        valor_multa=0,
        valor_desconto=0,
    )
    resposta = manutencao_routes.atualizar_conta_pagar(
        21,
        ContaPagarUpdate(afeta_dre=False),
        db=FakeSession(conta=conta),
        user_and_tenant=(SimpleNamespace(id=7), 3),
    )

    assert resposta["afeta_dre"] is False
    assert conta.categoria_id == 19
    assert conta.dre_subcategoria_id is None
    assert conta.valor_original == 1000


def test_editar_principal_parcelado_nao_cria_obrigacao_duplicada():
    principal = ContaPagar(
        id=25,
        tenant_id=3,
        descricao="Emprestimo parcelado (controle)",
        categoria_id=19,
        dre_subcategoria_id=8,
        afeta_dre=True,
        eh_parcelado=True,
        total_parcelas=3,
        status="parcelado",
        valor_original=300,
        valor_pago=0,
        valor_juros=0,
        valor_multa=0,
        valor_desconto=0,
    )
    parcelas = [
        ContaPagar(
            id=26 + indice,
            tenant_id=3,
            conta_principal_id=25,
            status=status,
            categoria_id=19,
            dre_subcategoria_id=8,
            afeta_dre=True,
            tipo_despesa_id=2,
            canal="loja_fisica",
            valor_original=100,
            valor_pago=valor_pago,
        )
        for indice, (status, valor_pago) in enumerate([("pago", 100), ("pendente", 0)])
    ]
    resposta = manutencao_routes.atualizar_conta_pagar(
        25,
        ContaPagarUpdate(afeta_dre=False),
        db=FakeSession(conta=principal, filhas=parcelas),
        user_and_tenant=(SimpleNamespace(id=7), 3),
    )

    assert resposta["status"] == "parcelado"
    assert resposta["parcelas_classificadas"] == 2
    assert principal.afeta_dre is False
    assert principal.dre_subcategoria_id is None
    assert all(parcela.afeta_dre is False for parcela in parcelas)
    assert all(parcela.dre_subcategoria_id is None for parcela in parcelas)
    assert [parcela.categoria_id for parcela in parcelas] == [19, 19]
    assert [parcela.tipo_despesa_id for parcela in parcelas] == [2, 2]
    assert [parcela.canal for parcela in parcelas] == ["loja_fisica", "loja_fisica"]
    assert [parcela.status for parcela in parcelas] == ["pago", "pendente"]
    assert [parcela.valor_pago for parcela in parcelas] == [100, 0]


def test_editar_descricao_do_principal_nao_sobrescreve_parcela_classificada(
    monkeypatch,
):
    monkeypatch.setattr(
        manutencao_routes,
        "_resolver_dre_subcategoria_conta_pagar",
        lambda *args, **kwargs: 8,
    )
    principal = ContaPagar(
        id=30,
        tenant_id=3,
        descricao="Parcelado",
        eh_parcelado=True,
        total_parcelas=2,
        status="parcelado",
        afeta_dre=True,
        categoria_id=19,
        dre_subcategoria_id=8,
        valor_original=200,
        valor_pago=0,
        valor_juros=0,
        valor_multa=0,
        valor_desconto=0,
    )
    parcela = ContaPagar(
        id=31,
        tenant_id=3,
        conta_principal_id=30,
        categoria_id=20,
        dre_subcategoria_id=9,
        afeta_dre=True,
    )
    resposta = manutencao_routes.atualizar_conta_pagar(
        30,
        ContaPagarUpdate(descricao="Parcelado revisado", afeta_dre=True),
        db=FakeSession(conta=principal, filhas=[parcela]),
        user_and_tenant=(SimpleNamespace(id=7), 3),
    )
    assert resposta["status"] == "parcelado"
    assert resposta["parcelas_classificadas"] == 0
    assert parcela.categoria_id == 20
    assert parcela.dre_subcategoria_id == 9


def test_reativar_dre_em_conta_existente_resolve_classificacao(monkeypatch):
    conta = ContaPagar(
        id=22,
        tenant_id=3,
        descricao="Despesa classificada",
        categoria_id=19,
        dre_subcategoria_id=None,
        afeta_dre=False,
        valor_original=100,
        valor_pago=0,
        valor_juros=0,
        valor_multa=0,
        valor_desconto=0,
    )
    chamadas = []

    def resolver(db, tenant_id, *, dre_subcategoria_id, categoria_id):
        chamadas.append((tenant_id, dre_subcategoria_id, categoria_id))
        return 8

    monkeypatch.setattr(
        manutencao_routes, "_resolver_dre_subcategoria_conta_pagar", resolver
    )
    resposta = manutencao_routes.atualizar_conta_pagar(
        22,
        ContaPagarUpdate(afeta_dre=True),
        db=FakeSession(conta=conta),
        user_and_tenant=(SimpleNamespace(id=7), 3),
    )

    assert chamadas == [(3, None, 19)]
    assert resposta["afeta_dre"] is True
    assert conta.dre_subcategoria_id == 8


def test_reativar_dre_sem_categoria_ou_subcategoria_e_rejeitado():
    conta = ContaPagar(
        id=24,
        tenant_id=3,
        descricao="Passivo sem categoria",
        categoria_id=None,
        dre_subcategoria_id=None,
        afeta_dre=False,
    )
    with pytest.raises(HTTPException) as erro:
        manutencao_routes.atualizar_conta_pagar(
            24,
            ContaPagarUpdate(afeta_dre=True),
            db=FakeSession(conta=conta),
            user_and_tenant=(SimpleNamespace(id=7), 3),
        )
    assert erro.value.status_code == 400


def test_edicao_rejeita_afeta_dre_nulo():
    conta = ContaPagar(id=23, tenant_id=3, descricao="Conta", afeta_dre=False)
    with pytest.raises(HTTPException) as erro:
        manutencao_routes.atualizar_conta_pagar(
            23,
            ContaPagarUpdate(afeta_dre=None),
            db=FakeSession(conta=conta),
            user_and_tenant=(SimpleNamespace(id=7), 3),
        )
    assert erro.value.status_code == 422


def test_edicao_de_recorrencia_propaga_flag_so_para_contas_futuras_nao_pagas(
    monkeypatch,
):
    futura = SimpleNamespace(
        afeta_dre=True, dre_subcategoria_id=8, data_vencimento=date(2026, 11, 10)
    )

    class QueryFuturas:
        def filter(self, *args):
            return self

        def all(self):
            return [futura]

    monkeypatch.setattr(
        recorrencia, "_obter_origem_recorrencia", lambda *args: SimpleNamespace(id=21)
    )
    origem = SimpleNamespace(
        id=21,
        data_vencimento=date(2026, 10, 10),
        afeta_dre=False,
        dre_subcategoria_id=None,
    )
    atualizadas = recorrencia._aplicar_edicao_recorrencia_futura(
        db=SimpleNamespace(query=lambda *args: QueryFuturas()),
        tenant_id=3,
        conta=origem,
        campos={"afeta_dre"},
    )
    assert atualizadas == 1
    assert futura.afeta_dre is False
    assert futura.dre_subcategoria_id is None
