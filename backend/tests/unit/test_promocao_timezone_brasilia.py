import os
from datetime import datetime, timezone
from types import SimpleNamespace


os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos.listagem import _resolver_promocao_erp_produto  # noqa: E402
from app.promocoes_venda_utils import detectar_promocao_por_preco_vendido  # noqa: E402
from app.services.validade_campanha_service import (  # noqa: E402
    resolver_preco_promocional_manual,
)


INICIO_PROMOCAO = datetime(2026, 7, 28, 13, 19, tzinfo=timezone.utc)
FIM_PROMOCAO = datetime(2026, 7, 28, 14, 22, tzinfo=timezone.utc)
AGORA_UTC_DENTRO_DA_JANELA = datetime(2026, 7, 28, 17, 9, tzinfo=timezone.utc)


def _produto_promocao():
    return SimpleNamespace(
        preco_venda=229.90,
        preco_promocional=None,
        promocao_inicio=None,
        promocao_fim=None,
        preco_ecommerce=None,
        preco_ecommerce_promo=228.00,
        preco_ecommerce_promo_inicio=INICIO_PROMOCAO,
        preco_ecommerce_promo_fim=FIM_PROMOCAO,
        preco_app=None,
        preco_app_promo=None,
        preco_app_promo_inicio=None,
        preco_app_promo_fim=None,
    )


def test_promocao_ecommerce_compara_referencia_utc_no_horario_de_brasilia():
    produto = _produto_promocao()

    preco = resolver_preco_promocional_manual(
        produto,
        "ecommerce",
        agora=AGORA_UTC_DENTRO_DA_JANELA,
    )

    assert preco == 228.00


def test_promocao_ecommerce_respeita_inicio_e_fim_em_brasilia():
    produto = _produto_promocao()

    antes = resolver_preco_promocional_manual(
        produto,
        "ecommerce",
        agora=datetime(2026, 7, 28, 16, 18, tzinfo=timezone.utc),
    )
    depois = resolver_preco_promocional_manual(
        produto,
        "ecommerce",
        agora=datetime(2026, 7, 28, 17, 23, tzinfo=timezone.utc),
    )

    assert antes is None
    assert depois is None


def test_promocao_erp_do_pdv_usa_horario_de_brasilia():
    produto = SimpleNamespace(
        preco_venda=229.90,
        preco_promocional=228.00,
        promocao_inicio=datetime(2026, 7, 28, 13, 19),
        promocao_fim=datetime(2026, 7, 28, 14, 22),
    )

    resultado = _resolver_promocao_erp_produto(
        produto,
        referencia=AGORA_UTC_DENTRO_DA_JANELA,
    )

    assert resultado["promocao_ativa"] is True
    assert resultado["preco_pdv"] == 228.00


def test_venda_ecommerce_identifica_promocao_na_janela_de_brasilia():
    produto = _produto_promocao()
    venda = SimpleNamespace(
        canal="ecommerce",
        loja_origem=None,
        data_venda=AGORA_UTC_DENTRO_DA_JANELA,
    )

    resultado = detectar_promocao_por_preco_vendido(
        produto,
        venda,
        preco_unitario=228.00,
        quantidade=1,
        subtotal_item=228.00,
    )

    assert resultado["em_promocao"] is True
    assert resultado["promocao_origem"] == "Promocao Ecommerce"
