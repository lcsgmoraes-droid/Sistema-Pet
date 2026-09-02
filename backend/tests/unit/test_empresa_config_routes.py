import os
from types import SimpleNamespace
from uuid import uuid4

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.empresa_config_routes import _serializar_config, get_config_empresa
from app.empresa_routes import ConfigEstoqueUpdate, atualizar_config_estoque


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _FakeSession:
    def query(self, *args, **kwargs):
        return _FakeQuery()


def test_get_config_empresa_usa_tenant_da_dependencia_multitenant(monkeypatch):
    user = SimpleNamespace(id=1, email="smoke@teste.local")
    tenant_id = uuid4()
    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission",
        lambda *args, **kwargs: True,
    )

    response = get_config_empresa(
        user_and_tenant=(user, tenant_id),
        db=_FakeSession(),
    )

    assert response.id == 0
    assert response.margem_saudavel_minima == 30.0


class _FakeTenantQuery:
    def __init__(self, tenant):
        self.tenant = tenant

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.tenant


class _FakeTenantSession:
    def __init__(self, tenant):
        self.tenant = tenant
        self.commits = 0
        self.refreshed = []

    def query(self, *args, **kwargs):
        return _FakeTenantQuery(self.tenant)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


def _tenant_config_estoque(**overrides):
    defaults = {
        "id": "tenant-1",
        "name": "Loja Teste",
        "permite_estoque_negativo": False,
        "protecao_validade_ativa": False,
        "dias_alerta_validade": 15,
        "bloquear_validade_pdv": True,
        "bloquear_validade_ecommerce": True,
        "bloquear_validade_integracoes_online": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_atualizar_config_estoque_processa_validade_ao_ativar(monkeypatch):
    tenant = _tenant_config_estoque(protecao_validade_ativa=False)
    db = _FakeTenantSession(tenant)
    chamadas = []

    class FakeValidadeService:
        @staticmethod
        def processar_lotes_em_risco(**kwargs):
            chamadas.append(kwargs)
            return {"processados": 2, "bloqueios": []}

    monkeypatch.setattr(
        "app.security.permissions_decorator.check_permission",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "app.empresa_routes.EstoqueValidadeService",
        FakeValidadeService,
        raising=False,
    )

    response = atualizar_config_estoque(
        ConfigEstoqueUpdate(
            permite_estoque_negativo=False,
            protecao_validade_ativa=True,
            dias_alerta_validade=15,
            bloquear_validade_pdv=True,
            bloquear_validade_ecommerce=True,
            bloquear_validade_integracoes_online=False,
        ),
        user_and_tenant=(SimpleNamespace(id=42), tenant.id),
        db=db,
    )

    assert response.protecao_validade_ativa is True
    assert tenant.protecao_validade_ativa is True
    assert chamadas
    assert chamadas[0]["tenant"] is tenant
    assert chamadas[0]["user_id"] == 42
    assert chamadas[0]["origem"] == "configuracao"


def test_serializar_config_antiga_aplica_defaults_sem_apagar_crediario():
    config = SimpleNamespace(
        id=10,
        razao_social=None,
        nome_fantasia=None,
        cnpj=None,
        margem_saudavel_minima=None,
        margem_alerta_minima=None,
        mensagem_venda_saudavel=None,
        mensagem_venda_alerta=None,
        mensagem_venda_critica=None,
        aliquota_imposto_padrao=None,
        dias_tolerancia_atraso=5,
        crediario_encargos_automaticos=True,
        crediario_multa_percentual=2,
        crediario_juros_mensal_percentual=1,
        meta_faturamento_mensal=None,
        alerta_estoque_percentual=None,
        dias_produto_parado=None,
    )

    resposta = _serializar_config(config)

    assert resposta.mensagem_venda_saudavel
    assert resposta.mensagem_venda_alerta
    assert resposta.mensagem_venda_critica
    assert resposta.crediario_encargos_automaticos is True
    assert resposta.crediario_multa_percentual == 2
    assert resposta.crediario_juros_mensal_percentual == 1
