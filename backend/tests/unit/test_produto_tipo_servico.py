from types import SimpleNamespace
from datetime import datetime

from app.produtos.schemas import ProdutoResponse
from app.produtos_catalogo_models import _aplicar_invariantes_servico_orm
from app.produtos.tipos import (
    aplicar_regras_servico_dados,
    normalizar_tipo_catalogo,
    tipo_controla_estoque,
)
from app.vendas.estoque_baixa import processar_baixa_estoque_item


def test_normaliza_tipo_servico_e_combinacoes_sem_perder_tipo_legado():
    assert normalizar_tipo_catalogo("Serviço") == "servico"
    assert normalizar_tipo_catalogo("ambos") == "produto_servico"
    assert normalizar_tipo_catalogo("ração") == "ração"
    assert tipo_controla_estoque("servico") is False
    assert tipo_controla_estoque("produto_servico") is True


def test_regras_de_servico_zeram_estoque_e_desligam_lotes():
    dados = {
        "tipo": "Serviço",
        "estoque_atual": 99,
        "estoque_minimo": 10,
        "estoque_maximo": 100,
        "estoque_fisico": 99,
        "estoque_ecommerce": 20,
        "controle_lote": True,
        "participa_sugestao_compra": True,
        "e_granel": True,
        "tipo_produto": "KIT",
        "tipo_kit": "VIRTUAL",
    }

    assert aplicar_regras_servico_dados(dados) is True
    assert dados["tipo"] == "servico"
    assert dados["estoque_atual"] == 0
    assert dados["estoque_minimo"] == 0
    assert dados["estoque_maximo"] == 0
    assert dados["estoque_fisico"] == 0
    assert dados["estoque_ecommerce"] == 0
    assert dados["controle_lote"] is False
    assert dados["participa_sugestao_compra"] is False
    assert dados["tipo_produto"] == "SIMPLES"
    assert dados["tipo_kit"] is None
    assert dados["produto_pai_id"] is None
    assert dados["is_parent"] is False
    assert dados["is_sellable"] is True


def test_baixa_de_venda_de_servico_nao_chama_estoque():
    servico = SimpleNamespace(id=42, controlar_estoque=False)

    resultado = processar_baixa_estoque_item(
        produto=servico,
        quantidade_vendida=1,
        venda_id=10,
        user_id=5,
        tenant_id="tenant-1",
        db=SimpleNamespace(),
    )

    assert resultado == []


def test_barreira_orm_zera_servico_gravado_por_fluxo_direto():
    servico = SimpleNamespace(
        tipo="servico",
        estoque_atual=25,
        controle_lote=True,
        tipo_produto="KIT",
    )

    _aplicar_invariantes_servico_orm(None, None, servico)

    assert servico.estoque_atual == 0
    assert servico.controle_lote is False
    assert servico.tipo_produto == "SIMPLES"


def test_resposta_de_servico_nao_expoe_saldo_ou_lotes_legados():
    agora = datetime.utcnow()
    response = ProdutoResponse.model_validate(
        {
            "id": 42,
            "codigo": "SERV-42",
            "nome": "Consulta",
            "tipo": "servico",
            "controlar_estoque": False,
            "estoque_atual": 999,
            "estoque_minimo": 10,
            "estoque_maximo": 1000,
            "estoque_reservado": 20,
            "estoque_disponivel": 979,
            "controle_lote": True,
            "lotes": [],
            "ativo": True,
            "created_at": agora,
            "updated_at": agora,
        }
    )

    assert response.estoque_atual == 0
    assert response.estoque_minimo == 0
    assert response.estoque_maximo == 0
    assert response.estoque_reservado == 0
    assert response.estoque_disponivel == 0
    assert response.controle_lote is False
    assert response.lotes == []
