from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.vendas.edicao_itens import atualizar_itens_venda_aberta
from app.vendas.schemas import VendaItemSchema
from app.vendas_models import VendaItem
from tests.unit import test_finalizacao_recebiveis_atomicidade as recebiveis

cenario = recebiveis.cenario


TENANT = "8f556b9e-3eb2-4e72-89db-10c512d53093"


class SessaoFake:
    def __init__(self):
        self.adicionados = []
        self.excluidos = []
        self.flushes = 0

    def add(self, item):
        self.adicionados.append(item)

    def delete(self, item):
        self.excluidos.append(item)

    def flush(self):
        self.flushes += 1
        for indice, item in enumerate(self.adicionados, start=800):
            item.id = indice


def _antigo(item_id=7, quantidade="2", preco="100", comprovante=None):
    return SimpleNamespace(
        id=item_id,
        venda_id=123,
        tenant_id=TENANT,
        tipo="produto",
        produto_id=11,
        estoque_origem_tenant_id=None,
        quantidade=Decimal(quantidade),
        preco_unitario=Decimal(preco),
        desconto_item=Decimal("0"),
        subtotal=Decimal(preco) * Decimal(quantidade),
        lote_id=None,
        servico_descricao=None,
        custo_original_saida=comprovante,
    )


def _novo(produto_id=11, quantidade=2, preco=100, item_id=None):
    return VendaItemSchema(
        item_id=item_id,
        tipo="produto",
        produto_id=produto_id,
        quantidade=quantidade,
        preco_unitario=preco,
        subtotal=quantidade * preco,
    )


def _resolucoes(*produto_ids):
    return {
        produto_id: SimpleNamespace(
            produto=SimpleNamespace(nome=f"Produto {produto_id}", eh_racao=False),
            tenant_origem_id=TENANT,
            compartilhado=False,
            compartilhamento_id=None,
            empresa_origem_nome=None,
        )
        for produto_id in produto_ids
    }


def _editar(antigos, novos, saidas=None):
    db = SessaoFake()
    db.ids_atualizados = atualizar_itens_venda_aberta(
        venda_id=123,
        cliente_id=None,
        tenant_id=TENANT,
        itens_antigos=antigos,
        itens_novos=novos,
        resolucoes_produtos=_resolucoes(*(item.produto_id for item in novos)),
        saidas_ajuste=saidas or {},
        db=db,
    )
    return db


def test_pagamento_de_venda_aberta_preserva_id_e_comprovante_da_baixa():
    comprovante = {"movimentacao_id": 91, "custo_total": "90.00"}
    item = _antigo(comprovante=comprovante)

    db = _editar([item], [_novo(preco=110)])

    assert db.adicionados == []
    assert db.excluidos == []
    assert db.flushes == 0
    assert item.id == 7
    assert item.custo_original_saida is comprovante
    assert item.preco_unitario == 110
    assert item.quantidade == Decimal("2")


def test_linhas_iguais_preservam_comprovantes_individuais():
    primeiro = _antigo(item_id=7, quantidade="1", comprovante={"movimentacao_id": 91})
    segundo = _antigo(item_id=8, quantidade="1", comprovante={"movimentacao_id": 92})

    db = _editar(
        [segundo, primeiro],
        [_novo(quantidade=1, item_id=7), _novo(quantidade=1, item_id=8)],
    )

    assert db.adicionados == []
    assert db.excluidos == []
    assert primeiro.custo_original_saida["movimentacao_id"] == 91
    assert segundo.custo_original_saida["movimentacao_id"] == 92


def test_remover_uma_de_duas_linhas_sem_id_nao_atribui_custo_da_outra():
    primeiro = _antigo(item_id=7, quantidade="1", comprovante={"movimentacao_id": 91})
    segundo = _antigo(item_id=8, quantidade="1", comprovante={"movimentacao_id": 92})

    db = _editar([primeiro, segundo], [_novo(quantidade=1)])

    assert db.excluidos == [primeiro, segundo]
    assert len(db.adicionados) == 1
    assert db.adicionados[0].custo_original_saida is None


def test_linhas_do_mesmo_produto_com_quantidades_distintas_exigem_id():
    primeiro = _antigo(item_id=7, quantidade="1", comprovante={"movimentacao_id": 91})
    segundo = _antigo(item_id=8, quantidade="2", comprovante={"movimentacao_id": 92})

    db = _editar([primeiro, segundo], [_novo(quantidade=1)])

    assert db.excluidos == [primeiro, segundo]
    assert db.adicionados[0].custo_original_saida is None


def test_remover_uma_de_duas_linhas_com_id_preserva_custo_correto():
    primeiro = _antigo(item_id=7, quantidade="1", comprovante={"movimentacao_id": 91})
    segundo = _antigo(item_id=8, quantidade="1", comprovante={"movimentacao_id": 92})

    db = _editar([primeiro, segundo], [_novo(quantidade=1, item_id=8)])

    assert db.excluidos == [primeiro]
    assert db.adicionados == []
    assert segundo.custo_original_saida["movimentacao_id"] == 92


def test_id_de_item_que_nao_pertence_a_venda_exige_recarregar():
    with pytest.raises(HTTPException) as erro:
        _editar([_antigo()], [_novo(item_id=999)])

    assert erro.value.status_code == 409


def test_produto_adicionado_na_edicao_captura_custo_da_nova_baixa():
    item_antigo = _antigo(comprovante={"movimentacao_id": 91})
    db = _editar(
        [item_antigo],
        [_novo(), _novo(produto_id=12, quantidade=1, preco=70)],
        {
            (12, TENANT): [
                {
                    "produto_id": 12,
                    "quantidade": 1,
                    "valor_total": 45,
                    "movimentacao_id": 93,
                }
            ]
        },
    )

    assert db.excluidos == []
    assert len(db.adicionados) == 1
    novo = db.adicionados[0]
    assert novo.custo_original_saida["venda_item_id"] == novo.id
    assert novo.custo_original_saida["movimentacao_id"] == 93
    assert novo.custo_original_saida["custo_total"] == "45.00"
    assert item_antigo.custo_original_saida == {"movimentacao_id": 91}


def test_quantidade_alterada_nao_herda_comprovante_da_linha_antiga():
    antigo = _antigo(comprovante={"movimentacao_id": 91, "custo_total": "90.00"})

    db = _editar([antigo], [_novo(quantidade=1)])

    assert db.excluidos == [antigo]
    assert len(db.adicionados) == 1
    assert db.adicionados[0].custo_original_saida is None


def test_mapeia_id_solicitado_para_id_novo_apos_quantidade_alterada():
    antigo = _antigo(item_id=7, quantidade="1")
    db = _editar([antigo], [_novo(item_id=7, quantidade=2)])
    assert db.excluidos == [antigo]
    assert db.flushes == 1
    assert db.ids_atualizados == {7: db.adicionados[0].id}
    assert db.adicionados[0].id == 800
    assert db.adicionados[0].quantidade == 2


def test_mapeia_linhas_do_mesmo_sku_sem_usar_ordem_ou_quantidade_antiga():
    primeiro = _antigo(item_id=7, quantidade="1")
    segundo = _antigo(item_id=8, quantidade="1")
    db = _editar(
        [primeiro, segundo],
        [_novo(item_id=8, quantidade=3), _novo(item_id=7, quantidade=2)],
    )
    assert db.ids_atualizados == {8: 800, 7: 801}
    assert [item.quantidade for item in db.adicionados] == [3, 2]
    assert db.excluidos == [primeiro, segundo]


def test_id_preservado_tem_mapeamento_exato_e_linha_sem_id_nao_tem():
    primeiro = _antigo(item_id=7, quantidade="1")
    segundo = _antigo(item_id=8, quantidade="2")
    db = _editar(
        [primeiro, segundo],
        [_novo(item_id=7, quantidade=1), _novo(quantidade=2)],
    )
    assert db.ids_atualizados == {7: 7}
    assert not db.adicionados and not db.excluidos
    assert db.flushes == 0


def test_duas_linhas_com_mesmo_id_e_quantidades_novas_nao_sao_associadas():
    with pytest.raises(HTTPException) as erro:
        _editar(
            [_antigo()],
            [_novo(item_id=7, quantidade=3), _novo(item_id=7, quantidade=4)],
        )
    assert erro.value.status_code == 409


@pytest.mark.parametrize(
    "campo,valor", [("tenant_id", "outro-tenant"), ("venda_id", 999)]
)
def test_id_de_outra_venda_ou_empresa_nao_entra_no_mapeamento(campo, valor):
    antigo = _antigo()
    setattr(antigo, campo, valor)
    with pytest.raises(HTTPException) as erro:
        _editar([antigo], [_novo(item_id=7, quantidade=3)])
    assert erro.value.status_code == 409


def test_mapeamento_usa_ids_gerados_no_flush_real_para_sku_repetido(cenario):
    antigos = [
        VendaItem(
            venda_id=1,
            tenant_id=cenario.tenant,
            tipo="produto",
            produto_id=11,
            quantidade=1,
            preco_unitario=100,
            desconto_item=10,
            subtotal=90,
        )
        for _ in range(2)
    ]
    cenario.db.add_all(antigos)
    cenario.db.flush()
    primeiro, segundo = [item.id for item in antigos]
    ids = atualizar_itens_venda_aberta(
        venda_id=1,
        cliente_id=None,
        tenant_id=cenario.tenant,
        itens_antigos=antigos,
        itens_novos=[
            _novo(item_id=segundo, quantidade=3),
            _novo(item_id=primeiro, quantidade=2),
        ],
        resolucoes_produtos={},
        saidas_ajuste={},
        db=cenario.db,
    )
    persistidos = (
        cenario.db.query(VendaItem)
        .filter_by(venda_id=1, tenant_id=cenario.tenant)
        .all()
    )
    assert len(persistidos) == 2
    assert set(ids) == {primeiro, segundo}
    assert not set(ids.values()).intersection({primeiro, segundo})
    quantidades = {item.id: item.quantidade for item in persistidos}
    assert quantidades[ids[primeiro]] == 2
    assert quantidades[ids[segundo]] == 3
    assert all(item.custo_original_saida is None for item in persistidos)
