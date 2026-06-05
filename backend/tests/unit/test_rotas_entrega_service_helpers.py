from types import SimpleNamespace

from app.services.rotas_entrega_service import (
    aplicar_ordem_otimizada_em_vendas,
    enriquecer_rota_para_resposta,
    montar_origem_config_entrega,
)


class _FakeResult:
    def __init__(self, one=None, many=None):
        self._one = one
        self._many = many or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


class _FakeDb:
    def __init__(self):
        self.commits = 0

    def execute(self, statement, params):
        sql = str(statement)
        if "FROM rotas_entrega" in sql and "lat_atual" in sql:
            return _FakeResult(
                one=(
                    10.1,
                    -20.2,
                    SimpleNamespace(isoformat=lambda: "2026-06-05T10:00:00"),
                    "token-existente",
                    12.5,
                    2.5,
                )
            )
        if "FROM rotas_entrega_paradas" in sql and "distancia_trecho_real_km" in sql:
            return _FakeResult(
                many=[
                    (20, 3.1, 7.2),
                    (10, 1.4, 1.4),
                ]
            )
        raise AssertionError(f"SQL inesperado: {sql}")

    def commit(self):
        self.commits += 1


def test_enriquecer_rota_para_resposta_aplica_distancias_e_dados_do_cliente():
    cliente = SimpleNamespace(nome="Cliente Teste", telefone="1833000000", celular="18999990000")
    venda = SimpleNamespace(cliente=cliente)
    parada_2 = SimpleNamespace(id=20, ordem=2, venda=venda)
    parada_1 = SimpleNamespace(id=10, ordem=1, venda=venda)
    rota = SimpleNamespace(id=99, paradas=[parada_2, parada_1])

    resultado = enriquecer_rota_para_resposta(_FakeDb(), rota, tenant_id="tenant-1")

    assert resultado is rota
    assert rota.token_rastreio == "token-existente"
    assert rota.lat_atual == 10.1
    assert rota.lon_atual == -20.2
    assert rota.distancia_ate_ultima_entrega_km_real == 10.0
    assert [parada.id for parada in rota.paradas] == [10, 20]
    assert rota.paradas[0].distancia_trecho_real_km == 1.4
    assert rota.paradas[1].distancia_acumulada_real_km == 7.2
    assert rota.paradas[0].cliente_nome == "Cliente Teste"
    assert rota.paradas[0].cliente_celular == "18999990000"


def test_montar_origem_config_entrega_ignora_campos_vazios():
    config = SimpleNamespace(
        logradouro="Rua Teste",
        numero="123",
        bairro="Centro",
        cidade="Presidente Prudente",
        estado="SP",
        cep=None,
    )

    assert montar_origem_config_entrega(config) == "Rua Teste, 123, Centro, Presidente Prudente, SP"


def test_aplicar_ordem_otimizada_em_vendas_preserva_numero_venda():
    venda_a = SimpleNamespace(numero_venda="A", ordem_entrega_otimizada=None)
    venda_b = SimpleNamespace(numero_venda="B", ordem_entrega_otimizada=None)

    ordem = aplicar_ordem_otimizada_em_vendas([venda_a, venda_b], [1, 0])

    assert ordem == ["B", "A"]
    assert venda_b.ordem_entrega_otimizada == 1
    assert venda_a.ordem_entrega_otimizada == 2
