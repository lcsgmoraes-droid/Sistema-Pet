from decimal import Decimal
from uuid import UUID

from sqlalchemy import event

from app.produtos import listagem as produtos_listagem
from app.produtos_models import Produto, ProdutoKitComponente
from app.services.kit_custo_service import KitCustoService


def _produto(*, tenant_id, user_id, codigo, nome, tipo_produto, custo, tipo_kit=None):
    return Produto(
        tenant_id=tenant_id,
        user_id=user_id,
        codigo=codigo,
        nome=nome,
        tipo_produto=tipo_produto,
        tipo_kit=tipo_kit,
        preco_custo=custo,
        preco_venda=50,
        estoque_atual=0,
        situacao=True,
        ativo=True,
    )


def test_calcular_custos_kits_em_lote_soma_componentes(
    db_session, tenant_context
):
    tenant_id = UUID("00000000-0000-0000-0000-000000000101")
    tenant_context(tenant_id)
    componente = _produto(
        tenant_id=tenant_id,
        user_id=101,
        codigo="013251.1",
        nome="Racao Megazoo Chinchila 500gr",
        tipo_produto="SIMPLES",
        custo=26.92,
    )
    kit = _produto(
        tenant_id=tenant_id,
        user_id=101,
        codigo="013259.1FBA",
        nome="Racao Megazoo Chinchila 500gr (Kit Virtual)",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        custo=0,
    )
    db_session.add_all([componente, kit])
    db_session.flush()
    db_session.add(
        ProdutoKitComponente(
            tenant_id=tenant_id,
            kit_id=kit.id,
            produto_componente_id=componente.id,
            quantidade=1,
        )
    )
    db_session.flush()

    custos = KitCustoService.calcular_custos_kits_em_lote(db_session, [kit])

    assert custos == {kit.id: Decimal("26.92")}
    assert kit.preco_custo == 0


def test_calcular_custos_kits_em_lote_consulta_todos_os_kits_juntos(
    db_session, tenant_context
):
    tenant_id = UUID("00000000-0000-0000-0000-000000000102")
    tenant_context(tenant_id)
    componente = _produto(
        tenant_id=tenant_id,
        user_id=102,
        codigo="COMP-LOTE",
        nome="Componente",
        tipo_produto="SIMPLES",
        custo=10,
    )
    kit_a = _produto(
        tenant_id=tenant_id,
        user_id=102,
        codigo="KIT-A",
        nome="Kit A",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        custo=0,
    )
    kit_b = _produto(
        tenant_id=tenant_id,
        user_id=102,
        codigo="KIT-B",
        nome="Kit B",
        tipo_produto="VARIACAO",
        tipo_kit="VIRTUAL",
        custo=0,
    )
    db_session.add_all([componente, kit_a, kit_b])
    db_session.flush()
    db_session.add_all(
        [
            ProdutoKitComponente(
                tenant_id=tenant_id,
                kit_id=kit_a.id,
                produto_componente_id=componente.id,
                quantidade=2,
            ),
            ProdutoKitComponente(
                tenant_id=tenant_id,
                kit_id=kit_b.id,
                produto_componente_id=componente.id,
                quantidade=3,
            ),
        ]
    )
    db_session.flush()

    consultas = []

    def registrar_consulta(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", registrar_consulta)
    try:
        custos = KitCustoService.calcular_custos_kits_em_lote(
            db_session, [kit_a, kit_b]
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", registrar_consulta)

    assert custos == {kit_a.id: Decimal("20.0"), kit_b.id: Decimal("30.0")}
    assert len(consultas) == 1


def test_recalcular_kits_que_usam_produtos_persiste_novo_custo(
    db_session, tenant_context
):
    tenant_id = UUID("00000000-0000-0000-0000-000000000103")
    tenant_context(tenant_id)
    componente = _produto(
        tenant_id=tenant_id,
        user_id=103,
        codigo="COMP-SYNC",
        nome="Componente sincronizado",
        tipo_produto="SIMPLES",
        custo=12.5,
    )
    kit = _produto(
        tenant_id=tenant_id,
        user_id=103,
        codigo="KIT-SYNC",
        nome="Kit sincronizado",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        custo=0,
    )
    db_session.add_all([componente, kit])
    db_session.flush()
    db_session.add(
        ProdutoKitComponente(
            tenant_id=tenant_id,
            kit_id=kit.id,
            produto_componente_id=componente.id,
            quantidade=2,
        )
    )
    db_session.flush()

    atualizados = KitCustoService.recalcular_kits_que_usam_produtos(
        db_session, [componente.id]
    )

    assert atualizados == {kit.id: Decimal("25.0")}
    assert kit.preco_custo == 25.0


def test_listagem_completa_expoe_custo_do_kit_sem_detalhes(
    db_session, tenant_context, monkeypatch
):
    tenant_id = UUID("00000000-0000-0000-0000-000000000104")
    tenant_context(tenant_id)
    componente = _produto(
        tenant_id=tenant_id,
        user_id=104,
        codigo="013251.1-LISTA",
        nome="Racao Megazoo Chinchila 500gr",
        tipo_produto="SIMPLES",
        custo=26.92,
    )
    kit = _produto(
        tenant_id=tenant_id,
        user_id=104,
        codigo="013259.1FBA-LISTA",
        nome="Racao Megazoo Chinchila 500gr (Kit Virtual)",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        custo=0,
    )
    db_session.add_all([componente, kit])
    db_session.flush()
    db_session.add(
        ProdutoKitComponente(
            tenant_id=tenant_id,
            kit_id=kit.id,
            produto_componente_id=componente.id,
            quantidade=1,
        )
    )
    db_session.flush()
    monkeypatch.setattr(
        produtos_listagem.KitEstoqueService,
        "calcular_estoque_virtual_kit",
        lambda *_args, **_kwargs: 7,
    )

    resultado = produtos_listagem._expandir_produtos_listagem(
        db_session,
        [kit],
        tenant_id=tenant_id,
        access_ids=[tenant_id],
        reservas_por_produto={},
        incluir_detalhes_composto=False,
        include_variations=False,
        termo_busca=None,
        load_options=[],
        validade_por_produto={},
    )

    assert resultado == [kit]
    assert kit.preco_custo == 26.92
    assert kit.composicao_kit == []
    assert kit.estoque_virtual == 7
