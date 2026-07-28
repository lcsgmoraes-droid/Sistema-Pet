from types import SimpleNamespace

import pytest

from app.services.pedido_cancelamento_fiscal_estoque_service import (
    decidir_retorno_estoque,
    registrar_nf_cancelada_aguardando_decisao,
    solicitar_cancelamento_nf_bling,
)
from app.services.pedido_nf_reconciliation_service import (
    registrar_alerta_pedido_cancelado_com_nf_ativa,
)


class FakeDB:
    def __init__(self):
        self.added = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_calls += 1

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1


def _pedido(*, payload=None, status="cancelado"):
    return SimpleNamespace(
        id=1098,
        tenant_id="00000000-0000-0000-0000-000000000001",
        status=status,
        cancelado_em=None,
        payload=payload
        or {
            "ultima_nf": {
                "id": "25432772133",
                "numero": "010985",
                "situacao": "Autorizada",
            }
        },
        pedido_bling_id="701-0090544-7112242",
        pedido_bling_numero="11605",
    )


def _silenciar_monitor(monkeypatch):
    monkeypatch.setattr(
        "app.services.bling_flow_monitor_service.registrar_evento",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.bling_flow_monitor_service.abrir_incidente",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.bling_flow_monitor_service.resolver_incidentes_relacionados",
        lambda *args, **kwargs: 1,
    )


def test_solicitacao_automatica_cancela_nf_uma_unica_vez(monkeypatch):
    chamadas = []

    class FakeBling:
        def cancelar_nfe(self, nf_id, justificativa):
            chamadas.append((nf_id, justificativa))
            return {"situacao": "solicitada"}

    monkeypatch.setattr("app.bling_integration.BlingAPI", lambda: FakeBling())
    _silenciar_monitor(monkeypatch)
    db = FakeDB()
    pedido = _pedido()

    primeira = solicitar_cancelamento_nf_bling(
        db,
        pedido=pedido,
        automatico=True,
    )
    segunda = solicitar_cancelamento_nf_bling(
        db,
        pedido=pedido,
        automatico=True,
    )

    assert primeira["solicitada"] is True
    assert segunda["motivo"] == "solicitacao_ja_registrada"
    assert len(chamadas) == 1
    assert pedido.payload["cancelamento_nf"]["status"] == "solicitado"
    assert pedido.payload["cancelamento_nf"]["tentativas"] == 1


def test_alerta_de_pedido_cancelado_dispara_solicitacao_automatica(monkeypatch):
    chamadas = []
    pedido = _pedido()
    db = FakeDB()
    _silenciar_monitor(monkeypatch)
    monkeypatch.setattr(
        "app.services.pedido_cancelamento_fiscal_estoque_service.solicitar_cancelamento_nf_bling",
        lambda *args, **kwargs: chamadas.append(kwargs) or {"success": True},
    )

    abriu = registrar_alerta_pedido_cancelado_com_nf_ativa(
        db,
        pedido=pedido,
    )

    assert abriu is True
    assert len(chamadas) == 1
    assert chamadas[0]["automatico"] is True
    assert chamadas[0]["nf_contexto"]["id"] == "25432772133"


def test_falha_automatica_fica_registrada_sem_interromper_fluxo(monkeypatch):
    class FakeBling:
        def cancelar_nfe(self, nf_id, justificativa):
            raise RuntimeError("SEFAZ indisponivel")

    monkeypatch.setattr("app.bling_integration.BlingAPI", lambda: FakeBling())
    _silenciar_monitor(monkeypatch)
    db = FakeDB()
    pedido = _pedido()

    resultado = solicitar_cancelamento_nf_bling(
        db,
        pedido=pedido,
        automatico=True,
    )

    assert resultado["success"] is False
    assert pedido.payload["cancelamento_nf"]["status"] == "erro"
    assert "SEFAZ indisponivel" in pedido.payload["cancelamento_nf"]["erro"]


def test_nf_cancelada_mantem_saldo_baixado_e_abre_pendencia(monkeypatch):
    movimento = SimpleNamespace(id=301, produto_id=6745, quantidade=1, status="confirmado")
    pedido = _pedido(
        payload={
            "ultima_nf": {
                "id": "25432772133",
                "numero": "010985",
                "situacao": "Cancelada",
                "situacao_codigo": 4,
            }
        },
        status="confirmado",
    )
    item = SimpleNamespace(vendido_em="agora", liberado_em=None)
    db = FakeDB()
    _silenciar_monitor(monkeypatch)
    monkeypatch.setattr(
        "app.services.pedido_cancelamento_fiscal_estoque_service._movimentos_saida_ativos",
        lambda db, pedido: [movimento],
    )

    resultado = registrar_nf_cancelada_aguardando_decisao(
        db,
        pedido=pedido,
        itens=[item],
        nf_id="25432772133",
    )

    assert resultado == "nf_cancelada_retorno_estoque_pendente"
    assert pedido.payload["cancelamento_nf"]["status"] == "confirmado"
    assert pedido.payload["retorno_estoque"]["status"] == "pendente"
    assert movimento.status == "confirmado"
    assert item.vendido_em == "agora"
    assert db.commit_calls == 1


def test_decisao_retornar_estorna_somente_apos_confirmacao_manual(monkeypatch):
    movimento = SimpleNamespace(
        id=301,
        produto_id=6745,
        quantidade=1,
        status="confirmado",
        observacao="Baixa via NF",
        user_id=12,
    )
    pedido = _pedido(
        payload={
            "ultima_nf": {"id": "25432772133", "situacao": "Cancelada"},
            "retorno_estoque": {
                "nf_id": "25432772133",
                "status": "pendente",
            },
        }
    )
    item = SimpleNamespace(vendido_em="agora", liberado_em=None)
    estornos = []
    db = FakeDB()
    _silenciar_monitor(monkeypatch)
    monkeypatch.setattr(
        "app.services.pedido_cancelamento_fiscal_estoque_service._movimentos_saida_ativos",
        lambda db, pedido: [movimento],
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._obter_usuario_padrao_tenant",
        lambda **kwargs: SimpleNamespace(id=55),
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._restaurar_lotes_consumidos",
        lambda db, movimentacao: 1,
    )
    monkeypatch.setattr(
        "app.services.bling_nf_service._sincronizar_cache_estoque_virtual",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.kit_estoque_service.KitEstoqueService.recalcular_kits_que_usam_produto",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        "app.estoque.service.EstoqueService.estornar_estoque",
        lambda **kwargs: estornos.append(kwargs),
    )

    resultado = decidir_retorno_estoque(
        db,
        pedido=pedido,
        itens=[item],
        acao="retornar",
        motivo="Produto conferido sem avarias",
        user_id=77,
    )

    assert resultado["status"] == "retornado"
    assert len(estornos) == 1
    assert estornos[0]["produto_id"] == 6745
    assert movimento.status == "cancelado"
    assert item.vendido_em is None
    assert item.liberado_em is not None
    assert pedido.payload["retorno_estoque"]["decidido_por"] == 77


def test_decisao_nao_retornar_preserva_baixa(monkeypatch):
    movimento = SimpleNamespace(
        id=302,
        produto_id=6745,
        quantidade=1,
        status="confirmado",
        observacao="Baixa via NF",
        user_id=12,
    )
    pedido = _pedido(
        payload={
            "ultima_nf": {"id": "25432772133", "situacao": "Cancelada"},
            "retorno_estoque": {
                "nf_id": "25432772133",
                "status": "pendente",
            },
        }
    )
    item = SimpleNamespace(vendido_em="agora", liberado_em=None)
    db = FakeDB()
    _silenciar_monitor(monkeypatch)
    monkeypatch.setattr(
        "app.services.pedido_cancelamento_fiscal_estoque_service._movimentos_saida_ativos",
        lambda db, pedido: [movimento],
    )

    resultado = decidir_retorno_estoque(
        db,
        pedido=pedido,
        itens=[item],
        acao="nao_retornar",
        motivo="Produto rasgado e sem condicao de venda",
        user_id=77,
    )

    assert resultado["status"] == "nao_retornado"
    assert movimento.status == "confirmado"
    assert "produto nao retornou" in movimento.observacao.lower()
    assert item.vendido_em == "agora"
    assert pedido.payload["retorno_estoque"]["status"] == "nao_retornado"


def test_decisao_de_estoque_exige_motivo():
    pedido = _pedido(payload={"retorno_estoque": {"status": "pendente"}})

    with pytest.raises(ValueError, match="pelo menos 5 caracteres"):
        decidir_retorno_estoque(
            FakeDB(),
            pedido=pedido,
            itens=[],
            acao="nao_retornar",
            motivo="ruim",
            user_id=77,
        )
