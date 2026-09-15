from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app import nfe_routes
from app.nfe import listagem
from app.nfe import operacional_routes
from fastapi import FastAPI


EXPECTED_SUBROUTES = {
    ("/{nfe_id}/reconciliar-fluxo", "POST"),
    ("/{nfe_id}", "GET"),
    ("/{nfe_id}/xml", "GET"),
    ("/{nfe_id}/cancelar", "POST"),
    ("/{nfe_id}/carta-correcao", "POST"),
    ("/{venda_id}", "DELETE"),
    ("/webhook/bling", "POST"),
    ("/{venda_id}/sincronizar-status", "POST"),
    ("/sincronizar-todos", "POST"),
    ("/{nfe_id}/danfe", "GET"),
    ("/config/testar-conexao", "GET"),
}

EXPECTED_PUBLIC_ROUTES = {
    (f"/nfe{path}", method) for path, method in EXPECTED_SUBROUTES
}


def _route_signatures(router):
    app = FastAPI()
    app.include_router(router)
    return {
        (path, method.upper())
        for path, methods in app.openapi()["paths"].items()
        for method in methods
    }


def test_rotas_operacionais_ficam_em_router_dedicado():
    assert EXPECTED_SUBROUTES <= _route_signatures(operacional_routes.router)


def test_nfe_routes_preserva_caminhos_publicos_operacionais():
    assert EXPECTED_PUBLIC_ROUTES <= _route_signatures(nfe_routes.router)


def test_nfe_routes_mantem_aliases_de_compatibilidade():
    assert nfe_routes.consultar_nfe is operacional_routes.consultar_nfe
    assert nfe_routes.cancelar_nfe is operacional_routes.cancelar_nfe
    assert nfe_routes.webhook_bling is operacional_routes.webhook_bling
    assert nfe_routes.baixar_danfe is operacional_routes.baixar_danfe


def test_nfe_routes_mantem_aliases_de_listagem_para_imports_legados():
    assert nfe_routes._normalizar_nota_bling is listagem._normalizar_nota_bling
    assert nfe_routes._status_nota_bling is listagem._status_nota_bling
    assert nfe_routes._obter_detalhe_nfe_cache is listagem._obter_detalhe_nfe_cache
    assert nfe_routes.upsert_nota_cache is listagem.upsert_nota_cache
    assert (
        nfe_routes._sincronizar_cache_nfes_com_bling
        is listagem._sincronizar_cache_nfes_com_bling
    )


@pytest.mark.asyncio
async def test_exclusao_limpa_rejeicao_intnfe_para_permitir_nova_tentativa():
    venda = SimpleNamespace(
        id=1116549,
        tenant_id="tenant",
        nfe_bling_id=None,
        nfe_correlation_id="corr-rejeitada",
        nfe_status="rejeitada",
        nfe_tipo="nfe",
        nfe_modelo="55",
        nfe_numero=17842,
        nfe_serie=2,
        nfe_chave="3" * 44,
        nfe_provider="intnfe",
        nfe_protocolo=None,
        nfe_ambiente=1,
        nfe_codigo_erro="600",
        nfe_idempotency_key="tentativa",
        nfe_payload_hash="hash",
        nfe_xml=None,
        nfe_data_emissao=None,
        nfe_data_autorizacao=None,
        nfe_motivo_rejeicao="CSOSN incompatível",
        status="pago_nf",
    )

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return venda

    class Db:
        def query(self, _model):
            return Query()

        def commit(self):
            return None

    resposta = await operacional_routes.excluir_nota(
        venda.id,
        db=Db(),
        user_and_tenant=(SimpleNamespace(id=1), "tenant"),
    )

    assert resposta["success"] is True
    assert venda.nfe_correlation_id is None
    assert venda.nfe_idempotency_key is None
    assert venda.nfe_status is None
    assert venda.status == "finalizada"


@pytest.mark.asyncio
async def test_consultar_nfe_atualiza_cache_com_detalhe_corrigido(monkeypatch):
    detalhe_bling = {"id": 123, "numero": "017890", "xml": "https://bling.test/nfe.xml"}
    detalhe_normalizado = {
        "id": "123",
        "numero": "017890",
        "modelo": 55,
        "canal": "tiktok",
        "canal_label": "TikTok",
    }
    upsert = Mock()
    fachada = SimpleNamespace(
        _consultar_detalhe_nota_bling=lambda *args, **kwargs: (
            detalhe_bling,
            55,
            None,
        ),
        _normalizar_detalhe_nota_bling=lambda *args, **kwargs: detalhe_normalizado,
        _enriquecer_detalhe_com_xml_link=lambda *args, **kwargs: None,
        _enriquecer_notas_com_pedidos_integrados=lambda *args, **kwargs: None,
        upsert_nota_cache=upsert,
    )
    db = Mock()
    monkeypatch.setattr(operacional_routes, "_nfe_routes", lambda: fachada)
    monkeypatch.setattr(operacional_routes, "BlingAPI", Mock)
    monkeypatch.setattr(
        operacional_routes, "_exigir_bling_configurado_para_tenant", lambda _: None
    )

    resultado = await operacional_routes.consultar_nfe(
        123,
        db=db,
        user_and_tenant=(object(), "tenant-1"),
    )

    assert resultado is detalhe_normalizado
    upsert.assert_called_once_with(
        db,
        "tenant-1",
        detalhe_normalizado,
        source="bling_detail",
        resumo_payload=detalhe_normalizado,
        detalhe_payload=detalhe_bling,
    )
    db.commit.assert_called_once_with()


@pytest.mark.asyncio
async def test_consultar_nfe_nao_falha_se_atualizacao_do_cache_falhar(monkeypatch):
    detalhe_normalizado = {"id": "123", "numero": "017890", "modelo": 55}
    fachada = SimpleNamespace(
        _consultar_detalhe_nota_bling=lambda *args, **kwargs: ({"id": 123}, 55, None),
        _normalizar_detalhe_nota_bling=lambda *args, **kwargs: detalhe_normalizado,
        _enriquecer_detalhe_com_xml_link=lambda *args, **kwargs: None,
        _enriquecer_notas_com_pedidos_integrados=lambda *args, **kwargs: None,
        upsert_nota_cache=Mock(),
    )
    db = Mock()
    db.commit.side_effect = RuntimeError("cache indisponivel")
    monkeypatch.setattr(operacional_routes, "_nfe_routes", lambda: fachada)
    monkeypatch.setattr(operacional_routes, "BlingAPI", Mock)
    monkeypatch.setattr(
        operacional_routes, "_exigir_bling_configurado_para_tenant", lambda _: None
    )

    resultado = await operacional_routes.consultar_nfe(
        123,
        db=db,
        user_and_tenant=(object(), "tenant-1"),
    )

    assert resultado is detalhe_normalizado
    db.rollback.assert_called_once_with()
