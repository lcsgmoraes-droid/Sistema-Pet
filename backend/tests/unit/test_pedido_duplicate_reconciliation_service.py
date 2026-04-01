import app.services.pedido_duplicate_reconciliation_service as service


def test_reconciliar_duplicidades_recentes_retorna_sem_execucao_quando_nao_ha_grupos(monkeypatch):
    monkeypatch.setattr(service, "listar_grupos_duplicados_pedido_loja", lambda *args, **kwargs: [])

    resultado = service.reconciliar_duplicidades_recentes_pedido_loja(
        object(),
        "tenant-1",
        dias=7,
        limite_grupos=10,
    )

    assert resultado["executada"] is False
    assert resultado["motivo"] == "sem_duplicidades_recentes"
    assert resultado["grupos_mapeados"] == 0


def test_reconciliar_duplicidades_recentes_consolida_grupo_seguro(monkeypatch):
    monkeypatch.setattr(
        service,
        "listar_grupos_duplicados_pedido_loja",
        lambda *args, **kwargs: [
            {
                "numero_pedido_loja": "LOJA-1",
                "pedido_canonico": {"id": 10},
                "pedidos_seguro_ids": [11, 12],
                "pedidos_bloqueados_ids": [],
                "pode_consolidar_automaticamente": True,
                "requer_revisao_manual": False,
            }
        ],
    )
    chamadas = []

    def fake_consolidar(db, *, tenant_id, pedido_id, source, auto_fix_applied, resolution_note):
        chamadas.append(
            {
                "tenant_id": tenant_id,
                "pedido_id": pedido_id,
                "source": source,
                "auto_fix_applied": auto_fix_applied,
                "resolution_note": resolution_note,
            }
        )
        return {
            "success": True,
            "pedido_canonico_id": pedido_id,
            "pedido_canonico_bling_numero": "11700",
            "numero_pedido_loja": "LOJA-1",
            "pedidos_mesclados": [{"pedido_id": 11}, {"pedido_id": 12}],
            "pedidos_bloqueados_ids": [],
        }

    monkeypatch.setattr(service, "consolidar_duplicidades_seguras_pedido", fake_consolidar)

    resultado = service.reconciliar_duplicidades_recentes_pedido_loja(
        object(),
        "tenant-1",
        dias=7,
        limite_grupos=10,
    )

    assert resultado["executada"] is True
    assert resultado["grupos_mapeados"] == 1
    assert resultado["grupos_consolidados"] == 1
    assert resultado["pedidos_mesclados"] == 2
    assert chamadas == [
        {
            "tenant_id": "tenant-1",
            "pedido_id": 10,
            "source": "scheduler",
            "auto_fix_applied": True,
            "resolution_note": "Duplicidades seguras consolidadas automaticamente pelo scheduler.",
        }
    ]


def test_reconciliar_duplicidades_recentes_mantem_grupo_bloqueado_sem_consolidar(monkeypatch):
    monkeypatch.setattr(
        service,
        "listar_grupos_duplicados_pedido_loja",
        lambda *args, **kwargs: [
            {
                "numero_pedido_loja": "LOJA-2",
                "pedido_canonico": {"id": 20},
                "pedidos_seguro_ids": [],
                "pedidos_bloqueados_ids": [21],
                "pode_consolidar_automaticamente": False,
                "requer_revisao_manual": True,
            }
        ],
    )
    monkeypatch.setattr(
        service,
        "consolidar_duplicidades_seguras_pedido",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("nao deveria consolidar")),
    )

    resultado = service.reconciliar_duplicidades_recentes_pedido_loja(
        object(),
        "tenant-1",
        dias=7,
        limite_grupos=10,
    )

    assert resultado["executada"] is True
    assert resultado["grupos_mapeados"] == 1
    assert resultado["grupos_consolidados"] == 0
    assert resultado["grupos_com_revisao_manual"] == 1
    assert resultado["resultados"][0]["acao"] == "sem_mescla_segura"


def test_executar_reconciliacao_automatica_duplicidades_agrega_tenants(monkeypatch):
    monkeypatch.setattr(service, "listar_tenants_com_duplicidades_recentes", lambda *args, **kwargs: ["tenant-1", "tenant-2"])
    monkeypatch.setattr(
        service,
        "reconciliar_duplicidades_recentes_pedido_loja",
        lambda db, tenant_id, **kwargs: {
            "tenant_id": tenant_id,
            "grupos_mapeados": 2 if tenant_id == "tenant-1" else 1,
            "grupos_consolidados": 1,
            "pedidos_mesclados": 3 if tenant_id == "tenant-1" else 1,
            "erros": 0,
        },
    )

    resultado = service.executar_reconciliacao_automatica_duplicidades_pedidos(
        object(),
        dias=7,
        limite_grupos_por_tenant=10,
    )

    assert resultado["tenants_processados"] == 2
    assert resultado["tenants_com_duplicidades"] == 2
    assert resultado["grupos_mapeados_total"] == 3
    assert resultado["grupos_consolidados_total"] == 2
    assert resultado["pedidos_mesclados_total"] == 4
