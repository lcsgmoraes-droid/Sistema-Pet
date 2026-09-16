from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import nfe_routes
from app.intnfe.sharing import extrair_link_publico_nfce


LINK_SEFAZ = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=chave|2|1|token"
CHAVE_NFE_TESTE = "3" * 44


def _xml_nfce(link=LINK_SEFAZ):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
      <NFe><infNFe Id="NFe{CHAVE_NFE_TESTE}"><ide><mod>65</mod></ide></infNFe>
        <infNFeSupl><qrCode><![CDATA[{link}]]></qrCode></infNFeSupl>
      </NFe>
    </nfeProc>"""


def test_extrai_link_publico_sefaz_do_xml_autorizado():
    assert extrair_link_publico_nfce(_xml_nfce()) == LINK_SEFAZ


def test_rejeita_link_fora_de_dominio_governamental():
    with pytest.raises(ValueError, match="não pertence à SEFAZ"):
        extrair_link_publico_nfce(_xml_nfce("https://exemplo.com/nota"))


def test_prepara_compartilhamento_intnfe_com_cliente_e_link_oficial():
    venda = SimpleNamespace(
        id=1476,
        tenant_id="tenant-1",
        nfe_provider="intnfe",
        nfe_correlation_id="corr-50",
        nfe_status="autorizada",
        nfe_tipo="nfce",
        nfe_modelo=65,
        nfe_xml=_xml_nfce(),
        nfe_numero=50,
        cliente=SimpleNamespace(
            nome="Camila Silva Pinto",
            razao_social=None,
            celular="18999990000",
            telefone=None,
        ),
    )

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return venda

    class Db:
        def query(self, _model):
            return Query()

    resultado = nfe_routes.preparar_compartilhamento_intnfe(
        venda.id,
        db=Db(),
        user_and_tenant=(object(), "tenant-1"),
    )

    assert resultado == {
        "link": LINK_SEFAZ,
        "telefone": "18999990000",
        "cliente": "Camila Silva Pinto",
        "numero": 50,
        "modelo": 65,
    }


def test_compartilhamento_intnfe_exige_nota_autorizada():
    venda = SimpleNamespace(
        tenant_id="tenant-1",
        nfe_provider="intnfe",
        nfe_correlation_id="corr-50",
        nfe_status="rejeitada",
    )

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return venda

    class Db:
        def query(self, _model):
            return Query()

    with pytest.raises(HTTPException) as erro:
        nfe_routes.preparar_compartilhamento_intnfe(
            1476,
            db=Db(),
            user_and_tenant=(object(), "tenant-1"),
        )

    assert erro.value.status_code == 409
