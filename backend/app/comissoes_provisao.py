"""
PASSO 2: Provisão Automática de Comissões como Despesa

Quando uma venda é efetivada (baixa_parcial ou finalizada),
as comissões calculadas devem gerar automaticamente:
1. Conta a Pagar (fornecedor = comissionado)
2. Lançamento na DRE (subcategoria: Comissões)

CONCEITO-CHAVE: Comissão é DESPESA por COMPETÊNCIA, não depende de pagamento.
"""

import logging
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.tenant_safe_sql import execute_tenant_safe
from app.db.transaction import transactional_session

logger = logging.getLogger(__name__)


def provisionar_comissoes_venda(
    venda_id: int,
    tenant_id: str,
    db: Session
) -> Dict:
    """
    Cria provisões (Contas a Pagar + DRE) para todas as comissões de uma venda.
    
    EVENTO DISPARADOR:
    - Venda mudou de 'aberta' → 'baixa_parcial' ou 'finalizada'
    - Comissões já foram calculadas e inseridas em comissoes_itens
    - Provisão ainda não foi feita (comissao_provisionada = False)
    
    AÇÃO:
    - Para cada comissão: criar Conta a Pagar
    - Lançar na DRE como DESPESA DIRETA
    - Marcar comissão como provisionada
    
    IDEMPOTÊNCIA:
    - Só provisiona comissões com comissao_provisionada = False
    - Se chamado múltiplas vezes, não duplica
    
    Args:
        venda_id: ID da venda
        tenant_id: ID do tenant (multi-tenant obrigatório)
        db: Sessão do SQLAlchemy
    
    Returns:
        Dict com resultado:
        {
            'success': bool,
            'comissoes_provisionadas': int,
            'valor_total': float,
            'contas_criadas': List[int],
            'message': str
        }
    """
    with transactional_session(db):
        # ============================================================
        # ETAPA 1: BUSCAR VENDA E VALIDAR
        # ============================================================
        
        result_venda = execute_tenant_safe(db, """
            SELECT 
                v.id, v.numero_venda, v.data_venda, v.canal,
                v.cliente_id, v.status
            FROM vendas v
            WHERE v.id = :venda_id AND {tenant_filter}
        """, {'venda_id': venda_id})
        
        venda = result_venda.fetchone()
        if not venda:
            logger.warning(f"Venda {venda_id} não encontrada para tenant {tenant_id}")
            return {
                'success': False,
                'comissoes_provisionadas': 0,
                'valor_total': 0.0,
                'contas_criadas': [],
                'message': 'Venda não encontrada'
            }
        
        # Validar status: só provisiona se efetivada
        if venda.status not in ['baixa_parcial', 'finalizada']:
            logger.info(f"Venda {venda_id} com status '{venda.status}' - Provisão não aplicável")
            return {
                'success': False,
                'comissoes_provisionadas': 0,
                'valor_total': 0.0,
                'contas_criadas': [],
                'message': f'Venda com status {venda.status} não gera provisão'
            }
        
        canal_venda = venda.canal or 'loja_fisica'
        data_competencia = venda.data_venda or date.today()
        
        # ============================================================
        # ETAPA 2: BUSCAR COMISSÕES NÃO PROVISIONADAS
        # ============================================================
        
        result_comissoes = db.execute(text("""
            SELECT 
                id, funcionario_id, valor_comissao_gerada, produto_id
            FROM comissoes_itens
            WHERE venda_id = :venda_id
              AND status = 'pendente'
              AND valor_comissao_gerada > 0
              AND tenant_id = CAST(:tenant_id AS UUID)
        """), {'venda_id': venda_id, 'tenant_id': str(tenant_id)})
        
        comissoes_pendentes = result_comissoes.fetchall()
        
        if not comissoes_pendentes:
            logger.info(f"Venda {venda_id}: Nenhuma comissão pendente de provisão")
            return {
                'success': True,
                'comissoes_provisionadas': 0,
                'valor_total': 0.0,
                'contas_criadas': [],
                'message': 'Nenhuma comissão pendente de provisão'
            }
        
        logger.info(
            f"🎯 Provisionando {len(comissoes_pendentes)} comissões da venda {venda.numero_venda}"
        )
        
        # ============================================================
        # ETAPA 3: BUSCAR SUBCATEGORIA DRE "Comissões de Vendas"
        # ============================================================
        
        result_subcat = db.execute(text("""
            SELECT id
            FROM dre_subcategorias
            WHERE nome LIKE '%Vendedores%'
              AND ativo = true
              AND tenant_id = CAST(:tenant_id AS UUID)
            LIMIT 1
        """), {'tenant_id': str(tenant_id)})
        
        subcat_comissoes = result_subcat.fetchone()
        
        if not subcat_comissoes:
            logger.error(
                f"⚠️ Subcategoria DRE 'Comissões de Vendas' não encontrada para tenant {tenant_id}"
            )
            return {
                'success': False,
                'comissoes_provisionadas': 0,
                'valor_total': 0.0,
                'contas_criadas': [],
                'message': 'Subcategoria DRE Comissões não configurada'
            }
        
        dre_subcategoria_id = subcat_comissoes[0]
        
        # ============================================================
        # ETAPA 4: PROCESSAR CADA COMISSÃO
        # ============================================================
        
        contas_criadas = []
        total_provisionado = Decimal('0')
        comissoes_provisionadas_count = 0
        
        for comissao in comissoes_pendentes:
            comissao_id = comissao[0]
            funcionario_id = comissao[1]
            valor_comissao = Decimal(str(comissao[2]))
            
            # Buscar dados do funcionário
            result_func = db.execute(text("""
                SELECT nome, data_fechamento_comissao
                FROM users
                WHERE id = :funcionario_id
                AND tenant_id = CAST(:tenant_id AS UUID)
            """), {'funcionario_id': funcionario_id, 'tenant_id': str(tenant_id)})
            
            funcionario = result_func.fetchone()
            funcionario_nome = funcionario[0] if funcionario else f"Funcionário #{funcionario_id}"
            
            # Calcular data de vencimento (baseado em data_fechamento_comissao ou padrão 30 dias)
            if funcionario and funcionario[1]:
                # Calcular próxima data de fechamento após a data da venda
                dia_fechamento = funcionario[1]
                if data_competencia.day <= dia_fechamento:
                    # Mesmo mês
                    data_vencimento = data_competencia.replace(day=dia_fechamento)
                else:
                    # Próximo mês
                    if data_competencia.month == 12:
                        data_vencimento = data_competencia.replace(
                            year=data_competencia.year + 1,
                            month=1,
                            day=dia_fechamento
                        )
                    else:
                        data_vencimento = data_competencia.replace(
                            month=data_competencia.month + 1,
                            day=dia_fechamento
                        )
            else:
                # Padrão: 30 dias após a venda
                data_vencimento = data_competencia + timedelta(days=30)
            
            # --------------------------------------------------------
            # 4.1: Criar Conta a Pagar
            # --------------------------------------------------------
            
            descricao_conta = (
                f"Comissão - Venda {venda.numero_venda} - {funcionario_nome}"
            )
            
            # Inserir conta a pagar
            # 🔒 CAMPO CRÍTICO: fornecedor_id = funcionario_id (comissionado)
            result_insert = db.execute(text("""
                INSERT INTO contas_pagar (
                    descricao,
                    fornecedor_id,
                    dre_subcategoria_id,
                    canal,
                    valor_original,
                    valor_pago,
                    valor_final,
                    data_emissao,
                    data_vencimento,
                    status,
                    documento,
                    observacoes,
                    user_id,
                    tenant_id,
                    created_at,
                    updated_at
                ) VALUES (
                    :descricao,
                    :fornecedor_id,
                    :dre_subcategoria_id,
                    :canal,
                    :valor,
                    0,
                    :valor,
                    :data_emissao,
                    :data_vencimento,
                    'pendente',
                    :documento,
                    :observacoes,
                    :user_id,
                    CAST(:tenant_id AS UUID),
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                ) RETURNING id
            """), {
                'descricao': descricao_conta,
                'fornecedor_id': funcionario_id,  # ✅ Comissionado é o fornecedor
                'dre_subcategoria_id': dre_subcategoria_id,
                'canal': canal_venda,
                'valor': float(valor_comissao),
                'data_emissao': data_competencia,
                'data_vencimento': data_vencimento,
                'documento': f"COMISSAO-VENDA-{venda_id}-{comissao_id}",
                'observacoes': f"Provisão automática - Comissão venda {venda.numero_venda}",
                'user_id': funcionario_id,  # Pode ser ajustado conforme lógica do sistema
                'tenant_id': str(tenant_id)
            })
            
            # Obter ID da conta criada
            conta_pagar_id = result_insert.fetchone()[0]
            
            contas_criadas.append(conta_pagar_id)
            
            logger.info(
                f"  ✅ Conta a Pagar #{conta_pagar_id} criada: R$ {float(valor_comissao):.2f} "
                f"vencimento {data_vencimento}"
            )
            
            # --------------------------------------------------------
            # 4.2: Lançar na DRE
            # --------------------------------------------------------
            
            # Usar função de sincronização DRE
            from app.domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
            
            atualizar_dre_por_lancamento(
                db=db,
                tenant_id=tenant_id,
                dre_subcategoria_id=dre_subcategoria_id,
                canal=canal_venda,
                valor=valor_comissao,
                data_lancamento=data_competencia,
                tipo_movimentacao='DESPESA'
            )
            
            logger.info(f"  ✅ DRE atualizada: Despesa de R$ {float(valor_comissao):.2f}")
            
            # --------------------------------------------------------
            # 4.3: Marcar comissão como provisionada
            # --------------------------------------------------------
            
            db.execute(text("""
                UPDATE comissoes_itens
                SET comissao_provisionada = TRUE,
                    conta_pagar_id = :conta_pagar_id,
                    data_provisao = :data_provisao
                WHERE id = :comissao_id
                AND tenant_id = CAST(:tenant_id AS UUID)
            """), {
                'conta_pagar_id': conta_pagar_id,
                'data_provisao': date.today(),
                'comissao_id': comissao_id,
                'tenant_id': str(tenant_id)
            })
            
            total_provisionado += valor_comissao
            comissoes_provisionadas_count += 1
        
        # ============================================================
        # ETAPA 5: RETORNO (Commit automático pelo transactional_session)
        # ============================================================
        
        logger.info(
            f"✅ Provisão concluída para venda {venda.numero_venda}: "
            f"{comissoes_provisionadas_count} comissões, "
            f"Total: R$ {float(total_provisionado):.2f}"
        )
        
        return {
            'success': True,
            'comissoes_provisionadas': comissoes_provisionadas_count,
            'valor_total': float(total_provisionado),
            'contas_criadas': contas_criadas,
            'message': f'{comissoes_provisionadas_count} comissões provisionadas'
        }
