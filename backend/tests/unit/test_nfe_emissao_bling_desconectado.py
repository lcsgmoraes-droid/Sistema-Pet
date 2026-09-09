import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import nfe_routes


@pytest.mark.parametrize("erro", ["invalid_token", "invalid_grant"])
def test_emissao_orienta_reconectar_sem_erro_500_ou_salvar_venda(monkeypatch, erro):
    venda = SimpleNamespace(id=30, nfe_bling_id=None)
    commits = []
    db = SimpleNamespace(commit=lambda: commits.append(True))
    monkeypatch.setattr(
        nfe_routes, "_exigir_bling_configurado_para_tenant", lambda t: None
    )
    monkeypatch.setattr(nfe_routes, "_buscar_venda_para_nfe", lambda *a: venda)
    monkeypatch.setattr(
        nfe_routes,
        "prevalidar_fiscal_venda",
        lambda *a: {"bloqueios": [], "correcoes": []},
    )

    def falhar(*a, **kw):
        raise RuntimeError(f"Bling: {erro}")

    monkeypatch.setattr(
        nfe_routes, "BlingAPI", lambda: SimpleNamespace(emitir_nota_fiscal=falhar)
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            nfe_routes.emitir_nfe(
                nfe_routes.EmitirNFeRequest(venda_id=30),
                db=db,
                user_and_tenant=(SimpleNamespace(id=2), "tenant-teste"),
            )
        )

    assert exc.value.status_code == 503
    assert exc.value.detail["erro"] == "bling_reconexao_necessaria"
    assert "Reconectar Bling" in exc.value.detail["mensagem"]
    assert commits == []
    assert venda.nfe_bling_id is None
