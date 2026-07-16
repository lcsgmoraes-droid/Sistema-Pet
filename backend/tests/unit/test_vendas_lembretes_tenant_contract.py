from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RECURRENCE_SERVICE = REPO_ROOT / "app" / "services" / "product_recurrence.py"
VENDAS_FINALIZACAO = REPO_ROOT / "app" / "vendas" / "finalizacao.py"
ECOMMERCE_WEBHOOK_SALES = REPO_ROOT / "app" / "routes" / "ecommerce_webhooks_sales.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_venda_recurrence_scopes_reminders_and_history_by_tenant():
    source = _source(RECURRENCE_SERVICE)

    assert "Lembrete.tenant_id == tenant_id" in source
    assert "Venda.tenant_id == tenant_id" in source
    assert "Produto.tenant_id == tenant_id" in source
    assert "Pet.tenant_id == tenant_id" in source
    assert "Lembrete.venda_id == venda.id" in source
    assert '"venda_ja_processada"' in source


def test_venda_recurrence_creates_reminder_with_explicit_tenant():
    source = _source(RECURRENCE_SERVICE)
    constructor = source.split("reminder = Lembrete(", 1)[1].split("\n        )", 1)[0]

    assert "tenant_id=tenant_id" in constructor
    assert "metodo_notificacao=\"app\"" in constructor


def test_all_sale_finalization_paths_delegate_to_recurrence_service_with_tenant():
    source = _source(VENDAS_FINALIZACAO)
    ecommerce_source = _source(ECOMMERCE_WEBHOOK_SALES)

    assert "process_finalized_sale_recurrence(" in source
    assert "tenant_id=tenant_id" in source
    assert "with db.begin_nested():" in source
    assert "process_finalized_sale_recurrence(" in ecommerce_source
    assert "tenant_id=pedido.tenant_id" in ecommerce_source
