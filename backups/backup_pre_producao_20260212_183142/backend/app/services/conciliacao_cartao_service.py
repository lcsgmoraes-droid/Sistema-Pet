"""
Service de Conciliação de Cartão

Responsável por:
- Validar NSU contra contas a receber
- Marcar como conciliado
- Chamar service oficial de baixa
- Registrar auditoria
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.financeiro_models import ContaReceber, Recebimento
import logging

logger = logging.getLogger(__name__)


def conciliar_parcela_cartao(
    *,
    db: Session,
    tenant_id: str,
    nsu: str,
    valor: float,
    data_recebimento: date,
    adquirente: str,
    usuario_id: int,
    forma_pagamento_id: int = None,
):
    """
    Concilia uma parcela de cartão com base no NSU
    
    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant (UUID)
        nsu: NSU da transação (Número Sequencial Único)
        valor: Valor da transação
        data_recebimento: Data em que o valor foi recebido
        adquirente: Nome da adquirente (Stone, Cielo, etc)
        usuario_id: ID do usuário que está executando a conciliação
        forma_pagamento_id: ID da forma de pagamento (opcional)
    
    Returns:
        ContaReceber: Conta conciliada
    
    Raises:
        HTTPException: Se conta não encontrada, já conciliada ou valor não confere
    """
    
    # Buscar conta pelo NSU e tenant
    conta = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.nsu == nsu,
        )
        .first()
    )

    if not conta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conta a receber não encontrada para o NSU {nsu}",
        )

    if conta.conciliado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conta já conciliada anteriormente em {conta.data_conciliacao}",
        )

    # Validar valor
    valor_conta = float(conta.valor_final or conta.valor_original)
    if abs(valor_conta - float(valor)) > 0.01:  # Tolerância de 1 centavo
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Valor informado (R$ {valor:.2f}) não confere com a parcela (R$ {valor_conta:.2f})",
        )

    # Marca conciliação
    conta.conciliado = True
    conta.nsu = nsu
    conta.adquirente = adquirente
    conta.data_conciliacao = date.today()
    
    db.flush()

    # Se já é recebível hoje ou no passado, executa baixa oficial
    if data_recebimento <= date.today() and conta.status != 'recebido':
        # Criar registro de recebimento oficial
        novo_recebimento = Recebimento(
            conta_receber_id=conta.id,
            forma_pagamento_id=forma_pagamento_id,
            valor_recebido=Decimal(str(valor)),
            data_recebimento=data_recebimento,
            observacoes=f"Conciliação automática - NSU: {nsu} - Adquirente: {adquirente}",
            user_id=usuario_id,
            tenant_id=tenant_id
        )
        db.add(novo_recebimento)
        
        # Atualizar conta
        conta.valor_recebido = (conta.valor_recebido or Decimal(0)) + Decimal(str(valor))
        conta.status = 'recebido'
        conta.data_recebimento = data_recebimento
        
        db.flush()

    logger.info(
        f"✅ Conciliação de cartão realizada - NSU: {nsu}, Adquirente: {adquirente}, "
        f"Valor: R$ {valor:.2f}, Tenant: {tenant_id}, Usuário: {usuario_id}"
    )

    return conta


def buscar_contas_nao_conciliadas(
    *,
    db: Session,
    tenant_id: str,
    data_inicio: date = None,
    data_fim: date = None,
    adquirente: str = None,
):
    """
    Busca contas a receber que ainda não foram conciliadas
    
    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        data_inicio: Data inicial do filtro (opcional)
        data_fim: Data final do filtro (opcional)
        adquirente: Nome da adquirente para filtrar (opcional)
    
    Returns:
        List[ContaReceber]: Lista de contas não conciliadas
    """
    query = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == tenant_id,
        ContaReceber.conciliado == False,
        ContaReceber.nsu.isnot(None),  # Apenas contas com NSU
    )
    
    if data_inicio:
        query = query.filter(ContaReceber.data_vencimento >= data_inicio)
    
    if data_fim:
        query = query.filter(ContaReceber.data_vencimento <= data_fim)
    
    if adquirente:
        query = query.filter(ContaReceber.adquirente == adquirente)
    
    return query.order_by(ContaReceber.data_vencimento).all()
