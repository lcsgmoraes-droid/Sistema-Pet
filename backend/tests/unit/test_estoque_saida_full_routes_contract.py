from io import BytesIO
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import estoque_saida_full_routes
from app.estoque_saida_full import parser_routes


ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_saida_full_routes_ficam_em_router_dedicado():
    routes = set()
    for route in estoque_saida_full_routes.router.routes:
        if hasattr(route, "path"):
            routes.add((route.path, ",".join(sorted(route.methods))))
            continue

        prefix = route.include_context.prefix
        routes.update(
            (f"{prefix}{nested.path}", ",".join(sorted(nested.methods)))
            for nested in route.original_router.routes
        )

    assert ("/estoque/saida-full-nf/historico", "GET") in routes
    assert ("/estoque/saida-full-nf/{numero_nf}/canal", "PUT") in routes
    assert ("/estoque/saida-full-nf/validar-estoque", "POST") in routes
    assert ("/estoque/saida-full-nf", "POST") in routes
    assert ("/estoque/saida-full-pdf/parse", "POST") in routes
    assert ("/estoque/saida-full-xml/parse", "POST") in routes


def test_estoque_routes_nao_expõe_mais_rotas_saida_full():
    source = _source("app/estoque_routes.py")

    assert '"/saida-full-nf' not in source
    assert '"/saida-full-pdf/parse"' not in source
    assert '"/saida-full-xml/parse"' not in source
    assert "class SaidaFullNFRequest" not in source
    assert "def saida_full_por_nf(" not in source


def test_main_registra_router_de_saida_full():
    main_source = _source("app/main_routers.py")

    assert (
        "from app.estoque_saida_full_routes import router as estoque_saida_full_router"
        in main_source
    )
    assert (
        'app.include_router(estoque_saida_full_router, tags=["Estoque - Saida FULL"])'
        in main_source
    )


def test_parser_pdf_saida_full_nao_usa_regex_de_sku_e_quantidade():
    source = _source("app/estoque_saida_full_routes.py")

    assert "SKU_EXPLICITO_REGEX" not in source
    assert "QTD_EXPLICITA_REGEX" not in source
    assert "SKU_QTD_LINHA_REGEX" not in source


def test_parser_pdf_saida_full_extrai_sku_quantidade_explicitos_e_em_linha():
    itens = estoque_saida_full_routes._extrair_itens_full_pdf(
        "\n".join(
            [
                "Produto A SKU: ABC-123 QTD: 2",
                "codigo # ABC-123 quantidade 1,5",
                "XYZ_999 3",
                "Linha sem item",
            ]
        )
    )

    assert itens == [
        {"sku": "ABC-123", "quantidade": 3.5},
        {"sku": "XYZ_999", "quantidade": 3.0},
    ]


def test_parser_pdf_saida_full_le_inbound_real_do_mercado_livre():
    dados = estoque_saida_full_routes._parse_saida_full_pdf(
        """
        Frete#73581550
        Produtos do envio:6|Total de unidades:335
        Codigo ML: XWPE19854 Codigo universal: 50 Etiquetagem
        7898401960398 SKU: 013267.1 obrigatoria
        Codigo ML: AKYR51637 Codigo universal: 7898401961999 100 Etiquetagem
        SKU: 022860.1 obrigatoria
        Codigo ML: FWEM52238 Codigo universal: 45 Etiquetagem
        7898401962019 SKU: 022861.1 obrigatoria
        Codigo ML: JMAH74400 Codigo universal: 10 Etiquetagem
        7898929877611 SKU: 013214.1 obrigatoria
        Codigo ML: MPLC74162 Codigo universal: 120 Etiquetagem
        7898929878540 SKU: 013248.1 obrigatoria
        Codigo ML: USIV19655 Codigo universal: 7898401960411 10 Etiquetagem
        SKU: 013269.1 obrigatoria
        """
    )

    assert dados == {
        "numero_documento": "ML-FRETE-73581550",
        "numero_nf": "ML-FRETE-73581550",
        "tipo_documento": "mercado_livre_inbound",
        "plataforma_sugerida": "mercado_livre",
        "total_itens": 6,
        "total_unidades": 335.0,
        "itens": [
            {"sku": "013267.1", "quantidade": 50.0},
            {"sku": "022860.1", "quantidade": 100.0},
            {"sku": "022861.1", "quantidade": 45.0},
            {"sku": "013214.1", "quantidade": 10.0},
            {"sku": "013248.1", "quantidade": 120.0},
            {"sku": "013269.1", "quantidade": 10.0},
        ],
    }


def test_parser_pdf_saida_full_le_picking_list_real_da_shopee():
    dados = estoque_saida_full_routes._parse_saida_full_pdf(
        """
        Shopee Picking List - Shopee Fulfillment
        Informacao de Inbound
        Data de Inbound ID de Envio (ASN ID) INBRFSP12608050215
        No. SKU do Shopee SKU ID Nome do Produto Variacao SKU do Qnt.
        vendedor Armazem Aprovada
        013251.1 42676789641_4 Produto A Item without 12
        020301.1 42676789643_4 Produto B Item without 21
        013209.1 42776789605_2 Produto C 7898929877 11
        018631.1 42876789640_3 Produto D 1 Unidade Item without 73
        025847.1/1 43176789635_3 Produto E 1 unidade Item without 31
        021765.1/1 43376789626_4 Produto F 1 unidade 7898401961 34
        025848.1/1 44802195781_4 Produto G 1 unidade Item without 22
        013269.1 51452175811_4 Produto H 7898401960 29
        022204.1 51452175898_4 Produto I 7898401961 10
        023983.1/2 51552175880_3 Produto J 2 unidades Item without 13
        013252.1/1 51852175873_4 Produto K 1 unidade Item without 21
        013248.1/2 56202166866_3 Produto L 2 unidades Item without 20
        020299.1 56902161847_4 Produto M 7898401961 13
        022860.1/1 57202161752_2 Produto N 1 unidade 7895455616 20
        022860.1/2 57202161752_2 Produto N 2 unidades 7895455616 5
        013256.1 57202166804_4 Produto O 7898401960 21
        013215.1 57202166878_1 Produto P 7898929877 15
        019516.1/1 57702161734_2 Produto Q 1 unidade Item without 14
        019516.1/2 57702161734_2 Produto Q 2 unidades Item without 13
        Notas Total 398
        """
    )

    assert dados["numero_documento"] == "INBRFSP12608050215"
    assert dados["numero_nf"] == "INBRFSP12608050215"
    assert dados["tipo_documento"] == "shopee_inbound"
    assert dados["plataforma_sugerida"] == "shopee"
    assert dados["total_itens"] == 19
    assert dados["total_unidades"] == 398.0
    assert dados["itens"] == [
        {"sku": "013251.1", "quantidade": 12.0},
        {"sku": "020301.1", "quantidade": 21.0},
        {"sku": "013209.1", "quantidade": 11.0},
        {"sku": "018631.1", "quantidade": 73.0},
        {"sku": "025847.1/1", "quantidade": 31.0},
        {"sku": "021765.1/1", "quantidade": 34.0},
        {"sku": "025848.1/1", "quantidade": 22.0},
        {"sku": "013269.1", "quantidade": 29.0},
        {"sku": "022204.1", "quantidade": 10.0},
        {"sku": "023983.1/2", "quantidade": 13.0},
        {"sku": "013252.1/1", "quantidade": 21.0},
        {"sku": "013248.1/2", "quantidade": 20.0},
        {"sku": "020299.1", "quantidade": 13.0},
        {"sku": "022860.1/1", "quantidade": 20.0},
        {"sku": "022860.1/2", "quantidade": 5.0},
        {"sku": "013256.1", "quantidade": 21.0},
        {"sku": "013215.1", "quantidade": 15.0},
        {"sku": "019516.1/1", "quantidade": 14.0},
        {"sku": "019516.1/2", "quantidade": 13.0},
    ]


def test_parser_pdf_saida_full_le_danfe_de_remessa():
    dados = estoque_saida_full_routes._parse_saida_full_pdf(
        """
        NF-e
        N 000.016.676
        DANFE Documento Auxiliar da Nota Fiscal Eletronica
        DESTINATARIO / REMETENTE
        EBAZAR.COM.BR LTDA
        DADOS DO PRODUTO / SERVICOS
        CODIGO DESCRICAO DOS PRODUTOS / SERVICOS NCM/SH CSOSN CFOP UNID. QTD.
        013267.1 MGZ EXT PAPAGAIOS REGULAR 600GR 23091000 0400 5949 UNID 50 47,56
        013214.1 MGZ MIX PAPAGAIOS 350GR 23099010 0400 5949 UNID 10 33,45
        022861.1 MGZ EXT PORQUINHO-DA-INDIA 1,2 KG 23099010 0400 5949 UNID 45 78,90
        013248.1 MGZ COELHO ORNAMENTAIS 500GR 23099090 0400 5949 UNID 120 42,86
        022860.1 MGZ EXT COELHOS ORNAMENTAIS 1,2 KG 23099010 0400 5949 UNID 100 92,80
        013269.1 MGZ EXT PAPAGAIOS LARGE 600GR 23091000 0400 5949 UNID 10 54,93
        CALCULO DO ISSQN
        """
    )

    assert dados["numero_documento"] == "16676"
    assert dados["tipo_documento"] == "danfe"
    assert dados["plataforma_sugerida"] == "mercado_livre"
    assert dados["total_unidades"] == 335.0
    assert dados["itens"] == [
        {"sku": "013267.1", "quantidade": 50.0},
        {"sku": "013214.1", "quantidade": 10.0},
        {"sku": "022861.1", "quantidade": 45.0},
        {"sku": "013248.1", "quantidade": 120.0},
        {"sku": "022860.1", "quantidade": 100.0},
        {"sku": "013269.1", "quantidade": 10.0},
    ]


def test_parser_pdf_saida_full_reconhece_campos_de_remessa_amazon():
    dados = estoque_saida_full_routes._parse_saida_full_pdf(
        """
        Amazon FBA - Shipment ID FBA19GQRV5K4
        MSKU: 013267.1FBA Quantidade: 20
        MSKU: 013268.1FBA
        Unidades: 5
        """
    )

    assert dados["numero_documento"] == "FBA19GQRV5K4"
    assert dados["tipo_documento"] == "amazon_inbound"
    assert dados["plataforma_sugerida"] == "amazon"
    assert dados["itens"] == [
        {"sku": "013267.1FBA", "quantidade": 20.0},
        {"sku": "013268.1FBA", "quantidade": 5.0},
    ]


def test_parser_pdf_saida_full_le_tabelas_do_danfe_amazon_em_duas_paginas():
    cabecalho = [
        "C�DIGO",
        "DESCRI��O DOS PRODUTOS / SERVI�OS",
        "NCM/SH",
        "CSOSN",
        "CFOP",
        "UNID",
        "QUANT.",
        "VALOR UNIT�RIO",
    ]

    def linha_item(sku, quantidade):
        return [
            sku,
            "Produto Amazon\nFNSKU:X000TESTE;",
            "23099010",
            "0400",
            "5949",
            "UN",
            str(quantidade),
            "10,00",
        ]

    itens_pagina_1 = [
        ("013195.1FBA", 3),
        ("013210.1FBA", 20),
        ("013221.1FBA", 20),
        ("013248.1FBA", 30),
        ("013250.1FBA", 20),
        ("013252.1FBAA", 50),
    ]
    itens_pagina_2 = [
        ("013260.1FBA", 20),
        ("013267.1FBA", 20),
        ("013270.1FBA", 10),
        ("013288.1FBA", 20),
        ("013808.1FBA", 20),
        ("015006.1FBA", 6),
        ("018631.1FBA", 150),
        ("020301.1FBA", 20),
        ("023983.1FBA", 50),
        ("024044.1FBA", 30),
        ("026947.1FBA", 20),
        ("030035.1FBA", 20),
    ]
    tabelas_paginas = [
        [[cabecalho, *[linha_item(*item) for item in itens_pagina_1]]],
        [[cabecalho, *[linha_item(*item) for item in itens_pagina_2]]],
    ]

    dados = estoque_saida_full_routes._parse_saida_full_pdf(
        """
        NF-e N 000.020.268
        DANFE Documento Auxiliar da Nota Fiscal Eletronica
        AMAZON SERVICOS DE VAREJO DO BRASIL LTDA
        DADOS DOS PRODUTOS / SERVI�OS
        DADOS ADICIONAIS
        DADOS DOS PRODUTOS / SERVI�OS
        """,
        tabelas_paginas=tabelas_paginas,
    )

    assert dados["numero_documento"] == "20268"
    assert dados["tipo_documento"] == "danfe"
    assert dados["plataforma_sugerida"] == "amazon"
    assert dados["total_itens"] == 18
    assert dados["total_unidades"] == 529.0
    assert dados["itens"] == [
        {"sku": sku, "quantidade": float(quantidade)}
        for sku, quantidade in itens_pagina_1 + itens_pagina_2
    ]


@pytest.mark.asyncio
async def test_rota_pdf_saida_full_repassa_tabelas_de_todas_as_paginas(
    monkeypatch,
):
    class PaginaFake:
        def __init__(self, numero):
            self.numero = numero

        def extract_text(self):
            return f"DANFE pagina {self.numero}"

        def extract_tables(self):
            return [[f"tabela-pagina-{self.numero}"]]

    class PdfFake:
        pages = [PaginaFake(1), PaginaFake(2)]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    capturado = {}

    def parse_fake(texto, tabelas_paginas=None):
        capturado["texto"] = texto
        capturado["tabelas_paginas"] = tabelas_paginas
        return {"itens": [{"sku": "SKU-1", "quantidade": 1.0}]}

    monkeypatch.setattr(
        parser_routes,
        "pdfplumber",
        SimpleNamespace(open=lambda _arquivo: PdfFake()),
    )
    monkeypatch.setattr(parser_routes, "_parse_saida_full_pdf", parse_fake)

    resultado = await parser_routes.parse_saida_full_pdf(
        UploadFile(filename="danfe.pdf", file=BytesIO(b"%PDF-fake")),
        _user_and_tenant=None,
    )

    assert resultado["success"] is True
    assert capturado == {
        "texto": "DANFE pagina 1\nDANFE pagina 2",
        "tabelas_paginas": [
            [["tabela-pagina-1"]],
            [["tabela-pagina-2"]],
        ],
    }


def test_saida_full_routes_vira_fachada_com_modulos_dedicados():
    fachada = _source("app/estoque_saida_full_routes.py")

    assert len(fachada.splitlines()) <= 145
    assert "from .estoque_saida_full.routes import router" in fachada
    assert "def saida_full_por_nf(" not in fachada
    assert "def parse_saida_full_pdf(" not in fachada
    assert "def _criar_conta_pagar_tarifa_full_nf(" not in fachada

    modulos = [
        "app/estoque_saida_full/nf_routes.py",
        "app/estoque_saida_full/parser_routes.py",
        "app/estoque_saida_full/parsers.py",
        "app/estoque_saida_full/financeiro.py",
    ]
    for modulo in modulos:
        source = _source(modulo)
        assert len(source.splitlines()) <= 700

    assert "_parse_saida_full_xml" in _source("app/estoque_saida_full/parsers.py")
    assert "_parse_saida_full_pdf" in _source("app/estoque_saida_full/parsers.py")
    assert "_criar_conta_pagar_tarifa_full_nf" in _source(
        "app/estoque_saida_full/financeiro.py"
    )
    assert '@router.post("/saida-full-pdf/parse")' in _source(
        "app/estoque_saida_full/parser_routes.py"
    )


def test_parser_xml_saida_full_evita_literal_http_e_preserva_namespace_nfe():
    source = _source("app/estoque_saida_full/parsers.py")

    literal_namespace = '"http' + '://www.portalfiscal.inf.br/nfe"'
    assert literal_namespace not in source

    namespace = "http" + "://www.portalfiscal.inf.br/nfe"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="{namespace}">
      <NFe>
        <infNFe>
          <ide><nNF>12345</nNF></ide>
          <det><prod><cProd>SKU-1</cProd><qCom>2.0000</qCom></prod></det>
          <det><prod><cProd>SKU-1</cProd><qCom>1.5000</qCom></prod></det>
        </infNFe>
      </NFe>
    </nfeProc>
    """.encode()

    dados = estoque_saida_full_routes._parse_saida_full_xml(xml)

    assert dados == {
        "numero_nf": "12345",
        "total_itens": 1,
        "itens": [{"sku": "SKU-1", "quantidade": 3.5}],
    }
