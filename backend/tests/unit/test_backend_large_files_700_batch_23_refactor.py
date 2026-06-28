from pathlib import Path

from app.services import bling_flow_monitor_diagnostics as facade
from app.services.bling_flow_monitor_diagnostics_parts import (
    context,
    incident_builder,
    inventory,
    pedido_diagnostics,
    recent_nfs,
)
from app.services import bling_flow_monitor_utils as utils


def test_bling_flow_monitor_diagnostics_preserva_reexports_legados():
    assert facade.NF_AUTHORIZED_CODES is context.NF_AUTHORIZED_CODES
    assert facade._ultima_nf is context._ultima_nf
    assert facade._nf_autorizada is context._nf_autorizada
    assert facade._nf_contexto_autorizado is context._nf_contexto_autorizado
    assert facade._numero_pedido_loja_pedido is context._numero_pedido_loja_pedido
    assert facade._loja_id_pedido_integrado is context._loja_id_pedido_integrado
    assert facade._loja_id_nf_contexto is context._loja_id_nf_contexto
    assert facade._canal_pedido_integrado is context._canal_pedido_integrado
    assert facade._pedido_total is context._pedido_total

    assert facade._obter_nfs_recentes_bling is recent_nfs._obter_nfs_recentes_bling
    assert (
        facade._indexar_nfs_por_pedido_loja is recent_nfs._indexar_nfs_por_pedido_loja
    )
    assert (
        facade._nf_detectada_combina_com_pedido
        is recent_nfs._nf_detectada_combina_com_pedido
    )
    assert facade._nf_recentes_cache is recent_nfs._nf_recentes_cache

    assert facade._produto_por_sku is inventory._produto_por_sku
    assert (
        facade._contar_movimentacoes_saida_nf
        is inventory._contar_movimentacoes_saida_nf
    )
    assert facade._make_incident is incident_builder._make_incident
    assert (
        facade.diagnosticar_pedido_integrado
        is pedido_diagnostics.diagnosticar_pedido_integrado
    )

    assert facade._coerce_int is utils._coerce_int
    assert facade._dict is utils._dict
    assert facade._json_safe is utils._json_safe
    assert facade._nf_bling_id_valido is utils._nf_bling_id_valido
    assert facade._primeiro_preenchido is utils._primeiro_preenchido
    assert facade._text is utils._text
    assert facade._utcnow is utils._utcnow


def test_bling_flow_monitor_diagnostics_fachada_e_modulos_abaixo_de_700_linhas():
    files = [
        Path(facade.__file__),
        Path(context.__file__),
        Path(recent_nfs.__file__),
        Path(inventory.__file__),
        Path(incident_builder.__file__),
        Path(pedido_diagnostics.__file__),
    ]

    for path in files:
        assert len(path.read_text(encoding="utf-8").splitlines()) < 700

    facade_source = Path(facade.__file__).read_text(encoding="utf-8")
    assert "def diagnosticar_pedido_integrado(" not in facade_source
    assert "def _obter_nfs_recentes_bling(" not in facade_source
    assert "def _make_incident(" not in facade_source
    assert "bling_flow_monitor_diagnostics_parts" in facade_source
