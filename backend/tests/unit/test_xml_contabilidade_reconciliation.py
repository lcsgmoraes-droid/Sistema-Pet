from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.services import xml_contabilidade_reconciliation as service


TENANT = "11111111-1111-1111-1111-111111111111"


def _db(vendas):
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = vendas
    return SimpleNamespace(query=Mock(return_value=query), rollback=Mock()), query


def test_consulta_so_emissoes_novas_producao_empresa_e_limita_ciclo(monkeypatch):
    db, query = _db([])
    api = Mock()
    monkeypatch.setattr(service, "IntNFeClient", api)

    assert service.reconciliar_pendentes(db, TENANT, datetime(2026, 10, 19, 15, tzinfo=timezone.utc)) == 0

    conditions = [str(cond.compile(compile_kwargs={"literal_binds": True})) for cond in query.filter.call_args.args]
    assert any("11111111" in value and "tenant_id" in value for value in conditions)
    assert "vendas.nfe_provider = 'intnfe'" in conditions
    assert "vendas.nfe_ambiente = 1" in conditions
    assert any("nfe_correlation_id IS NOT NULL" in value for value in conditions)
    assert any("2026-10-19 12:00:00" in value and "nfe_data_emissao" in value for value in conditions)
    query.limit.assert_called_once_with(10)
    api.assert_not_called()


def test_confirma_sem_tela_aberta_e_erro_de_uma_nota_nao_bloqueia_outras(monkeypatch):
    vendas = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    db, _ = _db(vendas)
    api = Mock()
    connection = object()
    monkeypatch.setattr(service, "IntNFeClient", lambda: api)
    monkeypatch.setattr(service, "_connection", Mock(return_value=connection))
    monkeypatch.setattr(service, "_access_token", Mock(return_value="test-token"))
    reconcile = Mock(side_effect=[RuntimeError("erro interno"), {"success": True}])
    monkeypatch.setattr(service, "reconcile", reconcile)

    assert service.reconciliar_pendentes(db, TENANT, datetime(2026, 10, 19, tzinfo=timezone.utc)) == 1

    assert reconcile.call_count == 2
    assert reconcile.call_args.args[1] is vendas[1]
    assert reconcile.call_args.kwargs == {"connection": connection, "token": "test-token"}
    db.rollback.assert_called_once()
    api.close.assert_called_once()


def test_credencial_falha_fecha_cliente_e_libera_fila(monkeypatch):
    db, _ = _db([SimpleNamespace(id=1)])
    api = Mock()
    monkeypatch.setattr(service, "IntNFeClient", lambda: api)
    monkeypatch.setattr(service, "_connection", Mock(side_effect=RuntimeError("sem credencial")))

    assert service.reconciliar_pendentes(db, TENANT, datetime(2026, 10, 19, tzinfo=timezone.utc)) == 0
    db.rollback.assert_called_once()
    api.close.assert_called_once()


def test_sem_ativacao_nao_consulta_historico():
    db, _ = _db([])

    assert service.reconciliar_pendentes(db, TENANT, None) == 0

    db.query.assert_not_called()
