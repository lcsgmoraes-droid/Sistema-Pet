import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.produtos import estado_routes
from app.produtos.schemas import ProdutoAtivoUpdate
from app.produto_identity_models import ProdutoSkuAlias


def test_liberar_sku_remove_identidades_iguais_e_preserva_produto(monkeypatch):
    produto = SimpleNamespace(
        id=87975,
        codigo="2040",
        codigo_barras="2040",
        codigos_barras_alternativos=json.dumps(["2040", "EAN-DIFERENTE"]),
        updated_at=None,
    )
    db = Mock()
    aliases = db.query.return_value.filter.return_value
    aliases.delete.return_value = 1
    validar = Mock()
    registrar = Mock()
    monkeypatch.setattr(estado_routes, "_validar_sku_unico", validar)
    monkeypatch.setattr(estado_routes, "log_action", registrar)

    liberado = estado_routes._liberar_sku_produto(db, produto, "tenant-1", 7)

    assert liberado == "2040"
    assert produto.codigo.startswith("__LIBERADO__87975__")
    assert produto.codigo_barras is None
    assert json.loads(produto.codigos_barras_alternativos) == ["EAN-DIFERENTE"]
    assert db.query.call_args.args[0] is ProdutoSkuAlias
    aliases.delete.assert_called_once_with(synchronize_session=False)
    validar.assert_called_once()
    assert registrar.call_args.kwargs["old_value"] == {"codigo": "2040"}
    assert registrar.call_args.kwargs["commit"] is False


def test_liberar_sku_ja_liberado_nao_cria_novo_codigo(monkeypatch):
    produto = SimpleNamespace(id=3, codigo="__LIBERADO__3__abc")
    db = Mock()
    registrar = Mock()
    monkeypatch.setattr(estado_routes, "log_action", registrar)

    assert estado_routes._liberar_sku_produto(db, produto, "tenant-1", 7) is None
    registrar.assert_not_called()
    db.query.assert_not_called()


def test_payload_de_status_aceita_liberar_sku_opcional():
    assert ProdutoAtivoUpdate(ativo=False).liberar_sku is False
    assert ProdutoAtivoUpdate(ativo=False, liberar_sku=True).liberar_sku is True
