import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.notas_entrada.fiscal import (  # noqa: E402
    calcular_quantidade_custo_efetivos,
    detectar_multiplicador_pack,
)


def test_detectar_multiplicador_pack_preserva_padroes_existentes():
    assert detectar_multiplicador_pack("BIONATURAL CAES 4x2,5KG") == 4
    assert detectar_multiplicador_pack("CAIXA C/ 12 UN") == 12
    assert detectar_multiplicador_pack("KIT 6\u00d73 SACHE") == 6
    assert detectar_multiplicador_pack("Produto unitario") == 1


def test_calcular_quantidade_custo_efetivos_rateia_pack_pelo_total():
    resultado = calcular_quantidade_custo_efetivos(
        "BIONATURAL CAES 4x2,5KG",
        quantidade=2,
        valor_unitario=123.45,
        valor_total=246.90,
    )

    assert resultado["pack_detectado"] is True
    assert resultado["multiplicador_pack"] == 4
    assert resultado["quantidade_efetiva"] == 8
    assert resultado["custo_unitario_efetivo"] == 30.8625
