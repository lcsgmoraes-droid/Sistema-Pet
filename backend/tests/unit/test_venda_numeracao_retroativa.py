from datetime import datetime
from types import SimpleNamespace

from app.vendas.numeracao import gerar_numero_venda


class _Query:
    def filter(self, *conditions):
        return self

    def order_by(self, *columns):
        return self

    def first(self):
        return SimpleNamespace(numero_venda="202610010023")


class _Session:
    def query(self, model):
        return _Query()


def test_venda_retroativa_recebe_numero_do_dia_da_ocorrencia():
    numero = gerar_numero_venda(
        _Session(), tenant_id="empresa-a", data_venda=datetime(2026, 10, 1, 14, 30)
    )
    assert numero == "202610010024"
