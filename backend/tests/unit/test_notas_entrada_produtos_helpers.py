import os
import json
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.notas_entrada.produtos import (  # noqa: E402
    _aplicar_codigos_barras_item_no_produto,
    _codigos_barras_nf,
    _montar_divergencia_codigo_barras_item,
    normalizar_codigo_barras,
)


def test_codigos_barras_nf_ignora_sem_gtin_e_prefere_ean_tributario():
    item = SimpleNamespace(ean="SEM GTIN", ean_tributario="789.82420-30076")

    codigos = _codigos_barras_nf(item)

    assert codigos == {
        "ean": "",
        "ean_tributario": "7898242030076",
        "principal": "7898242030076",
    }
    assert normalizar_codigo_barras("789-54321 0123-6") == "7895432101236"


def test_montar_divergencia_codigo_barras_item_compara_codigo_principal_e_fiscal():
    produto = SimpleNamespace(
        codigo_barras="7898242030076",
        gtin_ean="17898242030073",
        gtin_ean_tributario="7898242030076",
    )
    item = SimpleNamespace(
        produto=produto,
        ean="17898242030073",
        ean_tributario="9998242030076",
    )

    divergencia = _montar_divergencia_codigo_barras_item(item)

    assert divergencia["tem_divergencia"] is True
    assert divergencia["mensagens"] == [
        "EAN fiscal da NF nao encontrado no produto: NF=9998242030076"
    ]


def test_montar_divergencia_codigo_barras_nao_alerta_quando_ean_nf_existe_no_produto():
    produto = SimpleNamespace(
        codigo_barras="7898929878038",
        gtin_ean="7898401962828",
        gtin_ean_tributario="7898929878038",
        codigos_barras_alternativos=None,
    )
    item = SimpleNamespace(
        produto=produto,
        ean="7898929878038",
        ean_tributario="7898929878038",
    )

    divergencia = _montar_divergencia_codigo_barras_item(item)

    assert divergencia == {"tem_divergencia": False, "mensagens": []}


def test_aplicar_codigos_barras_nf_guarda_eans_alternativos_sem_sobrescrever():
    produto = SimpleNamespace(
        codigo="SKU-1",
        codigo_barras="7890000000001",
        gtin_ean="7890000000002",
        gtin_ean_tributario="7890000000003",
        codigos_barras_alternativos='["7890000000004"]',
    )
    item = SimpleNamespace(ean="17890000000005", ean_tributario="7890000000006")

    atualizou = _aplicar_codigos_barras_item_no_produto(produto, item)

    assert atualizou is True
    assert produto.codigo_barras == "7890000000001"
    assert produto.gtin_ean == "7890000000002"
    assert produto.gtin_ean_tributario == "7890000000003"
    assert json.loads(produto.codigos_barras_alternativos) == [
        "7890000000004",
        "17890000000005",
        "7890000000006",
    ]
