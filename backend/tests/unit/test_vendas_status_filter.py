from app.vendas.crud_routes import normalizar_status_filtro_vendas


def test_normaliza_um_status_unico():
    assert normalizar_status_filtro_vendas("finalizada") == ["finalizada"]


def test_normaliza_lista_de_status_separada_por_virgula():
    assert normalizar_status_filtro_vendas(
        "finalizada, baixa_parcial, pago_nf, finalizada_devolucao"
    ) == ["finalizada", "baixa_parcial", "pago_nf", "finalizada_devolucao"]


def test_ignora_status_vazio_na_lista():
    assert normalizar_status_filtro_vendas("finalizada,, finalizada_devolucao, ") == [
        "finalizada",
        "finalizada_devolucao",
    ]
