import json
from types import SimpleNamespace

from app.services.produto_ai_enrichment import gerar_rascunho_produto_por_ean


class _FakeResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "descricao": "## Produto\nDescricao comercial segura e suficientemente completa para a loja virtual.",
                    "ncm": "23091000",
                    "cest": "2200100",
                    "origem_mercadoria": "0",
                    "confianca_fiscal": "media",
                    "alertas_revisao": ["Conferir com o contador."],
                    "fontes": ["https://fabricante.example/produto"],
                }
            )
        )


def test_assistente_pesquisa_web_e_exige_saida_estruturada():
    responses = _FakeResponses()
    resultado = gerar_rascunho_produto_por_ean(
        api_key="teste",
        codigo_barras="7891234567890",
        nome="Racao Teste",
        client=SimpleNamespace(responses=responses),
    )

    assert responses.kwargs["tools"] == [{"type": "web_search"}]
    assert responses.kwargs["text"]["format"]["type"] == "json_schema"
    assert resultado.ncm == "23091000"
    assert resultado.cest == "2200100"
