from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.notas_entrada.listagem_routes import listar_notas_paginadas
from app.produtos_models import NotaEntrada, NotaEntradaItem


def _criar_nota(
    db_session,
    *,
    tenant_id,
    indice: int,
    status: str,
    valor_total: float,
    fornecedor_nome: str = "Fornecedor Teste",
):
    data_emissao = datetime(2026, 7, 1) + timedelta(days=indice)
    nota = NotaEntrada(
        tenant_id=tenant_id,
        numero_nota=f"{indice:06d}",
        serie="1",
        chave_acesso=f"{indice:044d}",
        fornecedor_cnpj=f"{indice:014d}",
        fornecedor_nome=fornecedor_nome,
        data_emissao=data_emissao,
        data_entrada=data_emissao,
        valor_produtos=valor_total,
        valor_total=valor_total,
        xml_content="<nfe />",
        status=status,
        produtos_vinculados=1,
        produtos_nao_vinculados=0,
        conferencia_status="nao_iniciada",
        user_id=1,
    )
    db_session.add(nota)
    db_session.flush()
    return nota


def _listar(db_session, tenant_id, **overrides):
    params = {
        "status": None,
        "fornecedor": None,
        "nf": None,
        "data_inicio": None,
        "data_fim": None,
        "conferencia": None,
        "page": 1,
        "page_size": 10,
        "db": db_session,
        "user_and_tenant": (object(), tenant_id),
    }
    params.update(overrides)
    return listar_notas_paginadas(**params)


def test_listagem_pagina_no_banco_e_mantem_metricas_globais(db_session, tenant_context):
    tenant_id = uuid4()
    tenant_context(tenant_id)

    for indice in range(1, 13):
        _criar_nota(
            db_session,
            tenant_id=tenant_id,
            indice=indice,
            status="pendente",
            valor_total=100,
        )
    _criar_nota(
        db_session,
        tenant_id=tenant_id,
        indice=20,
        status="processada",
        valor_total=250.5,
    )
    _criar_nota(
        db_session,
        tenant_id=tenant_id,
        indice=21,
        status="processada",
        valor_total=49.5,
    )
    _criar_nota(
        db_session,
        tenant_id=tenant_id,
        indice=22,
        status="erro",
        valor_total=80,
    )

    resposta = _listar(
        db_session,
        tenant_id,
        status="pendente",
        page=2,
    )

    assert resposta.total == 12
    assert resposta.page == 2
    assert resposta.pages == 2
    assert len(resposta.items) == 2
    assert resposta.metricas.total_notas == 15
    assert resposta.metricas.pendentes == 12
    assert resposta.metricas.conciliadas == 2
    assert resposta.metricas.com_erro == 1
    assert resposta.metricas.valor_conciliado == 300


def test_listagem_filtra_historico_e_resume_divergencias_sem_carregar_itens(
    db_session, tenant_context
):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    nota = _criar_nota(
        db_session,
        tenant_id=tenant_id,
        indice=30,
        status="pendente",
        valor_total=500,
        fornecedor_nome="Distribuidora Exemplo",
    )
    db_session.add(
        NotaEntradaItem(
            tenant_id=tenant_id,
            nota_entrada_id=nota.id,
            numero_item=1,
            descricao="Produto com falta",
            quantidade=10,
            quantidade_conferida=8,
            quantidade_avariada=0,
            valor_unitario=50,
            valor_total=500,
        )
    )
    _criar_nota(
        db_session,
        tenant_id=tenant_id,
        indice=31,
        status="pendente",
        valor_total=100,
        fornecedor_nome="Outro fornecedor",
    )
    db_session.flush()

    resposta = _listar(
        db_session,
        tenant_id,
        fornecedor="Exemplo",
        nf="000030",
        data_inicio=datetime(2026, 7, 31).date(),
        data_fim=datetime(2026, 7, 31).date(),
    )

    assert resposta.total == 1
    assert [item.numero_nota for item in resposta.items] == ["000030"]
    assert resposta.items[0].divergencias_count == 1


def test_router_registra_listagem_antes_das_rotas_dinamicas():
    routes_source = (
        Path(__file__).resolve().parents[2] / "app" / "notas_entrada_routes.py"
    ).read_text(encoding="utf-8")

    assert "from .notas_entrada.listagem_routes import router as listagem_router" in (
        routes_source
    )
    assert routes_source.index("router.include_router(listagem_router)") < (
        routes_source.index("router.include_router(consulta_router)")
    )
