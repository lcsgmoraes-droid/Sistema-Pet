import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


os.environ["DEBUG"] = "false"
if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
    os.environ["DATABASE_URL"] = (
        "postgresql://petshop_user:petshop_password@localhost:5432/petshop_db"
    )

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.bling_sync import exportacao_produtos_routes as exportacao  # noqa: E402


def _produto(**overrides):
    valores = {
        "id": 42,
        "nome": "Racao Teste 10kg",
        "codigo": "RACAO-10KG",
        "preco_venda": 149.9,
        "preco_custo": 91.5,
        "tipo": "produto",
        "situacao": True,
        "unidade": "UN",
        "condicao": "novo",
        "frete_gratis": True,
        "data_validade": datetime(2027, 1, 31, 12, 0, 0),
        "itens_por_caixa": 6,
        "producao": "terceiros",
        "descricao_curta": "Alimento completo",
        "descricao_completa": "Racao completa para caes adultos.",
        "gtin_ean": "7891234567895",
        "codigo_barras": None,
        "gtin_ean_tributario": "7891234567895",
        "marca": SimpleNamespace(nome="Marca Teste"),
        "peso_liquido": 10,
        "peso_bruto": 10.2,
        "estoque_minimo": 2,
        "estoque_maximo": 20,
        "localizacao": "A-01",
        "crossdocking_dias": 3,
        "ncm": "23091000",
        "cest": "2804100",
        "origem": "0",
        "informacoes_adicionais_nf": "Produto para revenda",
        "tipo_item": "00",
        "ipi_codigo_excecao": "001",
        "percentual_tributos": 12.5,
        "icms_base_retencao": 1.1,
        "icms_valor_retencao": 2.2,
        "icms_valor_proprio": 3.3,
        "pis_valor_fixo": 0.11,
        "cofins_valor_fixo": 0.22,
        "largura": 30,
        "altura": 50,
        "profundidade": 12,
        "imagem_principal": "/uploads/produtos/tenant/42/principal.webp",
        "imagens": [
            SimpleNamespace(
                id=1,
                url="/uploads/produtos/tenant/42/principal.webp",
                e_principal=True,
                ordem=0,
            ),
            SimpleNamespace(
                id=2,
                url="https://img.corepet.com.br/produtos/verso.webp",
                e_principal=False,
                ordem=1,
            ),
        ],
        "fornecedor_id": None,
        "fornecedor": None,
        "fornecedores_alternativos": [],
    }
    valores.update(overrides)
    return SimpleNamespace(**valores)


def test_payload_produto_bling_envia_campos_completos_e_todas_as_imagens(monkeypatch):
    monkeypatch.setenv("ECOMMERCE_PUBLIC_BASE_URL", "https://corepet.com.br")

    payload = exportacao._montar_payload_produto_bling(_produto())

    assert payload["dataValidade"] == "2027-01-31"
    assert payload["itensPorCaixa"] == 6
    assert payload["tipoProducao"] == "T"
    assert payload["condicao"] == 1
    assert payload["freteGratis"] is True
    assert payload["tributacao"] == {
        "ncm": "23091000",
        "cest": "2804100",
        "origem": 0,
        "dadosAdicionais": "Produto para revenda",
        "spedTipoItem": "00",
        "codigoExcecaoTipi": "001",
        "percentualTributos": 12.5,
        "valorBaseStRetencao": 1.1,
        "valorStRetencao": 2.2,
        "valorICMSSubstituto": 3.3,
        "valorPisFixo": 0.11,
        "valorCofinsFixo": 0.22,
    }
    assert payload["midia"]["imagens"]["imagensURL"] == [
        {"link": "https://corepet.com.br/uploads/produtos/tenant/42/principal.webp"},
        {"link": "https://img.corepet.com.br/produtos/verso.webp"},
    ]


def test_fornecedor_e_custo_sao_enviados_pelo_vinculo_proprio_do_bling():
    chamadas = []

    class FakeBling:
        def listar_contatos(self, **params):
            assert params["numero_documento"] == "12345678000199"
            return {
                "data": [
                    {
                        "id": 987,
                        "nome": "Fornecedor Teste",
                        "numeroDocumento": "12.345.678/0001-99",
                        "situacao": "A",
                    }
                ]
            }

        def criar_produto_fornecedor(self, payload):
            chamadas.append(payload)
            return {"data": {"id": 654}}

    fornecedor = SimpleNamespace(
        id=7,
        cnpj="12.345.678/0001-99",
        cpf=None,
        nome="Fornecedor Teste",
        razao_social="Fornecedor Teste",
        nome_fantasia=None,
    )
    vinculo = SimpleNamespace(
        id=10,
        fornecedor=fornecedor,
        fornecedor_id=7,
        codigo_fornecedor="COD-FORN-42",
        preco_custo=88.7,
        e_principal=True,
        ativo=True,
    )
    produto = _produto(
        fornecedor_id=7,
        fornecedor=fornecedor,
        fornecedores_alternativos=[vinculo],
    )

    resultado = exportacao._enviar_fornecedores_produto_bling(
        FakeBling(), produto, "123456"
    )

    assert resultado["fornecedores_enviados"] == 1
    assert chamadas == [
        {
            "descricao": "Racao Teste 10kg",
            "codigo": "COD-FORN-42",
            "precoCusto": 88.7,
            "precoCompra": 88.7,
            "padrao": True,
            "produto": {"id": 123456},
            "fornecedor": {"id": 987},
        }
    ]


def test_vinculo_obsoleto_e_limpo_quando_bling_retorna_404():
    sync = SimpleNamespace(
        bling_produto_id="123",
        sincronizar=True,
        status="ativo",
        erro_mensagem="erro anterior",
        ultima_conferencia_bling=None,
        updated_at=None,
    )

    assert exportacao._erro_bling_nao_encontrado(
        Exception("Erro na API Bling: 404 Not Found")
    )

    exportacao._limpar_vinculo_bling_inexistente(sync)

    assert sync.bling_produto_id is None
    assert sync.sincronizar is False
    assert sync.status == "pausado"
    assert sync.erro_mensagem is None
    assert sync.ultima_conferencia_bling is not None


def test_detalhe_vazio_ou_excluido_nao_confirma_produto_no_bling():
    assert exportacao._detalhe_bling_confirma_produto({"id": 123}, "123")
    assert not exportacao._detalhe_bling_confirma_produto({}, "123")
    assert not exportacao._detalhe_bling_confirma_produto(
        {"id": 123, "situacao": "E"}, "123"
    )
    assert not exportacao._detalhe_bling_confirma_produto({"id": 999}, "123")
