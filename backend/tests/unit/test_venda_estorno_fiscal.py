from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.intnfe.cancellation import campos_cancelamento_com_aliases
from app.vendas.fiscal_status import (
    nota_fiscal_requer_regularizacao,
    pendencia_fiscal_cancelamento,
    sincronizar_venda_apos_estorno,
)


def dados():
    venda = SimpleNamespace(
        id=12,
        tenant_id=uuid4(),
        status="cancelada",
        nfe_status="autorizada",
        nfe_ambiente=1,
        nfe_chave="1" * 44,
        nfe_protocolo="141261734844045",
        nfe_estorno_status=None,
        nfe_estorno_numero=None,
        nfe_estorno_serie=None,
        nfe_estorno_protocolo=None,
    )
    estorno = SimpleNamespace(
        tenant_id=venda.tenant_id,
        venda_id=venda.id,
        ambiente_codigo=1,
        status="autorizado",
        xml_validado=True,
        numero=55,
        serie=3,
        protocolo="141261734844999",
    )
    return venda, estorno


def test_estorno_confirmado_fecha_pendencia_sem_cancelar_nota_original():
    venda, estorno = dados()
    assert pendencia_fiscal_cancelamento(venda)
    db = MagicMock()
    sincronizar_venda_apos_estorno(db, venda, estorno)
    assert venda.status == "cancelada"
    assert venda.nfe_status == "autorizada"
    assert venda.nfe_chave == "1" * 44
    assert venda.nfe_protocolo == "141261734844045"
    assert nota_fiscal_requer_regularizacao(
        venda
    )  # Continua protegida contra exclusão.
    assert not pendencia_fiscal_cancelamento(venda)
    db.delete.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "status",
    ["enviando", "processando", "incerto", "rejeitado", "divergente", "cancelado"],
)
def test_estorno_sem_autorizacao_preserva_pendencia(status):
    venda, estorno = dados()
    estorno.status = status
    sincronizar_venda_apos_estorno(MagicMock(), venda, estorno)
    assert pendencia_fiscal_cancelamento(venda)


def test_homologacao_nao_regulariza_nota_de_producao():
    venda, estorno = dados()
    estorno.ambiente_codigo = 2
    sincronizar_venda_apos_estorno(MagicMock(), venda, estorno)
    assert venda.nfe_estorno_status is None
    assert pendencia_fiscal_cancelamento(venda)


@pytest.mark.parametrize("campo", ["tenant_id", "venda_id"])
def test_estorno_de_outra_empresa_ou_venda_nao_se_aplica(campo):
    venda, estorno = dados()
    setattr(estorno, campo, uuid4() if campo == "tenant_id" else 13)
    with pytest.raises(ValueError):
        sincronizar_venda_apos_estorno(MagicMock(), venda, estorno)
    assert venda.nfe_estorno_status is None


def test_autorizacao_sem_comprovante_xml_nao_fecha_pendencia():
    venda, estorno = dados()
    estorno.xml_validado = False
    with pytest.raises(ValueError):
        sincronizar_venda_apos_estorno(MagicMock(), venda, estorno)
    assert pendencia_fiscal_cancelamento(venda)


def test_serializacao_nao_expoe_objetos_mock_ou_campos_incompativeis():
    campos = campos_cancelamento_com_aliases(MagicMock())
    assert campos["nfe_estorno_status"] is None
    assert campos["nfe_estorno_numero"] is None
