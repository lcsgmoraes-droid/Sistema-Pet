import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.notas_entrada.produtos import (  # noqa: E402
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
    assert (
        "Codigo de barras principal: NF=9998242030076 vs cadastro=7898242030076"
        in divergencia["mensagens"]
    )
    assert (
        "EAN fiscal: NF=9998242030076 vs cadastro=7898242030076"
        in divergencia["mensagens"]
    )
