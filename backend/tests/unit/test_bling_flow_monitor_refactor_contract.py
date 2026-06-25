from pathlib import Path

from app.services import bling_flow_monitor_autofix as autofix
from app.services import bling_flow_monitor_diagnostics as diagnostics
from app.services import bling_flow_monitor_service as service
from app.services import bling_flow_monitor_utils as utils


def test_bling_flow_monitor_service_preserva_reexports_legados():
    assert service._json_safe is utils._json_safe
    assert service._payload_with_correlation is utils._payload_with_correlation
    assert (
        service.normalizar_data_evento_monitor is utils.normalizar_data_evento_monitor
    )
    assert service._obter_nfs_recentes_bling is diagnostics._obter_nfs_recentes_bling
    assert service._nf_detectada_combina_com_pedido is (
        diagnostics._nf_detectada_combina_com_pedido
    )
    assert service.diagnosticar_pedido_integrado is (
        diagnostics.diagnosticar_pedido_integrado
    )
    assert service.autocorrigir_incidente is autofix.autocorrigir_incidente
    assert service._reconciliar_pedido_confirmado is (
        autofix._reconciliar_pedido_confirmado
    )


def test_bling_flow_monitor_service_fica_somente_com_orquestracao():
    source_path = Path(service.__file__)
    source = source_path.read_text(encoding="utf-8")

    assert "def diagnosticar_pedido_integrado(" not in source
    assert "def autocorrigir_incidente(" not in source
    assert "def _obter_nfs_recentes_bling(" not in source
    assert len(source.splitlines()) < 900
    assert (
        len(Path(diagnostics.__file__).read_text(encoding="utf-8").splitlines()) < 850
    )
    assert len(Path(autofix.__file__).read_text(encoding="utf-8").splitlines()) < 500
