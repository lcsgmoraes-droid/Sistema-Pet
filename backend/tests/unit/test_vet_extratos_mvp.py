import importlib


def _extratos():
    return importlib.import_module("app.veterinario_extratos")


def test_extrato_contabiliza_procedimento_e_detalha_insumos_sem_duplicar():
    extratos = _extratos()
    produto = {
        "id": 10,
        "codigo": "DEF123",
        "nome": "Defenza",
        "unidade": "un",
        "preco_venda": 40,
    }
    procedimento = {
        "id": 5,
        "nome": "Consulta clinica",
        "valor": 120,
        "created_at": "2026-05-18T12:00:00",
        "insumos": [
            {
                "produto_id": 10,
                "nome": "Defenza",
                "quantidade": 1,
                "unidade": "un",
                "custo_unitario": 25,
                "custo_total": 25,
                "baixar_estoque": True,
            }
        ],
        "estoque_baixado": True,
        "estoque_movimentacao_ids": [99],
    }

    extrato = extratos.montar_extrato_atendimento(
        consulta={"id": 123, "tipo": "consulta"},
        procedimentos_consulta=[procedimento],
        produtos_por_id={10: produto},
    )

    assert extrato["totais"]["preco_total"] == 120
    assert extrato["totais"]["custo_total"] == 25
    assert extrato["totais"]["margem_valor"] == 95
    assert len(extrato["linhas"]) == 2
    assert extrato["linhas"][0]["contabilizar_total"] is True
    assert extrato["linhas"][1]["contabilizar_total"] is False
    assert extrato["linhas"][1]["preco_unitario"] == 40
    assert extrato["linhas"][1]["preco_total"] == 40


def test_extrato_contabiliza_insumo_manual_quando_procedimento_nao_tem_valor():
    extratos = _extratos()
    produto = {
        "id": 11,
        "codigo": "SER3",
        "nome": "Seringa 3ml",
        "unidade": "un",
        "preco_venda": 2.5,
    }
    procedimento = {
        "id": 6,
        "nome": "Insumo: Seringa 3ml",
        "valor": 0,
        "insumos": [
            {
                "produto_id": 11,
                "nome": "Seringa 3ml",
                "quantidade": 3,
                "unidade": "un",
                "custo_unitario": 0.9,
                "custo_total": 2.7,
            }
        ],
    }

    extrato = extratos.montar_extrato_atendimento(
        consulta={"id": 124, "tipo": "consulta"},
        procedimentos_consulta=[procedimento],
        produtos_por_id={11: produto},
    )

    contabilizadas = [linha for linha in extrato["linhas"] if linha["contabilizar_total"]]
    assert len(contabilizadas) == 1
    assert contabilizadas[0]["origem"] == "insumo_consulta"
    assert contabilizadas[0]["preco_total"] == 7.5
    assert extrato["totais"]["preco_total"] == 7.5
    assert extrato["totais"]["custo_total"] == 2.7


def test_colunas_do_extrato_sao_normalizadas_sem_duplicar():
    extratos = _extratos()

    assert extratos.normalizar_colunas_extrato("nome,preco_total,nome,x") == ["nome", "preco_total"]
    assert extratos.normalizar_colunas_extrato([]) == extratos.EXTRATO_COLUNAS_DEFAULT


def test_exportacoes_pdf_e_excel_usam_o_payload_do_extrato():
    extratos = _extratos()
    extrato = extratos.montar_extrato_atendimento(
        consulta={"id": 125, "tipo": "consulta"},
        procedimentos_consulta=[
            {"id": 7, "consulta_id": 125, "nome": "Retorno", "valor": 80, "insumos": []}
        ],
        produtos_por_id={},
        colunas=["nome", "preco_total"],
    )

    excel = extratos.gerar_excel_extrato_bytes(extrato, ["nome", "preco_total"])
    pdf = extratos.gerar_pdf_extrato_bytes(extrato, ["nome", "preco_total"])

    assert excel.startswith(b"PK")
    assert pdf.startswith(b"%PDF")


def test_rotas_de_extrato_veterinario_estao_registradas():
    from app.veterinario_routes import router

    routes = {
        (route.path, method)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }
    assert ("/vet/extratos/atendimento", "GET") in routes
    assert ("/vet/extratos/atendimento/export.pdf", "GET") in routes
    assert ("/vet/extratos/atendimento/export.xlsx", "GET") in routes
