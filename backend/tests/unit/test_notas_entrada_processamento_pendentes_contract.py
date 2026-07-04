from pathlib import Path

from app.notas_entrada.processamento_acoes import (
    calcular_acoes_pendentes_processamento,
    mesclar_acoes_realizadas_processamento,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_acoes_pendentes_desmarcam_o_que_ja_foi_lancado():
    sugeridas = {
        "lancar_estoque": True,
        "atualizar_custo": True,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": True,
    }
    realizadas = {
        "lancar_estoque": True,
        "atualizar_custo": False,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": False,
    }

    pendentes = calcular_acoes_pendentes_processamento(sugeridas, realizadas)

    assert pendentes == {
        "lancar_estoque": False,
        "atualizar_custo": True,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": True,
    }


def test_acoes_realizadas_sao_acumuladas_a_cada_processamento():
    realizadas = {
        "lancar_estoque": True,
        "atualizar_custo": False,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": False,
    }
    novas = {
        "lancar_estoque": False,
        "atualizar_custo": True,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": True,
    }

    assert mesclar_acoes_realizadas_processamento(realizadas, novas) == {
        "lancar_estoque": True,
        "atualizar_custo": True,
        "atualizar_preco_venda": False,
        "gerar_contas_pagar": True,
    }


def test_preview_informa_acoes_realizadas_e_pendentes():
    source = read_source("backend/app/notas_entrada/processamento_precos.py")

    assert "acoes_processamento_realizadas" in source
    assert "acoes_processamento_pendentes" in source


def test_processamento_permite_nota_processada_com_acoes_pendentes():
    source = read_source("backend/app/notas_entrada/processamento_routes.py")

    assert 'detail="Entrada no estoque j' not in source
    assert "Nenhum movimento pendente selecionado" in source
    assert "mesclar_acoes_realizadas_processamento" in source


def test_processamento_aborta_quando_financeiro_da_nf_falha():
    source = read_source("backend/app/notas_entrada/processamento_routes.py")
    bloco_financeiro = source.split("# CRIAR CONTAS A PAGAR", 1)[1].split(
        "db.commit()", 1
    )[0]

    assert "db.rollback()" in bloco_financeiro
    assert "raise HTTPException" in bloco_financeiro
    assert "Nao abortar" not in bloco_financeiro
