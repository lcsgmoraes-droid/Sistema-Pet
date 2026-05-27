from datetime import date
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db",
)

from app.notas_entrada_pdf_parser import (
    PDFEntradaFornecedor,
    build_pdf_synthetic_nfe_xml,
    parse_pedido_pdf_text,
)
from app.notas_entrada_routes import (
    _aplicar_dados_fiscais_item_no_produto,
    parse_nfe_xml,
)


PEDIDO_2_TEXT = """
CODIGO PRODUTO
117061
QTDE UNITARIO VL TOTAL
22/05/20269541
CLIENTE LJ COMERCIO DE RACOES E PET SHOP LTDA 2406
ENDERECO BAIRRO VILA INDUSTRIAL
CIDADE PRESIDENTE PRUDENTE FONE (18) 3928-9584
AVENIDA BRASIL,        2550
ROMANEIO DE CARGAS:
UNI
CODIGO
PEDIDO
00009038 LOLLY CAES FILHOTES CARNE 10,1KG 2 62,03 124,06SC
30200068 LAND DOG 25KG 3 78,40 235,20SC
00009011 LOLLY CAES CARNE E BATATA DOCE 15KG 16 82,38 1.318,08SC
00009013 LOLLY GATOS MIX CARNE FRANGO PEIXE 20KG 3 122,09 366,27SC
30200002 KIDAN 15 KG 4 44,34 177,36SC
PESO TOTAL: 455,200 Kg VALOR TOTAL: 2.220,97EMPRESAREPRESENTANTE:
1 de 1
BOLETO 19/06/26 03/07/2626/06/26
740,33 740,32 740,3228/35/42
"""

PEDIDO_2_PDFPLUMBER_TEXT = """
PEDIDO 117061 ROMANEIO DE CARGAS: 9541 22/05/2026
CLIENTE LJ COMERCIO DE RACOES E PET SHOP LTDA CODIGO 2406
ENDERECO AVENIDA BRASIL, 2550 BAIRRO VILA INDUSTRIAL
CIDADE PRESIDENTE PRUDENTE FONE (18) 3928-9584
CODIGO PRODUTO UNI QTDE UNITARIO VL TOTAL
00009038 LOLLY CAES FILHOTES CARNE 10,1KG SC 2 62,03 124,06
30200068 LAND DOG 25KG SC 3 78,40 235,20
00009011 LOLLY CAES CARNE E BATATA DOCE 15KG SC 16 82,38 1.318,08
00009013 LOLLY GATOS MIX CARNE FRANGO PEIXE 20KG SC 3 122,09 366,27
30200002 KIDAN 15 KG SC 4 44,34 177,36
1 de 1
BOLETO 19/06/26 26/06/26 03/07/26
28/35/42 740,33 740,32 740,32
REPRESENTANTE: EMPRESA PESO TOTAL: 455,200 Kg VALOR TOTAL: 2.220,97
"""

PEDIDO_1_PDFPLUMBER_TEXT = """
PEDIDO 117058 ROMANEIO DE CARGAS: 9541 22/05/2026
CLIENTE LJ COMERCIO DE RACOES E PET SHOP LTDA CODIGO 2406
ENDERECO AVENIDA BRASIL, 2550 BAIRRO VILA INDUSTRIAL
CIDADE PRESIDENTE PRUDENTE FONE (18) 3928-9584
CODIGO PRODUTO UNI QTDE UNITARIO VL TOTAL
MRN00869 PIPICAT ULTRA DRY 4KG UN 48 32,05 1.538,40
PAN01058 PIPICAT FLORAL SC 12KG SC 14 31,22 437,08
MRN00916 PIPICAT BIO BUT CEREAIS 7SD 2,2KG UN 2 22,62 45,24
0579 AGUA SANITARIA RAJJA 3 X 5L CX 1 30,01 30,01
MRN00876 PIPICAT BIANCO ORIGINAL 1,8KG UN 60 9,60 576,00
PAN01115 PIPICAT CLASSIC SC 20KG SC 10 34,08 340,80
MRN00870 PIPICAT ULTRA CONTROL BUT 4KG UN 6 27,82 166,92
3000055 BIRBO AD CARNE 25KG SC 1 115,90 115,90
PAN01063 PIPICAT MULTICAT SC 12KG SC 3 25,02 75,06
PAN01069 MITZI FD 6X4 KG FD 1 41,26 41,26
1 de 2
BOLETO 11/06/26 01/07/26 21/07/26
20/40/60 1.178,27 1.178,26 1.178,26
REPRESENTANTE: EMPRESA PESO TOTAL: 823,000 Kg VALOR TOTAL: 3.534,79
PEDIDO 117058 ROMANEIO DE CARGAS: 9541 22/05/2026
CLIENTE LJ COMERCIO DE RACOES E PET SHOP LTDA CODIGO 2406
ENDERECO AVENIDA BRASIL, 2550 BAIRRO VILA INDUSTRIAL
CIDADE PRESIDENTE PRUDENTE FONE (18) 3928-9584
CODIGO PRODUTO UNI QTDE UNITARIO VL TOTAL
MRN00877 PIPICAT BIANCO SENSITIVE 1,8KG UN 6 14,01 84,06
MRN00889 PIPICAT BIANCO LAVANDA 1,8KG UN 6 14,01 84,06
2 de 2
BOLETO 11/06/26 01/07/26 21/07/26
20/40/60 1.178,27 1.178,26 1.178,26
REPRESENTANTE: EMPRESA PESO TOTAL: 823,000 Kg VALOR TOTAL: 3.534,79
"""

PEDIDO_APP_VENDAS_MOBILE_TEXT = """
Juliana Lacerda
CNPJ:43922456000111
Cidade:Presidente Prudente -Sp
Fones: 18 99795-2282/
E-mail: julysanchezpp@hotmail.com
26/05/2026 11:13:09 PEDIDO N°:241
Empresa PETS MAR DISTRIBUIDORA LTDA
Número Vencimento Valor Número Vencimento Valor Número Vencimento Valor
241/1-1 26/05/2026 1.220,00
Código Descrição Unid. Qtde. Vlr. unit. Desconto Vlr. total
36 Osso nò 10/11 a granel 1 kilo 10 61,00 610,00
35 Osso nò 9/10 a granel 1 kilo 10 61,00 610,00
2 itens Peso liq.:0 Peso bru.:0 Volumes:20 Total unid.:0 1.220,00 0,00 1.220,00
Desconto (0%): 0,00
Vlr.frete: 0,00
----------------------- ----------------------- Total:R$ 1.220,00
APP VENDAS MOBILE Ass. vendedor Ass. cliente
"""


def test_parse_pedido_pdf_text_extracts_order_items_total_and_installments():
    pedido = parse_pedido_pdf_text(PEDIDO_2_TEXT)

    assert pedido.numero_pedido == "117061"
    assert pedido.data_emissao == date(2026, 5, 22)
    assert pedido.valor_total == pytest.approx(2220.97)
    assert pedido.peso_total_kg == pytest.approx(455.2)

    assert len(pedido.itens) == 5
    primeiro = pedido.itens[0]
    assert primeiro.codigo == "00009038"
    assert primeiro.descricao == "LOLLY CAES FILHOTES CARNE 10,1KG"
    assert primeiro.quantidade == pytest.approx(2)
    assert primeiro.valor_unitario == pytest.approx(62.03)
    assert primeiro.valor_total == pytest.approx(124.06)
    assert primeiro.unidade == "SC"

    assert [(dup.vencimento, dup.valor) for dup in pedido.duplicatas] == [
        (date(2026, 6, 19), pytest.approx(740.33)),
        (date(2026, 6, 26), pytest.approx(740.32)),
        (date(2026, 7, 3), pytest.approx(740.32)),
    ]


def test_parse_pedido_pdf_text_accepts_pdfplumber_layout_from_real_file():
    pedido = parse_pedido_pdf_text(PEDIDO_2_PDFPLUMBER_TEXT)

    assert pedido.numero_pedido == "117061"
    assert pedido.data_emissao == date(2026, 5, 22)
    assert len(pedido.itens) == 5
    assert pedido.itens[0].unidade == "SC"
    assert pedido.itens[0].quantidade == pytest.approx(2)
    assert pedido.itens[2].valor_total == pytest.approx(1318.08)
    assert [(dup.vencimento, dup.valor) for dup in pedido.duplicatas] == [
        (date(2026, 6, 19), pytest.approx(740.33)),
        (date(2026, 6, 26), pytest.approx(740.32)),
        (date(2026, 7, 3), pytest.approx(740.32)),
    ]


def test_parse_pedido_pdf_text_accepts_alphanumeric_and_multipage_items():
    pedido = parse_pedido_pdf_text(PEDIDO_1_PDFPLUMBER_TEXT)

    assert pedido.numero_pedido == "117058"
    assert pedido.data_emissao == date(2026, 5, 22)
    assert pedido.valor_total == pytest.approx(3534.79)
    assert pedido.valor_produtos == pytest.approx(3534.79)
    assert pedido.peso_total_kg == pytest.approx(823.0)

    assert len(pedido.itens) == 12
    assert pedido.itens[0].codigo == "MRN00869"
    assert pedido.itens[0].descricao == "PIPICAT ULTRA DRY 4KG"
    assert pedido.itens[0].unidade == "UN"
    assert pedido.itens[0].quantidade == pytest.approx(48)
    assert pedido.itens[0].valor_total == pytest.approx(1538.40)
    assert pedido.itens[3].codigo == "0579"
    assert pedido.itens[3].descricao == "AGUA SANITARIA RAJJA 3 X 5L"
    assert pedido.itens[-1].codigo == "MRN00889"
    assert pedido.itens[-1].valor_total == pytest.approx(84.06)

    assert [(dup.vencimento, dup.valor) for dup in pedido.duplicatas] == [
        (date(2026, 6, 11), pytest.approx(1178.27)),
        (date(2026, 7, 1), pytest.approx(1178.26)),
        (date(2026, 7, 21), pytest.approx(1178.26)),
    ]


def test_parse_pedido_pdf_text_accepts_app_vendas_mobile_layout():
    pedido = parse_pedido_pdf_text(PEDIDO_APP_VENDAS_MOBILE_TEXT)

    assert pedido.numero_pedido == "241"
    assert pedido.data_emissao == date(2026, 5, 26)
    assert pedido.valor_total == pytest.approx(1220.00)
    assert pedido.valor_produtos == pytest.approx(1220.00)

    assert len(pedido.itens) == 2
    assert pedido.itens[0].codigo == "36"
    assert pedido.itens[0].descricao == "Osso nò 10/11 a granel 1 kilo"
    assert pedido.itens[0].quantidade == pytest.approx(10)
    assert pedido.itens[0].valor_unitario == pytest.approx(61.00)
    assert pedido.itens[0].valor_total == pytest.approx(610.00)
    assert pedido.itens[0].unidade == "UN"

    assert pedido.itens[1].codigo == "35"
    assert pedido.itens[1].descricao == "Osso nò 9/10 a granel 1 kilo"
    assert [(dup.vencimento, dup.valor) for dup in pedido.duplicatas] == [
        (date(2026, 5, 26), pytest.approx(1220.00)),
    ]


def test_build_pdf_synthetic_nfe_xml_is_compatible_with_existing_nfe_parser():
    pedido = parse_pedido_pdf_text(PEDIDO_2_TEXT)
    fornecedor = PDFEntradaFornecedor(
        id=77,
        nome="Fornecedor PDF Teste",
        cnpj="12.345.678/0001-90",
    )

    xml_content = build_pdf_synthetic_nfe_xml(pedido, fornecedor, tenant_id=3)
    dados_nfe = parse_nfe_xml(xml_content)

    assert dados_nfe["numero_nota"] == "117061"
    assert dados_nfe["serie"] == "PDF"
    assert dados_nfe["fornecedor_nome"] == "Fornecedor PDF Teste"
    assert dados_nfe["fornecedor_cnpj"] == "12345678000190"
    assert dados_nfe["valor_total"] == pytest.approx(2220.97)
    assert len(dados_nfe["itens"]) == 5
    assert dados_nfe["itens"][1]["codigo_produto"] == "30200068"
    assert dados_nfe["itens"][1]["descricao"] == "LAND DOG 25KG"
    assert dados_nfe["duplicatas"][2]["vencimento"] == date(2026, 7, 3)


def test_apply_fiscal_data_preserves_product_fields_when_pdf_item_is_empty():
    produto = SimpleNamespace(
        ncm="23091000",
        cfop="5405",
        cest="1234567",
        origem="0",
        aliquota_icms=18.0,
        aliquota_pis=1.65,
        aliquota_cofins=7.6,
    )
    item_pdf = SimpleNamespace(
        ncm="",
        cfop="",
        cest=None,
        origem="",
        aliquota_icms=None,
        aliquota_pis=None,
        aliquota_cofins=None,
    )

    atualizou = _aplicar_dados_fiscais_item_no_produto(produto, item_pdf)

    assert atualizou is False
    assert produto.ncm == "23091000"
    assert produto.cfop == "5405"
    assert produto.cest == "1234567"
    assert produto.origem == "0"
    assert produto.aliquota_icms == pytest.approx(18.0)


def test_apply_fiscal_data_fills_missing_product_fields_from_xml_item():
    produto = SimpleNamespace(
        ncm="",
        cfop=None,
        cest=None,
        origem=None,
        aliquota_icms=None,
        aliquota_pis=None,
        aliquota_cofins=None,
    )
    item_xml = SimpleNamespace(
        ncm="23091000",
        cfop="5405",
        cest="1234567",
        origem="0",
        aliquota_icms=18.0,
        aliquota_pis=1.65,
        aliquota_cofins=7.6,
    )

    atualizou = _aplicar_dados_fiscais_item_no_produto(produto, item_xml)

    assert atualizou is True
    assert produto.ncm == "23091000"
    assert produto.cfop == "5405"
    assert produto.cest == "1234567"
    assert produto.origem == "0"
    assert produto.aliquota_icms == pytest.approx(18.0)
