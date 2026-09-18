import asyncio
import inspect
from types import SimpleNamespace

from app import nfe_routes


def test_emissao_usa_exclusivamente_intnfe(monkeypatch):
    venda = SimpleNamespace(
        id=30,
        nfe_bling_id=None,
        nfe_correlation_id=None,
        nfe_numero=None,
    )
    db = SimpleNamespace()
    cliente_intnfe = SimpleNamespace(close=lambda: None)
    chamadas = []

    monkeypatch.setattr(nfe_routes, "_buscar_venda_para_nfe", lambda *a: venda)
    monkeypatch.setattr(nfe_routes, "_intnfe_client", lambda: cliente_intnfe)
    monkeypatch.setattr(
        nfe_routes,
        "get_connection",
        lambda *a: SimpleNamespace(emission_environment=1),
    )
    monkeypatch.setattr(nfe_routes, "get_tenant", lambda *a: SimpleNamespace(id="t"))
    monkeypatch.setattr(nfe_routes, "log_action", lambda *a, **kw: None)

    def emitir(*args):
        chamadas.append(args)
        return {"success": True, "provedor": "intnfe"}

    monkeypatch.setattr(nfe_routes, "issue_intnfe", emitir)

    resposta = asyncio.run(
        nfe_routes.emitir_nfe(
            nfe_routes.EmitirNFeRequest(venda_id=30),
            db=db,
            user_and_tenant=(SimpleNamespace(id=2), "tenant-teste"),
        )
    )

    assert resposta == {"success": True, "provedor": "intnfe"}
    assert chamadas[0][2:] == (venda, "nfce", cliente_intnfe)


def test_prevalidacao_sem_intnfe_configurada_nao_faz_fallback_bling(monkeypatch):
    venda = SimpleNamespace(id=30, nfe_bling_id=None, nfe_correlation_id=None)
    monkeypatch.setattr(nfe_routes, "_buscar_venda_para_nfe", lambda *a: venda)
    monkeypatch.setattr(
        nfe_routes,
        "prevalidar_produtos_fiscais_venda",
        lambda *a, **kw: {"pode_emitir": True, "bloqueios": [], "correcoes": []},
    )
    monkeypatch.setattr(nfe_routes, "get_tenant", lambda *a: SimpleNamespace(id="t"))
    monkeypatch.setattr(
        nfe_routes,
        "preview_intnfe",
        lambda *a: (_ for _ in ()).throw(
            nfe_routes.DirectEmissionError(
                "Conclua o vínculo com a IntNFe em Configurações > Integrações.",
                status=409,
            )
        ),
    )

    resposta = asyncio.run(
        nfe_routes.prevalidar_nfe(
            nfe_routes.PrevalidarNFeRequest(venda_id=30),
            db=SimpleNamespace(),
            user_and_tenant=(SimpleNamespace(id=2), "tenant-teste"),
        )
    )

    assert resposta["provedor"] == "intnfe"
    assert resposta["pode_emitir"] is False
    assert "IntNFe" in resposta["bloqueios"][0]["mensagem"]


def test_rota_de_emissao_nao_contem_chamada_ao_bling():
    fonte = inspect.getsource(nfe_routes.emitir_nfe)

    assert "BlingAPI" not in fonte
    assert "emitir_nota_fiscal" not in fonte
