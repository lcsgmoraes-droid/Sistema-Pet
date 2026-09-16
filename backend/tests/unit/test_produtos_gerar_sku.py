from unittest.mock import MagicMock
from uuid import uuid4

from app.produtos.codigo_sku_routes import gerar_sku


def _db_com_codigos(*codigos):
    db = MagicMock()
    consulta = db.query.return_value.filter.return_value.order_by.return_value
    consulta.all.return_value = [(codigo,) for codigo in codigos]
    return db


def test_gerar_sku_pula_toda_faixa_ja_ocupada():
    db = _db_com_codigos(
        "PROD-00012",
        "PROD-00032",
        "PROD-00022",
        "PROD-00016",
        "PROD-00015",
        "PROD-00014",
        "PROD-00013",
    )

    resposta = gerar_sku(
        prefixo="PROD",
        db=db,
        user_and_tenant=(object(), uuid4()),
    )

    assert resposta == {
        "sku": "PROD-00017",
        "prefixo": "PROD",
        "numero": 17,
        "disponivel": True,
    }


def test_gerar_sku_ignora_sufixo_nao_numerico_mais_recente():
    db = _db_com_codigos("PROD-ESPECIAL", "PROD-00003", "PROD-00002")

    resposta = gerar_sku(
        prefixo="prod",
        db=db,
        user_and_tenant=(object(), uuid4()),
    )

    assert resposta["sku"] == "PROD-00004"
    assert resposta["numero"] == 4


def test_gerar_sku_trata_numero_com_padding_diferente_como_ocupado():
    db = _db_com_codigos("PROD-00012", "PROD-13", "PROD-00014")

    resposta = gerar_sku(
        prefixo="PROD",
        db=db,
        user_and_tenant=(object(), uuid4()),
    )

    assert resposta["sku"] == "PROD-00015"
    assert resposta["numero"] == 15


def test_gerar_sku_inicia_em_um_quando_nao_ha_codigo_anterior():
    db = _db_com_codigos()

    resposta = gerar_sku(
        prefixo="PROD",
        db=db,
        user_and_tenant=(object(), uuid4()),
    )

    assert resposta["sku"] == "PROD-00001"
    assert resposta["numero"] == 1
