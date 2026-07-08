from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    full_path = REPO_ROOT / path
    assert full_path.exists(), f"Arquivo esperado nao existe: {path}"
    return full_path.read_text(encoding="utf-8")


def contas_receber_source() -> str:
    paths = (
        "frontend/src/components/ContasReceber.jsx",
        "frontend/src/components/contasReceber/ContasReceberPanels.jsx",
        "frontend/src/components/contasReceber/ContasReceberAnalise.jsx",
    )
    return "\n".join(read_repo(path) for path in paths)


def test_contas_receber_frontend_tem_aba_analise_com_exclusao_de_cliente():
    source = contas_receber_source()

    assert "ContasReceberAnalise" in source
    assert "abaAtivaContasReceber" in source
    assert "Lancamentos" in source
    assert "Analise" in source
    assert 'api.get("/contas-receber/analise-abertos"' in source
    assert "cliente_modo" in source
    assert "cliente_ids" in source
    assert "Excluir selecionados" in source
    assert "Tudo menos" in source
    assert "proximos_12_meses" in source
    assert "agenda_mensal" in source
    assert "por_cliente" in source
    assert "por_forma_pagamento" in source
    assert "por_canal" in source


def test_contas_receber_usa_formas_pagamento_financeiras_validas():
    source = contas_receber_source()
    carregar_formas = source.split("const carregarFormasPagamento = async (headers) => {", 1)[
        1
    ].split(
        "// Aplicar filtro automaticamente",
        1,
    )[0]

    assert 'api.get("/financeiro/formas-pagamento?apenas_ativas=true"' in carregar_formas
    assert "/comissoes/formas-pagamento" not in carregar_formas
    assert "safeArray(response.data).map" in carregar_formas
