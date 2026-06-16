from types import SimpleNamespace
from uuid import UUID

from app.services import produto_merge_service
from app.utils.tenant_safe_sql import TENANT_FILTER_MARKER, TENANT_SCOPED_TABLES


TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")


class _FakeDB:
    def execute(self, *args, **kwargs):
        raise AssertionError("duplicatas_ignoradas deve usar execute_tenant_safe")

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, _obj):
        pass


def _produto(produto_id: int, codigo: str):
    return SimpleNamespace(
        id=produto_id,
        codigo=codigo,
        estoque_atual=0,
        estoque_fisico=0,
        estoque_ecommerce=0,
        informacoes_adicionais_nf="",
        ativo=True,
        situacao=True,
        deleted_at=None,
        data_descontinuacao=None,
        produto_predecessor_id=None,
        motivo_descontinuacao=None,
        updated_at=None,
        nome=f"Produto {produto_id}",
        preco_venda=0,
        preco_custo=0,
    )


def test_fusao_produtos_remove_duplicatas_ignoradas_com_sql_tenant_safe(monkeypatch):
    principal = _produto(10, "SKU-10")
    duplicado = _produto(20, "SKU-20")
    chamadas = []

    monkeypatch.setattr(
        produto_merge_service,
        "_obter_produtos",
        lambda db, tenant_id, principal_id, duplicado_id: (principal, duplicado),
    )
    monkeypatch.setattr(produto_merge_service, "_mesclar_fornecedores", lambda *args: 0)
    monkeypatch.setattr(produto_merge_service, "_mesclar_listas_preco", lambda *args: 0)
    monkeypatch.setattr(produto_merge_service, "_mesclar_bling_sync", lambda *args: 0)
    monkeypatch.setattr(
        produto_merge_service, "_mesclar_config_fiscal", lambda *args: 0
    )
    monkeypatch.setattr(
        produto_merge_service, "_mesclar_componentes_kit", lambda *args: 0
    )
    monkeypatch.setattr(
        produto_merge_service, "_mesclar_vinculos_granel", lambda *args: 0
    )
    monkeypatch.setattr(
        produto_merge_service,
        "_transferir_referencias_genericas",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        produto_merge_service, "_gerar_codigo_merged_unico", lambda *args: "MERGED-20"
    )

    def fake_execute_tenant_safe(db, sql, params, *, tenant_id):
        chamadas.append((sql, params, tenant_id))
        return SimpleNamespace(rowcount=1)

    monkeypatch.setattr(
        produto_merge_service,
        "execute_tenant_safe",
        fake_execute_tenant_safe,
        raising=False,
    )

    produto_merge_service.executar_fusao_produtos(
        _FakeDB(),
        tenant_id=TENANT_ID,
        principal_id=principal.id,
        duplicado_id=duplicado.id,
        decisoes_campos={},
        user_id=7,
    )

    assert len(chamadas) == 1
    sql, params, tenant_id = chamadas[0]
    assert "delete from duplicatas_ignoradas" in sql
    assert TENANT_FILTER_MARKER in sql
    assert params == {"principal_id": principal.id, "duplicado_id": duplicado.id}
    assert tenant_id == TENANT_ID


def test_duplicatas_ignoradas_entra_no_guard_de_sql_tenant_safe():
    assert "duplicatas_ignoradas" in TENANT_SCOPED_TABLES
