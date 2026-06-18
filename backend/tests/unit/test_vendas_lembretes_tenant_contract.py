from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VENDAS_ROUTES = REPO_ROOT / "app" / "vendas_routes.py"


def _recurrence_block() -> str:
    source = VENDAS_ROUTES.read_text(encoding="utf-8")
    start = source.index("SISTEMA DE RECORR")
    end = source.index("db.commit()", start)
    return source[start:end]


def test_venda_recurrence_query_scopes_existing_reminder_by_tenant():
    block = _recurrence_block()
    query_start = block.index("lembrete_existente =")
    query_end = block.index("if lembrete_existente:", query_start)
    query_block = block[query_start:query_end]

    assert "Lembrete.tenant_id == tenant_id" in query_block


def test_venda_recurrence_creates_new_reminders_with_explicit_tenant():
    block = _recurrence_block()
    creation_blocks = block.split("novo_lembrete = Lembrete(")[1:]

    assert len(creation_blocks) == 2
    for creation_block in creation_blocks:
        constructor_body = creation_block.split(")", 1)[0]
        assert "tenant_id=tenant_id" in constructor_body
