from types import SimpleNamespace

from app.services.ecommerce_catalog_health import classify_catalog_product


def _tenant(**overrides):
    values = {
        "ecommerce_usar_estoque_canal": False,
        "ecommerce_ocultar_sem_estoque": False,
        "ecommerce_ocultar_sem_imagem": False,
        "ecommerce_ocultar_servicos": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _product(**overrides):
    values = {
        "id": 10,
        "ativo": True,
        "situacao": True,
        "tipo": "produto",
        "tipo_produto": "SIMPLES",
        "is_sellable": True,
        "anunciar_ecommerce": True,
        "anunciar_app": True,
        "preco_venda": 20,
        "preco_ecommerce": None,
        "preco_app": None,
        "estoque_atual": 5,
        "estoque_ecommerce": 0,
        "imagem_principal": "foto.jpg",
        "imagens": [],
        "descricao_curta": "Descricao",
        "descricao_completa": None,
        "categoria_id": 1,
        "marca_id": 1,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_esgotado_continua_visivel_para_avise_me_quando_configurado():
    result = classify_catalog_product(
        _product(estoque_atual=0), _tenant(), waitlist_count=4
    )

    assert result["status"] == "esgotado"
    assert result["visivel"] is True
    assert result["compravel"] is False
    assert result["avise_me_pendentes"] == 4


def test_preco_zero_e_bloqueante_mesmo_com_estoque():
    result = classify_catalog_product(_product(preco_venda=0), _tenant())

    assert result["status"] == "bloqueado"
    assert result["visivel"] is False
    assert [issue["codigo"] for issue in result["bloqueios"]] == ["sem_preco"]


def test_dado_faltante_nao_impede_compra():
    result = classify_catalog_product(_product(marca_id=None), _tenant())

    assert result["status"] == "pendencias"
    assert result["compravel"] is True
    assert [issue["codigo"] for issue in result["pendencias"]] == ["sem_marca"]


def test_configuracao_antiga_pode_ocultar_esgotado_sem_confundir_com_preco():
    result = classify_catalog_product(
        _product(estoque_atual=0),
        _tenant(ecommerce_ocultar_sem_estoque=True),
    )

    assert result["status"] == "esgotado"
    assert result["visivel"] is False
    assert [issue["codigo"] for issue in result["bloqueios"]] == ["estoque_oculto"]


def test_estoque_de_canal_e_preco_do_app_sao_respeitados():
    result = classify_catalog_product(
        _product(estoque_atual=9, estoque_ecommerce=0, preco_app=12),
        _tenant(ecommerce_usar_estoque_canal=True),
        "app",
    )

    assert result["estoque"] == 0
    assert result["preco"] == 12
    assert result["status"] == "esgotado"
