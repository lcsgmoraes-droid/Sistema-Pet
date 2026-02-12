"""
TESTE DE ATOMICIDADE - PROVISÃO DE COMISSÕES

Prova que provisionar_comissoes_venda é TOTALMENTE ATÔMICA:
- Se ocorrer exceção NO MEIO do processamento,
- NENHUMA provisão parcial persiste no banco.

CENÁRIO:
- Venda com 3 comissões pendentes de provisão
- Forçar exceção após criar PRIMEIRA conta a pagar
- Verificar que ZERO provisões foram criadas

MOCK ESTRATÉGICO:
- atualizar_dre_por_lancamento (chamada na 2ª iteração do loop)
- Lança exceção após primeira provisão estar "completa"
- Testa rollback no meio do loop de processamento

VERIFICAÇÕES:
1. Nenhuma conta a pagar criada
2. Nenhum lançamento DRE registrado
3. Todas comissões permanecem comissao_provisionada = 0
4. Campo conta_pagar_id permanece NULL
5. Campo data_provisao permanece NULL
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.comissoes_provisao import provisionar_comissoes_venda


@pytest.fixture(scope="function")
def db_session():
    """
    Cria sessão de teste com transação REAL para rollback.
    """
    engine = create_engine("postgresql://postgres:postgres@localhost:5432/sistemapet_test")
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    # Garantir que tenant_id está disponível
    @event.listens_for(session, "before_cursor_execute", retval=True)
    def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
        if isinstance(params, dict) and "tenant_id" not in params:
            params["tenant_id"] = "test_tenant"
        return statement, params

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def cenario_venda_com_comissoes(db_session):
    """
    Cria cenário completo para teste de provisão:
    - Cliente
    - Fornecedor (funcionário comissionado)
    - 3 Funcionários (users)
    - Subcategoria DRE "Comissões"
    - 3 Produtos
    - Venda com status 'finalizada'
    - 3 Itens de venda
    - 3 Comissões pendentes de provisão (comissao_provisionada = 0)
    """
    tenant_id = "test_tenant"

    # ============================================================
    # 1. CLIENTE
    # ============================================================
    db_session.execute(
        text("""
            INSERT INTO clientes (
                id, nome, cpf_cnpj, telefone, email, 
                tipo, ativo, tenant_id, created_at, updated_at
            ) VALUES (
                9001, 'Cliente Teste Provisão', '12345678901', 
                '11999999001', 'cliente.provisao@test.com',
                'pessoa_fisica', 1, :tenant_id, 
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """),
        {"tenant_id": tenant_id}
    )

    # ============================================================
    # 2. FORNECEDOR (para funcionário ser vinculado)
    # ============================================================
    db_session.execute(
        text("""
            INSERT INTO fornecedores (
                id, nome, cpf_cnpj, tipo, ativo, 
                tenant_id, created_at, updated_at
            ) VALUES 
            (8001, 'Vendedor A - Fornecedor', '11111111111', 'pessoa_fisica', 1, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (8002, 'Vendedor B - Fornecedor', '22222222222', 'pessoa_fisica', 1, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (8003, 'Vendedor C - Fornecedor', '33333333333', 'pessoa_fisica', 1, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {"tenant_id": tenant_id}
    )

    # ============================================================
    # 3. FUNCIONÁRIOS (users)
    # ============================================================
    db_session.execute(
        text("""
            INSERT INTO users (
                id, nome, email, password, role, ativo, 
                data_fechamento_comissao, tenant_id, 
                created_at, updated_at
            ) VALUES 
            (7001, 'Vendedor A', 'vendedorA@test.com', 'hash123', 'vendedor', 1, 5, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (7002, 'Vendedor B', 'vendedorB@test.com', 'hash456', 'vendedor', 1, 10, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (7003, 'Vendedor C', 'vendedorC@test.com', 'hash789', 'vendedor', 1, 15, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {"tenant_id": tenant_id}
    )

    # ============================================================
    # 4. SUBCATEGORIA DRE "Comissões"
    # ============================================================
    db_session.execute(
        text("""
            INSERT INTO dre_subcategorias (
                id, nome, tipo, categoria_id, ativo, 
                tenant_id, created_at, updated_at
            ) VALUES (
                6001, 'Comissões', 'DESPESA', 1, 1, 
                :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """),
        {"tenant_id": tenant_id}
    )

    # ============================================================
    # 5. PRODUTOS
    # ============================================================
    db_session.execute(
        text("""
            INSERT INTO produtos (
                id, nome, preco_venda, controlar_estoque, estoque_minimo,
                ativo, tenant_id, created_at, updated_at
            ) VALUES 
            (5001, 'Produto A', 100.00, 1, 10, 1, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (5002, 'Produto B', 150.00, 1, 10, 1, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (5003, 'Produto C', 200.00, 1, 10, 1, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {"tenant_id": tenant_id}
    )

    # ============================================================
    # 6. VENDA FINALIZADA
    # ============================================================
    data_venda = date.today()
    db_session.execute(
        text("""
            INSERT INTO vendas (
                id, numero_venda, cliente_id, data_venda, 
                valor_total, valor_desconto, valor_final, 
                status, canal, tipo_pagamento, 
                user_id, tenant_id, created_at, updated_at
            ) VALUES (
                4001, 'VENDA-PROV-001', 9001, :data_venda, 
                450.00, 0.00, 450.00, 
                'finalizada', 'loja_fisica', 'dinheiro',
                7001, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """),
        {"tenant_id": tenant_id, "data_venda": data_venda}
    )

    # ============================================================
    # 7. ITENS DA VENDA
    # ============================================================
    db_session.execute(
        text("""
            INSERT INTO vendas_itens (
                id, venda_id, produto_id, quantidade, 
                preco_unitario, subtotal, desconto, 
                tenant_id, created_at, updated_at
            ) VALUES 
            (3001, 4001, 5001, 1, 100.00, 100.00, 0.00, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (3002, 4001, 5002, 1, 150.00, 150.00, 0.00, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (3003, 4001, 5003, 1, 200.00, 200.00, 0.00, :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {"tenant_id": tenant_id}
    )

    # ============================================================
    # 8. COMISSÕES PENDENTES (comissao_provisionada = 0)
    # ============================================================
    db_session.execute(
        text("""
            INSERT INTO comissoes_itens (
                id, venda_id, item_venda_id, funcionario_id, 
                produto_id, tipo_comissao, percentual_comissao, 
                valor_base_calculo, valor_comissao_gerada, 
                status, comissao_provisionada, comissao_paga,
                tenant_id, created_at, updated_at
            ) VALUES 
            (
                2001, 4001, 3001, 7001, 
                5001, 'percentual', 10.00, 
                100.00, 10.00, 
                'pendente', 0, 0,
                :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ),
            (
                2002, 4001, 3002, 7002, 
                5002, 'percentual', 10.00, 
                150.00, 15.00, 
                'pendente', 0, 0,
                :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ),
            (
                2003, 4001, 3003, 7003, 
                5003, 'percentual', 10.00, 
                200.00, 20.00, 
                'pendente', 0, 0,
                :tenant_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """),
        {"tenant_id": tenant_id}
    )

    db_session.commit()

    return {
        "venda_id": 4001,
        "tenant_id": tenant_id,
        "comissoes_ids": [2001, 2002, 2003],
        "funcionarios_ids": [7001, 7002, 7003],
        "valores_comissoes": [Decimal("10.00"), Decimal("15.00"), Decimal("20.00")]
    }


def test_provisionar_comissoes_rollback_on_exception(db_session, cenario_venda_com_comissoes):
    """
    TESTE: Provisão de comissões com rollback completo ao falhar no meio.

    ESTRATÉGIA:
    1. Montar venda com 3 comissões pendentes
    2. Mockar atualizar_dre_por_lancamento para falhar na 2ª chamada
    3. Executar provisionar_comissoes_venda (deve lançar exceção)
    4. Verificar rollback total:
       - 0 contas a pagar criadas
       - 0 lançamentos DRE
       - 3 comissões ainda com comissao_provisionada = 0
       - campos conta_pagar_id e data_provisao ainda NULL
    """
    venda_id = cenario_venda_com_comissoes["venda_id"]
    tenant_id = cenario_venda_com_comissoes["tenant_id"]

    # ============================================================
    # MOCK: Falhar ao processar 2ª comissão
    # ============================================================
    call_count = {"count": 0}

    def atualizar_dre_mock(db, tenant_id, dre_subcategoria_id, canal, valor, data_lancamento, tipo_movimentacao):
        call_count["count"] += 1
        if call_count["count"] == 2:
            # Na 2ª comissão, lançar exceção
            raise Exception("ERRO SIMULADO: Falha ao atualizar DRE na 2ª comissão")
        # 1ª chamada: continuar normalmente (sem fazer nada, pois é mock)
        return

    # ============================================================
    # EXECUTAR: Deve lançar exceção
    # ============================================================
    with patch("app.comissoes_provisao.atualizar_dre_por_lancamento", side_effect=atualizar_dre_mock):
        with pytest.raises(Exception, match="ERRO SIMULADO"):
            provisionar_comissoes_venda(
                venda_id=venda_id,
                tenant_id=tenant_id,
                db=db_session
            )

    # ============================================================
    # INVALIDAR CACHE ORM
    # ============================================================
    db_session.expire_all()

    # ============================================================
    # VERIFICAÇÃO 1: ZERO contas a pagar criadas
    # ============================================================
    result_contas = db_session.execute(
        text("""
            SELECT COUNT(*) as total
            FROM contas_pagar
            WHERE tenant_id = :tenant_id
        """),
        {"tenant_id": tenant_id}
    )
    total_contas = result_contas.fetchone()[0]
    assert total_contas == 0, (
        f"❌ FALHA: Esperado 0 contas a pagar após rollback, mas encontrado {total_contas}. "
        "O rollback não funcionou!"
    )

    # ============================================================
    # VERIFICAÇÃO 2: ZERO lançamentos DRE
    # ============================================================
    result_dre = db_session.execute(
        text("""
            SELECT COUNT(*) as total
            FROM dre_totalizador
            WHERE tenant_id = :tenant_id
            AND dre_subcategoria_id = 6001
        """),
        {"tenant_id": tenant_id}
    )
    total_dre = result_dre.fetchone()[0]
    assert total_dre == 0, (
        f"❌ FALHA: Esperado 0 lançamentos DRE após rollback, mas encontrado {total_dre}. "
        "O rollback não funcionou!"
    )

    # ============================================================
    # VERIFICAÇÃO 3: Todas comissões permanecem NÃO provisionadas
    # ============================================================
    result_comissoes = db_session.execute(
        text("""
            SELECT 
                id,
                comissao_provisionada,
                conta_pagar_id,
                data_provisao
            FROM comissoes_itens
            WHERE venda_id = :venda_id
            ORDER BY id
        """),
        {"venda_id": venda_id}
    )
    comissoes = result_comissoes.fetchall()

    assert len(comissoes) == 3, f"Esperado 3 comissões, encontrado {len(comissoes)}"

    for idx, comissao in enumerate(comissoes, start=1):
        assert comissao.comissao_provisionada == 0, (
            f"❌ FALHA: Comissão #{comissao.id} tem comissao_provisionada = {comissao.comissao_provisionada}, "
            f"esperado 0. O rollback não funcionou!"
        )
        assert comissao.conta_pagar_id is None, (
            f"❌ FALHA: Comissão #{comissao.id} tem conta_pagar_id = {comissao.conta_pagar_id}, "
            f"esperado NULL. O rollback não funcionou!"
        )
        assert comissao.data_provisao is None, (
            f"❌ FALHA: Comissão #{comissao.id} tem data_provisao = {comissao.data_provisao}, "
            f"esperado NULL. O rollback não funcionou!"
        )

    # ============================================================
    # ✅ SUCESSO: Rollback total confirmado
    # ============================================================
    print("\n" + "="*80)
    print("✅ TESTE PASSOU: Rollback total confirmado!")
    print("="*80)
    print(f"✅ 0 contas a pagar criadas (esperado: 0)")
    print(f"✅ 0 lançamentos DRE registrados (esperado: 0)")
    print(f"✅ 3 comissões permanecem comissao_provisionada = 0")
    print(f"✅ 3 comissões permanecem conta_pagar_id = NULL")
    print(f"✅ 3 comissões permanecem data_provisao = NULL")
    print("="*80)
    print("CONCLUSÃO: transactional_session GARANTE atomicidade completa.")
    print("Mesmo com exceção após processar 1 comissão, NADA foi persistido.")
    print("="*80 + "\n")


def test_provisionar_comissoes_sucesso_sem_mock(db_session, cenario_venda_com_comissoes):
    """
    TESTE CONTROLE: Provisão completa SEM mock (deve ter sucesso).
    
    Prova que a função funciona corretamente quando NÃO há exceções.
    """
    venda_id = cenario_venda_com_comissoes["venda_id"]
    tenant_id = cenario_venda_com_comissoes["tenant_id"]

    # ============================================================
    # EXECUTAR: Sem mock, deve ter sucesso
    # ============================================================
    resultado = provisionar_comissoes_venda(
        venda_id=venda_id,
        tenant_id=tenant_id,
        db=db_session
    )

    # ============================================================
    # VERIFICAÇÕES: Sucesso completo
    # ============================================================
    assert resultado["success"] is True
    assert resultado["comissoes_provisionadas"] == 3
    assert resultado["valor_total"] == 45.00  # 10 + 15 + 20
    assert len(resultado["contas_criadas"]) == 3

    # Invalidar cache
    db_session.expire_all()

    # Verificar contas a pagar criadas
    result_contas = db_session.execute(
        text("""
            SELECT COUNT(*) as total
            FROM contas_pagar
            WHERE tenant_id = :tenant_id
        """),
        {"tenant_id": tenant_id}
    )
    total_contas = result_contas.fetchone()[0]
    assert total_contas == 3, f"Esperado 3 contas a pagar, encontrado {total_contas}"

    # Verificar comissões provisionadas
    result_comissoes = db_session.execute(
        text("""
            SELECT COUNT(*) as total
            FROM comissoes_itens
            WHERE venda_id = :venda_id
            AND comissao_provisionada = 1
        """),
        {"venda_id": venda_id}
    )
    total_provisionadas = result_comissoes.fetchone()[0]
    assert total_provisionadas == 3, f"Esperado 3 comissões provisionadas, encontrado {total_provisionadas}"

    print("\n" + "="*80)
    print("✅ TESTE CONTROLE PASSOU: Provisão completa com sucesso!")
    print("="*80)
    print(f"✅ 3 contas a pagar criadas")
    print(f"✅ 3 comissões marcadas como provisionadas")
    print(f"✅ Valor total: R$ 45.00")
    print("="*80 + "\n")
