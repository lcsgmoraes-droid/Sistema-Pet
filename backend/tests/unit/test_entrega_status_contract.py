from datetime import datetime
from types import SimpleNamespace

from app.api.endpoints.rotas_entrega import _sincronizar_venda_entregue_por_parada
from app.vendas_routes import _resolver_status_entrega_atualizacao


def test_atualizacao_de_venda_preserva_status_entrega_concluido():
    assert _resolver_status_entrega_atualizacao(True, "entregue") == "entregue"
    assert _resolver_status_entrega_atualizacao(True, "em_rota") == "em_rota"
    assert _resolver_status_entrega_atualizacao(True, "cancelada") == "cancelada"


def test_atualizacao_de_venda_define_pendente_apenas_para_entrega_nova():
    assert _resolver_status_entrega_atualizacao(True, None) == "pendente"
    assert _resolver_status_entrega_atualizacao(False, "entregue") is None


def test_sincronizar_parada_entregue_atualiza_venda_para_pdv():
    entrega_em = datetime(2026, 4, 24, 10, 30)
    parada = SimpleNamespace(venda_id=10, status="pendente", data_entrega=None)
    venda = SimpleNamespace(id=10, tenant_id="tenant-1", status_entrega="em_rota", data_entrega=None)

    class QueryFake:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return venda

    class DbFake:
        def query(self, _model):
            return QueryFake()

    retorno = _sincronizar_venda_entregue_por_parada(DbFake(), parada, "tenant-1", entrega_em)

    assert retorno is venda
    assert parada.status == "entregue"
    assert parada.data_entrega == entrega_em
    assert venda.status_entrega == "entregue"
    assert venda.data_entrega == entrega_em

