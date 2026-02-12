"""
Constantes do Sistema - Padronização de valores
"""

# ========================================================================
# ORIGENS DE TRANSAÇÕES (origem_tipo)
# ========================================================================

class OrigemTransacao:
    """Tipos de origem para rastreabilidade de transações"""
    
    # Comissões
    COMISSAO_FECHAMENTO = 'comissao_fechamento'
    COMISSAO_ESTORNO = 'comissao_estorno'
    COMISSAO_AJUSTE = 'comissao_ajuste'
    
    # Vendas
    VENDA = 'venda'
    DEVOLUCAO = 'devolucao'
    
    # Contas
    CONTA_PAGAR = 'conta_pagar'
    CONTA_RECEBER = 'conta_receber'
    
    # Movimentações
    TRANSFERENCIA = 'transferencia'
    AJUSTE_MANUAL = 'ajuste_manual'
    
    # Lista completa para validação
    ALL = [
        COMISSAO_FECHAMENTO,
        COMISSAO_ESTORNO,
        COMISSAO_AJUSTE,
        VENDA,
        DEVOLUCAO,
        CONTA_PAGAR,
        CONTA_RECEBER,
        TRANSFERENCIA,
        AJUSTE_MANUAL
    ]


# ========================================================================
# STATUS DE COMISSÕES
# ========================================================================

class StatusComissao:
    """Status possíveis para comissões"""
    
    PENDENTE = 'pendente'
    PAGO = 'pago'
    PAGO_COM_COMPENSACAO = 'pago_com_compensacao'
    COMPENSADO_INTEGRALMENTE = 'compensado_integralmente'
    CANCELADO = 'cancelado'
    ESTORNADO = 'estornado'
    
    # Lista completa
    ALL = [
        PENDENTE,
        PAGO,
        PAGO_COM_COMPENSACAO,
        COMPENSADO_INTEGRALMENTE,
        CANCELADO,
        ESTORNADO
    ]
    
    # Status que impedem fechamento
    NAO_FECHAVEL = [PAGO, PAGO_COM_COMPENSACAO, COMPENSADO_INTEGRALMENTE, ESTORNADO]


# ========================================================================
# STATUS DE DÍVIDAS
# ========================================================================

class StatusDivida:
    """Status possíveis para dívidas de parceiros"""
    
    ABERTA = 'aberta'
    PARCIALMENTE_COMPENSADA = 'parcialmente_compensada'
    COMPENSADA = 'compensada'
    CANCELADA = 'cancelada'
    
    # Lista completa
    ALL = [ABERTA, PARCIALMENTE_COMPENSADA, COMPENSADA, CANCELADA]
    
    # Status elegíveis para compensação
    COMPENSAVEL = [ABERTA, PARCIALMENTE_COMPENSADA]


# ========================================================================
# STATUS DE CONTAS A PAGAR/RECEBER
# ========================================================================

class StatusConta:
    """Status possíveis para contas a pagar/receber"""
    
    PENDENTE = 'pendente'
    PAGO = 'pago'
    PARCIAL = 'parcial'
    ATRASADO = 'atrasado'
    CANCELADO = 'cancelado'
    
    # Lista completa
    ALL = [PENDENTE, PAGO, PARCIAL, ATRASADO, CANCELADO]


# ========================================================================
# TIPOS DE DÍVIDAS
# ========================================================================

class TipoDivida:
    """Tipos de dívidas de parceiros"""
    
    PRODUTO_DEFEITUOSO = 'produto_defeituoso'
    DEVOLUCAO = 'devolucao'
    ERRO_COMISSAO = 'erro_comissao'
    ESTORNO_VENDA = 'estorno_venda'
    AJUSTE_MANUAL = 'ajuste_manual'
    OUTRO = 'outro'
    
    # Lista completa
    ALL = [
        PRODUTO_DEFEITUOSO,
        DEVOLUCAO,
        ERRO_COMISSAO,
        ESTORNO_VENDA,
        AJUSTE_MANUAL,
        OUTRO
    ]


# ========================================================================
# MENSAGENS PADRÃO
# ========================================================================

class MensagensPadrao:
    """Mensagens padronizadas do sistema"""
    
    # Compensação
    COMPENSACAO_AUTOMATICA = "Compensação automática de dívidas do parceiro"
    COMPENSACAO_SEM_MOVIMENTACAO = "Pago integralmente por compensação automática (sem movimentação bancária)"
    COMPENSACAO_PARCIAL = "Pago parcialmente com compensação de R$ {valor_compensado:.2f}"
    
    # Fechamento
    FECHAMENTO_SUCESSO = "{total} comissões fechadas com sucesso"
    FECHAMENTO_COM_COMPENSACAO = "{total} comissões fechadas. Compensado: R$ {valor_compensado:.2f}. Pago: R$ {valor_liquido:.2f}"
    
    # Erros
    COMISSAO_JA_FECHADA = "Comissão já foi fechada anteriormente (status: {status})"
    COMISSAO_NAO_PENDENTE = "Somente comissões pendentes podem ser fechadas"
    
    @staticmethod
    def compensacao_observacao(valor_compensado: float, dividas_ids: list) -> str:
        """Gera observação de compensação"""
        if not dividas_ids:
            return f"Compensado R$ {valor_compensado:.2f}"
        return f"Compensado R$ {valor_compensado:.2f} nas dívidas: {', '.join(f'#{id}' for id in dividas_ids)}"
