from decimal import Decimal
import os
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.engine import make_url

# Registra os alvos das FKs do catálogo para o schema isolado de teste.
from app import caixa_models, especie_raca_mestre_models, produto_identidade_models  # noqa: F401

from app.comissoes_config_service import (
    calcular_comissao_item,
    calcular_comissao_fixa_parcela,
)
from app.comissoes_demonstrativo_calculo import montar_demonstrativo_calculo_comissao
from app.comissoes_grupos_routes import (
    GrupoProdutosPayload,
    ProvisionarGrupoPayload,
    _validar_produtos,
    provisionar_grupo,
    salvar_grupo,
    atualizar_grupo,
    listar_grupos,
)
from app.comissoes_schemas import ConfiguracaoComissaoCreate


def _postgres_dev_habilitado():
    if os.getenv("COMISSOES_POSTGRES_DEV") != "1":
        return False
    url = make_url(os.getenv("DATABASE_URL", "sqlite://"))
    return (
        url.drivername.startswith("postgresql")
        and url.host in {"localhost", "127.0.0.1"}
        and url.database == "petshop_dev"
    )


postgres_dev = pytest.mark.skipif(
    not _postgres_dev_habilitado(),
    reason="Aceite opt-in no PostgreSQL DEV local com rollback",
)


def _calcular(tipo, quantidade="2", **config):
    return calcular_comissao_item(
        config={"tipo_calculo": tipo, "percentual": 10, "valor_fixo": "3.25", **config},
        valor_bruto_item=Decimal("100"),
        valor_liquido_item=Decimal("90"),
        custo_unitario=Decimal("20"),
        quantidade=Decimal(quantidade),
        proporcao_item=Decimal("1"),
        custos_rateados={
            "taxa_cartao_produtos": 5,
            "impostos_produtos": 6,
            "taxa_paga_entregador": 7,
            "custo_operacional_entrega": 8,
        },
        tem_entrega=True,
    )


def test_fixo_por_unidade_nao_sofre_deducoes_e_respeita_fracao():
    assert _calcular("fixo")["valor_comissao"] == 6.5
    fracionado = _calcular("fixo", "0.5", desconta_custo_entrega=True)
    assert fracionado["valor_comissao"] == 1.63
    assert fracionado["base_calculo"] == 0.5
    assert fracionado["percentual"] == 0
    assert fracionado["valor_fixo"] == 3.25


def test_percentual_e_lucro_preservam_calculo_anterior():
    assert _calcular("percentual")["valor_comissao"] == 6.4
    assert _calcular("lucro")["valor_comissao"] == 2.4


def test_fixo_parcelado_distribui_centavos_sem_ultrapassar_total():
    primeira = calcular_comissao_fixa_parcela("1.63", 5, 10, 0)
    segunda = calcular_comissao_fixa_parcela("1.63", 5, 10, 5)
    assert (primeira, segunda) == (Decimal("0.82"), Decimal("0.81"))
    assert primeira + segunda == Decimal("1.63")
    assert sum(
        calcular_comissao_fixa_parcela("0.01", 1, 3, pago) for pago in (0, 1, 2)
    ) == Decimal("0.01")
    # Uma regra nova só vale para o recebimento atual, sem recalcular o anterior.
    assert calcular_comissao_fixa_parcela("5", 5, 10, 5) == Decimal("2.50")
    assert calcular_comissao_fixa_parcela("5", 10, 10, 10) == 0


@pytest.mark.parametrize("valor", [0, -1, float("nan"), float("inf")])
def test_configuracao_fixa_rejeita_valor_invalido(valor):
    with pytest.raises(ValidationError):
        ConfiguracaoComissaoCreate(
            funcionario_id=1,
            tipo="produto",
            referencia_id=2,
            tipo_calculo="fixo",
            valor_fixo=valor,
        )


def test_configuracao_fixa_nao_usa_percentual_ou_edicao_na_venda():
    config = ConfiguracaoComissaoCreate(
        funcionario_id=1,
        tipo="produto",
        referencia_id=2,
        tipo_calculo="fixo",
        valor_fixo=5,
        percentual=12,
        permite_edicao_venda=True,
    )
    assert config.percentual == 0
    assert config.permite_edicao_venda is False
    assert config.valor_fixo == 5


def test_demonstrativo_fixo_usa_snapshot_e_quantidade_proporcional():
    dados = montar_demonstrativo_calculo_comissao(
        tipo_calculo="fixo",
        valor_fixo=5,
        valor_base_calculo=0.75,
        valor_comissao=3.75,
        valor_comissao_gerada=3.75,
        percentual_comissao=0,
        percentual_aplicado=50,
        valor_bruto=100,
        desconto=20,
        beneficio=5,
        taxa_cartao=7,
        imposto=8,
        taxa_entregador=2,
        custo_operacional=1,
        receita_taxa_entrega=10,
        custo_produto=50,
    )
    assert dados["conferencia_ok"] is True
    assert dados["linhas"][0]["tipo"] == "quantidade"
    assert dados["linhas"][1]["valor"] == 5
    assert all(linha["operador"] != "-" for linha in dados["linhas"])


def test_grupo_normaliza_produtos_sem_duplicar_e_nao_aceita_nome_vazio():
    grupo = GrupoProdutosPayload(nome="  Grupo   Ração  ", produto_ids=[3, 2, 3])
    assert grupo.nome == "Grupo Ração"
    assert grupo.produto_ids == [2, 3]
    with pytest.raises(ValidationError):
        GrupoProdutosPayload(nome="   ", produto_ids=[2])


def test_grupo_nao_aceita_produto_de_outra_empresa():
    query = SimpleNamespace(filter=lambda *args: SimpleNamespace(all=lambda: [(2,)]))
    db = SimpleNamespace(query=lambda *args: query)
    with pytest.raises(HTTPException) as erro:
        _validar_produtos(db, UUID(int=1), [2, 3])
    assert erro.value.status_code == 400


@postgres_dev
def test_grupos_persistem_selecao_e_isolam_empresas(
    db_session, tenant_factory, user_factory, tenant_context
):
    from app.produtos_models import Produto
    from app.comissoes_grupos_models import ComissaoGrupoProdutos

    ComissaoGrupoProdutos.__table__.create(db_session.get_bind(), checkfirst=True)
    tenant_a = tenant_factory(nome="Comissões grupo empresa A")
    usuario_a = user_factory(tenant_id=tenant_a.id)
    tenant_context(tenant_a.id)
    produto_a = Produto(
        tenant_id=UUID(str(tenant_a.id)),
        codigo="GRUPO-A",
        nome="Produto A",
        user_id=usuario_a.id,
        preco_venda=10,
        preco_custo=5,
    )
    db_session.add(produto_a)
    db_session.flush()
    payload = GrupoProdutosPayload(nome="Grupo persistido", produto_ids=[produto_a.id])
    criado = salvar_grupo(payload, db_session, (usuario_a, UUID(str(tenant_a.id))))[
        "data"
    ]
    assert criado["produto_ids"] == [produto_a.id]
    assert criado["produtos"][0]["codigo"] == "GRUPO-A"
    assert (
        listar_grupos(db_session, (usuario_a, UUID(str(tenant_a.id))))["data"][0]["id"]
        == criado["id"]
    )
    atualizado = atualizar_grupo(
        criado["id"],
        GrupoProdutosPayload(nome="Grupo atualizado", produto_ids=[produto_a.id]),
        db_session,
        (usuario_a, UUID(str(tenant_a.id))),
    )
    assert atualizado["data"]["nome"] == "Grupo atualizado"
    tenant_b = tenant_factory(nome="Comissões grupo empresa B")
    usuario_b = user_factory(tenant_id=tenant_b.id)
    tenant_context(tenant_b.id)
    assert listar_grupos(db_session, (usuario_b, UUID(str(tenant_b.id))))["data"] == []
    with pytest.raises(HTTPException) as nao_encontrado:
        atualizar_grupo(
            criado["id"], payload, db_session, (usuario_b, UUID(str(tenant_b.id)))
        )
    assert nao_encontrado.value.status_code == 404
    with pytest.raises(HTTPException) as produto_alheio:
        salvar_grupo(payload, db_session, (usuario_b, UUID(str(tenant_b.id))))
    assert produto_alheio.value.status_code == 400


@postgres_dev
def test_provisao_postgres_filtra_grupo_e_nao_duplica_contas(
    db_session, tenant_factory, user_factory, tenant_context
):
    from datetime import date, datetime
    from app.models import Cliente
    from app.produtos_models import Produto
    from app.vendas_models import Venda
    from app.comissoes_models import ComissaoItem
    from app.financeiro_models import ContaPagar
    from app.dre_plano_contas_models import (
        DRECategoria,
        DRESubcategoria,
        NaturezaDRE,
        TipoCusto,
        EscopoRateio,
    )

    tenant = tenant_factory(nome="Comissões provisão fictícia")
    usuario = user_factory(tenant_id=tenant.id)
    tid = UUID(str(tenant.id))
    tenant_context(tid)
    parceiro = Cliente(
        tenant_id=tid,
        user_id=usuario.id,
        codigo="COM-GRUPO",
        nome="Parceiro fictício",
        parceiro_ativo=True,
        data_fechamento_comissao=31,
    )
    produtos = [
        Produto(
            tenant_id=tid,
            codigo=f"COM-PROD-{indice}",
            nome=f"Produto comissão {indice}",
            user_id=usuario.id,
            preco_venda=10,
            preco_custo=5,
        )
        for indice in range(2)
    ]
    categoria = DRECategoria(
        tenant_id=tid, nome="Despesas operacionais", natureza=NaturezaDRE.DESPESA
    )
    db_session.add_all([parceiro, *produtos, categoria])
    db_session.flush()
    sub = DRESubcategoria(
        tenant_id=tid,
        categoria_id=categoria.id,
        nome="Comissões de Vendas",
        tipo_custo=TipoCusto.DIRETO,
        escopo_rateio=EscopoRateio.AMBOS,
    )
    venda = Venda(
        tenant_id=tid,
        numero_venda="COM-TEST-GRUPO",
        vendedor_id=usuario.id,
        user_id=usuario.id,
        subtotal=20,
        total=20,
        status="finalizada",
        data_venda=datetime(2026, 2, 28),
    )
    db_session.add_all([sub, venda])
    db_session.flush()
    itens = [
        ComissaoItem(
            tenant_id=tid,
            venda_id=venda.id,
            funcionario_id=parceiro.id,
            produto_id=produto.id,
            data_venda=date(2026, 2, 28),
            tipo_calculo="fixo",
            valor_fixo=3.25,
            quantidade=2,
            valor_base_calculo=2,
            percentual_comissao=0,
            valor_comissao=6.5,
            valor_comissao_gerada=6.5,
            status="pendente",
            comissao_provisionada=False,
        )
        for produto in produtos
    ]
    db_session.add_all(itens)
    db_session.flush()
    grupo = salvar_grupo(
        GrupoProdutosPayload(nome="Somente produto zero", produto_ids=[produtos[0].id]),
        db_session,
        (usuario, tid),
    )["data"]
    periodo = ProvisionarGrupoPayload(
        data_inicio="2026-02-01", data_fim="2026-02-28", funcionario_id=parceiro.id
    )
    primeiro = provisionar_grupo(grupo["id"], periodo, db_session, (usuario, tid))
    assert primeiro["comissoes_provisionadas"] == 1
    assert primeiro["valor_total"] == 6.5
    assert len(primeiro["contas_criadas"]) == 1
    conta = (
        db_session.query(ContaPagar)
        .filter(
            ContaPagar.id == primeiro["contas_criadas"][0], ContaPagar.tenant_id == tid
        )
        .one()
    )
    assert conta.valor_original == Decimal("6.50")
    assert conta.data_vencimento == date(2026, 2, 28)
    db_session.refresh(itens[0])
    db_session.refresh(itens[1])
    assert itens[0].conta_pagar_id == conta.id
    assert itens[1].conta_pagar_id is None
    segundo = provisionar_grupo(grupo["id"], periodo, db_session, (usuario, tid))
    assert segundo["comissoes_provisionadas"] == 0
    assert segundo["contas_criadas"] == []
    assert db_session.query(ContaPagar).filter(ContaPagar.tenant_id == tid).count() == 1


def test_provisao_grupo_e_atomica_e_repassa_somente_itens_do_grupo(monkeypatch):
    import app.comissoes_grupos_routes as routes

    eventos = []
    itens = [SimpleNamespace(id=11, venda_id=1), SimpleNamespace(id=12, venda_id=2)]

    class Query:
        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def with_for_update(self):
            return self

        def all(self):
            return itens

    db = SimpleNamespace(
        query=lambda *args: Query(),
        commit=lambda: eventos.append("commit"),
        rollback=lambda: eventos.append("rollback"),
    )
    monkeypatch.setattr(
        routes, "_grupo", lambda *args: SimpleNamespace(produto_ids=[2])
    )

    def provisionar(**kwargs):
        eventos.append((kwargs["venda_id"], kwargs["comissao_ids"], kwargs["commit"]))
        if kwargs["venda_id"] == 2:
            raise RuntimeError("Falha no segundo item")
        return {
            "success": True,
            "comissoes_provisionadas": 1,
            "valor_total": 5,
            "contas_criadas": [100],
        }

    monkeypatch.setattr(routes, "provisionar_comissoes_venda", provisionar)
    with pytest.raises(RuntimeError):
        provisionar_grupo(
            1,
            ProvisionarGrupoPayload(data_inicio="2026-10-01", data_fim="2026-10-31"),
            db,
            (SimpleNamespace(id=1), UUID(int=1)),
        )
    assert eventos == [(1, [11], False), (2, [12], False), "rollback"]
