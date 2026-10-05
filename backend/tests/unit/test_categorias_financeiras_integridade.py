"""Integridade dos cadastros financeiros sem alterar registros legados."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.categorias_routes import (
    CategoriaFinanceiraCreate,
    CategoriaFinanceiraUpdate,
    atualizar_categoria,
    criar_categoria,
    listar_categorias,
    listar_subcategorias_dre_da_categoria,
    obter_categoria,
)
from app.db import Base
from app.dre_plano_contas_models import (
    DRECategoria,
    DRESubcategoria,
    EscopoRateio,
    NaturezaDRE,
    TipoCusto,
)
from app.dre_plano_contas_routes import (
    DRECategoriaCreate,
    DRECategoriaUpdate,
    DRESubcategoriaCreate,
    DRESubcategoriaUpdate,
    atualizar_categoria as atualizar_categoria_dre,
    atualizar_subcategoria as atualizar_subcategoria_dre,
    criar_categoria as criar_categoria_dre,
    criar_subcategoria as criar_subcategoria_dre,
    deletar_subcategoria as deletar_subcategoria_dre,
)
from app.financeiro_models import CategoriaFinanceira, ContaPagar, ContaReceber
from app.models import User
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas.devolucoes_routes import _buscar_categoria_devolucoes


@pytest.fixture
def db():
    clear_current_tenant()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            CategoriaFinanceira.__table__,
            DRECategoria.__table__,
            DRESubcategoria.__table__,
            ContaPagar.__table__,
            ContaReceber.__table__,
        ],
    )
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()
    clear_current_tenant()


def _contexto(tenant_id, usuario_id=10):
    set_current_tenant(tenant_id)
    return (SimpleNamespace(id=usuario_id), tenant_id)


def _categoria(
    db, tenant_id, *, nome, user_id=10, tipo="despesa", pai=None, ativo=True
):
    set_current_tenant(tenant_id)
    categoria = CategoriaFinanceira(
        tenant_id=tenant_id,
        user_id=user_id,
        nome=nome,
        tipo=tipo,
        categoria_pai_id=pai,
        ativo=ativo,
    )
    db.add(categoria)
    db.commit()
    return categoria


def _listar(db, tenant_id, usuario_id=10):
    return listar_categorias(
        db=db,
        user_and_tenant=_contexto(tenant_id, usuario_id),
    )


def test_lista_categoria_de_outro_usuario_do_tenant_sem_ampliar_escrita(db):
    tenant, outro_tenant = uuid4(), uuid4()
    compartilhada = _categoria(db, tenant, nome="Aluguel", user_id=10)
    _categoria(db, outro_tenant, nome="Energia", user_id=20)

    visiveis = _listar(db, tenant, usuario_id=20)
    assert [categoria.id for categoria in visiveis] == [compartilhada.id]
    assert visiveis[0].pode_editar is False
    assert _listar(db, tenant, usuario_id=10)[0].pode_editar is True
    assert (
        obter_categoria(
            compartilhada.id, db=db, user_and_tenant=_contexto(tenant, 20)
        ).pode_editar
        is False
    )
    assert (
        listar_subcategorias_dre_da_categoria(
            compartilhada.id, db=db, user_and_tenant=_contexto(tenant, 20)
        )
        == []
    )

    with pytest.raises(HTTPException) as fora_do_tenant:
        obter_categoria(
            compartilhada.id, db=db, user_and_tenant=_contexto(outro_tenant, 20)
        )
    assert fora_do_tenant.value.status_code == 404

    with pytest.raises(HTTPException) as erro:
        atualizar_categoria(
            compartilhada.id,
            CategoriaFinanceiraUpdate(descricao="Sem permissão"),
            db=db,
            user_and_tenant=_contexto(tenant, 20),
        )
    assert erro.value.status_code == 404

    with pytest.raises(HTTPException) as pai_de_outro_usuario:
        criar_categoria(
            CategoriaFinanceiraCreate(
                nome="Aluguel - Filial",
                tipo="despesa",
                categoria_pai_id=compartilhada.id,
            ),
            db=db,
            user_and_tenant=_contexto(tenant, 20),
        )
    assert pai_de_outro_usuario.value.status_code == 404


def test_bloqueia_nova_duplicata_normalizada_sem_bloquear_legado(db):
    tenant, outro_tenant = uuid4(), uuid4()
    primeira = _categoria(db, tenant, nome="Devoluções de Vendas", user_id=10)
    segunda = _categoria(db, tenant, nome="Devoluções de Vendas", user_id=20)

    with pytest.raises(HTTPException) as erro:
        criar_categoria(
            CategoriaFinanceiraCreate(nome=" devolucoes   DE vendas ", tipo="despesa"),
            db=db,
            user_and_tenant=_contexto(tenant),
        )
    assert erro.value.status_code == 409

    alterada = atualizar_categoria(
        segunda.id,
        CategoriaFinanceiraUpdate(descricao="Duplicata histórica preservada"),
        db=db,
        user_and_tenant=_contexto(tenant, 20),
    )
    assert alterada.id == segunda.id
    assert db.get(CategoriaFinanceira, primeira.id).ativo is True

    criada_outro_tenant = criar_categoria(
        CategoriaFinanceiraCreate(nome="Devoluções de Vendas", tipo="despesa"),
        db=db,
        user_and_tenant=_contexto(outro_tenant),
    )
    assert criada_outro_tenant.id not in {primeira.id, segunda.id}

    criada_outra_natureza = criar_categoria(
        CategoriaFinanceiraCreate(nome="Devoluções de Vendas", tipo="receita"),
        db=db,
        user_and_tenant=_contexto(tenant),
    )
    assert criada_outra_natureza.tipo == "receita"


def test_bloqueia_ciclo_e_tipo_incompativel_no_put(db):
    tenant = uuid4()
    raiz = _categoria(db, tenant, nome="Despesas")
    filha = _categoria(db, tenant, nome="Marketing", pai=raiz.id)
    receita = _categoria(db, tenant, nome="Receitas", tipo="receita")

    with pytest.raises(HTTPException) as ciclo:
        atualizar_categoria(
            raiz.id,
            CategoriaFinanceiraUpdate(categoria_pai_id=filha.id),
            db=db,
            user_and_tenant=_contexto(tenant),
        )
    assert ciclo.value.status_code == 400
    assert db.get(CategoriaFinanceira, raiz.id).categoria_pai_id is None

    with pytest.raises(HTTPException) as tipo:
        atualizar_categoria(
            filha.id,
            CategoriaFinanceiraUpdate(categoria_pai_id=receita.id),
            db=db,
            user_and_tenant=_contexto(tenant),
        )
    assert tipo.value.status_code == 400

    with pytest.raises(HTTPException) as mudanca_de_tipo:
        atualizar_categoria(
            receita.id,
            CategoriaFinanceiraUpdate(tipo="despesa"),
            db=db,
            user_and_tenant=_contexto(tenant),
        )
    assert mudanca_de_tipo.value.status_code == 400
    assert db.get(CategoriaFinanceira, receita.id).tipo == "receita"


def test_listagem_interrompe_ciclo_legado(db):
    tenant = uuid4()
    primeira = _categoria(db, tenant, nome="A")
    segunda = _categoria(db, tenant, nome="B", pai=primeira.id)
    primeira.categoria_pai_id = segunda.id
    db.commit()

    categorias = _listar(db, tenant)
    assert len(categorias) == 2
    assert all(categoria.nivel <= 2 for categoria in categorias)


def test_plano_dre_rejeita_duplicatas_novas_e_preserva_antigas(db):
    tenant = uuid4()
    contexto = _contexto(tenant)
    categoria = criar_categoria_dre(
        DRECategoriaCreate(nome="Marketing", natureza=NaturezaDRE.DESPESA),
        db=db,
        user_and_tenant=contexto,
    )
    with pytest.raises(HTTPException) as categoria_duplicada:
        criar_categoria_dre(
            DRECategoriaCreate(nome=" MÁRKETING ", natureza=NaturezaDRE.DESPESA),
            db=db,
            user_and_tenant=contexto,
        )
    assert categoria_duplicada.value.status_code == 409

    subcategoria = criar_subcategoria_dre(
        DRESubcategoriaCreate(
            categoria_id=categoria.id,
            nome="Anúncios",
            tipo_custo=TipoCusto.DIRETO,
            base_rateio=None,
            escopo_rateio=EscopoRateio.AMBOS,
        ),
        db=db,
        user_and_tenant=contexto,
    )
    with pytest.raises(HTTPException) as subcategoria_duplicada:
        criar_subcategoria_dre(
            DRESubcategoriaCreate(
                categoria_id=categoria.id,
                nome=" anuncios ",
                tipo_custo=TipoCusto.DIRETO,
                escopo_rateio=EscopoRateio.AMBOS,
            ),
            db=db,
            user_and_tenant=contexto,
        )
    assert subcategoria_duplicada.value.status_code == 409

    legada = DRESubcategoria(
        tenant_id=tenant,
        categoria_id=categoria.id,
        nome="Anúncios",
        tipo_custo=TipoCusto.DIRETO,
        escopo_rateio=EscopoRateio.AMBOS,
        ativo=True,
    )
    db.add(legada)
    db.commit()
    assert (
        atualizar_subcategoria_dre(
            legada.id,
            DRESubcategoriaUpdate(custo_pe="fixo"),
            db=db,
            user_and_tenant=contexto,
        ).id
        == legada.id
    )
    assert (
        atualizar_categoria_dre(
            categoria.id,
            DRECategoriaUpdate(ordem=2),
            db=db,
            user_and_tenant=contexto,
        ).id
        == categoria.id
    )
    assert db.get(DRESubcategoria, subcategoria.id).ativo is True


def test_subcategoria_dre_vinculada_respeita_dono_e_geral_e_compartilhada(db):
    tenant = uuid4()
    categoria_financeira = _categoria(db, tenant, nome="Operações", user_id=10)
    categoria_dre = criar_categoria_dre(
        DRECategoriaCreate(nome="Operações", natureza=NaturezaDRE.DESPESA),
        db=db,
        user_and_tenant=_contexto(tenant, 10),
    )
    vinculada = criar_subcategoria_dre(
        DRESubcategoriaCreate(
            categoria_id=categoria_dre.id,
            categoria_financeira_id=categoria_financeira.id,
            nome="Internet",
            tipo_custo=TipoCusto.DIRETO,
            escopo_rateio=EscopoRateio.AMBOS,
        ),
        db=db,
        user_and_tenant=_contexto(tenant, 10),
    )

    with pytest.raises(HTTPException) as criar_de_outro_dono:
        criar_subcategoria_dre(
            DRESubcategoriaCreate(
                categoria_id=categoria_dre.id,
                categoria_financeira_id=categoria_financeira.id,
                nome="Energia",
                tipo_custo=TipoCusto.DIRETO,
                escopo_rateio=EscopoRateio.AMBOS,
            ),
            db=db,
            user_and_tenant=_contexto(tenant, 20),
        )
    assert criar_de_outro_dono.value.status_code == 404

    with pytest.raises(HTTPException) as editar_de_outro_dono:
        atualizar_subcategoria_dre(
            vinculada.id,
            DRESubcategoriaUpdate(custo_pe="fixo"),
            db=db,
            user_and_tenant=_contexto(tenant, 20),
        )
    assert editar_de_outro_dono.value.status_code == 404
    assert db.get(DRESubcategoria, vinculada.id).custo_pe is None

    with pytest.raises(HTTPException) as excluir_de_outro_dono:
        deletar_subcategoria_dre(
            vinculada.id,
            db=db,
            user_and_tenant=_contexto(tenant, 20),
        )
    assert excluir_de_outro_dono.value.status_code == 404
    assert db.get(DRESubcategoria, vinculada.id).ativo is True

    geral = criar_subcategoria_dre(
        DRESubcategoriaCreate(
            categoria_id=categoria_dre.id,
            nome="Compartilhada",
            tipo_custo=TipoCusto.DIRETO,
            escopo_rateio=EscopoRateio.AMBOS,
        ),
        db=db,
        user_and_tenant=_contexto(tenant, 20),
    )
    atualizada = atualizar_subcategoria_dre(
        geral.id,
        DRESubcategoriaUpdate(custo_pe="variavel"),
        db=db,
        user_and_tenant=_contexto(tenant, 10),
    )
    assert atualizada.custo_pe == "variavel"


def test_nao_exclui_subcategoria_dre_geral_usada_por_categoria_ativa(db):
    tenant = uuid4()
    categoria_dre = criar_categoria_dre(
        DRECategoriaCreate(nome="Serviços", natureza=NaturezaDRE.DESPESA),
        db=db,
        user_and_tenant=_contexto(tenant, 10),
    )
    geral = criar_subcategoria_dre(
        DRESubcategoriaCreate(
            categoria_id=categoria_dre.id,
            nome="Hospedagem",
            tipo_custo=TipoCusto.DIRETO,
            escopo_rateio=EscopoRateio.AMBOS,
        ),
        db=db,
        user_and_tenant=_contexto(tenant, 10),
    )
    categoria_financeira = _categoria(db, tenant, nome="Hospedagem", user_id=20)
    categoria_financeira.dre_subcategoria_id = geral.id
    db.commit()

    for usuario_id in (10, 20):
        with pytest.raises(HTTPException) as erro:
            deletar_subcategoria_dre(
                geral.id,
                db=db,
                user_and_tenant=_contexto(tenant, usuario_id),
            )
        assert erro.value.status_code == 409
        assert "Desvincule" in erro.value.detail
        assert (
            db.get(CategoriaFinanceira, categoria_financeira.id).dre_subcategoria_id
            == geral.id
        )
        assert db.get(DRESubcategoria, geral.id).ativo is True

    categoria_financeira.ativo = False
    db.commit()
    deletar_subcategoria_dre(
        geral.id,
        db=db,
        user_and_tenant=_contexto(tenant, 10),
    )
    assert db.get(DRESubcategoria, geral.id) is None
    assert (
        db.get(CategoriaFinanceira, categoria_financeira.id).dre_subcategoria_id is None
    )


def test_devolucao_reutiliza_categoria_plural_no_mesmo_tenant(db):
    tenant, outro_tenant = uuid4(), uuid4()
    _categoria(db, outro_tenant, nome="Devoluções de Vendas")
    _categoria(db, tenant, nome="Devoluções de Vendas", tipo="receita")
    primeira = _categoria(db, tenant, nome="Devoluções de Vendas", user_id=10)
    _categoria(db, tenant, nome="Devoluções de Vendas", user_id=20)

    encontrada = _buscar_categoria_devolucoes(db, tenant)
    assert encontrada.id == primeira.id
