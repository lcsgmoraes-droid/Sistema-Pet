from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    ROOT / "docs" / "marketing" / "base-demo" / "dados_base_demo_sistema_pet.json"
)
APPLIER_PATH = ROOT / "scripts" / "aplicar_seed_base_demo_marketing.py"
DEMO_TENANT_EMAIL = "demo.atacadaopetpp@sistemapet.local"
REAL_TENANT_EMAIL = "atacadaopetpp" + "@gmail.com"
MARKETING_DOCS = [
    ROOT / "docs" / "marketing" / "BASE_DEMO_GRAVACAO.md",
    ROOT / "docs" / "marketing" / "PACOTE_INICIAL_VIDEOS.md",
    ROOT / "docs" / "marketing" / "PLANO_CAPTURA_TELAS_DEMO.md",
]


class RecordingRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def upsert(self, action: dict) -> dict:
        self.calls.append(action)
        return {
            "section": action["section"],
            "operation": action["operation"],
            "items": action["items"],
            "status": "applied",
        }


class FakeUserField:
    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other: object) -> tuple[str, str, object]:  # type: ignore[override]
        return ("eq", self.name, other)


class FakeUserModel:
    email = FakeUserField("email")


class FakeUser:
    id = 44
    tenant_id = "tenant-123"
    email = DEMO_TENANT_EMAIL


class EmptyTenantUser:
    id = 45
    tenant_id = None
    email = "semtenant@example.com"


class FakeQuery:
    def __init__(self, user: object | None) -> None:
        self.user = user
        self.filters: list[object] = []

    def filter(self, *filters: object) -> "FakeQuery":
        self.filters.extend(filters)
        return self

    def first(self) -> object | None:
        return self.user


class FakeDb:
    def __init__(self, user: object | None) -> None:
        self.user = user
        self.queried_model: object | None = None

    def query(self, model: object) -> FakeQuery:
        self.queried_model = model
        return FakeQuery(self.user)


class FakeSeedRecord:
    def __init__(self, **kwargs: object) -> None:
        self.id: int | None = None
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeContaBancaria(FakeSeedRecord):
    pass


class FakeFormaPagamento(FakeSeedRecord):
    pass


class FakeCategoriaFinanceira(FakeSeedRecord):
    pass


class FakeCliente(FakeSeedRecord):
    pass


class FakePet(FakeSeedRecord):
    pass


class FakeCategoria(FakeSeedRecord):
    pass


class FakeProduto(FakeSeedRecord):
    pass


class FakeBanhoTosaServico(FakeSeedRecord):
    pass


class FakeSeedQuery:
    def __init__(self, session: "FakeSeedSession", model: type[FakeSeedRecord]) -> None:
        self.session = session
        self.model = model
        self.filters: dict[str, object] = {}

    def filter_by(self, **filters: object) -> "FakeSeedQuery":
        self.filters.update(filters)
        return self

    def filter(self, *filters: object) -> "FakeSeedQuery":
        return self

    def first(self) -> FakeSeedRecord | None:
        for record in self.session.records.get(self.model, []):
            if all(getattr(record, key, None) == value for key, value in self.filters.items()):
                return record
        return None


class FakeSeedSession:
    def __init__(self) -> None:
        self.records: dict[type[FakeSeedRecord], list[FakeSeedRecord]] = {}
        self._next_id = 1
        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.close_count = 0

    def query(self, model: type[FakeSeedRecord]) -> FakeSeedQuery:
        return FakeSeedQuery(self, model)

    def add(self, record: FakeSeedRecord) -> None:
        if getattr(record, "id", None) is None:
            record.id = self._next_id
            self._next_id += 1
        self.records.setdefault(type(record), []).append(record)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.close_count += 1


FAKE_SEED_MODELS = {
    "ContaBancaria": FakeContaBancaria,
    "FormaPagamento": FakeFormaPagamento,
    "CategoriaFinanceira": FakeCategoriaFinanceira,
    "Cliente": FakeCliente,
    "Pet": FakePet,
    "Categoria": FakeCategoria,
    "Produto": FakeProduto,
    "BanhoTosaServico": FakeBanhoTosaServico,
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    assert_true(APPLIER_PATH.exists(), "Aplicador de seed demo nao encontrado")

    sys.path.insert(0, str(ROOT / "scripts"))
    from aplicar_seed_base_demo_marketing import (
        apply_seed_plan,
        apply_seed_plan_for_tenant_email,
        assert_safe_seed_environment,
        resolve_tenant_context_by_email,
        SQLAlchemyDemoSeedRepository,
    )
    from gerar_seed_base_demo_marketing import build_seed_plan

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    plan = build_seed_plan(payload, tenant_slug="tenant_demo")

    for doc_path in MARKETING_DOCS:
        doc_content = doc_path.read_text(encoding="utf-8")
        assert_true(
            REAL_TENANT_EMAIL not in doc_content,
            f"{doc_path.name} nao deve apontar para tenant real ja usado",
        )

    dry_repo = RecordingRepository()
    dry_result = apply_seed_plan(
        plan,
        repository=dry_repo,
        dry_run=True,
        environment="development",
        tenant_email=DEMO_TENANT_EMAIL,
    )
    assert_true(dry_result["dry_run"] is True, "Dry-run deve ser explicito")
    assert_true(
        dry_result["tenant_email"] == DEMO_TENANT_EMAIL,
        "Dry-run deve registrar o email do tenant alvo",
    )
    assert_true(dry_result["total_actions"] == 14, "Dry-run deve cobrir manifesto")
    assert_true(dry_repo.calls == [], "Dry-run nao deve chamar repositorio")
    assert_true(
        all(item["status"] == "would_upsert" for item in dry_result["results"]),
        "Dry-run deve marcar acoes como simuladas",
    )

    apply_repo = RecordingRepository()
    apply_result = apply_seed_plan(
        plan,
        repository=apply_repo,
        dry_run=False,
        environment="development",
    )
    assert_true(apply_result["dry_run"] is False, "Apply deve registrar modo real")
    assert_true(len(apply_repo.calls) == 14, "Apply deve chamar repositorio")
    assert_true(
        [call["section"] for call in apply_repo.calls][:4]
        == [
            "empresa",
            "usuarios",
            "financeiro.bancos",
            "financeiro.formas_pagamento",
        ],
        "Apply deve preservar ordem operacional",
    )
    assert_true(
        all(item["status"] == "applied" for item in apply_result["results"]),
        "Apply deve devolver resultado do repositorio",
    )

    try:
        assert_safe_seed_environment("production", allow_production=False)
    except ValueError as exc:
        assert_true("producao" in str(exc).lower(), "Erro deve citar producao")
    else:
        raise AssertionError("Ambiente de producao deve ser bloqueado")

    cli_result = subprocess.run(
        [
            sys.executable,
            str(APPLIER_PATH),
            "--json",
            str(DATA_PATH),
            "--tenant-slug",
            "tenant_demo",
            "--tenant-email",
            DEMO_TENANT_EMAIL,
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(cli_result.returncode == 0, cli_result.stderr or cli_result.stdout)
    cli_payload = json.loads(cli_result.stdout)
    assert_true(cli_payload["dry_run"] is True, "CLI deve executar dry-run")
    assert_true(
        cli_payload["tenant_email"] == DEMO_TENANT_EMAIL,
        "CLI deve manter email do tenant alvo no resumo",
    )
    assert_true(cli_payload["total_actions"] == 14, "CLI deve resumir acoes")

    no_mode_result = subprocess.run(
        [
            sys.executable,
            str(APPLIER_PATH),
            "--json",
            str(DATA_PATH),
            "--tenant-slug",
            "tenant_demo",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(no_mode_result.returncode == 1, "CLI deve exigir modo de execucao")
    assert_true(
        "--dry-run" in no_mode_result.stderr and "--apply" in no_mode_result.stderr,
        "Erro deve orientar entre dry-run e apply",
    )

    missing_email_result = subprocess.run(
        [
            sys.executable,
            str(APPLIER_PATH),
            "--json",
            str(DATA_PATH),
            "--tenant-slug",
            "tenant_demo",
            "--apply",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(
        missing_email_result.returncode == 1,
        "Apply deve exigir email do tenant alvo",
    )
    assert_true(
        "--tenant-email" in missing_email_result.stderr,
        "Erro de apply deve orientar tenant-email",
    )

    production_apply_result = subprocess.run(
        [
            sys.executable,
            str(APPLIER_PATH),
            "--json",
            str(DATA_PATH),
            "--tenant-slug",
            "tenant_demo",
            "--tenant-email",
            DEMO_TENANT_EMAIL,
            "--environment",
            "production",
            "--apply",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert_true(
        production_apply_result.returncode == 1,
        "Apply deve continuar bloqueado em producao",
    )
    assert_true(
        "producao" in production_apply_result.stderr.lower(),
        "Erro de producao deve ser claro",
    )

    context = resolve_tenant_context_by_email(
        FakeDb(FakeUser()),
        " Demo.AtacadaoPetPP@SISTEMAPET.LOCAL ",
        user_model=FakeUserModel,
    )
    assert_true(
        context
        == {
            "tenant_email": DEMO_TENANT_EMAIL,
            "tenant_id": "tenant-123",
            "user_id": 44,
        },
        "Resolver deve devolver tenant, usuario e email normalizado",
    )

    try:
        resolve_tenant_context_by_email(
            FakeDb(None),
            DEMO_TENANT_EMAIL,
            user_model=FakeUserModel,
        )
    except ValueError as exc:
        assert_true("nao encontrado" in str(exc).lower(), "Erro deve citar ausencia")
    else:
        raise AssertionError("Resolver deve falhar quando email nao existe")

    try:
        resolve_tenant_context_by_email(
            FakeDb(EmptyTenantUser()),
            "semtenant@example.com",
            user_model=FakeUserModel,
        )
    except ValueError as exc:
        assert_true("tenant" in str(exc).lower(), "Erro deve citar tenant ausente")
    else:
        raise AssertionError("Resolver deve falhar quando usuario nao tem tenant")

    actions = {action["section"]: action for action in plan["actions"]}
    fake_seed_db = FakeSeedSession()
    repository = SQLAlchemyDemoSeedRepository(
        fake_seed_db,
        tenant_id="tenant-123",
        user_id=44,
        models=FAKE_SEED_MODELS,
    )

    for section in [
        "financeiro.bancos",
        "financeiro.formas_pagamento",
        "financeiro.categorias",
        "fornecedores",
        "clientes",
        "pets",
        "produtos",
        "servicos",
    ]:
        result = repository.upsert(actions[section])
        assert_true(result["status"] == "applied", f"{section} deve ser aplicado")

    repository.upsert(actions["financeiro.bancos"])
    assert_true(
        len(fake_seed_db.records[FakeContaBancaria]) == 1,
        "Bancos devem ser idempotentes por tenant e nome",
    )
    assert_true(
        fake_seed_db.records[FakeContaBancaria][0].tipo == "corrente",
        "Tipo de conta corrente deve ser normalizado",
    )
    assert_true(
        len(fake_seed_db.records[FakeFormaPagamento]) == 4,
        "Formas de pagamento demo devem ser criadas",
    )
    assert_true(
        fake_seed_db.records[FakeFormaPagamento][0].tipo == "pix",
        "PIX deve ser normalizado como tipo pix",
    )
    assert_true(
        len(fake_seed_db.records[FakeCliente]) == 4,
        "Fornecedor e clientes devem compartilhar cadastro de pessoas",
    )
    assert_true(
        len(fake_seed_db.records[FakePet]) == 3,
        "Pets demo devem ser vinculados aos tutores",
    )
    assert_true(
        len(fake_seed_db.records[FakeProduto]) == 4,
        "Produtos demo devem ser criados",
    )
    assert_true(
        fake_seed_db.records[FakeProduto][0].categoria_id
        == fake_seed_db.records[FakeCategoria][0].id,
        "Produto deve apontar para categoria criada",
    )
    assert_true(
        len(fake_seed_db.records[FakeBanhoTosaServico]) == 2,
        "Somente servicos de banho/tosa devem ser criados nesta fatia",
    )
    skipped_result = repository.upsert(actions["compras"])
    assert_true(
        skipped_result["status"] == "skipped",
        "Secoes ainda sem modelo seguro devem ser puladas",
    )

    apply_session = FakeSeedSession()
    apply_session.records[FakeUserModel] = [FakeUser()]  # type: ignore[dict-item]
    context_events: list[object] = []
    tenant_apply_result = apply_seed_plan_for_tenant_email(
        plan,
        tenant_email=" Demo.AtacadaoPetPP@SISTEMAPET.LOCAL ",
        session_factory=lambda: apply_session,
        environment="development",
        models=FAKE_SEED_MODELS,
        user_model=FakeUserModel,
        set_tenant_context=context_events.append,
        clear_tenant_context=lambda: context_events.append("clear"),
    )
    assert_true(
        tenant_apply_result["dry_run"] is False,
        "Aplicacao por tenant email deve sair do dry-run",
    )
    assert_true(
        tenant_apply_result["tenant_email"] == DEMO_TENANT_EMAIL,
        "Aplicacao deve normalizar o email alvo",
    )
    assert_true(
        tenant_apply_result["tenant_id"] == "tenant-123",
        "Aplicacao deve devolver tenant resolvido",
    )
    assert_true(apply_session.commit_count == 1, "Aplicacao deve commitar uma vez")
    assert_true(apply_session.rollback_count == 0, "Aplicacao verde nao deve rollback")
    assert_true(apply_session.close_count == 1, "Aplicacao deve fechar sessao")
    assert_true(
        context_events == ["tenant-123", "clear"],
        "Aplicacao deve ativar e limpar contexto do tenant",
    )
    assert_true(
        len(apply_session.records[FakeProduto]) == 4,
        "Aplicacao por tenant email deve usar repository SQLAlchemy",
    )

    print("Marketing demo seed apply contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
