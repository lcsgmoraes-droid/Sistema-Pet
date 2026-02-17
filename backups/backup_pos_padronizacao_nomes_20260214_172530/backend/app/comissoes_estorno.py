"""
Serviço de Estorno de Comissões
Sprint 3 - Hardening Financeiro - Passo 1
"""
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from sqlalchemy import text, bindparam
from app.db import SessionLocal
from app.db.transaction import transactional_session
from .utils.logger import logger as struct_logger
from .utils.tenant_safe_sql import execute_tenant_safe

# Logger tradicional
logger = logging.getLogger(__name__)


def estornar_comissoes_venda(
    venda_id: int,
    motivo: str,
    usuario_id: int,
    db=None  # Opcional: para transações externas
) -> Dict[str, Any]:
    """
    Marca comissões da venda como estornadas.
    
    Operação IDEMPOTENTE: Se já estiver estornada, retorna sucesso.
    
    Regras:
    - Apenas comissões com status 'pendente' ou 'gerada' podem ser estornadas
    - Comissões 'pago' ou 'estornado' não são alteradas
    - Mantém histórico completo (não deleta)
    
    Args:
        venda_id: ID da venda cancelada
        motivo: Motivo do estorno (ex: "Venda cancelada")
        usuario_id: ID do usuário que está estornando
        db: Sessão de banco (opcional, para transações externas)
        
    Returns:
        Dict com:
            - success: bool
            - comissoes_estornadas: int (quantidade)
            - valor_estornado: float
            - message: str
            - duplicated: bool (se já estava estornado)
    """
    
    # Log estruturado
    struct_logger.info(
        event="COMMISSION_REFUND_START",
        message=f"Iniciando estorno de comissões",
        venda_id=venda_id,
        motivo=motivo
    )
    
    # Usar conexão própria se não foi passada
    conn_externa = db is not None
    if not conn_externa:
        db = SessionLocal()
    
    try:
        with transactional_session(db) if not conn_externa else _no_op_context():
            # 1. Buscar comissões da venda
            result = execute_tenant_safe(db, """
                SELECT 
                    id,
                    status,
                    valor_comissao,
                    funcionario_id
                FROM comissoes_itens
                WHERE venda_id = :venda_id
                AND {tenant_filter}
            """, {"venda_id": venda_id})
            
            comissoes = result.fetchall()
            
            if not comissoes:
                struct_logger.warning(
                    event="COMMISSION_REFUND_NOT_FOUND",
                    message="Nenhuma comissão encontrada para esta venda",
                    venda_id=venda_id
                )
                return {
                    'success': True,
                    'comissoes_estornadas': 0,
                    'valor_estornado': 0.0,
                    'message': 'Nenhuma comissão encontrada para esta venda',
                    'duplicated': False
                }
            
            # 2. Verificar se já estão estornadas (idempotência)
            ja_estornadas = [c for c in comissoes if c[1] == 'estornado']
            pendentes = [c for c in comissoes if c[1] in ('pendente', 'gerada')]
            pagas = [c for c in comissoes if c[1] == 'pago']
            
            if ja_estornadas and not pendentes:
                struct_logger.warning(
                    event="COMMISSION_ALREADY_REFUNDED",
                    message="Comissões já estavam estornadas (operação idempotente)",
                    venda_id=venda_id,
                    quantidade=len(ja_estornadas)
                )
                return {
                    'success': True,
                    'comissoes_estornadas': 0,
                    'valor_estornado': 0.0,
                    'message': 'Comissões já estavam estornadas',
                    'duplicated': True
                }
            
            # 3. Avisar se há comissões pagas (não estorna pagas)
            if pagas:
                logger.warning(
                    f"⚠️  Venda #{venda_id} possui {len(pagas)} comissões já PAGAS. "
                    f"Estas NÃO serão estornadas automaticamente."
                )
            
            # 4. Estornar apenas as pendentes
            if not pendentes:
                return {
                    'success': True,
                    'comissoes_estornadas': 0,
                    'valor_estornado': 0.0,
                    'message': f'Nenhuma comissão pendente para estornar. {len(pagas)} já pagas.',
                    'duplicated': False
                }
            
            # 5. Executar estorno
            ids_para_estornar = [c[0] for c in pendentes]
            valor_total_estornado = sum(float(c[2]) for c in pendentes)
            data_estorno = datetime.now().isoformat()
            
            # Atualizar status para 'estornado'
            stmt = text("""
                UPDATE comissoes_itens
                SET
                    status = 'estornado',
                    data_estorno = :data_estorno,
                    motivo_estorno = :motivo,
                    estornado_por = :usuario_id
                WHERE id IN :ids
                  AND {tenant_filter}
            """).bindparams(bindparam("ids", expanding=True))
            
            execute_tenant_safe(
                db,
                stmt,
                {
                    "ids": tuple(ids_para_estornar),
                    "data_estorno": data_estorno,
                    "motivo": motivo,
                    "usuario_id": usuario_id,
                }
            )
            
            # Commit automático se conexão própria (via context manager)
            # Se conexão externa, o commit é responsabilidade do chamador
        
        # Log estruturado de sucesso
        struct_logger.info(
            event="COMMISSION_REFUNDED",
            message="Comissões estornadas com sucesso",
            venda_id=venda_id,
            quantidade=len(pendentes),
            valor_estornado=valor_total_estornado
        )
        
        logger.info(
            f"✅ Estornadas {len(pendentes)} comissões da venda #{venda_id} "
            f"(R$ {valor_total_estornado:.2f})"
        )
        
        return {
            'success': True,
            'comissoes_estornadas': len(pendentes),
            'valor_estornado': valor_total_estornado,
            'message': f'{len(pendentes)} comissão(ões) estornada(s)',
            'duplicated': False
        }
        
    finally:
        # Fechar conexão apenas se foi criada aqui
        if not conn_externa:
            db.close()


from contextlib import contextmanager

@contextmanager
def _no_op_context():
    """Context manager que não faz nada (para compatibilidade quando db é externa)."""
    yield
