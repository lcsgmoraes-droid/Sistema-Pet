from app.notas_entrada.processamento_acoes import (
    resolver_custo_operacional_entrada,
    sugerir_acoes_processamento,
)


def test_sugere_todas_acoes_para_nota_comum():
    dados_xml = {
        "natureza_operacao": "Compra para comercializacao",
        "valor_total": 125.50,
        "duplicatas": [{"valor": 125.50}],
        "itens": [{"cfop": "1102", "valor_total": 125.50}],
    }

    sugestao = sugerir_acoes_processamento(dados_xml)

    assert sugestao["acoes"] == {
        "lancar_estoque": True,
        "atualizar_custo": True,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": True,
    }
    assert sugestao["contexto"] == "nota_comum"


def test_sugere_apenas_estoque_para_bonificacao():
    dados_xml = {
        "natureza_operacao": "Bonificacao sem cobranca",
        "valor_total": 0,
        "duplicatas": [],
        "itens": [{"cfop": "1910", "valor_total": 0}],
    }

    sugestao = sugerir_acoes_processamento(dados_xml)

    assert sugestao["acoes"] == {
        "lancar_estoque": True,
        "atualizar_custo": False,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": False,
    }
    assert sugestao["contexto"] == "bonificacao"
    assert "custo atual do sistema" in sugestao["mensagem"]


def test_bonificacao_com_valor_fiscal_sem_duplicata_nao_gera_custo_financeiro():
    dados_xml = {
        "natureza_operacao": "Bonificacao em mercadoria",
        "valor_total": 250.0,
        "duplicatas": [],
        "itens": [{"cfop": "1910", "valor_total": 250.0}],
    }

    sugestao = sugerir_acoes_processamento(dados_xml)

    assert sugestao["contexto"] == "bonificacao"
    assert sugestao["acoes"] == {
        "lancar_estoque": True,
        "atualizar_custo": False,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": False,
    }


def test_resolve_custo_operacional_usando_custo_atual_quando_nao_atualiza_cadastro():
    custo = resolver_custo_operacional_entrada(
        custo_nf=1.25,
        custo_atual_sistema=8.9,
        atualizar_custo=False,
    )

    assert custo == 8.9


def test_resolve_custo_operacional_faz_fallback_para_nf_sem_custo_atual():
    custo = resolver_custo_operacional_entrada(
        custo_nf=1.25,
        custo_atual_sistema=0,
        atualizar_custo=False,
    )

    assert custo == 1.25


def test_resolve_custo_operacional_usa_nf_quando_atualiza_cadastro():
    custo = resolver_custo_operacional_entrada(
        custo_nf=1.25,
        custo_atual_sistema=8.9,
        atualizar_custo=True,
    )

    assert custo == 1.25
