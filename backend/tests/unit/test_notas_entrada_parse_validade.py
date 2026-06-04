import os
from datetime import date
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app import notas_entrada_routes as routes  # noqa: E402


def test_parse_nfe_xml_extrai_lote_e_validade_de_infadprod_no_det():
    xml = """
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
      <NFe>
        <infNFe Id="NFe123">
          <ide>
            <nNF>231564</nNF>
            <serie>1</serie>
            <dhEmi>2026-05-15T10:00:00-03:00</dhEmi>
          </ide>
          <emit>
            <CNPJ>12345678000199</CNPJ>
            <xNome>Fornecedor Teste</xNome>
            <xFant>Fornecedor Teste</xFant>
            <IE>123</IE>
          </emit>
          <det nItem="1">
            <prod>
              <cProd>023983.1</cProd>
              <xProd>Produto Teste</xProd>
              <NCM>23091000</NCM>
              <CFOP>5102</CFOP>
              <uCom>UN</uCom>
              <qCom>2.0000</qCom>
              <vUnCom>10.0000</vUnCom>
              <vProd>20.00</vProd>
              <cEAN>SEM GTIN</cEAN>
            </prod>
            <imposto />
            <infAdProd>LOTE: ABC123 VALIDADE: 31/08/2027</infAdProd>
          </det>
          <total>
            <ICMSTot>
              <vProd>20.00</vProd>
              <vFrete>0.00</vFrete>
              <vDesc>0.00</vDesc>
              <vNF>20.00</vNF>
            </ICMSTot>
          </total>
        </infNFe>
      </NFe>
    </nfeProc>
    """

    dados = routes.parse_nfe_xml(xml)

    assert dados["numero_nota"] == "231564"
    assert dados["itens"][0]["codigo_produto"] == "023983.1"
    assert dados["itens"][0]["lote"] == "ABC123"
    assert dados["itens"][0]["data_validade"] == date(2027, 8, 31)


def test_parse_nfe_xml_extrai_ean_comercial_e_ean_tributario():
    xml = """
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
      <NFe>
        <infNFe Id="NFe123">
          <ide>
            <nNF>9398</nNF>
            <serie>1</serie>
            <dhEmi>2026-06-02T10:00:00-03:00</dhEmi>
          </ide>
          <emit>
            <CNPJ>63287129000495</CNPJ>
            <xNome>SPECIAL DOG PET FOOD LTDA</xNome>
            <IE>123</IE>
          </emit>
          <det nItem="25">
            <prod>
              <cProd>150.050.003.008</cProd>
              <cEAN>17898242030073</cEAN>
              <xProd>BIONATURAL CAES RP AD FRANGO 4x2,5KG</xProd>
              <NCM>23091000</NCM>
              <CFOP>5102</CFOP>
              <uCom>FD</uCom>
              <qCom>2.0000</qCom>
              <vUnCom>123.4500</vUnCom>
              <vProd>246.90</vProd>
              <cEANTrib>7898242030076</cEANTrib>
            </prod>
            <imposto />
          </det>
          <total>
            <ICMSTot>
              <vProd>246.90</vProd>
              <vFrete>0.00</vFrete>
              <vDesc>0.00</vDesc>
              <vNF>246.90</vNF>
            </ICMSTot>
          </total>
        </infNFe>
      </NFe>
    </nfeProc>
    """

    dados = routes.parse_nfe_xml(xml)

    item = dados["itens"][0]
    assert item["ean"] == "17898242030073"
    assert item["ean_tributario"] == "7898242030076"


def test_aplicar_codigos_barras_nf_preenche_campos_vazios_preferindo_ean_tributario():
    produto = SimpleNamespace(
        codigo="6083",
        codigo_barras=None,
        gtin_ean=None,
        gtin_ean_tributario=None,
    )
    item = SimpleNamespace(ean="17898242030073", ean_tributario="7898242030076")

    atualizou = routes._aplicar_codigos_barras_item_no_produto(produto, item)

    assert atualizou is True
    assert produto.codigo_barras == "7898242030076"
    assert produto.gtin_ean == "17898242030073"
    assert produto.gtin_ean_tributario == "7898242030076"


def test_aplicar_codigos_barras_nf_nao_sobrescreve_codigo_existente_divergente():
    produto = SimpleNamespace(
        codigo="6083",
        codigo_barras="7898242030076",
        gtin_ean="17898242030073",
        gtin_ean_tributario="7898242030076",
    )
    item = SimpleNamespace(ean="11111111111111", ean_tributario="2222222222222")

    atualizou = routes._aplicar_codigos_barras_item_no_produto(produto, item)

    assert atualizou is False
    assert produto.codigo_barras == "7898242030076"
    assert produto.gtin_ean == "17898242030073"
    assert produto.gtin_ean_tributario == "7898242030076"


def test_monta_lotes_entrada_com_multiplos_rastros_do_xml():
    xml = """
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
      <NFe>
        <infNFe Id="NFe123">
          <det nItem="10">
            <prod>
              <cProd>023983.1</cProd>
              <xProd>Produto Teste</xProd>
              <rastro>
                <nLote>86925</nLote>
                <qLote>23.000</qLote>
                <dFab>2025-11-29</dFab>
                <dVal>2027-11-29</dVal>
              </rastro>
              <rastro>
                <nLote>93325</nLote>
                <qLote>17.000</qLote>
                <dFab>2025-12-18</dFab>
                <dVal>2027-12-18</dVal>
              </rastro>
            </prod>
          </det>
        </infNFe>
      </NFe>
    </nfeProc>
    """
    lotes_por_item = routes._mapear_lotes_rastro_xml(xml)
    item = SimpleNamespace(numero_item=10, lote="86925", data_validade=date(2027, 11, 29))
    nota = SimpleNamespace(numero_nota="231564")

    lotes = routes._montar_lotes_entrada_item(
        item,
        nota,
        quantidade_entrada=40,
        lotes_rastro_por_item=lotes_por_item,
    )

    assert [(lote["nome_lote"], lote["quantidade"]) for lote in lotes] == [
        ("86925", 23),
        ("93325", 17),
    ]
    assert lotes[0]["data_validade"].date() == date(2027, 11, 29)
    assert lotes[1]["data_validade"].date() == date(2027, 12, 18)
