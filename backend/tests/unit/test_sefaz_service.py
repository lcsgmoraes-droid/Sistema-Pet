from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.sefaz_service import SefazService


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
