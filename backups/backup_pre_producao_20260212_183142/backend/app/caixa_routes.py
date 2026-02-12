"""
Rotas para o Sistema de Controle de Caixa
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel

from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.idempotency import idempotent  # ← IDEMPOTÊNCIA
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.models import User
from app.pdf_caixa import gerar_pdf_fechamento_caixa
from app.utils.security_helpers import safe_get_caixa

router = APIRouter(prefix='/caixas', tags=['caixas'])


# Schemas
class AbrirCaixaSchema(BaseModel):
    valor_abertura: float
    conta_origem_id: Optional[int] = None
    conta_origem_nome: Optional[str] = None
    observacoes_abertura: Optional[str] = None


class FecharCaixaSchema(BaseModel):
    valor_informado: float
    observacoes_fechamento: Optional[str] = None


class MovimentacaoSchema(BaseModel):
    tipo: str  # suprimento, sangria, despesa, transferencia, devolucao
    valor: float
    forma_pagamento: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    conta_origem_id: Optional[int] = None
    conta_origem_nome: Optional[str] = None
    conta_destino_id: Optional[int] = None
    conta_destino_nome: Optional[str] = None
    fornecedor_id: Optional[int] = None
    fornecedor_nome: Optional[str] = None
    documento: Optional[str] = None


# Rotas
@router.post("/abrir")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita abertura duplicada de caixa
async def abrir_caixa(
    dados: AbrirCaixaSchema,
    request: Request,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Abrir um novo caixa"""
    current_user, tenant_id = current_user_and_tenant
    
    # Verificar se já existe caixa aberto para o usuário
    caixa_aberto = db.query(Caixa).filter(
        and_(
            Caixa.usuario_id == current_user.id,
            Caixa.tenant_id == tenant_id,
            Caixa.status == 'aberto'
        )
    ).first()
    
    if caixa_aberto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já possui um caixa aberto. Feche-o antes de abrir outro."
        )
    
    # Gerar número do caixa (próximo número disponível por tenant)
    ultimo_caixa = db.query(func.max(Caixa.numero_caixa)).filter(
        Caixa.tenant_id == tenant_id
    ).scalar()
    numero_caixa = (ultimo_caixa or 0) + 1
    
    # Criar novo caixa
    novo_caixa = Caixa(
        numero_caixa=numero_caixa,
        usuario_id=current_user.id,
        usuario_nome=current_user.nome,
        valor_abertura=dados.valor_abertura,
        conta_origem_id=dados.conta_origem_id,
        conta_origem_nome=dados.conta_origem_nome,
        observacoes_abertura=dados.observacoes_abertura,
        status='aberto',
        tenant_id=tenant_id
    )
    
    db.add(novo_caixa)
    db.commit()
    db.refresh(novo_caixa)
    
    return novo_caixa.to_dict()


@router.get("/aberto")
def obter_caixa_aberto(
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obter caixa aberto do usuário atual"""
    current_user, tenant_id = current_user_and_tenant
    
    caixa = db.query(Caixa).filter(
        and_(
            Caixa.usuario_id == current_user.id,
            Caixa.tenant_id == tenant_id,
            Caixa.status == 'aberto'
        )
    ).first()
    
    if not caixa:
        return None
    
    return caixa.to_dict()


@router.get("")
def listar_caixas(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Listar caixas do usuário"""
    current_user, tenant_id = current_user_and_tenant
    
    query = db.query(Caixa).filter(
        Caixa.usuario_id == current_user.id,
        Caixa.tenant_id == tenant_id
    )
    
    if data_inicio:
        query = query.filter(Caixa.data_abertura >= datetime.fromisoformat(data_inicio))
    
    if data_fim:
        query = query.filter(Caixa.data_abertura <= datetime.fromisoformat(data_fim))
    
    if status_filter:
        query = query.filter(Caixa.status == status_filter)
    
    caixas = query.order_by(Caixa.data_abertura.desc()).all()
    
    return [caixa.to_dict() for caixa in caixas]


@router.get("/{caixa_id}")
def obter_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obter detalhes de um caixa específico"""
    current_user, tenant_id = current_user_and_tenant
    
    # 🔒 SEGURANÇA: Validar que o caixa pertence ao usuário e tenant
    caixa = db.query(Caixa).filter(
        Caixa.id == caixa_id,
        Caixa.usuario_id == current_user.id,
        Caixa.tenant_id == tenant_id
    ).first()
    
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    
    return caixa.to_dict()


@router.post("/{caixa_id}/movimentacao")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita movimentações duplicadas
async def criar_movimentacao(
    caixa_id: int,
    dados: MovimentacaoSchema,
    request: Request,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Adicionar movimentação ao caixa"""
    current_user, tenant_id = current_user_and_tenant
    
    # 🔒 SEGURANÇA: Validar que o caixa pertence ao usuário e tenant
    caixa = db.query(Caixa).filter(
        Caixa.id == caixa_id,
        Caixa.usuario_id == current_user.id,
        Caixa.tenant_id == tenant_id
    ).first()
    
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    
    if caixa.status != 'aberto':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caixa não está aberto"
        )
    
    # Criar movimentação
    movimentacao = MovimentacaoCaixa(
        caixa_id=caixa_id,
        tipo=dados.tipo,
        valor=dados.valor,
        forma_pagamento=dados.forma_pagamento,
        descricao=dados.descricao,
        categoria=dados.categoria,
        conta_origem_id=dados.conta_origem_id,
        conta_origem_nome=dados.conta_origem_nome,
        conta_destino_id=dados.conta_destino_id,
        conta_destino_nome=dados.conta_destino_nome,
        fornecedor_id=dados.fornecedor_id,
        fornecedor_nome=dados.fornecedor_nome,
        documento=dados.documento,
        usuario_id=current_user.id,
        usuario_nome=current_user.nome,
        tenant_id=tenant_id
    )
    
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    
    return movimentacao.to_dict()


@router.post("/{caixa_id}/fechar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita fechamento duplicado de caixa
async def fechar_caixa(
    caixa_id: int,
    dados: FecharCaixaSchema,
    request: Request,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Fechar caixa"""
    current_user, tenant_id = current_user_and_tenant
    
    # 🔒 SEGURANÇA: Validar que o caixa pertence ao usuário e tenant
    caixa = db.query(Caixa).filter(
        Caixa.id == caixa_id,
        Caixa.usuario_id == current_user.id,
        Caixa.tenant_id == tenant_id
    ).first()
    
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    
    if caixa.status != 'aberto':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caixa já está fechado"
        )
    
    # Calcular valor esperado
    movimentacoes = db.query(MovimentacaoCaixa).filter(
        MovimentacaoCaixa.caixa_id == caixa_id,
        MovimentacaoCaixa.tenant_id == tenant_id
    ).all()
    
    valor_esperado = caixa.valor_abertura
    
    for mov in movimentacoes:
        if mov.tipo in ['venda', 'suprimento', 'devolucao']:
            valor_esperado += mov.valor
        elif mov.tipo in ['sangria', 'despesa', 'transferencia']:
            valor_esperado -= mov.valor
    
    # 🔒 VALIDAÇÃO CRÍTICA: Não permitir fechar caixa com saldo em dinheiro
    # Exigir sangria antes do fechamento
    if valor_esperado > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"❌ Não é possível fechar o caixa com R$ {valor_esperado:.2f} em dinheiro. "
                   f"Faça uma SANGRIA antes de fechar o caixa para retirar o dinheiro."
        )
    
    # Calcular diferença
    diferenca = dados.valor_informado - valor_esperado
    
    # Atualizar caixa
    caixa.data_fechamento = datetime.now()
    caixa.valor_esperado = valor_esperado
    caixa.valor_informado = dados.valor_informado
    caixa.diferenca = diferenca
    caixa.observacoes_fechamento = dados.observacoes_fechamento
    caixa.status = 'fechado'
    
    db.commit()
    db.refresh(caixa)
    
    return caixa.to_dict()


@router.post("/{caixa_id}/reabrir")
def reabrir_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Reabrir um caixa fechado"""
    current_user, tenant_id = current_user_and_tenant
    
    # Verificar se já existe caixa aberto
    caixa_aberto = db.query(Caixa).filter(
        and_(
            Caixa.usuario_id == current_user.id,
            Caixa.tenant_id == tenant_id,
            Caixa.status == 'aberto'
        )
    ).first()
    
    if caixa_aberto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já possui um caixa aberto. Feche-o antes de reabrir outro."
        )
    
    # 🔒 SEGURANÇA: Validar que o caixa pertence ao usuário e tenant
    caixa = db.query(Caixa).filter(
        Caixa.id == caixa_id,
        Caixa.usuario_id == current_user.id,
        Caixa.tenant_id == tenant_id
    ).first()
    
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    
    if caixa.status != 'fechado':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas caixas fechados podem ser reabertos"
        )
    
    # Reabrir caixa
    caixa.status = 'aberto'
    caixa.data_fechamento = None
    caixa.valor_esperado = None
    caixa.valor_informado = None
    caixa.diferenca = None
    caixa.observacoes_fechamento = None
    
    db.commit()
    db.refresh(caixa)
    
    return caixa.to_dict()


@router.get("/{caixa_id}/resumo")
def obter_resumo_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Obter resumo do caixa com totais"""
    current_user, tenant_id = current_user_and_tenant
    
    # 🔒 SEGURANÇA: Validar que o caixa pertence ao usuário e tenant
    caixa = db.query(Caixa).filter(
        Caixa.id == caixa_id,
        Caixa.usuario_id == current_user.id,
        Caixa.tenant_id == tenant_id
    ).first()
    
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    
    # Calcular totais
    movimentacoes = db.query(MovimentacaoCaixa).filter(
        MovimentacaoCaixa.caixa_id == caixa_id,
        MovimentacaoCaixa.tenant_id == tenant_id
    ).all()
    
    total_vendas = sum(
        m.valor for m in movimentacoes 
        if m.tipo == 'venda' and m.forma_pagamento == 'Dinheiro'
    )
    total_suprimentos = sum(m.valor for m in movimentacoes if m.tipo == 'suprimento')
    total_sangrias = sum(m.valor for m in movimentacoes if m.tipo == 'sangria')
    total_despesas = sum(m.valor for m in movimentacoes if m.tipo == 'despesa')
    total_transferencias = sum(m.valor for m in movimentacoes if m.tipo == 'transferencia')
    total_devolucoes = sum(m.valor for m in movimentacoes if m.tipo == 'devolucao')
    
    # 💰 Calcular totais por forma de pagamento de TODAS as vendas DESTE CAIXA
    # Buscar vendas vinculadas a este caixa específico (não apenas do dia)
    from app.vendas_models import Venda, VendaPagamento
    from sqlalchemy import func
    
    vendas_do_caixa = db.query(
        VendaPagamento.forma_pagamento,
        func.count(VendaPagamento.id).label('quantidade'),
        func.sum(VendaPagamento.valor).label('total')
    ).join(Venda).filter(
        Venda.caixa_id == caixa_id,
        Venda.tenant_id == tenant_id,
        Venda.status.in_(['finalizada', 'baixa_parcial'])
    ).group_by(VendaPagamento.forma_pagamento).all()
    
    vendas_por_forma = {}
    for forma_id, qtd, total in vendas_do_caixa:
        # Buscar nome da forma de pagamento
        from app.financeiro_models import FormaPagamento
        # forma_id é na verdade o NOME da forma (String), não o ID
        forma = db.query(FormaPagamento).filter(
            FormaPagamento.nome == forma_id,
            FormaPagamento.tenant_id == tenant_id
        ).first()
        nome_forma = forma.nome if forma else str(forma_id)
        
        vendas_por_forma[nome_forma] = {
            'quantidade': qtd,
            'total': float(total) if total else 0.0
        }
    
    saldo_atual = (
        caixa.valor_abertura +
        total_vendas +
        total_suprimentos +
        total_devolucoes -
        total_sangrias -
        total_despesas -
        total_transferencias
    )
    
    return {
        'caixa': caixa.to_dict(),
        'totais': {
            'vendas': total_vendas,
            'suprimentos': total_suprimentos,
            'sangrias': total_sangrias,
            'despesas': total_despesas,
            'transferencias': total_transferencias,
            'devolucoes': total_devolucoes,
            'saldo_atual': saldo_atual
        },
        'vendas_por_forma_pagamento': vendas_por_forma
    }


@router.get("/{caixa_id}/movimentacoes")
def listar_movimentacoes_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as movimentações de um caixa (extrato completo)"""
    current_user, tenant_id = current_user_and_tenant
    
    # Verificar se o caixa existe e pertence ao usuário e tenant
    caixa = db.query(Caixa).filter_by(
        id=caixa_id,
        usuario_id=current_user.id,
        tenant_id=tenant_id
    ).first()
    
    if not caixa:
        raise HTTPException(status_code=404, detail='Caixa não encontrado')
    
    # Buscar todas as movimentações ordenadas por data (mais recentes primeiro)
    movimentacoes = db.query(MovimentacaoCaixa).filter(
        MovimentacaoCaixa.caixa_id == caixa_id,
        MovimentacaoCaixa.tenant_id == tenant_id
    ).order_by(MovimentacaoCaixa.data_movimento.desc()).all()
    
    # Converter para dicionário com informações extras
    resultado = []
    for mov in movimentacoes:
        mov_dict = mov.to_dict()
        
        # Adicionar emoji e cor baseado no tipo
        if mov.tipo == 'venda':
            mov_dict['emoji'] = '💰'
            mov_dict['cor'] = 'green'
            mov_dict['natureza'] = 'entrada'
        elif mov.tipo == 'suprimento':
            mov_dict['emoji'] = '➕'
            mov_dict['cor'] = 'blue'
            mov_dict['natureza'] = 'entrada'
        elif mov.tipo == 'sangria':
            mov_dict['emoji'] = '➖'
            mov_dict['cor'] = 'orange'
            mov_dict['natureza'] = 'saida'
        elif mov.tipo == 'despesa':
            mov_dict['emoji'] = '💸'
            mov_dict['cor'] = 'red'
            mov_dict['natureza'] = 'saida'
        elif mov.tipo == 'devolucao':
            mov_dict['emoji'] = '🔄'
            mov_dict['cor'] = 'purple'
            mov_dict['natureza'] = 'saida'
        elif mov.tipo == 'transferencia':
            mov_dict['emoji'] = '🔁'
            mov_dict['cor'] = 'gray'
            mov_dict['natureza'] = 'saida'
        else:
            mov_dict['emoji'] = '📝'
            mov_dict['cor'] = 'gray'
            mov_dict['natureza'] = 'neutro'
        
        resultado.append(mov_dict)
    
    return {
        'caixa': {
            'id': caixa.id,
            'numero_caixa': caixa.numero_caixa,
            'usuario_nome': caixa.usuario_nome,
            'status': caixa.status,
            'valor_abertura': float(caixa.valor_abertura)
        },
        'movimentacoes': resultado,
        'total_movimentacoes': len(resultado)
    }


@router.get("/{caixa_id}/pdf")
def gerar_pdf_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Gera PDF do fechamento de caixa
    """
    current_user, tenant_id = current_user_and_tenant
    
    # Buscar caixa
    caixa = db.query(Caixa).filter_by(
        id=caixa_id,
        usuario_id=current_user.id,
        tenant_id=tenant_id
    ).first()
    
    if not caixa:
        raise HTTPException(status_code=404, detail='Caixa não encontrado')
    
    # Buscar movimentações
    movimentacoes = db.query(MovimentacaoCaixa).filter_by(
        caixa_id=caixa_id,
        tenant_id=tenant_id
    ).order_by(MovimentacaoCaixa.created_at).all()
    
    # Preparar dados do caixa
    caixa_data = {
        'numero_caixa': caixa.numero_caixa,
        'data_abertura': caixa.data_abertura,
        'data_fechamento': caixa.data_fechamento,
        'responsavel': caixa.usuario_nome,
        'status': caixa.status,
        'saldo_inicial': float(caixa.valor_abertura),
        'total_entradas': float(caixa.total_entradas or 0),
        'total_saidas': float(caixa.total_saidas or 0),
        'saldo_final': float(caixa.saldo_final or 0),
        'saldo_fechamento': float(caixa.valor_fechamento) if caixa.valor_fechamento else None,
        'diferenca': float(caixa.diferenca) if caixa.diferenca else None
    }
    
    # Preparar dados das movimentações
    mov_list = []
    for mov in movimentacoes:
        mov_list.append({
            'created_at': mov.created_at,
            'tipo': mov.tipo,
            'descricao': mov.descricao,
            'forma_pagamento_nome': mov.forma_pagamento,
            'valor': float(mov.valor)
        })
    
    # Gerar PDF
    pdf_buffer = gerar_pdf_fechamento_caixa(caixa_data, mov_list)
    
    # Retornar PDF
    filename = f"Caixa_{caixa.numero_caixa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

