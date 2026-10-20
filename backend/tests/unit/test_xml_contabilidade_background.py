"""Enfileirar XML não espera rede; o processamento lento não ocupa a API."""

from datetime import datetime, timezone
from threading import Event, get_ident
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
)
from apscheduler.executors.pool import ThreadPoolExecutor
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_user_and_tenant
from app.db import base as _registry, get_session  # noqa: F401
from app import xml_contabilidade_routes as routes
from app.schedulers.xml_contabilidade_scheduler import XmlContabilidadeScheduler
from app.security import permissions_decorator
from app.services import (
    email_service,
    xml_contabilidade_documentos,
    xml_contabilidade_eventos,
)
from app.services import xml_contabilidade_service as service
from app.tenancy.context import tenant_context
from app.xml_contabilidade_models import (
    XmlContabilidadeConfig,
    XmlContabilidadeEnvio,
    XmlContabilidadeTentativa,
)


@pytest.fixture
def api_local(tmp_path, monkeypatch):
    """Sessões distintas por requisição/thread, sem banco fixo ou app startup."""
    tenant = uuid4()
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'fila.sqlite').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    for model in (
        XmlContabilidadeConfig,
        XmlContabilidadeEnvio,
        XmlContabilidadeTentativa,
    ):
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with tenant_context(tenant), factory() as db:
        db.add(
            XmlContabilidadeConfig(
                tenant_id=tenant, email_contador="contador@example.com"
            )
        )
        db.commit()
    monkeypatch.setattr(
        service, "_agora", lambda: datetime(2026, 10, 19, 15, tzinfo=timezone.utc)
    )
    monkeypatch.setattr(permissions_decorator, "check_permission", Mock())
    monkeypatch.setattr(routes, "log_action", Mock())
    app = FastAPI()
    app.include_router(routes.router)

    @app.middleware("http")
    async def escopo_empresa(request, call_next):
        with tenant_context(tenant):
            return await call_next(request)

    @app.get("/probe-event-loop")
    async def probe_event_loop():
        return {"thread": get_ident()}

    def session_request():
        with factory() as db:
            yield db

    app.dependency_overrides[get_session] = session_request
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=7),
        tenant,
    )
    with TestClient(app) as client:
        yield client, tenant, factory
    engine.dispose()


def portas_externas_proibidas(monkeypatch):
    portas = []
    for obj, nome in (
        (service, "gerar_anexos_periodo"),
        (service, "gerar_zip_periodo"),
        (xml_contabilidade_documentos, "_obter_xml"),
        (xml_contabilidade_eventos, "obter_eventos_intnfe"),
        (email_service, "send_email"),
    ):
        porta = Mock(side_effect=AssertionError(f"A requisição não pode chamar {nome}"))
        monkeypatch.setattr(obj, nome, porta)
        portas.append(porta)
    return portas


def enfileirar(client):
    return client.post(
        "/contabilidade/xml/envios",
        json={"data_inicio": "2026-10-13", "data_fim": "2026-10-16"},
    )


def test_post_persiste_fila_e_responde_sem_preparar_xml_nem_usar_rede(
    api_local, monkeypatch
):
    client, _, _ = api_local
    portas = portas_externas_proibidas(monkeypatch)
    processar = Mock(side_effect=AssertionError("POST não executa worker"))
    monkeypatch.setattr(service, "_processar_envio", processar)
    inicio = perf_counter()
    response = enfileirar(client)
    duracao = perf_counter() - inicio
    assert response.status_code == 201
    assert duracao < 1.0
    criado = response.json()
    assert criado["status"] == "pendente"
    assert criado["tentativas"] == 0
    historico = client.get("/contabilidade/xml/envios")
    assert historico.status_code == 200
    assert historico.json()[0]["id"] == criado["id"]
    assert historico.json()[0]["status"] == "pendente"
    assert historico.json()[0]["tentativas"] == 0
    processar.assert_not_called()
    for porta in portas:
        porta.assert_not_called()


def test_worker_lento_roda_em_thread_sem_bloquear_historico_nem_sobrepor_ciclos(
    api_local, monkeypatch
):
    import app.db as db_module

    client, tenant, factory = api_local
    portas = portas_externas_proibidas(monkeypatch)
    response = enfileirar(client)
    assert response.status_code == 201
    envio_id = response.json()["id"]
    iniciou, liberar, terminou, segundo_recusado = Event(), Event(), Event(), Event()
    threads, erros, chamadas = [], [], []

    def rotina_lenta(session_factory):
        with tenant_context(tenant), session_factory() as db:
            chamadas.append(service.listar_envios(db, tenant)[0]["id"])
            threads.append(get_ident())
            iniciou.set()
            assert liberar.wait(5), "O teste deve liberar o job em finally"
        return 0

    def observar(evento):
        if evento.code == EVENT_JOB_MAX_INSTANCES:
            segundo_recusado.set()
        else:
            if evento.code == EVENT_JOB_ERROR:
                erros.append(type(evento.exception).__name__)
            terminou.set()

    monkeypatch.setattr(db_module, "SessionLocal", factory)
    monkeypatch.setattr(service, "executar_rotina_xml_contabilidade", rotina_lenta)
    scheduler = XmlContabilidadeScheduler()
    scheduler.scheduler.add_listener(
        observar, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MAX_INSTANCES
    )
    try:
        scheduler.start()
        assert isinstance(scheduler.scheduler._executors["default"], ThreadPoolExecutor)
        scheduler.scheduler.modify_job(
            "xml_contabilidade", next_run_time=datetime.now(timezone.utc)
        )
        assert iniciou.wait(2), "Job deveria iniciar no executor em background"
        assert not terminou.is_set()
        inicio = perf_counter()
        historico = client.get("/contabilidade/xml/envios")
        assert perf_counter() - inicio < 1.0
        assert historico.status_code == 200
        assert historico.json()[0]["id"] == envio_id
        assert client.get("/contabilidade/xml/config").status_code == 200
        event_loop_thread = client.get("/probe-event-loop").json()["thread"]
        assert event_loop_thread != threads[0]
        assert not terminou.is_set(), (
            "A API deve responder enquanto o job ainda aguarda"
        )
        scheduler.scheduler.modify_job(
            "xml_contabilidade", next_run_time=datetime.now(timezone.utc)
        )
        assert segundo_recusado.wait(2), (
            "Um ciclo lento não pode iniciar duas instâncias"
        )
        assert chamadas == [envio_id]
        assert scheduler.scheduler.get_job("xml_contabilidade").coalesce is True
    finally:
        liberar.set()
        if scheduler.scheduler.running:
            scheduler.scheduler.shutdown(wait=True)
    assert terminou.is_set()
    assert erros == []
    for porta in portas:
        porta.assert_not_called()
