from pathlib import Path

from app.services import bling_sync_service as facade
from app.services import bling_sync_shared as shared
from app.services.bling_sync_auto_link import BlingSyncAutoLinkMixin
from app.services.bling_sync_queue import BlingSyncQueueMixin
from app.services.bling_sync_reconciliation import BlingSyncReconciliationMixin
from app.services.bling_sync_reprocess import BlingSyncReprocessMixin


ROOT = Path(__file__).resolve().parents[2]


def test_bling_sync_service_preserva_imports_legados():
    assert facade.DIVERGENCIA_MINIMA is shared.DIVERGENCIA_MINIMA
    assert (
        facade._buscar_item_bling_para_produto is shared._buscar_item_bling_para_produto
    )
    assert facade._cooldown_rate_limit_segundos is shared._cooldown_rate_limit_segundos
    assert (
        facade.listar_tenants_com_produto_bling_sync_recentes
        is shared.listar_tenants_com_produto_bling_sync_recentes
    )


def test_bling_sync_service_compoe_fluxos_extraidos():
    service = facade.BlingSyncService

    assert (
        service.queue_product_sync.__func__
        is BlingSyncQueueMixin.queue_product_sync.__func__
    )
    assert (
        service.reprocess_failed_syncs.__func__
        is BlingSyncReprocessMixin.reprocess_failed_syncs.__func__
    )
    assert (
        service.reconcile_recent_products.__func__
        is BlingSyncReconciliationMixin.reconcile_recent_products.__func__
    )
    assert (
        service.auto_link_by_sku.__func__
        is BlingSyncAutoLinkMixin.auto_link_by_sku.__func__
    )


def test_bling_sync_service_refactor_mantem_arquivos_focados():
    limits = {
        "app/services/bling_sync_service.py": 100,
        "app/services/bling_sync_shared.py": 520,
        "app/services/bling_sync_queue.py": 650,
        "app/services/bling_sync_reprocess.py": 250,
        "app/services/bling_sync_reconciliation.py": 300,
        "app/services/bling_sync_auto_link.py": 220,
    }

    for relative_path, max_lines in limits.items():
        path = ROOT / relative_path
        assert sum(1 for _ in path.open(encoding="utf-8")) <= max_lines
