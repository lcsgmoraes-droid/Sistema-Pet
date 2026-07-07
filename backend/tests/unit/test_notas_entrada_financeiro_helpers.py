from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.notas_entrada import financeiro


class _FakeDb:
    def __init__(self):
        self.adicionados = []
        self.flushes = 0

    def add(self, obj):
        obj.id = len(self.adicionados) + 1
        self.adicionados.append(obj)

    def flush(self):
        self.flushes += 1


class _FakeContaPagar:
    def __init__(self, **kwargs):
        self.id = None
        for chave, valor in kwargs.items():
            setattr(self, chave, valor)


def test_criar_contas_pagar_da_nota_usa_tipo_tenant_e_classificacao(monkeypatch):
    chamadas_classificacao = []
    monkeypatch.setattr(financeiro, "ContaPagar", _FakeContaPagar)
    monkeypatch.setattr(
        financeiro, "_obter_tipo_produto_revenda_id", lambda db, tenant_id: 123
    )
    monkeypatch.setattr(
        financeiro,
        "aplicar_classificacao_aprendida_conta_pagar",
        lambda db, tenant_id, conta: chamadas_classificacao.append((tenant_id, conta)),
    )

    nota = SimpleNamespace(
        id=9,
        numero_nota="9398",
        fornecedor_id=77,
        data_emissao=date(2026, 6, 2),
        valor_total=Decimal("9207.21"),
        percentual_online=30,
        percentual_loja=70,
    )
    dados_xml = {
        "duplicatas": [
            {"numero": "001", "vencimento": date(2026, 7, 2), "valor": "4603.60"},
            {"numero": "002", "vencimento": date(2026, 8, 2), "valor": "4603.61"},
        ],
    }
    db = _FakeDb()

    ids = financeiro.criar_contas_pagar_da_nota(
        nota, dados_xml, db, user_id=42, tenant_id="tenant-1"
    )

    assert ids == [1, 2]
    assert db.flushes == 2
    assert len(chamadas_classificacao) == 2
    primeira = db.adicionados[0]
    assert primeira.tipo_despesa_id == 123
    assert primeira.valor_original == Decimal("4603.60")
    assert primeira.eh_parcelado is True
    assert primeira.numero_parcela == 1
    assert primeira.total_parcelas == 2
    assert primeira.tenant_id == "tenant-1"
    assert primeira.user_id == 42
    assert primeira.percentual_online == 30
    assert primeira.percentual_loja == 70


def test_criar_contas_pagar_da_nota_nao_afeta_dre_mesmo_com_regra_aprendida(
    monkeypatch,
):
    monkeypatch.setattr(financeiro, "ContaPagar", _FakeContaPagar)
    monkeypatch.setattr(
        financeiro, "_obter_tipo_produto_revenda_id", lambda db, tenant_id: 123
    )

    def aplicar_regra_perigosa(_db, _tenant_id, conta):
        conta.dre_subcategoria_id = 999
        conta.canal = "loja_fisica"
        return True

    monkeypatch.setattr(
        financeiro,
        "aplicar_classificacao_aprendida_conta_pagar",
        aplicar_regra_perigosa,
    )

    nota = SimpleNamespace(
        id=10,
        numero_nota="785638",
        fornecedor_id=88,
        data_emissao=date(2026, 6, 5),
        valor_total=Decimal("3708.75"),
        percentual_online=0,
        percentual_loja=100,
    )
    db = _FakeDb()

    financeiro.criar_contas_pagar_da_nota(
        nota,
        {
            "duplicatas": [
                {
                    "numero": "001",
                    "vencimento": date(2026, 6, 8),
                    "valor": "3708.75",
                }
            ]
        },
        db,
        user_id=42,
        tenant_id="tenant-1",
    )

    conta = db.adicionados[0]
    assert conta.tipo_despesa_id == 123
    assert conta.nota_entrada_id == 10
    assert conta.afeta_dre is False
    assert conta.dre_subcategoria_id is None
