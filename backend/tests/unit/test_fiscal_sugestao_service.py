from contextlib import nullcontext
from uuid import uuid4

from app.services import fiscal_sugestao_service as service


class FakeSession:
    def begin_nested(self):
        return nullcontext()


def test_pesquisa_consolida_evidencias_e_informa_fontes(monkeypatch):
    monkeypatch.setattr(
        service,
        "_buscar_historico_tenant",
        lambda *_args, **_kwargs: [
            {
                "ncm": "23091000",
                "cest": "1701600",
                "descricao": "Ração cães adultos",
                "fonte": "cadastro_confirmado_da_empresa",
                "fonte_rotulo": "cadastro fiscal já usado por esta empresa",
                "score": 90,
                "qualidade": 100,
            }
        ],
    )
    monkeypatch.setattr(
        service,
        "_buscar_catalogo_mestre",
        lambda *_args, **_kwargs: [
            {
                "ncm": "23091000",
                "cest": "1701600",
                "descricao": "Ração para cães",
                "fonte": "catalogo_mestre_corepet",
                "fonte_rotulo": "catálogo mestre do CorePet",
                "score": 90,
                "qualidade": 90,
            },
            {
                "ncm": "23091000",
                "cest": "1701600",
                "descricao": "Alimento para cães",
                "fonte": "catalogo_mestre_corepet",
                "fonte_rotulo": "catálogo mestre do CorePet",
                "score": 80,
                "qualidade": 85,
            },
        ],
    )

    resposta = service.pesquisar_base_fiscal(
        FakeSession(), uuid4(), "ração cães", limite=5
    )

    resultado = resposta["resultados"][0]
    assert resultado["ncm"] == "23091000"
    assert resultado["cest"] == "1701600"
    assert resultado["ocorrencias"] == 3
    assert resultado["confianca"] == "alta"
    assert "esta empresa" in resultado["fonte"]
    assert resultado["fonte_oficial"]["url"].endswith("/classif/")


def test_referencias_explicam_csosn_e_pis_cofins(monkeypatch):
    monkeypatch.setattr(service, "_buscar_historico_tenant", lambda *_a, **_k: [])
    monkeypatch.setattr(service, "_buscar_catalogo_mestre", lambda *_a, **_k: [])

    resposta = service.pesquisar_base_fiscal(
        FakeSession(), uuid4(), "portão pet", limite=5
    )

    csosn = {item["codigo"]: item for item in resposta["referencias"]["csosn"]}
    pis = {item["codigo"]: item for item in resposta["referencias"]["pis"]}
    assert "sem permissão de crédito" in csosn["102"]["descricao"]
    assert "substituição tributária" in csosn["500"]["descricao"]
    assert "Outras operações de saída" in pis["49"]["descricao"]
    assert pis["49"]["fonte"]["url"].startswith("https://sped.rfb.gov.br/")
