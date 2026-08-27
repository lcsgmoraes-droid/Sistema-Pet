from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.nao_venda_relatorio import montar_relatorio_nao_vendas


def _item(
    item_id,
    *,
    produto_id,
    nome,
    sku=None,
    marca=None,
    fornecedor=None,
    quantidade="1",
    valor="0",
    lista_espera=False,
):
    return SimpleNamespace(
        id=item_id,
        produto_id=produto_id,
        produto_nome=nome,
        sku=sku,
        marca_nome=marca,
        fornecedor_nome=fornecedor,
        quantidade=Decimal(quantidade),
        valor_unitario_estimado=Decimal(valor) if valor is not None else None,
        adicionado_lista_espera=lista_espera,
    )


def _registro(
    registro_id,
    *,
    cliente_id=None,
    nome=None,
    telefone=None,
    motivo="outro",
    itens=None,
    valor_total=None,
):
    return SimpleNamespace(
        id=registro_id,
        cliente_id=cliente_id,
        cliente_nome=nome,
        cliente_telefone=telefone,
        motivo=motivo,
        observacoes=None,
        valor_estimado_total=valor_total,
        created_at=datetime(2026, 8, 27, 15, registro_id, tzinfo=timezone.utc),
        usuario_registrou=SimpleNamespace(nome="Atendente Teste", email=None),
        itens=itens or [],
    )


def test_relatorio_totaliza_atendimentos_motivos_e_produtos_sem_misturar_itens():
    registros = [
        _registro(
            1,
            cliente_id=10,
            nome="Ana",
            telefone="(11) 99999-0000",
            motivo="produto_sem_estoque",
            itens=[
                _item(
                    11,
                    produto_id=100,
                    nome="Special Dog Carne",
                    sku="SD-CARNE",
                    marca="Special Dog",
                    fornecedor="Distribuidora Pet",
                    quantidade="2",
                    valor="10",
                    lista_espera=True,
                ),
                _item(
                    12,
                    produto_id=None,
                    nome="Petisco de pato",
                    marca="Marca procurada",
                    fornecedor=None,
                    quantidade="1",
                    valor="5",
                ),
            ],
        ),
        _registro(
            2,
            motivo="preco",
            itens=[
                _item(
                    21,
                    produto_id=100,
                    nome="Special Dog Carne",
                    sku="SD-CARNE",
                    marca="Special Dog",
                    fornecedor="Distribuidora Pet",
                    quantidade="3",
                    valor="10",
                )
            ],
        ),
    ]

    relatorio = montar_relatorio_nao_vendas(registros)

    assert relatorio["resumo"] == {
        "total_atendimentos": 2,
        "atendimentos_identificados": 1,
        "clientes_identificados_distintos": 1,
        "atendimentos_anonimos": 1,
        "total_itens": 3,
        "total_produtos_distintos": 2,
        "quantidade_total": 6.0,
        "valor_estimado_total": 55.0,
    }
    assert [
        (item["codigo"], item["total_atendimentos"]) for item in relatorio["motivos"]
    ] == [
        ("preco", 1),
        ("produto_sem_estoque", 1),
    ]

    special_dog = next(
        item for item in relatorio["produtos"] if item["sku"] == "SD-CARNE"
    )
    assert special_dog["total_atendimentos"] == 2
    assert special_dog["total_clientes_identificados"] == 1
    assert special_dog["total_solicitacoes"] == 2
    assert special_dog["quantidade_total"] == 5.0
    assert special_dog["valor_estimado_total"] == 50.0

    grupo = next(
        item
        for item in relatorio["agrupado_por_fornecedor"]
        if item["fornecedor"] == "Distribuidora Pet"
    )
    assert grupo["marcas"][0]["marca"] == "Special Dog"
    assert grupo["marcas"][0]["produtos"][0]["produto_nome"] == "Special Dog Carne"
    assert relatorio["detalhes"][1]["itens"][0]["adicionado_lista_espera"] is True


def test_relatorio_conta_atendimento_sem_cliente_e_sem_produto():
    relatorio = montar_relatorio_nao_vendas(
        [_registro(1, motivo="cliente_pesquisando", itens=[])]
    )

    assert relatorio["resumo"]["total_atendimentos"] == 1
    assert relatorio["resumo"]["atendimentos_anonimos"] == 1
    assert relatorio["resumo"]["total_itens"] == 0
    assert relatorio["produtos"] == []
    assert relatorio["detalhes"][0]["cliente_nome"] == "Cliente não identificado"
