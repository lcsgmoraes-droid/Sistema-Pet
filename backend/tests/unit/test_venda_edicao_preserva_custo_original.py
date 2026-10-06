from decimal import Decimal
from types import SimpleNamespace

from app.vendas.edicao_itens import atualizar_itens_venda_aberta
from app.vendas.schemas import VendaItemSchema


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


def _novo(produto_id=11, quantidade=2, preco=100):
    return VendaItemSchema(
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
    atualizar_itens_venda_aberta(
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

    db = _editar([segundo, primeiro], [_novo(quantidade=1), _novo(quantidade=1)])

    assert db.adicionados == []
    assert db.excluidos == []
    assert primeiro.custo_original_saida["movimentacao_id"] == 91
    assert segundo.custo_original_saida["movimentacao_id"] == 92


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
