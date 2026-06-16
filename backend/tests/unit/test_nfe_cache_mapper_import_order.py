def test_nfe_cache_model_initializes_after_notas_entrada_routes_import():
    import app.notas_entrada_routes  # noqa: F401
    from app.nfe_cache_models import BlingNotaFiscalCache

    cache = BlingNotaFiscalCache(
        tenant_id="tenant-1",
        bling_id="25461868579",
        modelo=55,
        tipo="nfe",
        numero="011149",
    )

    assert cache.bling_id == "25461868579"
