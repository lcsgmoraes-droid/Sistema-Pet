import httpx
import pytest

from app.services import consulta_cnpj_service as service


CNPJ = "66403971000190"


@pytest.fixture(autouse=True)
def limpar_estado():
    service._cache.clear()
    service._fallback_calls.clear()
    yield
    service._cache.clear()
    service._fallback_calls.clear()


def _mock_client(monkeypatch, handler):
    original_client = httpx.Client
    monkeypatch.setattr(
        service.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_fallback_preenche_campos_quando_primeira_fonte_retorna_429(monkeypatch):
    chamadas = []

    def handler(request):
        chamadas.append(request.url.host)
        if request.url.host == "minhareceita.org":
            return httpx.Response(429)
        return httpx.Response(200, json={
            "razao_social": "M.A. DE ALMEIDA CLINICA VETERINARIA LTDA",
            "estabelecimento": {
                "cnpj": CNPJ,
                "nome_fantasia": "SAO JOSE CLINICA VETERINARIA",
                "email": "contato@exemplo.com",
                "ddd1": "18",
                "telefone1": "96312465",
                "cep": "19020120",
                "logradouro": "JOSE SOARES MARCONDES-CEL",
                "numero": "379",
                "bairro": "VILA MACHADINHO",
                "cidade": {"nome": "PRESIDENTE PRUDENTE", "ibge_id": 3541406},
                "estado": {"sigla": "SP"},
                "atividade_principal": {"id": "7500100", "descricao": "Atividades veterinárias"},
                "atividades_secundarias": [{"id": "4789004", "descricao": "Comércio varejista"}],
            },
        })

    _mock_client(monkeypatch, handler)
    dados = service.consultar_cnpj(CNPJ)

    assert chamadas == ["minhareceita.org", "publica.cnpj.ws"]
    assert dados["razao_social"] == "M.A. DE ALMEIDA CLINICA VETERINARIA LTDA"
    assert dados["nome_fantasia"] == "SAO JOSE CLINICA VETERINARIA"
    assert dados["codigo_municipio_ibge"] == 3541406
    assert dados["cnae_fiscal"] == "7500100"
    assert dados["cnaes_secundarios"] == [{"codigo": "4789004", "descricao": "Comércio varejista"}]

    assert service.consultar_cnpj(CNPJ) == dados
    assert len(chamadas) == 2


def test_primeira_fonte_valida_dispensa_fallback(monkeypatch):
    chamadas = []

    def handler(request):
        chamadas.append(request.url.host)
        return httpx.Response(200, json={
            "cnpj": CNPJ,
            "razao_social": "Empresa Teste",
            "codigo_municipio_ibge": 3541406,
            "cnaes_secundarios": [],
        })

    _mock_client(monkeypatch, handler)
    assert service.consultar_cnpj(CNPJ)["razao_social"] == "Empresa Teste"
    assert chamadas == ["minhareceita.org"]


def test_cnpj_invalido_nao_consulta_fontes():
    with pytest.raises(service.CnpjInvalido):
        service.consultar_cnpj("66403971000191")


def test_duas_fontes_sem_registro_retorna_nao_encontrado(monkeypatch):
    _mock_client(monkeypatch, lambda request: httpx.Response(404))
    with pytest.raises(service.CnpjNaoEncontrado):
        service.consultar_cnpj(CNPJ)


def test_falha_das_duas_fontes_retorna_indisponivel(monkeypatch):
    _mock_client(monkeypatch, lambda request: httpx.Response(429))
    with pytest.raises(service.ConsultaCnpjIndisponivel):
        service.consultar_cnpj(CNPJ)
