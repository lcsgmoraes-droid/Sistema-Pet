from app.evolucao_corepet import (
    ITENS_EVOLUCAO,
    listar_evolucao_corepet,
    validar_catalogo_evolucao,
)


def test_catalogo_evolucao_respeita_contrato_de_publicacao():
    validar_catalogo_evolucao()

    ids = [item["id"] for item in ITENS_EVOLUCAO]
    assert len(ids) == len(set(ids))
    for item in ITENS_EVOLUCAO:
        if item["status"] == "disponivel":
            assert item["publicado_em"]
            assert item["caminho_ajuda"]


def test_catalogo_filtra_projetos_por_canal_sem_expor_item_interno():
    erp = listar_evolucao_corepet("erp")
    cliente = listar_evolucao_corepet("app_cliente")

    ids_erp = {item["id"] for item in erp["itens"]}
    ids_cliente = {item["id"] for item in cliente["itens"]}

    assert "grupos-empresas-transferencia-integrada" in ids_erp
    assert "grupos-empresas-transferencia-integrada" not in ids_cliente
    assert "avaliacao-entrega-app" in ids_cliente
    assert erp["total_disponivel"] >= 1


def test_catalogo_rejeita_canal_desconhecido():
    try:
        listar_evolucao_corepet("canal_inexistente")
    except ValueError as exc:
        assert "Canal de evolucao invalido" in str(exc)
    else:
        raise AssertionError("Canal desconhecido deveria ser rejeitado")
