from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
import inspect

import app.routes.acertos_routes as acertos_routes
import app.services.acerto_service as acerto_service
from app.services.acerto_service import EmailQueueService
from app.tenancy.context import clear_current_tenant, get_current_tenant, set_current_tenant


TENANT_A = UUID("11111111-1111-4111-8111-111111111111")
TENANT_B = UUID("22222222-2222-4222-8222-222222222222")
PREVIOUS_TENANT = UUID("99999999-9999-4999-8999-999999999999")


def teardown_function():
    clear_current_tenant()


class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)
        self.criteria = []
        self.limit_value = None

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def order_by(self, *criteria):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        if self.limit_value is None:
            return list(self.rows)
        return list(self.rows[: self.limit_value])

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, query):
        self.query_obj = query
        self.queried_entities = []
        self.commits = 0

    def query(self, *entities):
        self.queried_entities.append(entities)
        return self.query_obj

    def commit(self):
        self.commits += 1


def _fake_email(**overrides):
    base = {
        "id": 10,
        "tenant_id": TENANT_A,
        "destinatarios": "financeiro@example.com, copia@example.com",
        "assunto": "Acerto",
        "corpo_html": "<p>ok</p>",
        "corpo_texto": "ok",
        "status": "pendente",
        "tentativas": 0,
        "max_tentativas": 3,
        "data_enfileiramento": datetime.now() - timedelta(minutes=10),
        "data_envio": None,
        "proxima_tentativa": datetime.now() - timedelta(minutes=1),
        "ultimo_erro": None,
        "historico_erros": None,
        "observacoes": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _has_tenant_filter(query, tenant_id):
    for criterion in query.criteria:
        left_name = getattr(getattr(criterion, "left", None), "name", None)
        right_value = getattr(getattr(criterion, "right", None), "value", None)
        if left_name == "tenant_id" and str(right_value) == str(tenant_id):
            return True
    return False


def test_processar_fila_aplica_contexto_filtro_e_rls_do_tenant(monkeypatch):
    email = _fake_email()
    query = FakeQuery([email])
    db = FakeSession(query)
    sync_calls = []
    tenant_visto_no_envio = []

    monkeypatch.setattr(
        acerto_service,
        "sync_rls_tenant",
        lambda db_arg, tenant_id=None: sync_calls.append((db_arg, tenant_id)) or False,
        raising=False,
    )

    def fake_enviar_email(destinatarios, assunto, corpo_html, corpo_texto=None):
        tenant_visto_no_envio.append(get_current_tenant())
        return {"sucesso": True}

    monkeypatch.setattr(acerto_service.EmailService, "enviar_email", staticmethod(fake_enviar_email))

    set_current_tenant(PREVIOUS_TENANT)

    resultado = EmailQueueService.processar_fila(db, limite=5, tenant_id=TENANT_A)

    assert resultado == {"processados": 1, "enviados": 1, "erros": 0}
    assert email.status == "enviado"
    assert db.commits == 1
    assert tenant_visto_no_envio == [TENANT_A]
    assert sync_calls == [(db, TENANT_A)]
    assert _has_tenant_filter(query, TENANT_A)
    assert get_current_tenant() == PREVIOUS_TENANT


def test_reenviar_email_filtra_por_tenant_e_restaura_contexto(monkeypatch):
    email = _fake_email(id=77, status="erro", tentativas=2, ultimo_erro="smtp")
    query = FakeQuery([email])
    db = FakeSession(query)
    sync_calls = []

    monkeypatch.setattr(
        acerto_service,
        "sync_rls_tenant",
        lambda db_arg, tenant_id=None: sync_calls.append((db_arg, tenant_id)) or False,
        raising=False,
    )

    set_current_tenant(PREVIOUS_TENANT)

    resultado = EmailQueueService.reenviar_email(db, email_id=77, tenant_id=TENANT_A)

    assert resultado["sucesso"] is True
    assert email.status == "pendente"
    assert email.tentativas == 0
    assert email.ultimo_erro is None
    assert db.commits == 1
    assert sync_calls == [(db, TENANT_A)]
    assert _has_tenant_filter(query, TENANT_A)
    assert get_current_tenant() == PREVIOUS_TENANT


def test_processar_fila_global_processa_tenants_ativos_com_contexto(monkeypatch):
    tenant_query = FakeQuery([(str(TENANT_A),), (TENANT_B,)])
    db = FakeSession(tenant_query)
    chamadas = []

    def fake_processar_fila(db_arg, limite=10, tenant_id=None):
        chamadas.append((db_arg, limite, tenant_id, get_current_tenant()))
        processados = 2 if tenant_id == TENANT_A else 1
        return {"processados": processados, "enviados": processados, "erros": 0}

    monkeypatch.setattr(EmailQueueService, "processar_fila", staticmethod(fake_processar_fila))

    resultado = EmailQueueService.processar_fila_global(db, limite=3)

    assert resultado == {
        "processados": 3,
        "enviados": 3,
        "erros": 0,
        "tenants_processados": 2,
    }
    assert chamadas == [
        (db, 3, TENANT_A, TENANT_A),
        (db, 1, TENANT_B, TENANT_B),
    ]
    assert get_current_tenant() is None


def test_rotas_e_scheduler_usam_api_de_email_com_tenant_explicito():
    reenviar_source = inspect.getsource(acertos_routes.reenviar_email)
    manual_source = inspect.getsource(acertos_routes.processar_fila_manual)
    scheduler_source = Path("app/schedulers/acerto_scheduler.py").read_text(encoding="utf-8")

    assert "tenant_id=tenant_id" in reenviar_source
    assert "tenant_id=tenant_id" in manual_source
    assert "processar_fila_global" in scheduler_source


def test_scheduler_acertos_diarios_processa_parceiros_por_tenant():
    source = Path("app/schedulers/acerto_scheduler.py").read_text(encoding="utf-8")

    assert "db.query(Tenant.id)" in source
    assert "with tenant_context" in source
