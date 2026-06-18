"""
Teste de Integração: Rollback de Transaction em Cancelamento de Venda

OBJETIVO:
Provar que, se ocorrer uma exceção NO MEIO da função cancelar_venda,
NENHUMA alteração parcial persiste no banco.

ESTRATÉGIA:
1. Montar cenário completo (venda + itens + estoque + financeiro)
2. Mockar UMA função interna chamada por cancelar_venda para lançar exceção
   (ex: após estornar primeiro item, antes de cancelar contas a receber)
3. Executar cancelar_venda esperando exceção
4. Verificar que NENHUM dado foi alterado (rollback total)
"""

# ruff: noqa: E402

import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
from decimal import Decimal

# Importações do sistema
import sys
import os
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.vendas.service import VendaService
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto, EstoqueMovimentacao
from app.financeiro_models import ContaReceber, MovimentacaoFinanceira, ContaBancaria, LancamentoManual
from app.caixa_models import MovimentacaoCaixa
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
    tenant = db_session.query(Tenant).filter_by(tenant_id='test_tenant_cancelar').first()
    if not tenant:
        tenant = Tenant(
            tenant_id='test_tenant_cancelar',
            nome='Tenant Teste Cancelar',
            ativo=True
        )
        db_session.add(tenant)
    
    # Verificar se usuário de teste já existe
    user = db_session.query(User).filter_by(
        email='test_cancelar@test.com',
        tenant_id='test_tenant_cancelar'
    ).first()
    
    if not user:
        user = User(
            nome='Usuario Teste Cancelar',
            email='test_cancelar@test.com',
            password_hash='hash_teste',
            tenant_id='test_tenant_cancelar',
            ativo=True,
            role='admin'
        )
        db_session.add(user)
    
    db_session.commit()
    
    return tenant, user


@pytest.fixture
def cenario_venda_ativa(db_session, tenant_e_usuario):
    """
    Montar cenário completo de venda ATIVA:
    - 1 Produto com estoque reduzido pela venda
    - 1 Venda com status 'finalizada' (ativa)
    - 2 itens na venda
    - Conta a receber pendente
    - Movimentação de caixa
    - Movimentação bancária
    - Lançamento manual
    - Estoque já reduzido pela venda
    """
    tenant, user = tenant_e_usuario
    tenant_id = tenant.tenant_id
    
    # ============================================================
    # 1. Criar Produto
    # ============================================================
    produto = Produto(
        nome='Produto Teste Cancelar',
        preco_venda=Decimal('150.00'),
        estoque_atual=Decimal('100'),  # Estoque inicial alto
        estoque_minimo=Decimal('10'),
        controlar_estoque=True,
        ativo=True,
        tenant_id=tenant_id
    )
    db_session.add(produto)
    db_session.flush()
    
    produto_id = produto.id
    estoque_inicial = float(produto.estoque_atual)
    
    # ============================================================
    # 2. Criar Venda ATIVA (status='finalizada')
    # ============================================================
    venda = Venda(
        numero_venda='VENDA-CANCEL-001',
        data_venda=date.today(),
        cliente_id=None,
        usuario_id=user.id,
        user_id=user.id,  # Campo legado
        total=Decimal('300.00'),
        subtotal=Decimal('300.00'),
        desconto=Decimal('0'),
        status='finalizada',  # Status ativo (não cancelada)
        canal='loja_fisica',
        tenant_id=tenant_id
    )
    db_session.add(venda)
    db_session.flush()
    
    venda_id = venda.id
    status_inicial = venda.status
    
    # ============================================================
    # 3. Criar Itens da Venda
    # ============================================================
    item1 = VendaItem(
        venda_id=venda_id,
        produto_id=produto_id,
        produto_nome='Produto Teste Cancelar',
        quantidade=Decimal('1'),
        preco_unitario=Decimal('150.00'),
        subtotal=Decimal('150.00'),
        tenant_id=tenant_id
    )
    db_session.add(item1)
    
    item2 = VendaItem(
        venda_id=venda_id,
        produto_id=produto_id,
        produto_nome='Produto Teste Cancelar',
        quantidade=Decimal('1'),
        preco_unitario=Decimal('150.00'),
        subtotal=Decimal('150.00'),
        tenant_id=tenant_id
    )
    db_session.add(item2)
    
    # ============================================================
    # 4. Reduzir Estoque (simulando venda)
    # ============================================================
    mov_estoque_saida = EstoqueMovimentacao(
        produto_id=produto_id,
        tipo='saida',
        quantidade=Decimal('2'),  # 2 itens vendidos
        motivo='venda',
        referencia_id=venda_id,
        referencia_tipo='venda',
        user_id=user.id,
        tenant_id=tenant_id,
        data_movimentacao=datetime.now()
    )
    db_session.add(mov_estoque_saida)
    
    # Atualizar estoque do produto
    produto.estoque_atual -= Decimal('2')
    estoque_apos_venda = float(produto.estoque_atual)
    
    # ============================================================
    # 5. Criar Conta a Receber
    # ============================================================
    conta_receber = ContaReceber(
        descricao=f'Venda {venda.numero_venda}',
        cliente_id=None,
        venda_id=venda_id,
        valor_original=Decimal('300.00'),
        valor_recebido=Decimal('0'),
        valor_final=Decimal('300.00'),
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status='pendente',
        tenant_id=tenant_id
    )
    db_session.add(conta_receber)
    db_session.flush()
    
    conta_receber_id = conta_receber.id
    
    # ============================================================
    # 6. Criar Movimentação de Caixa
    # ============================================================
    mov_caixa = MovimentacaoCaixa(
        tipo='receita',
        valor=Decimal('300.00'),
        descricao=f'Venda {venda.numero_venda}',
        venda_id=venda_id,
        user_id=user.id,
        tenant_id=tenant_id,
        data_movimentacao=datetime.now()
    )
    db_session.add(mov_caixa)
    db_session.flush()
    
    mov_caixa_id = mov_caixa.id
    
    # ============================================================
    # 7. Criar Conta Bancária e Movimentação Bancária
    # ============================================================
    conta_bancaria = ContaBancaria(
        nome='Banco Teste Cancelar',
        saldo_atual=Decimal('500.00'),
        ativo=True,
        user_id=user.id,
        tenant_id=tenant_id
    )
    db_session.add(conta_bancaria)
    db_session.flush()
    
    conta_bancaria_id = conta_bancaria.id
    saldo_bancario_inicial = float(conta_bancaria.saldo_atual)
    
    mov_bancaria = MovimentacaoFinanceira(
        tipo='receita',
        valor=Decimal('300.00'),
        descricao=f'Venda {venda.numero_venda}',
        venda_id=venda_id,
        conta_bancaria_id=conta_bancaria_id,
        data_movimentacao=datetime.now(),
        tenant_id=tenant_id
    )
    db_session.add(mov_bancaria)
    db_session.flush()
    
    mov_bancaria_id = mov_bancaria.id
    
    # Atualizar saldo da conta bancária
    conta_bancaria.saldo_atual += Decimal('300.00')
    saldo_bancario_apos_venda = float(conta_bancaria.saldo_atual)
    
    # ============================================================
    # 8. Criar Lançamento Manual
    # ============================================================
    lancamento = LancamentoManual(
        descricao=f'Venda {venda.numero_venda}',
        valor=Decimal('300.00'),
        tipo='receita',
        status='realizado',
        documento=f'VENDA-{venda_id}',
        data_lancamento=date.today(),
        tenant_id=tenant_id
    )
    db_session.add(lancamento)
    db_session.flush()
    
    lancamento_id = lancamento.id
    
    # ============================================================
    # COMMIT do cenário
    # ============================================================
    db_session.commit()
    
    # Retornar IDs e valores iniciais para verificação
    return {
        'tenant_id': tenant_id,
        'user_id': user.id,
        'user': user,
        'venda_id': venda_id,
        'produto_id': produto_id,
        'estoque_inicial': estoque_inicial,
        'estoque_apos_venda': estoque_apos_venda,
        'status_inicial': status_inicial,
        'conta_receber_id': conta_receber_id,
        'mov_caixa_id': mov_caixa_id,
        'conta_bancaria_id': conta_bancaria_id,
        'saldo_bancario_inicial': saldo_bancario_inicial,
        'saldo_bancario_apos_venda': saldo_bancario_apos_venda,
        'mov_bancaria_id': mov_bancaria_id,
        'lancamento_id': lancamento_id
    }


class TestTransactionRollbackCancelarVenda:
    """
    Testes de Rollback em Cancelamento de Venda.
    
    Prova que o transactional_session garante atomicidade:
    se qualquer exceção ocorrer no meio do processo,
    NENHUMA alteração parcial persiste.
    """
    
    def test_rollback_total_quando_excecao_no_meio_do_cancelamento(
        self,
        db_session,
        cenario_venda_ativa
    ):
        """
        TESTE PRINCIPAL: Rollback total quando exceção ocorre no meio do cancelamento.
        
        CENÁRIO:
        1. Venda ativa (status='finalizada') com estoque já reduzido
        2. Mockar EstoqueService.estornar_estoque para lançar exceção APÓS processar primeiro item
        3. Executar VendaService.cancelar_venda
        4. Esperar exceção
        5. Verificar que NENHUM dado foi alterado (rollback total)
        
        GARANTIA:
        Se o rollback funcionar corretamente:
        - Status da venda NÃO mudou (continua 'finalizada')
        - Estoque NÃO foi alterado (continua reduzido)
        - Conta a receber NÃO foi cancelada
        - Movimentação de caixa NÃO foi removida
        - Movimentação bancária NÃO foi removida
        - Saldo bancário NÃO foi alterado
        - Lançamento manual NÃO foi cancelado
        """
        cenario = cenario_venda_ativa
        
        # ============================================================
        # ANTES: Capturar estado inicial
        # ============================================================
        
        # Venda
        venda_antes = db_session.query(Venda).filter_by(id=cenario['venda_id']).first()
        assert venda_antes is not None, "Venda deve existir antes do teste"
        assert venda_antes.status == 'finalizada', "Venda deve estar finalizada"
        
        # Itens
        itens_antes = db_session.query(VendaItem).filter_by(venda_id=cenario['venda_id']).count()
        assert itens_antes == 2, "Deve haver 2 itens antes do teste"
        
        # Produto (estoque)
        produto_antes = db_session.query(Produto).filter_by(id=cenario['produto_id']).first()
        estoque_antes = float(produto_antes.estoque_atual)
        assert estoque_antes == cenario['estoque_apos_venda'], "Estoque deve estar reduzido pela venda"
        
        # Conta a receber
        conta_receber_antes = db_session.query(ContaReceber).filter_by(
            id=cenario['conta_receber_id']
        ).first()
        assert conta_receber_antes is not None, "Conta a receber deve existir"
        assert conta_receber_antes.status == 'pendente', "Conta deve estar pendente"
        
        # Movimentação de caixa
        mov_caixa_antes = db_session.query(MovimentacaoCaixa).filter_by(
            id=cenario['mov_caixa_id']
        ).first()
        assert mov_caixa_antes is not None, "Movimentação de caixa deve existir"
        
        # Conta bancária (saldo)
        conta_bancaria_antes = db_session.query(ContaBancaria).filter_by(
            id=cenario['conta_bancaria_id']
        ).first()
        saldo_bancario_antes = float(conta_bancaria_antes.saldo_atual)
        assert saldo_bancario_antes == cenario['saldo_bancario_apos_venda'], "Saldo bancário deve incluir a venda"
        
        # Movimentação bancária
        mov_bancaria_antes = db_session.query(MovimentacaoFinanceira).filter_by(
            id=cenario['mov_bancaria_id']
        ).first()
        assert mov_bancaria_antes is not None, "Movimentação bancária deve existir"
        
        # Lançamento manual
        lancamento_antes = db_session.query(LancamentoManual).filter_by(
            id=cenario['lancamento_id']
        ).first()
        assert lancamento_antes is not None, "Lançamento manual deve existir"
        assert lancamento_antes.status == 'realizado', "Lançamento deve estar realizado"
        
        print("\n" + "="*80)
        print("📊 ESTADO INICIAL (ANTES DO CANCELAMENTO):")
        print("="*80)
        print(f"✅ Venda ID: {venda_antes.id} - Status: {venda_antes.status}")
        print(f"✅ Itens: {itens_antes}")
        print(f"✅ Estoque produto: {estoque_antes} (reduzido pela venda)")
        print(f"✅ Conta a receber: ID {conta_receber_antes.id} - Status: {conta_receber_antes.status}")
        print(f"✅ Movimentação caixa: ID {mov_caixa_antes.id}")
        print(f"✅ Saldo bancário: R$ {saldo_bancario_antes}")
        print(f"✅ Movimentação bancária: ID {mov_bancaria_antes.id}")
        print(f"✅ Lançamento manual: ID {lancamento_antes.id} - Status: {lancamento_antes.status}")
        print("="*80)
        
        # ============================================================
        # MOCKAR: EstoqueService.estornar_estoque
        # Lançar exceção APÓS processar primeiro item
        # ============================================================
        
        call_count = {'count': 0}
        
        def estornar_estoque_mock(*args, **kwargs):
            """
            Mock que lança exceção na segunda chamada.
            
            Primeira chamada (item 1): sucesso
            Segunda chamada (item 2): EXCEÇÃO
            
            Isso simula falha NO MEIO do processo de cancelamento.
            """
            call_count['count'] += 1
            
            if call_count['count'] == 1:
                # Primeira chamada: sucesso
                print("\n🔧 MOCK: Primeira chamada (item 1) - SUCESSO")
                return {
                    'success': True,
                    'produto_nome': 'Produto Teste Cancelar',
                    'estoque_anterior': 98.0,
                    'estoque_novo': 99.0
                }
            else:
                # Segunda chamada: EXCEÇÃO
                print("\n💥 MOCK: Segunda chamada (item 2) - LANÇANDO EXCEÇÃO")
                raise Exception("ERRO SIMULADO: Falha ao estornar estoque do segundo item durante cancelamento")
        
        # ============================================================
        # EXECUTAR: VendaService.cancelar_venda com mock
        # ============================================================
        
        with patch('app.estoque.service.EstoqueService.estornar_estoque', side_effect=estornar_estoque_mock):
            print("\n" + "="*80)
            print("🚀 EXECUTANDO CANCELAMENTO DA VENDA (COM MOCK)")
            print("="*80)
            
            # Esperar HTTPException (função lança HTTPException em caso de erro)
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as excinfo:
                VendaService.cancelar_venda(
                    venda_id=cenario['venda_id'],
                    motivo='Teste de rollback',
                    user_id=cenario['user_id'],
                    tenant_id=cenario['tenant_id'],
                    db=db_session
                )
            
            print(f"\n✅ EXCEÇÃO CAPTURADA (esperado): {excinfo.value.detail}")
        
        # ============================================================
        # VERIFICAR: Rollback total (NENHUM dado alterado)
        # ============================================================
        
        # Forçar refresh da sessão
        db_session.expire_all()
        
        print("\n" + "="*80)
        print("🔍 VERIFICANDO ROLLBACK TOTAL:")
        print("="*80)
        
        # 1. Status da venda NÃO mudou
        venda_depois = db_session.query(Venda).filter_by(id=cenario['venda_id']).first()
        assert venda_depois is not None, "❌ FALHA: Venda foi excluída"
        assert venda_depois.status == venda_antes.status, \
            f"❌ FALHA: Status da venda mudou ({venda_antes.status} --> {venda_depois.status})"
        assert venda_depois.status == 'finalizada', "❌ FALHA: Status deveria continuar 'finalizada'"
        print(f"✓ Status da venda NÃO mudou (status: {venda_depois.status})")
        
        # 2. Itens NÃO foram excluídos
        itens_depois = db_session.query(VendaItem).filter_by(venda_id=cenario['venda_id']).count()
        assert itens_depois == itens_antes, f"❌ FALHA: Itens foram alterados ({itens_antes} --> {itens_depois})"
        print(f"✅ Itens NÃO foram alterados (quantidade: {itens_depois})")
        
        # 3. Estoque NÃO foi alterado
        produto_depois = db_session.query(Produto).filter_by(id=cenario['produto_id']).first()
        estoque_depois = float(produto_depois.estoque_atual)
        assert estoque_depois == estoque_antes, \
            f"❌ FALHA: Estoque foi alterado ({estoque_antes} --> {estoque_depois})"
        print(f"✓ Estoque NÃO foi alterado (quantidade: {estoque_depois})")
        
        # 4. Conta a receber NÃO foi cancelada
        conta_receber_depois = db_session.query(ContaReceber).filter_by(
            id=cenario['conta_receber_id']
        ).first()
        assert conta_receber_depois is not None, "❌ FALHA: Conta a receber foi excluída"
        assert conta_receber_depois.status == conta_receber_antes.status, \
            f"❌ FALHA: Status da conta mudou ({conta_receber_antes.status} --> {conta_receber_depois.status})"
        print(f"✅ Conta a receber NÃO foi alterada (status: {conta_receber_depois.status})")
        
        # 5. Movimentação de caixa NÃO foi removida
        mov_caixa_depois = db_session.query(MovimentacaoCaixa).filter_by(
            id=cenario['mov_caixa_id']
        ).first()
        assert mov_caixa_depois is not None, "❌ FALHA: Movimentação de caixa foi removida"
        print(f"✅ Movimentação de caixa NÃO foi removida (ID: {mov_caixa_depois.id})")
        
        # 6. Saldo bancário NÃO foi alterado
        conta_bancaria_depois = db_session.query(ContaBancaria).filter_by(
            id=cenario['conta_bancaria_id']
        ).first()
        saldo_bancario_depois = float(conta_bancaria_depois.saldo_atual)
        assert saldo_bancario_depois == saldo_bancario_antes, \
            f"❌ FALHA: Saldo bancário foi alterado (R$ {saldo_bancario_antes} → R$ {saldo_bancario_depois})"
        print(f"✅ Saldo bancário NÃO foi alterado (R$ {saldo_bancario_depois})")
        
        # 7. Movimentação bancária NÃO foi removida
        mov_bancaria_depois = db_session.query(MovimentacaoFinanceira).filter_by(
            id=cenario['mov_bancaria_id']
        ).first()
        assert mov_bancaria_depois is not None, "❌ FALHA: Movimentação bancária foi removida"
        print(f"✅ Movimentação bancária NÃO foi removida (ID: {mov_bancaria_depois.id})")
        
        # 8. Lançamento manual NÃO foi cancelado
        lancamento_depois = db_session.query(LancamentoManual).filter_by(
            id=cenario['lancamento_id']
        ).first()
        assert lancamento_depois is not None, "❌ FALHA: Lançamento manual foi excluído"
        assert lancamento_depois.status == lancamento_antes.status, \
            f"❌ FALHA: Status do lançamento mudou ({lancamento_antes.status} → {lancamento_depois.status})"
        print(f"✅ Lançamento manual NÃO foi alterado (status: {lancamento_depois.status})")
        
        print("\n" + "="*80)
        print("🎉 ROLLBACK TOTAL VERIFICADO COM SUCESSO!")
        print("="*80)
        print("✅ TODAS as verificações passaram")
        print("✅ NENHUM dado foi alterado após a exceção")
        print("✅ transactional_session garantiu atomicidade total")
        print("✅ Status da venda continua 'finalizada' (não foi cancelada)")
        print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
