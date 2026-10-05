"""Garante que as exportacoes da DRE preservam os custos separados."""

import asyncio
from datetime import date
from io import BytesIO

from openpyxl import load_workbook

from app import dre_export_routes
from app.dre_canais.schemas import DREPorCanalResponse, LinhaCanal


def _linha(campo: str, valor: float) -> LinhaCanal:
    return LinhaCanal(
        descricao=campo,
        valor=valor,
        percentual=0,
        cor="#000000",
        cor_bg="#ffffff",
        canal="loja_fisica",
        canal_nome="Loja Física",
        nivel=1,
        tipo="despesa",
        campo=campo,
    )


def _dre_mista() -> DREPorCanalResponse:
    return DREPorCanalResponse(
        periodo="01/10/2026 a 05/10/2026",
        mes_inicial=10,
        mes=10,
        ano=2026,
        data_final=date(2026, 10, 5),
        canais_encontrados=["loja_fisica", "mercado_livre"],
        linhas=[
            _linha("despesas_pessoal", 0),
            _linha("despesas_administrativas", 10),
            _linha("taxas_cartao", 2.45),
        ],
        totais={
            "receita_bruta": 280,
            "vendas_produtos": 100,
            "vendas_servicos": 130,
            "receita_frete": 0,
            "outras_receitas": 50,
            "deducoes_total": 13,
            "descontos": 5,
            "devolucoes": 3,
            "receita_liquida": 267,
            "cmv": 45,
            "custo_servicos": 65,
            "lucro_bruto": 157,
            "margem_bruta": 59.26,
            "despesas_operacionais": 12.45,
            "resultado_operacional": 144.55,
            "lucro_liquido": 144.55,
            "margem_liquida": 54.65,
        },
    )


async def _conteudo_resposta(resposta) -> bytes:
    partes = []
    async for parte in resposta.body_iterator:
        partes.append(parte if isinstance(parte, bytes) else parte.encode())
    return b"".join(partes)


def test_exportacao_pdf_e_excel_separam_cmv_e_custo_servicos(monkeypatch):
    dre = _dre_mista()
    chamadas = []

    def gerar_dre_mock(**kwargs):
        chamadas.append(kwargs)
        return dre

    monkeypatch.setattr(dre_export_routes, "gerar_dre_por_canais", gerar_dre_mock)
    parametros = {
        "ano": 2026,
        "mes": 10,
        "mes_inicial": 10,
        "data_final": date(2026, 10, 5),
        "canais": "loja_fisica,mercado_livre",
        "db": object(),
        "user_and_tenant": (object(), "tenant-teste"),
    }

    pdf = asyncio.run(dre_export_routes.exportar_dre_pdf(**parametros))
    conteudo_pdf = asyncio.run(_conteudo_resposta(pdf))
    assert pdf.media_type == "application/pdf"
    assert pdf.headers["content-disposition"].endswith(".pdf")
    assert conteudo_pdf.startswith(b"%PDF-")
    assert len(conteudo_pdf) > 1000

    excel = asyncio.run(dre_export_routes.exportar_dre_excel(**parametros))
    conteudo_excel = asyncio.run(_conteudo_resposta(excel))
    assert excel.media_type.endswith("spreadsheetml.sheet")
    assert excel.headers["content-disposition"].endswith(".xlsx")
    assert conteudo_excel.startswith(b"PK")
    assert len(chamadas) == 2
    for chamada in chamadas:
        assert chamada == parametros

    planilha = load_workbook(BytesIO(conteudo_excel), read_only=True, data_only=True)
    try:
        assert planilha["DRE"]["A2"].value == "Período: 01/10/2026 a 05/10/2026"
        linhas = {
            linha[0]: linha[1]
            for linha in planilha["DRE"].iter_rows(values_only=True)
            if linha[0]
        }
        assert linhas["(-) CMV (Custo Mercadorias Vendidas)"] == 45
        assert linhas["(-) Custo dos Serviços Prestados"] == 65
        assert linhas["  Outras Receitas"] == 50
        assert linhas["  Devoluções de Vendas"] == 3
        assert linhas["  Impostos sobre Vendas"] == 5
        assert linhas["  Taxas de Cartão"] == 2.45
        assert linhas["(=) LUCRO BRUTO"] == 157
        assert linhas["(=) LUCRO LÍQUIDO"] == 144.55
    finally:
        planilha.close()
