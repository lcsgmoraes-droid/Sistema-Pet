"""
Contrato do seed de templates de adquirentes (Stone/Cielo/Rede).

Por que este teste existe
--------------------------
``backend/app/seed_adquirentes.py`` montava e consultava ``AdquirenteTemplate``
com campos inexistentes (``adquirente``, ``versao``, ``descricao``): a query
``filter(AdquirenteTemplate.adquirente == ...)`` levantava ``AttributeError`` e o
construtor ``AdquirenteTemplate(adquirente=..., versao=..., descricao=...)``
levantava ``TypeError``. O schema real expõe ``nome`` e ``tipo_arquivo``.

Além disso, ``AdquirenteTemplate`` é ``TenantScoped`` (entra no filtro global de
tenant com fail-fast). O endpoint ``POST /admin/seed/adquirentes`` precisa setar o
contexto de tenant — só ``get_current_user_and_tenant`` faz isso. Com
``get_current_user`` o SELECT do seed dispararia o fail-fast por falta de tenant.

Estes testes travam (ratchet) os dois contratos.
"""
import inspect
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")

from app import admin_routes
from app.auth.dependencies import get_current_user_and_tenant
from app.conciliacao_models import AdquirenteTemplate
from app.seed_adquirentes import criar_templates_adquirentes

ROOT = Path(__file__).resolve().parents[3]
TENANT_ID = "00000000-0000-0000-0000-000000000001"

# Campos que NÃO existem no modelo e não podem voltar ao seed.
CAMPOS_FANTASMA = ("adquirente", "versao", "descricao")


class _FakeQuery:
    def __init__(self, model):
        self.model = model

    def filter(self, *criteria):
        self.criteria = criteria
        return self

    def first(self):
        return None  # nenhum template pré-existente → cria todos


class _FakeDb:
    def __init__(self):
        self.added = []
        self.commits = 0

    def query(self, model):
        return _FakeQuery(model)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def test_seed_cria_templates_usando_schema_real_de_adquirente_template():
    db = _FakeDb()

    resultado = criar_templates_adquirentes(db, TENANT_ID)

    assert resultado["total_criados"] == 3
    assert sorted(resultado["adquirentes"]) == ["CIELO", "REDE", "STONE"]
    assert db.commits == 1
    assert len(db.added) == 3

    colunas = set(AdquirenteTemplate.__table__.columns.keys())
    # Sanidade: o modelo realmente não tem os campos fantasma.
    for campo in CAMPOS_FANTASMA:
        assert campo not in colunas

    for obj in db.added:
        assert isinstance(obj, AdquirenteTemplate)
        # 'adquirente' virou 'nome'; 'tipo_arquivo' é NOT NULL no schema real.
        assert obj.nome in {"STONE", "CIELO", "REDE"}
        assert obj.tipo_arquivo
        assert str(obj.tenant_id) == TENANT_ID
        # mapeamento de colunas continua presente (parser configurável).
        assert isinstance(obj.mapeamento, dict) and obj.mapeamento
        # nenhum campo inexistente foi setado no objeto.
        for campo in CAMPOS_FANTASMA:
            assert not hasattr(obj, campo)


def _seed_route_depends_on_selected_tenant() -> bool:
    sig = inspect.signature(admin_routes.seed_adquirentes_templates)
    return any(
        getattr(param.default, "dependency", None) is get_current_user_and_tenant
        for param in sig.parameters.values()
    )


def test_seed_endpoint_usa_tenant_selecionado_para_evitar_fail_fast():
    assert _seed_route_depends_on_selected_tenant(), (
        "POST /admin/seed/adquirentes deve depender de get_current_user_and_tenant "
        "para setar o contexto de tenant; senão o filtro ORM (fail-fast) bloqueia "
        "SELECTs nas tabelas TenantScoped da conciliação."
    )

    source = (ROOT / "backend" / "app" / "admin_routes.py").read_text(encoding="utf-8")
    # Substring exata: 'Depends(get_current_user)' NÃO casa com
    # 'Depends(get_current_user_and_tenant)' por causa do ')'.
    assert "Depends(get_current_user)" not in source
