from __future__ import annotations

from types import SimpleNamespace

from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.services import notificacao_entrega_service as service
from app.vendas_models import Venda, VendaItem
from app.models import Cliente


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._result


class _FakeSession:
    def __init__(self, results_by_model):
        self._results_by_model = {
            model: list(results) for model, results in results_by_model.items()
        }

    def query(self, model):
        results = self._results_by_model[model]
        if not results:
            raise AssertionError(f"Unexpected query for {model}")
        return _FakeQuery(results.pop(0))


def test_notificar_inicio_rota_usa_pagamento_e_ignora_tempo_estimado_ausente(
    monkeypatch,
):
    captured = {}
    db = _FakeSession(
        {
            RotaEntrega: [SimpleNamespace(id=10)],
            RotaEntregaParada: [SimpleNamespace(venda_id=101, tempo_acumulado=None)],
            Venda: [
                SimpleNamespace(
                    id=101,
                    cliente_id=501,
                    pagamentos=[SimpleNamespace(forma_pagamento="PIX")],
                )
            ],
            Cliente: [
                SimpleNamespace(id=501, nome="Jefferson", celular="5518999999999")
            ],
            VendaItem: [[]],
        }
    )

    def fake_enviar_whatsapp(telefone, mensagem):
        captured["telefone"] = telefone
        captured["mensagem"] = mensagem
        return True

    monkeypatch.setattr(service, "enviar_whatsapp", fake_enviar_whatsapp)

    assert service.notificar_inicio_rota(db, rota_id=10, tenant_id=1) == 1
    assert captured["telefone"] == "5518999999999"
    assert "Pix" in captured["mensagem"]


def test_notificar_proximo_cliente_fallback_usa_tempo_acumulado_sem_tempo_estimado(
    monkeypatch,
):
    captured = {}
    db = _FakeSession(
        {
            RotaEntregaParada: [
                SimpleNamespace(ordem=1, endereco="Origem", tempo_acumulado=120),
                SimpleNamespace(
                    venda_id=202,
                    endereco="Destino",
                    tempo_acumulado=420,
                    status="pendente",
                ),
            ],
            Venda: [
                SimpleNamespace(
                    id=202,
                    cliente_id=502,
                    pagamentos=[SimpleNamespace(forma_pagamento="Cartao debito")],
                )
            ],
            Cliente: [
                SimpleNamespace(id=502, nome="Jefferson", celular="5518988888888")
            ],
            VendaItem: [[]],
        }
    )

    def fake_enviar_whatsapp(telefone, mensagem):
        captured["telefone"] = telefone
        captured["mensagem"] = mensagem
        return True

    monkeypatch.setattr(
        service,
        "calcular_tempo_estimado",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("maps off")),
    )
    monkeypatch.setattr(service, "enviar_whatsapp", fake_enviar_whatsapp)

    assert (
        service.notificar_proximo_cliente(
            db, rota_id=10, parada_entregue_ordem=1, tenant_id=1
        )
        is True
    )
    assert captured["telefone"] == "5518988888888"
    assert "Cart" in captured["mensagem"]
    assert "5 minutos" in captured["mensagem"]
