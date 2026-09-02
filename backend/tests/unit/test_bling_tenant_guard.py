from uuid import UUID, uuid4

from app.nfe.listagem_sync import _sincronizar_cache_nfes_com_bling
from app.services.bling_tenant_guard import (
    bling_tenant_id_configurado,
    resolver_tenant_bling,
    tenant_pode_usar_bling_global,
)
from app.tenancy.context import clear_current_tenant


def test_bling_global_so_pode_ser_usado_pelo_tenant_configurado(monkeypatch):
    tenant_bling = str(uuid4())
    outro_tenant = str(uuid4())
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", tenant_bling)

    assert bling_tenant_id_configurado() == tenant_bling
    assert tenant_pode_usar_bling_global(tenant_bling) is True
    assert tenant_pode_usar_bling_global(outro_tenant) is False


def test_sincronizacao_de_nfe_bloqueia_tenant_sem_credencial(monkeypatch):
    tenant_bling = str(uuid4())
    outro_tenant = str(uuid4())
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", tenant_bling)

    def falhar_se_instanciar_bling():
        raise AssertionError("BlingAPI nao deveria ser instanciada")

    monkeypatch.setattr(
        "app.nfe.listagem_sync.BlingAPI",
        falhar_se_instanciar_bling,
    )

    assert _sincronizar_cache_nfes_com_bling(object(), outro_tenant) == (False, [])


def test_configuracao_invalida_nega_acesso(monkeypatch):
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", "tenant-invalido")

    assert bling_tenant_id_configurado() is None
    assert tenant_pode_usar_bling_global(str(uuid4())) is False


def test_company_id_desconhecido_nao_cai_no_tenant_legado(monkeypatch):
    legacy_tenant = str(uuid4())
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", legacy_tenant)
    monkeypatch.setattr(
        "app.services.bling_connection_service.resolve_bling_webhook_tenant",
        lambda *_args, **_kwargs: None,
    )
    clear_current_tenant()

    assert resolver_tenant_bling({"companyId": "empresa-desconhecida"}) is None
    assert resolver_tenant_bling({}) == UUID(legacy_tenant)
