from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_chave_de_classificacao_remove_numero_variavel_da_venda():
    from app.financeiro.contas_pagar_classificacao import (
        normalizar_chave_descricao_conta_pagar,
    )

    assert (
        normalizar_chave_descricao_conta_pagar("Taxa Crédito - Venda 202604250001")
        == "taxa credito"
    )
    assert (
        normalizar_chave_descricao_conta_pagar("Taxa Débito - Venda 202605250008")
        == "taxa debito"
    )


def test_classificar_conta_pagar_aprende_regra_e_aplica_similares():
    source = _source("backend/app/financeiro/contas_pagar_consulta_routes.py")
    endpoint = source.split("def classificar_conta_pagar(", 1)[1].split(
        "# ============================================================================\n# BUSCAR CONTA",
        1,
    )[0]

    assert "registrar_regra_classificacao_conta_pagar" in endpoint
    assert "aplicar_classificacao_similar_contas_pagar" in endpoint


def test_criacao_manual_de_conta_pagar_usa_classificacao_aprendida():
    source = _source("backend/app/financeiro/contas_pagar_criacao_routes.py")
    criar_endpoint = source.split("async def criar_conta_pagar(", 1)[1]

    assert "aplicar_classificacao_aprendida_conta_pagar(" in criar_endpoint


def test_contas_de_nf_entrada_usam_classificacao_aprendida_por_fornecedor():
    source = _source("backend/app/notas_entrada/financeiro.py")
    gerar_contas = source.split("def criar_contas_pagar_da_nota(", 1)[1].split(
        'logger.info("Total de contas criadas:',
        1,
    )[0]

    assert "aplicar_classificacao_aprendida_conta_pagar(" in gerar_contas


def test_contas_de_taxa_pdv_usam_classificacao_aprendida_por_descricao():
    source = _source("backend/app/vendas/pos_processamento.py")
    taxas = source.split("def processar_contas_pagar_taxas(", 1)[1].split(
        "def gerar_dre_competencia_venda(",
        1,
    )[0]

    assert "aplicar_classificacao_aprendida_conta_pagar(" in taxas


def test_vendas_service_mantem_imports_publicos_de_pos_processamento():
    from app.vendas import pos_processamento, service

    assert service.processar_contas_pagar_taxas is (
        pos_processamento.processar_contas_pagar_taxas
    )
    assert service.processar_comissoes_venda is (
        pos_processamento.processar_comissoes_venda
    )


def test_falha_ao_criar_taxa_do_pdv_limpa_transacao_da_venda_finalizada():
    source = _source("backend/app/vendas/finalizacao_pos_commit.py")
    bloco_taxas = source.split("resultado_taxas = processar_contas_pagar_taxas(", 1)[
        1
    ].split(
        "if venda.status == 'finalizada' and venda.cliente_id:",
        1,
    )[0]
    ramo_falha = bloco_taxas.split("else:", 1)[1].split("except Exception as e:", 1)[0]

    assert "db.rollback()" in ramo_falha
