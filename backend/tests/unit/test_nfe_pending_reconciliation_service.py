from datetime import datetime
from types import SimpleNamespace

import app.services.nfe_pending_reconciliation_service as service


def test_planejar_janela_reconciliacao_usa_datas_minima_e_maxima():
    registros = [
        SimpleNamespace(data_emissao=datetime(2026, 3, 30, 12, 0, 0)),
        SimpleNamespace(data_emissao=datetime(2026, 3, 28, 9, 30, 0)),
        SimpleNamespace(data_emissao=datetime(2026, 3, 29, 18, 45, 0)),
    ]

    data_inicial, data_final = service._planejar_janela_reconciliacao(registros)

    assert data_inicial == "2026-03-28"
    assert data_final == "2026-03-30"


def test_reconciliar_nfes_pendentes_recentes_retorna_sem_execucao_quando_nao_ha_registros(monkeypatch):
    monkeypatch.setattr(service, "_contar_nfes_pendentes_recentes", lambda *args, **kwargs: 0)
    monkeypatch.setattr(service, "_buscar_nfes_pendentes_recentes", lambda *args, **kwargs: [])

    resultado = service.reconciliar_nfes_pendentes_recentes(object(), "tenant-1", dias=3, limite_notas=50)

    assert resultado["executada"] is False
    assert resultado["motivo"] == "sem_nfs_pendentes_recentes"
    assert resultado["pendentes_antes"] == 0
    assert resultado["pendentes_depois"] == 0


def test_reconciliar_nfes_pendentes_recentes_executa_sync_incremental(monkeypatch):
    registros = [
        SimpleNamespace(data_emissao=datetime(2026, 3, 29, 14, 0, 0)),
        SimpleNamespace(data_emissao=datetime(2026, 3, 30, 10, 30, 0)),
    ]
    contagens = iter([5, 1])
    sync_args = {}

    monkeypatch.setattr(service, "_contar_nfes_pendentes_recentes", lambda *args, **kwargs: next(contagens))
    monkeypatch.setattr(service, "_buscar_nfes_pendentes_recentes", lambda *args, **kwargs: registros)

    def fake_sync(db, tenant_id, *, data_inicial, data_final):
        sync_args["tenant_id"] = tenant_id
        sync_args["data_inicial"] = data_inicial
        sync_args["data_final"] = data_final
        return True, [{"id": "1"}, {"id": "2"}]

    monkeypatch.setattr(service, "_executar_sync_incremental", fake_sync)

    resultado = service.reconciliar_nfes_pendentes_recentes(object(), "tenant-1", dias=3, limite_notas=50)

    assert resultado["executada"] is True
    assert resultado["bling_ok"] is True
    assert resultado["pendentes_antes"] == 5
    assert resultado["pendentes_depois"] == 1
    assert resultado["pendentes_atualizadas"] == 4
    assert resultado["notas_sincronizadas"] == 2
    assert sync_args == {
        "tenant_id": "tenant-1",
        "data_inicial": "2026-03-29",
        "data_final": "2026-03-30",
    }
