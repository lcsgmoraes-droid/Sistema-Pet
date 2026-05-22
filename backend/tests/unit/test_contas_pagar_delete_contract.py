from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_contas_pagar_tem_endpoint_delete_seguro_por_tenant():
    source = _source("app/contas_pagar_routes.py")

    assert '@router.delete("/{conta_id}")' in source

    delete_endpoint = source.split('@router.delete("/{conta_id}")', 1)[1].split(
        "def buscar_conta_pagar",
        1,
    )[0]

    assert "ContaPagar.tenant_id == tenant_id" in delete_endpoint
    assert "valor_pago" in delete_endpoint
    assert "status_code=400" in delete_endpoint
    assert "db.delete(conta)" in delete_endpoint
