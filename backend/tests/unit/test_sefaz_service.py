from __future__ import annotations

import pytest
import requests
from fastapi import HTTPException

from app.middlewares.request_context import clear_request_context, set_request_id
from app.services.sefaz_service import SefazConsumoIndevidoError, SefazService
from app.utils.logger import clear_context


def teardown_function():
    clear_request_context()
    clear_context()


def _config_real_base() -> dict:
    return {
        "enabled": True,
        "modo": "real",
        "ambiente": "homologacao",
        "uf": "SP",
        "cnpj": "12345678000195",
        "cert_path": "cert.pfx",
        "cert_password": "senha",
    }


def test_consultar_nfe_mock_retorna_sucesso_sem_soap() -> None:
    set_request_id("req-sefaz-123")

    data = SefazService.consultar_nfe_por_chave(
        "35250112345678000195550010000001231234567890",
        {
            "enabled": False,
            "modo": "mock",
            "ambiente": "homologacao",
            "uf": "SP",
            "cnpj": "",
            "cert_path": "",
            "cert_password": "",
        },
    )

    assert data["modo"] == "mock"
    assert data["correlation_id"] == "req-sefaz-123"
    assert data["numero_nf"] == "000123"
    assert data["chave_acesso"] == "35250112345678000195550010000001231234567890"


def test_consultar_nfe_real_chama_fluxo_real(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _config_real_base()
    esperado = {
        "chave_acesso": "35250112345678000195550010000001231234567890",
        "numero_nf": "123",
        "serie": "1",
        "data_emissao": "2026-03-09",
        "emitente_cnpj": "12345678000195",
        "emitente_nome": "Fornecedor Real",
        "destinatario_cnpj": None,
        "destinatario_nome": "Petshop",
        "valor_total_nf": 10.0,
        "itens": [],
        "aviso": "Consulta real realizada na SEFAZ via distribuição DF-e.",
    }

    monkeypatch.setattr(SefazService, "garantir_pronto_para_consulta_real", classmethod(lambda cls, _cfg=None: None))
    monkeypatch.setattr(SefazService, "_consultar_por_chave_real", classmethod(lambda cls, chave, _cfg: {**esperado, "chave_acesso": chave}))

    resultado = SefazService.consultar_nfe_por_chave("35250112345678000195550010000001231234567890", cfg)

    assert resultado["aviso"].startswith("Consulta real")
    assert resultado["numero_nf"] == "123"


def test_sincronizar_nsu_caso_feliz(monkeypatch: pytest.MonkeyPatch) -> None:
    set_request_id("req-sefaz-sync")
    cfg = _config_real_base()

    monkeypatch.setattr(SefazService, "garantir_pronto_para_consulta_real", classmethod(lambda cls, _cfg=None: None))
    monkeypatch.setattr(SefazService, "_post_soap_dist_dfe", classmethod(lambda cls, _cfg, _xml: "<xml />"))
    monkeypatch.setattr(
        SefazService,
        "_parse_retorno_dist_dfe",
        classmethod(
            lambda cls, _soap: {
                "c_stat": "138",
                "x_motivo": "Documento localizado",
                "ult_nsu": "000000000000010",
                "max_nsu": "000000000000010",
                "docs": [{"nsu": "10", "schema": "resNFe_v1.01.xsd", "xml": "<resNFe />"}],
            }
        ),
    )

    resultado = SefazService.sincronizar_nsu(config=cfg, ultimo_nsu="000000000000009")

    assert resultado["status"] == "ok"
    assert resultado["correlation_id"] == "req-sefaz-sync"
    assert resultado["documentos"] == 1
    assert resultado["ultimo_nsu"] == "000000000000010"


def test_sincronizar_nsu_retorno_inesperado_gera_502(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _config_real_base()

    monkeypatch.setattr(SefazService, "garantir_pronto_para_consulta_real", classmethod(lambda cls, _cfg=None: None))
    monkeypatch.setattr(SefazService, "_post_soap_dist_dfe", classmethod(lambda cls, _cfg, _xml: "<xml />"))
    monkeypatch.setattr(
        SefazService,
        "_parse_retorno_dist_dfe",
        classmethod(
            lambda cls, _soap: {
                "c_stat": "999",
                "x_motivo": "Erro qualquer",
                "ult_nsu": "000000000000009",
                "max_nsu": "000000000000009",
                "docs": [],
            }
        ),
    )

    with pytest.raises(HTTPException) as exc:
        SefazService.sincronizar_nsu(config=cfg, ultimo_nsu="000000000000009")

    assert exc.value.status_code == 502
    assert "cStat 999" in str(exc.value.detail)


def test_sincronizar_nsu_cstat_656_retorna_excecao_com_nsu(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _config_real_base()

    monkeypatch.setattr(SefazService, "garantir_pronto_para_consulta_real", classmethod(lambda cls, _cfg=None: None))
    monkeypatch.setattr(SefazService, "_post_soap_dist_dfe", classmethod(lambda cls, _cfg, _xml: "<xml />"))
    monkeypatch.setattr(
        SefazService,
        "_parse_retorno_dist_dfe",
        classmethod(
            lambda cls, _soap: {
                "c_stat": "656",
                "x_motivo": "Rejeicao: Consumo Indevido (Use ultNSU)",
                "ult_nsu": "000000000001234",
                "max_nsu": "000000000001240",
                "docs": [],
            }
        ),
    )

    with pytest.raises(SefazConsumoIndevidoError) as exc:
        SefazService.sincronizar_nsu(config=cfg, ultimo_nsu="000000000000009")

    assert "cStat 656" in str(exc.value)
    assert exc.value.ult_nsu == "000000000001234"
    assert exc.value.max_nsu == "000000000001240"


def test_falha_cloudflare_na_sefaz_retorna_mensagem_operacional() -> None:
    raw_msg = (
        "The origin web server returned an invalid or incomplete response to Cloudflare. "
        "This typically indicates the origin is overloaded or misconfigured."
    )

    detail = SefazService._mensagem_falha_comunicacao(
        requests.exceptions.RequestException(raw_msg)
    )

    assert "SEFAZ esta temporariamente indisponivel" in detail
    assert "tente novamente em alguns minutos" in detail
    assert "Cloudflare" not in detail
    assert "origin web server" not in detail
