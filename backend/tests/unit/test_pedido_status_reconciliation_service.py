from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services import pedido_status_reconciliation_service as service


def test_mensagem_rate_limit_diario_detecta_resposta_do_bling():
    mensagem = (
        "Erro na API Bling: 429 Client Error: Too Many Requests - "
        "{'error': {'type': 'TOO_MANY_REQUESTS', 'description': "
        "'O limite de requisições por dia foi atingido, tente novamente amanhã.', "
        "'period': 'day'}}"
    )

    assert service._mensagem_rate_limit_diario(mensagem) is True


def test_registrar_bloqueio_rate_limit_diario_define_janela_futura(monkeypatch):
    fake_now = datetime(2026, 4, 12, 17, 30, tzinfo=timezone(timedelta(hours=-3)))

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fake_now
            return fake_now.astimezone(tz)

    monkeypatch.setattr(service, "datetime", FakeDateTime)
    monkeypatch.setattr(service, "_RATE_LIMIT_DIARIO_BLOQUEADO_ATE", None)

    bloqueado_ate = service._registrar_bloqueio_rate_limit_diario()

    assert bloqueado_ate > fake_now.astimezone(timezone.utc)
    assert bloqueado_ate.astimezone(fake_now.tzinfo).hour == 0
    assert bloqueado_ate.astimezone(fake_now.tzinfo).minute == 5


def test_rate_limit_diario_ativo_respeita_bloqueio(monkeypatch):
    monkeypatch.setattr(
        service,
        "_RATE_LIMIT_DIARIO_BLOQUEADO_ATE",
        datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    assert service._rate_limit_diario_ativo() is True


def test_reconciliar_status_atendido_com_nf_autorizada_consolida_venda(monkeypatch):
    class FakeQuery:
        def __init__(self, all_result=None):
            self.all_result = all_result or []

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return list(self.all_result)

    class FakeDB:
        def __init__(self, itens):
            self.itens = itens
            self.added = []
            self.commit_calls = 0

        def query(self, model):
            if getattr(model, "__name__", "") == "PedidoIntegradoItem":
                return FakeQuery(all_result=self.itens)
            raise AssertionError(
                f"Modelo inesperado: {getattr(model, '__name__', model)}"
            )

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            self.commit_calls += 1

    class FakeBling:
        def consultar_pedido(self, pedido_bling_id):
            assert pedido_bling_id == "25997676807"
            return {
                "id": 25997676807,
                "numero": "15207",
                "numeroPedidoLoja": "260605AJ6TS27W",
                "situacao": {"id": 9, "valor": 1},
                "notaFiscal": {"id": "26005873647"},
            }

        def consultar_nfe(self, nf_id):
            assert nf_id == 26005873647
            return {
                "id": 26005873647,
                "numero": "003663",
                "situacao": 5,
                "valorNota": 76.92,
            }

        def consultar_nfce(self, nf_id):
            raise AssertionError("nao deve consultar NFC-e quando NFe respondeu")

    pedido = SimpleNamespace(
        id=4678,
        tenant_id="tenant-1",
        pedido_bling_id="25997676807",
        pedido_bling_numero="15207",
        status="aberto",
        confirmado_em=None,
        payload={"pedido": {"numeroPedidoLoja": "260605AJ6TS27W"}},
    )
    item = SimpleNamespace(sku="022860.1/1", quantidade=1, vendido_em=None)
    db = FakeDB([item])
    chamadas = {}

    monkeypatch.setattr("app.bling_integration.BlingAPI", lambda: FakeBling())
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.registrar_evento",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.integracao_bling_pedido_routes.registrar_vinculo_nf_pedido",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service.processar_nf_autorizada",
        lambda **kwargs: (
            chamadas.setdefault("processou_nf", kwargs),
            "venda_confirmada",
        )[1],
    )

    resultado = service.reconciliar_status_pedido_local(db, pedido)

    assert resultado["success"] is True
    assert resultado["acao"] == "venda_confirmada"
    assert resultado["nf_numero"] == "003663"
    assert chamadas["processou_nf"]["pedido"] is pedido
    assert chamadas["processou_nf"]["itens"] == [item]
    assert chamadas["processou_nf"]["nf_id"] == "26005873647"
