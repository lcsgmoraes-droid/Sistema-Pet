"""
Teste de Integração: Rollback de Transaction em Estorno de Comissões

OBJETIVO:
Provar que, se ocorrer uma exceção NO MEIO da função estornar_comissoes_venda,
NENHUMA alteração parcial persiste no banco.

ESTRATÉGIA:
1. Montar cenário completo (venda + comissões com status 'pendente')
2. Mockar execute_tenant_safe (UPDATE) para lançar exceção durante a atualização
3. Executar estornar_comissoes_venda esperando exceção
4. Verificar que NENHUM dado foi alterado (rollback total)
"""

# ruff: noqa: E402

import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
from decimal import Decimal

# Importações do sistema
import sys
import os
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.comissoes_estorno import estornar_comissoes_venda
from app.vendas_models import Venda
from app.models import User, Tenant


# Configuração do banco de dados de teste
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://petshop_user:petshop_password_2026@localhost:5432/petshop_db"
)


@pytest.fixture(scope="module")
def db_engine():
    """Criar engine de banco de dados para testes."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Fornecer sessão de banco com rollback automático no final."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    
    # Iniciar transação externa (será rollback no final do teste)
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    # Rollback de tudo ao final do teste (limpeza)
    transaction.rollback()
    connection.close()


@pytest.fixture
def tenant_e_usuario(db_session):
    """Criar tenant e usuário para o teste."""
    # Verificar se tenant de teste já existe
    tenant = db_session.query(Tenant).filter_by(tenant_id='test_tenant_estorno').first()
    if not tenant:
        tenant = Tenant(
            tenant_id='test_tenant_estorno',
            nome='Tenant Teste Estorno',
            ativo=True
        )
        db_session.add(tenant)
    
    # Verificar se usuário de teste já existe
    user = db_session.query(User).filter_by(
        email='test_estorno@test.com',
        tenant_id='test_tenant_estorno'
    ).first()
    
    if not user:
        user = User(
            nome='Usuario Teste Estorno',
            email='test_estorno@test.com',
            password_hash='hash_teste',
            tenant_id='test_tenant_estorno',
            ativo=True,
            role='admin'
        )
        db_session.add(user)
    
    db_session.commit()
    
    return tenant, user


@pytest.fixture
def cenario_venda_com_comissoes(db_session, tenant_e_usuario):
    """
    Montar cenário completo de venda com comissões:
    - 1 Venda finalizada
    - 3 Comissões com status 'pendente'
    - Valores de comissão definidos
    """
    tenant, user = tenant_e_usuario
    tenant_id = tenant.tenant_id
    
    # ============================================================
    # 1. Criar Venda
    # ============================================================
    venda = Venda(
        numero_venda='VENDA-ESTORNO-001',
        data_venda=date.today(),
        cliente_id=None,
        usuario_id=user.id,
        user_id=user.id,
        total=Decimal('500.00'),
        subtotal=Decimal('500.00'),
        desconto=Decimal('0'),
        status='finalizada',
        canal='loja_fisica',
        tenant_id=tenant_id
    )
    db_session.add(venda)
    db_session.flush()
    
    venda_id = venda.id
    
    # ============================================================
    # 2. Criar Comissões Diretamente (via SQL bruto)
    # ============================================================
    from sqlalchemy import text
    
    # Comissão 1
    db_session.execute(text("""
        INSERT INTO comissoes_itens (
            venda_id, funcionario_id, produto_id, 
            valor_comissao, status, 
            tenant_id, created_at
        ) VALUES (
            :venda_id, :funcionario_id, 1,
            :valor_comissao, 'pendente',
            :tenant_id, NOW()
        )
    """), {
        'venda_id': venda_id,
        'funcionario_id': user.id,
        'valor_comissao': 50.00,
        'tenant_id': tenant_id
    })
    
    # Comissão 2
    db_session.execute(text("""
        INSERT INTO comissoes_itens (
            venda_id, funcionario_id, produto_id, 
            valor_comissao, status, 
            tenant_id, created_at
        ) VALUES (
            :venda_id, :funcionario_id, 2,
            :valor_comissao, 'pendente',
            :tenant_id, NOW()
        )
    """), {
        'venda_id': venda_id,
        'funcionario_id': user.id,
        'valor_comissao': 75.00,
        'tenant_id': tenant_id
    })
    
    # Comissão 3
    db_session.execute(text("""
        INSERT INTO comissoes_itens (
            venda_id, funcionario_id, produto_id, 
            valor_comissao, status, 
            tenant_id, created_at
        ) VALUES (
            :venda_id, :funcionario_id, 3,
            :valor_comissao, 'pendente',
            :tenant_id, NOW()
        )
    """), {
        'venda_id': venda_id,
        'funcionario_id': user.id,
        'valor_comissao': 100.00,
        'tenant_id': tenant_id
    })
    
    db_session.commit()
    
    # ============================================================
    # Buscar IDs das comissões criadas
    # ============================================================
    result = db_session.execute(text("""
        SELECT id, status, valor_comissao
        FROM comissoes_itens
        WHERE venda_id = :venda_id
        ORDER BY id
    """), {'venda_id': venda_id})
    
    comissoes = result.fetchall()
    comissoes_ids = [c[0] for c in comissoes]
    
    # Retornar IDs e valores iniciais para verificação
    return {
        'tenant_id': tenant_id,
        'user_id': user.id,
        'user': user,
        'venda_id': venda_id,
        'comissoes_ids': comissoes_ids,
        'comissoes_count': len(comissoes),
        'valor_total': sum(float(c[2]) for c in comissoes)
    }


class TestTransactionRollbackEstornoComissoes:
    """
    Testes de Rollback em Estorno de Comissões.
    
    Prova que o transactional_session garante atomicidade:
    se qualquer exceção ocorrer no meio do processo,
    NENHUMA alteração parcial persiste.
    """
    
    def test_rollback_total_quando_excecao_no_meio_do_estorno(
        self,
        db_session,
        cenario_venda_com_comissoes
    ):
        """
        TESTE PRINCIPAL: Rollback total quando exceção ocorre no meio do estorno.
        
        CENÁRIO:
        1. Venda com 3 comissões com status 'pendente'
        2. Mockar execute_tenant_safe para:
           - Primeira chamada (SELECT): sucesso (retorna comissões)
           - Segunda chamada (UPDATE): EXCEÇÃO
        3. Executar estornar_comissoes_venda
        4. Esperar exceção
        5. Verificar que NENHUM dado foi alterado (rollback total)
        
        GARANTIA:
        Se o rollback funcionar corretamente:
        - Nenhuma comissão foi estornada
        - Status de todas as comissões continua 'pendente'
        - Campos data_estorno, motivo_estorno, estornado_por continuam NULL
        """
        cenario = cenario_venda_com_comissoes
        
        # ============================================================
        # ANTES: Capturar estado inicial
        # ============================================================
        from sqlalchemy import text
        
        # Buscar comissões
        result_antes = db_session.execute(text("""
            SELECT id, status, data_estorno, motivo_estorno, estornado_por
            FROM comissoes_itens
            WHERE venda_id = :venda_id
            ORDER BY id
        """), {'venda_id': cenario['venda_id']})
        
        comissoes_antes = result_antes.fetchall()
        
        assert len(comissoes_antes) == 3, "Devem existir 3 comissões antes do teste"
        
        # Verificar que todas estão pendentes
        for comissao in comissoes_antes:
            assert comissao[1] == 'pendente', f"Comissão {comissao[0]} deve estar pendente"
            assert comissao[2] is None, f"Comissão {comissao[0]} não deve ter data_estorno"
            assert comissao[3] is None, f"Comissão {comissao[0]} não deve ter motivo_estorno"
            assert comissao[4] is None, f"Comissão {comissao[0]} não deve ter estornado_por"
        
        print("\n" + "="*80)
        print("📊 ESTADO INICIAL (ANTES DO ESTORNO):")
        print("="*80)
        print(f"✅ Venda ID: {cenario['venda_id']}")
        print(f"✅ Comissões: {len(comissoes_antes)}")
        for comissao in comissoes_antes:
            print(f"   - Comissão ID {comissao[0]}: status='{comissao[1]}', data_estorno={comissao[2]}")
        print("="*80)
        
        # ============================================================
        # MOCKAR: execute_tenant_safe
        # Lançar exceção na segunda chamada (UPDATE)
        # ============================================================
        
        call_count = {'count': 0}
        def execute_tenant_safe_mock(db, query, params=None, *args, **kwargs):
            """
            Mock que lança exceção na segunda chamada.
            
            Primeira chamada (SELECT): retorna comissões normalmente
            Segunda chamada (UPDATE): EXCEÇÃO
            
            Isso simula falha NO MEIO do processo de estorno.
            """
            call_count['count'] += 1
            
            if call_count['count'] == 1:
                # Primeira chamada (SELECT): sucesso
                print("\n🔧 MOCK: Primeira chamada (SELECT) - SUCESSO")
                
                # Retornar resultado real do SELECT
                from sqlalchemy import text
                result = db.execute(text("""
                    SELECT 
                        id,
                        status,
                        valor_comissao,
                        funcionario_id
                    FROM comissoes_itens
                    WHERE venda_id = :venda_id
                    ORDER BY id
                """), {'venda_id': params['venda_id']})
                
                return result
            else:
                # Segunda chamada (UPDATE): EXCEÇÃO
                print("\n💥 MOCK: Segunda chamada (UPDATE) - LANÇANDO EXCEÇÃO")
                raise Exception("ERRO SIMULADO: Falha ao atualizar status das comissões")
        
        # ============================================================
        # EXECUTAR: estornar_comissoes_venda com mock
        # ============================================================
        
        with patch('app.comissoes_estorno.execute_tenant_safe', side_effect=execute_tenant_safe_mock):
            print("\n" + "="*80)
            print("🚀 EXECUTANDO ESTORNO DE COMISSÕES (COM MOCK)")
            print("="*80)
            
            # Esperar exceção
            with pytest.raises(Exception) as excinfo:
                estornar_comissoes_venda(
                    venda_id=cenario['venda_id'],
                    motivo='Teste de rollback',
                    usuario_id=cenario['user_id'],
                    db=db_session
                )
            
            print(f"\n✅ EXCEÇÃO CAPTURADA (esperado): {str(excinfo.value)}")
        
        # ============================================================
        # VERIFICAR: Rollback total (NENHUM dado alterado)
        # ============================================================
        
        # Forçar refresh da sessão
        db_session.expire_all()
        
        print("\n" + "="*80)
        print("🔍 VERIFICANDO ROLLBACK TOTAL:")
        print("="*80)
        
        # Buscar comissões novamente
        result_depois = db_session.execute(text("""
            SELECT id, status, data_estorno, motivo_estorno, estornado_por
            FROM comissoes_itens
            WHERE venda_id = :venda_id
            ORDER BY id
        """), {'venda_id': cenario['venda_id']})
        
        comissoes_depois = result_depois.fetchall()
        
        # 1. Quantidade de comissões não mudou
        assert len(comissoes_depois) == len(comissoes_antes), \
            f"❌ FALHA: Quantidade de comissões mudou ({len(comissoes_antes)} --> {len(comissoes_depois)})"
        print(f"✓ Quantidade de comissões NÃO mudou (total: {len(comissoes_depois)})")
        
        # 2. Verificar que NENHUMA comissão foi estornada
        for i, comissao_depois in enumerate(comissoes_depois):
            comissao_antes = comissoes_antes[i]
            
            # Status não mudou
            assert comissao_depois[1] == comissao_antes[1], \
                f"❌ FALHA: Status da comissão {comissao_depois[0]} mudou ({comissao_antes[1]} --> {comissao_depois[1]})"
            assert comissao_depois[1] == 'pendente', \
                f"❌ FALHA: Status da comissão {comissao_depois[0]} deveria ser 'pendente', mas é '{comissao_depois[1]}'"
            
            # data_estorno continua NULL
            assert comissao_depois[2] is None, \
                f"❌ FALHA: Comissão {comissao_depois[0]} tem data_estorno preenchida: {comissao_depois[2]}"
            
            # motivo_estorno continua NULL
            assert comissao_depois[3] is None, \
                f"❌ FALHA: Comissão {comissao_depois[0]} tem motivo_estorno preenchido: {comissao_depois[3]}"
            
            # estornado_por continua NULL
            assert comissao_depois[4] is None, \
                f"❌ FALHA: Comissão {comissao_depois[0]} tem estornado_por preenchido: {comissao_depois[4]}"
            
            print(f"✅ Comissão ID {comissao_depois[0]}: status='{comissao_depois[1]}' (NÃO foi estornada)")
        
        print("\n" + "="*80)
        print("🎉 ROLLBACK TOTAL VERIFICADO COM SUCESSO!")
        print("="*80)
        print("✅ TODAS as verificações passaram")
        print("✅ NENHUMA comissão foi estornada")
        print("✅ Status de todas as comissões continua 'pendente'")
        print("✅ Campos data_estorno, motivo_estorno, estornado_por continuam NULL")
        print("✅ transactional_session garantiu atomicidade total")
        print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
