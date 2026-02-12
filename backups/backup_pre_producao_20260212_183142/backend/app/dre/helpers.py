"""
Helper para criar lançamentos DRE com rastreabilidade completa
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.ia.aba7_dre_detalhada_models import DREDetalheCanal


def criar_lancamento_dre(
    *,
    db: Session,
    tenant_id: int,
    mes: int,
    ano: int,
    canal: str,
    categoria_financeira_id: Optional[int] = None,
    valor: Decimal,
    origem: str,
    origem_evento: str,
    referencia_id: Optional[str] = None,
    usuario_id: Optional[int] = None,
    observacao: Optional[str] = None,
    **kwargs  # Permite passar outros campos do DRE (receita_bruta, impostos, etc)
) -> DREDetalheCanal:
    """
    Cria um lançamento no DRE com rastreabilidade completa.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        mes: Mês da competência
        ano: Ano da competência
        canal: Canal de venda (loja_fisica, mercado_livre, etc)
        categoria_financeira_id: ID da categoria financeira (opcional)
        valor: Valor do lançamento
        origem: Tipo do lançamento (PROVISAO, AJUSTE, REAL)
        origem_evento: Evento que gerou (NF, DAS, FGTS, FERIAS, 13, BOLETO)
        referencia_id: ID de referência (NF, Conta a Pagar, etc)
        usuario_id: ID do usuário responsável
        observacao: Texto explicativo
        **kwargs: Outros campos do DRE
        
    Returns:
        DREDetalheCanal criado
        
    Exemplos:
        # Provisão de Simples via NF
        criar_lancamento_dre(
            db=db,
            tenant_id=1,
            mes=1,
            ano=2026,
            canal="loja_fisica",
            valor=Decimal("600.00"),
            origem="PROVISAO",
            origem_evento="NF",
            referencia_id="NF-12345",
            usuario_id=1,
            observacao="Provisão Simples Nacional da NF 12345"
        )
        
        # Ajuste de DAS pago
        criar_lancamento_dre(
            db=db,
            tenant_id=1,
            mes=1,
            ano=2026,
            canal="loja_fisica",
            valor=Decimal("580.00"),
            origem="AJUSTE",
            origem_evento="DAS",
            referencia_id="CP-789",
            usuario_id=1,
            observacao="DAS pago menor que provisão"
        )
    """
    
    # Validar origem
    ORIGENS_VALIDAS = ["PROVISAO", "AJUSTE", "REAL"]
    if origem not in ORIGENS_VALIDAS:
        raise ValueError(f"Origem inválida: {origem}. Use: {', '.join(ORIGENS_VALIDAS)}")
    
    # Validar origem_evento
    EVENTOS_VALIDOS = ["NF", "DAS", "FGTS", "INSS", "FOLHA", "FERIAS", "13", "BOLETO", "AJUSTE_MANUAL"]
    if origem_evento not in EVENTOS_VALIDOS:
        raise ValueError(f"Evento inválido: {origem_evento}. Use: {', '.join(EVENTOS_VALIDOS)}")
    
    # Criar registro base
    lancamento_data = {
        "tenant_id": tenant_id,
        "mes": mes,
        "ano": ano,
        "canal": canal,
        "origem": origem,
        "origem_evento": origem_evento,
        "referencia_id": referencia_id,
        "usuario_id": usuario_id,
        "observacao": observacao,
        **kwargs  # Adiciona campos extras (receita_bruta, impostos, etc)
    }
    
    # Criar lançamento
    lancamento = DREDetalheCanal(**lancamento_data)
    
    db.add(lancamento)
    
    return lancamento


def atualizar_lancamento_dre(
    *,
    db: Session,
    lancamento: DREDetalheCanal,
    usuario_id: int,
    observacao: str,
    **kwargs
) -> DREDetalheCanal:
    """
    Atualiza um lançamento DRE mantendo rastreabilidade.
    
    Args:
        db: Sessão do banco
        lancamento: Lançamento a ser atualizado
        usuario_id: ID do usuário que está atualizando
        observacao: Motivo da atualização
        **kwargs: Campos a serem atualizados
        
    Returns:
        Lançamento atualizado
    """
    
    # Adicionar histórico na observação
    historico = f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Atualizado por user_id={usuario_id}: {observacao}"
    
    if lancamento.observacao:
        lancamento.observacao += historico
    else:
        lancamento.observacao = observacao + historico
    
    # Atualizar campos
    for key, value in kwargs.items():
        if hasattr(lancamento, key):
            setattr(lancamento, key, value)
    
    lancamento.atualizado_em = datetime.utcnow()
    
    return lancamento


def buscar_lancamentos_por_referencia(
    db: Session,
    tenant_id: int,
    referencia_id: str
) -> list[DREDetalheCanal]:
    """
    Busca todos os lançamentos DRE relacionados a uma referência.
    
    Útil para rastrear impacto de uma NF ou pagamento no DRE.
    """
    return (
        db.query(DREDetalheCanal)
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.referencia_id == referencia_id
        )
        .order_by(DREDetalheCanal.criado_em.desc())
        .all()
    )


def buscar_lancamentos_por_evento(
    db: Session,
    tenant_id: int,
    origem_evento: str,
    mes: Optional[int] = None,
    ano: Optional[int] = None
) -> list[DREDetalheCanal]:
    """
    Busca lançamentos por tipo de evento.
    
    Útil para auditoria de provisões, ajustes, etc.
    """
    query = db.query(DREDetalheCanal).filter(
        DREDetalheCanal.tenant_id == tenant_id,
        DREDetalheCanal.origem_evento == origem_evento
    )
    
    if mes:
        query = query.filter(DREDetalheCanal.mes == mes)
    
    if ano:
        query = query.filter(DREDetalheCanal.ano == ano)
    
    return query.order_by(DREDetalheCanal.criado_em.desc()).all()
