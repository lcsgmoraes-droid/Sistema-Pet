from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.catalogo_mestre_models import (
    CatalogoMestreEnriquecimentoExecucao,
    CatalogoMestrePendencia,
    CatalogoMestreProduto,
)
from app.db import Base
from app.services.catalogo_mestre_enrichment_provider import (
    CatalogDescriptionDraft,
    CatalogDescriptionResult,
    OpenAICatalogDescriptionProvider,
)
from app.services.catalogo_mestre_enrichment_worker import (
    CatalogEnrichmentConfig,
    CatalogMasterEnrichmentWorker,
)


NOW = datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc)


class FakeProvider:
    provider_name = "openai"
    model = "modelo-teste"
    prompt_version = "prompt-teste-v1"

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[dict] = []

    def generate(self, product_context: dict) -> CatalogDescriptionResult:
        self.calls.append(product_context)
        if self.error:
            raise self.error
        draft = CatalogDescriptionDraft(
            descricao_completa=(
                "Racao da marca informada para identificacao no catalogo pet, "
                "apresentada conforme os dados disponiveis no cadastro de origem "
                "e sem alegacoes adicionais nao verificadas."
            ),
            tags=["Racao", "Caes adultos", "racao"],
            confianca="media",
            alertas_revisao=["Composicao nao fornecida; revisar rotulo oficial."],
        )
        return CatalogDescriptionResult(
            draft=draft,
            provider=self.provider_name,
            model=self.model,
            prompt_version=self.prompt_version,
        )


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            CatalogoMestreProduto.__table__,
            CatalogoMestrePendencia.__table__,
            CatalogoMestreEnriquecimentoExecucao.__table__,
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def add_pending_product(
    session_factory,
    *,
    product_type: str = "racao",
    description: str | None = None,
    task_status: str = "pendente",
    lease_expiry: datetime | None = None,
) -> tuple[int, int]:
    with session_factory() as db:
        product = CatalogoMestreProduto(
            status="em_curadoria",
            ativo=True,
            fonte_primaria="tenant_produto",
            origem_tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            origem_produto_id=10,
            codigo_origem="TESTE-10",
            nome="Racao Teste Adultos 10 kg",
            tipo_catalogo=product_type,
            gtin_status="ausente",
            marca="Marca Teste",
            categoria="Racoes",
            departamento="Alimentos",
            descricao_curta="Produto para caes adultos.",
            descricao_completa=description,
            tags=["adultos"],
            unidade="UN",
            imagem_quantidade=0,
            imagem_meta_quantidade=5,
            imagem_faltantes=5,
            qualidade_percentual=0,
            lacunas=["descricao_completa", "imagens"],
            proveniencia={"fonte_primaria": {}, "campos": {}},
            snapshot_origem={},
            snapshot_origem_hash="0" * 64,
            ultima_sincronizacao_em=NOW,
        )
        db.add(product)
        db.flush()
        task = CatalogoMestrePendencia(
            produto_id=product.id,
            tipo="descricao_completa",
            posicao_alvo=0,
            status=task_status,
            prioridade=50,
            tentativas=0,
            reservada_por="worker-antigo" if lease_expiry else None,
            reserva_expira_em=lease_expiry,
        )
        db.add(task)
        db.commit()
        return int(product.id), int(task.id)


def make_worker(session_factory, provider, **config_overrides):
    config_values = {
        "enabled": True,
        "apply_enabled": True,
        "batch_size": 1,
        "daily_limit": 25,
        "max_attempts": 5,
        "lease_seconds": 900,
    }
    config_values.update(config_overrides)
    return CatalogMasterEnrichmentWorker(
        session_factory=session_factory,
        provider=provider,
        config=CatalogEnrichmentConfig(**config_values),
        worker_id="worker-teste",
        now_factory=lambda: NOW,
    )


def test_worker_creates_reviewable_draft_with_provenance(session_factory):
    product_id, task_id = add_pending_product(session_factory)
    provider = FakeProvider()

    stats = make_worker(session_factory, provider).run_batch()

    assert stats.succeeded == 1
    assert stats.claimed == 1
    assert len(provider.calls) == 1
    assert "origem_tenant_id" not in provider.calls[0]
    assert "origem_produto_id" not in provider.calls[0]

    with session_factory() as db:
        product = db.get(CatalogoMestreProduto, product_id)
        task = db.get(CatalogoMestrePendencia, task_id)
        execution = db.scalar(select(CatalogoMestreEnriquecimentoExecucao))

        assert product.descricao_completa.startswith("Racao da marca")
        assert product.tags == ["adultos", "racao", "caes adultos"]
        owner = product.proveniencia["campos"]["descricao_completa"]
        assert owner["tipo"] == "openai_rascunho"
        assert owner["status_revisao"] == "pendente"
        assert owner["modelo"] == "modelo-teste"
        assert task.status == "aguardando_revisao"
        assert task.reservada_por is None
        assert task.tentativas == 1
        assert execution.status == "rascunho_gerado"


@pytest.mark.parametrize("product_type", ["medicamento", "outro"])
def test_worker_never_generates_medication_or_generic_descriptions(
    session_factory, product_type
):
    _product_id, task_id = add_pending_product(
        session_factory, product_type=product_type
    )
    provider = FakeProvider()

    stats = make_worker(session_factory, provider).run_batch()

    assert stats.claimed == 0
    assert not provider.calls
    with session_factory() as db:
        assert db.get(CatalogoMestrePendencia, task_id).status == "pendente"


def test_worker_does_not_overwrite_existing_description(session_factory):
    product_id, task_id = add_pending_product(
        session_factory, description="Descricao humana ja revisada."
    )
    provider = FakeProvider()

    stats = make_worker(session_factory, provider).run_batch()

    assert stats.claimed == 0
    assert not provider.calls
    with session_factory() as db:
        assert (
            db.get(CatalogoMestreProduto, product_id).descricao_completa
            == "Descricao humana ja revisada."
        )
        assert db.get(CatalogoMestrePendencia, task_id).status == "pendente"


def test_worker_retries_with_backoff_and_stops_at_limit(session_factory):
    _product_id, task_id = add_pending_product(session_factory)
    provider = FakeProvider(error=RuntimeError("falha simulada"))

    stats = make_worker(session_factory, provider, max_attempts=1).run_batch()

    assert stats.failed == 1
    with session_factory() as db:
        task = db.get(CatalogoMestrePendencia, task_id)
        execution = db.scalar(select(CatalogoMestreEnriquecimentoExecucao))
        assert task.status == "falha_permanente"
        assert task.tentativas == 1
        assert task.reservada_por is None
        assert task.proxima_tentativa_em is None
        assert "RuntimeError" in task.ultimo_erro
        assert execution.status == "falha"


def test_worker_reclaims_expired_lease(session_factory):
    _product_id, task_id = add_pending_product(
        session_factory,
        task_status="processando",
        lease_expiry=NOW - timedelta(minutes=1),
    )

    stats = make_worker(session_factory, FakeProvider()).run_batch()

    assert stats.succeeded == 1
    with session_factory() as db:
        assert db.get(CatalogoMestrePendencia, task_id).status == "aguardando_revisao"


def test_worker_respects_persistent_daily_limit(session_factory):
    add_pending_product(session_factory)
    with session_factory() as db:
        db.add(
            CatalogoMestreEnriquecimentoExecucao(
                tipo="descricao_completa",
                provedor="openai",
                modelo="modelo-teste",
                versao_prompt="prompt-teste-v1",
                worker_id="worker-anterior",
                status="rascunho_gerado",
                iniciada_em=NOW - timedelta(hours=1),
            )
        )
        db.commit()
    provider = FakeProvider()

    stats = make_worker(session_factory, provider, daily_limit=1).run_batch()

    assert stats.reason == "limite_diario_atingido"
    assert stats.claimed == 0
    assert not provider.calls


def test_double_activation_guard_prevents_writes(session_factory):
    _product_id, task_id = add_pending_product(session_factory)
    provider = FakeProvider()
    worker = make_worker(session_factory, provider, apply_enabled=False)

    stats = worker.run_batch()

    assert stats.reason == "gravacao_desativada"
    assert not provider.calls
    with session_factory() as db:
        assert db.get(CatalogoMestrePendencia, task_id).status == "pendente"


def test_worker_source_has_no_operational_product_write_statements():
    source = (
        Path(__file__).resolve().parents[2]
        / "app/services/catalogo_mestre_enrichment_worker.py"
    ).read_text(encoding="utf-8")
    lowered = source.casefold()

    for forbidden in (
        "update produtos",
        "insert into produtos",
        "delete from produtos",
        "produto_imagens",
        "produto_config_fiscal",
    ):
        assert forbidden not in lowered


def test_openai_provider_uses_structured_output_without_storage():
    expected_draft = CatalogDescriptionDraft(
        descricao_completa=(
            "Descricao objetiva baseada somente nos fatos fornecidos no contexto "
            "do produto, mantida como rascunho para posterior revisao humana."
        ),
        tags=["produto pet"],
        confianca="baixa",
        alertas_revisao=["Revisar dados oficiais."],
    )

    class FakeResponses:
        def __init__(self):
            self.kwargs = None

        def parse(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(output_parsed=expected_draft)

    responses = FakeResponses()
    provider = OpenAICatalogDescriptionProvider.__new__(
        OpenAICatalogDescriptionProvider
    )
    provider.model = "modelo-teste"
    provider._client = SimpleNamespace(responses=responses)

    result = provider.generate({"nome": "Produto Teste"})

    assert result.draft is expected_draft
    assert responses.kwargs["text_format"] is CatalogDescriptionDraft
    assert responses.kwargs["store"] is False
    assert responses.kwargs["model"] == "modelo-teste"
    assert responses.kwargs["reasoning"] == {"effort": "low"}
