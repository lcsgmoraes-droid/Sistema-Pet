import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.demanda_nao_atendida import montar_central_demanda_nao_atendida


def _produto(produto_id=10, *, publicado=True, estoque=0):
    return SimpleNamespace(
        id=produto_id,
        nome="Ração Premium 15 kg",
        codigo="RAC-15",
        marca=SimpleNamespace(nome="Marca Boa"),
        fornecedor=SimpleNamespace(nome="Distribuidora Pet"),
        ativo=True,
        situacao=True,
        is_sellable=True,
        tipo_produto="SIMPLES",
        tipo="produto",
        preco_venda=149.9,
        preco_ecommerce=None,
        anunciar_ecommerce=publicado,
        estoque_atual=estoque,
        estoque_ecommerce=0,
        imagens=[],
        imagem_principal=None,
        descricao_curta=None,
        descricao_completa=None,
        categoria_id=None,
        marca_id=1,
    )


TENANT = SimpleNamespace(
    ecommerce_usar_estoque_canal=False,
    ecommerce_ocultar_servicos=True,
    ecommerce_ocultar_sem_estoque=False,
    ecommerce_ocultar_sem_imagem=False,
)


def test_central_separa_procuras_de_inscricoes_e_agrupa_canais():
    agora = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
    item_produto = SimpleNamespace(
        produto_id=10,
        produto_nome="Snapshot",
        sku="RAC-15",
        marca_nome="Marca Boa",
        fornecedor_nome="Distribuidora Pet",
        quantidade=Decimal("2"),
        valor_unitario_estimado=Decimal("149.90"),
    )
    item_livre = SimpleNamespace(
        produto_id=None,
        produto_nome="Petisco de pato",
        sku=None,
        marca_nome="Marca Nova",
        fornecedor_nome=None,
        quantidade=Decimal("1"),
        valor_unitario_estimado=Decimal("20"),
    )
    registros = [
        SimpleNamespace(
            id=1,
            cliente_id=7,
            cliente_nome="Ana",
            cliente_telefone="11999990000",
            created_at=agora,
            itens=[item_produto, item_livre],
        )
    ]
    pendencias = [
        SimpleNamespace(
            produto_id=10,
            produto=_produto(),
            cliente_id=7,
            quantidade_desejada=2,
            data_registro=agora,
        ),
        SimpleNamespace(
            produto_id=10,
            produto=_produto(),
            cliente_id=7,
            quantidade_desejada=1,
            data_registro=agora,
        ),
    ]
    avisos = [
        SimpleNamespace(
            product_id=10,
            product_name="Ração Premium 15 kg",
            email="ANA@EXEMPLO.COM",
            created_at=agora,
        ),
        SimpleNamespace(
            product_id=10,
            product_name="Ração Premium 15 kg",
            email="ana@exemplo.com",
            created_at=agora,
        ),
    ]

    central = montar_central_demanda_nao_atendida(
        registros_pdv=registros,
        pendencias_pdv=pendencias,
        avisos_ecommerce=avisos,
        produtos=[_produto()],
        tenant=TENANT,
    )

    produto = next(item for item in central["itens"] if item["produto_id"] == 10)
    livre = next(item for item in central["itens"] if item["produto_id"] is None)
    assert central["resumo"]["procuras_pdv"] == 2
    assert central["resumo"]["atendimentos_pdv"] == 1
    assert central["resumo"]["inscricoes_ativas"] == 2
    assert central["resumo"]["produtos_nao_cadastrados"] == 1
    assert produto["aguardando_pdv"] == 1
    assert produto["aguardando_ecommerce"] == 1
    assert produto["aguardando_total"] == 2
    assert produto["quantidade_aguardada_pdv"] == 3
    assert produto["ecommerce"]["status"] == "esgotado"
    assert produto["ecommerce"]["visivel"] is True
    assert livre["produto_nome"] == "Petisco de pato"
    assert livre["cadastrado"] is False
    assert central["resumo"]["valor_estimado_oportunidade"] == 319.8
    assert json.loads(json.dumps(central))["total"] == 2


def test_filtro_ausente_no_ecommerce_inclui_livre_e_produto_nao_publicado():
    agora = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
    produto = _produto(publicado=False, estoque=5)
    registros = [
        SimpleNamespace(
            id=1,
            cliente_id=None,
            cliente_nome=None,
            cliente_telefone=None,
            created_at=agora,
            itens=[
                SimpleNamespace(
                    produto_id=10,
                    produto_nome="Ração Premium 15 kg",
                    sku="RAC-15",
                    marca_nome=None,
                    fornecedor_nome=None,
                    quantidade=1,
                    valor_unitario_estimado=0,
                ),
                SimpleNamespace(
                    produto_id=None,
                    produto_nome="Brinquedo diferente",
                    sku=None,
                    marca_nome=None,
                    fornecedor_nome=None,
                    quantidade=1,
                    valor_unitario_estimado=0,
                ),
            ],
        )
    ]

    central = montar_central_demanda_nao_atendida(
        registros_pdv=registros,
        pendencias_pdv=[],
        avisos_ecommerce=[],
        produtos=[produto],
        tenant=TENANT,
        situacao="ausente_ecommerce",
    )

    assert central["total"] == 2
    cadastrado = next(item for item in central["itens"] if item["produto_id"] == 10)
    assert cadastrado["ecommerce"]["visivel"] is False
    assert cadastrado["ecommerce"]["bloqueios"][0]["codigo"] == "nao_publicado"
