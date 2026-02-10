"""
ROTAS DE CONTAS A RECEBER - Módulo Financeiro
Gestão completa de receitas e recebimentos de clientes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel
from decimal import Decimal

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .idempotency import idempotent  # ← IDEMPOTÊNCIA
from .models import User, Cliente
from .financeiro_models import (
    ContaReceber, Recebimento, CategoriaFinanceira, FormaPagamento, LancamentoManual
)
from .domain.validators.dre_validator import validar_categoria_financeira_dre
from .domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from .dre_plano_contas_models import DRESubcategoria

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contas-receber", tags=["Contas a Receber"])

# ============================================================================
# SCHEMAS
# ============================================================================

class ContaReceberCreate(BaseModel):
    descricao: str
    cliente_id: Optional[int] = None
    categoria_id: Optional[int] = None  # UX/Agrupamento
    
    # ============================
    # DRE - CAMPOS OBRIGATORIOS
    # ============================
    dre_subcategoria_id: Optional[int] = None  # OPCIONAL - será classificado automaticamente se não fornecido
    canal: str = 'loja_fisica'  # OBRIGATORIO - loja_fisica, mercado_livre, shopee, amazon
    
    valor_original: float
    data_emissao: date
    data_vencimento: date
    documento: Optional[str] = None
    observacoes: Optional[str] = None
    venda_id: Optional[int] = None
    
    # Parcelamento
    eh_parcelado: bool = False
    total_parcelas: int = 1
    
    # Recorrência
    eh_recorrente: bool = False
    tipo_recorrencia: Optional[str] = None  # 'semanal', 'quinzenal', 'mensal', 'personalizado'
    intervalo_dias: Optional[int] = None
    data_inicio_recorrencia: Optional[date] = None
    data_fim_recorrencia: Optional[date] = None
    numero_repeticoes: Optional[int] = None


class RecebimentoCreate(BaseModel):
    valor_recebido: float
    data_recebimento: date
    forma_pagamento_id: Optional[int] = None
    valor_juros: float = 0
    valor_multa: float = 0
    valor_desconto: float = 0
    observacoes: Optional[str] = None


class ContaReceberResponse(BaseModel):
    id: int
    descricao: str
    cliente_nome: Optional[str] = None
    categoria_nome: Optional[str] = None
    valor_original: float
    valor_recebido: float
    valor_final: float
    data_emissao: date
    data_vencimento: date
    data_recebimento: Optional[date] = None
    status: str
    dias_vencimento: Optional[int] = None
    eh_parcelado: bool
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    documento: Optional[str] = None
    venda_id: Optional[int] = None
    numero_venda: Optional[str] = None  # ✅ CAMPO ADICIONADO
    
    model_config = {"from_attributes": True}


# ============================================================================
# FUNÇÃO HELPER: CALCULAR PRÓXIMA DATA DE RECORRÊNCIA
# ============================================================================

def calcular_proxima_recorrencia(data_base: date, tipo_recorrencia: str, intervalo_dias: Optional[int] = None) -> date:
    """
    Calcula a próxima data de recorrência baseado no tipo
    """
    if tipo_recorrencia == 'semanal':
        return data_base + timedelta(days=7)
    elif tipo_recorrencia == 'quinzenal':
        return data_base + timedelta(days=15)
    elif tipo_recorrencia == 'mensal':
        # Adicionar 1 mês
        mes = data_base.month + 1
        ano = data_base.year
        if mes > 12:
            mes = 1
            ano += 1
        try:
            return data_base.replace(year=ano, month=mes)
        except ValueError:
            # Caso dia não exista no próximo mês (ex: 31 de fev), usar último dia do mês
            import calendar
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return date(ano, mes, ultimo_dia)
    elif tipo_recorrencia == 'personalizado' and intervalo_dias:
        return data_base + timedelta(days=intervalo_dias)
    else:
        raise ValueError(f"Tipo de recorrência inválido: {tipo_recorrencia}")


# ============================================================================
# CRIAR CONTA A RECEBER
# ============================================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita criação duplicada de contas a receber
async def criar_conta_receber(
    conta: ContaReceberCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria uma ou mais contas a receber (com parcelamento se necessário)
    + ATUALIZA DRE EM TEMPO REAL
    """
    current_user, tenant_id = user_and_tenant
    contas_criadas = []
    
    try:
        # ============================
        # VALIDAÇÃO DRE - CRÍTICA
        # ============================
        subcategoria = db.query(DRESubcategoria).filter(
            DRESubcategoria.id == conta.dre_subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True)
        ).first()
        
        if not subcategoria:
            raise HTTPException(
                status_code=400,
                detail=f"Subcategoria DRE {conta.dre_subcategoria_id} inválida ou não pertence a este tenant"
            )
        
        # ============================
        # CRIAÇÃO DE CONTAS
        # ============================
        if conta.eh_parcelado and conta.total_parcelas > 1:
            # Criar conta principal (controle)
            conta_principal = ContaReceber(
                descricao=f"{conta.descricao} (Parcelado)",
                cliente_id=conta.cliente_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status='parcelado',
                eh_parcelado=True,
                total_parcelas=conta.total_parcelas,
                venda_id=conta.venda_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                user_id=current_user.id
            )
            db.add(conta_principal)
            db.flush()
            
            # Criar parcelas
            valor_parcela = conta.valor_original / conta.total_parcelas
            
            for i in range(1, conta.total_parcelas + 1):
                # Vencimento: soma i meses
                vencimento_parcela = conta.data_vencimento
                if i > 1:
                    mes = vencimento_parcela.month + (i - 1)
                    ano = vencimento_parcela.year
                    while mes > 12:
                        mes -= 12
                        ano += 1
                    vencimento_parcela = vencimento_parcela.replace(year=ano, month=mes)
                
                parcela = ContaReceber(
                    descricao=f"{conta.descricao} - Parcela {i}/{conta.total_parcelas}",
                    cliente_id=conta.cliente_id,
                    categoria_id=conta.categoria_id,
                    dre_subcategoria_id=conta.dre_subcategoria_id,
                    canal=conta.canal,
                    valor_original=valor_parcela,
                    valor_final=valor_parcela,
                    data_emissao=conta.data_emissao,
                    data_vencimento=vencimento_parcela,
                    status='pendente',
                    eh_parcelado=True,
                    numero_parcela=i,
                    total_parcelas=conta.total_parcelas,
                    conta_principal_id=conta_principal.id,
                    venda_id=conta.venda_id,
                    documento=conta.documento,
                    observacoes=f"Parcela {i} de {conta.total_parcelas}",
                    user_id=current_user.id
                )
                db.add(parcela)
                contas_criadas.append(parcela)
        
        else:
            # Conta simples
            nova_conta = ContaReceber(
                descricao=conta.descricao,
                cliente_id=conta.cliente_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status='pendente',
                venda_id=conta.venda_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                # Recorrência
                eh_recorrente=conta.eh_recorrente,
                tipo_recorrencia=conta.tipo_recorrencia,
                intervalo_dias=conta.intervalo_dias,
                data_inicio_recorrencia=conta.data_inicio_recorrencia or conta.data_vencimento,
                data_fim_recorrencia=conta.data_fim_recorrencia,
                numero_repeticoes=conta.numero_repeticoes,
                user_id=current_user.id
            )
            
            # Se é recorrente, calcular próxima recorrência
            if nova_conta.eh_recorrente and nova_conta.tipo_recorrencia:
                try:
                    nova_conta.proxima_recorrencia = calcular_proxima_recorrencia(
                        nova_conta.data_vencimento, 
                        nova_conta.tipo_recorrencia, 
                        nova_conta.intervalo_dias
                    )
                except Exception as e:
                    logger.warning(f"⚠️  Erro ao calcular próxima recorrência: {e}")
            
            db.add(nova_conta)
            contas_criadas.append(nova_conta)
        
        db.commit()
        
        # ============================
        # ATUALIZAÇÃO DRE EM TEMPO REAL
        # ============================
        for conta_criada in contas_criadas:
            try:
                atualizar_dre_por_lancamento(
                    db=db,
                    tenant_id=tenant_id,
                    dre_subcategoria_id=conta_criada.dre_subcategoria_id,
                    canal=conta_criada.canal,
                    valor=conta_criada.valor_original,
                    data_lancamento=conta_criada.data_vencimento,
                    tipo_movimentacao='RECEITA'  # ← Contas a RECEBER = RECEITA
                )
                logger.info(f"✅ DRE atualizado: ContaReceber #{conta_criada.id} → Subcategoria {conta_criada.dre_subcategoria_id} → Canal {conta_criada.canal}")
            except Exception as e:
                # Não bloqueia criação se DRE falhar (logging apenas)
                logger.warning(f"⚠️ Erro ao atualizar DRE para ContaReceber #{conta_criada.id}: {e}")
        
        # INTEGRAÇÃO REVERSA: Criar lançamentos manuais no fluxo de caixa
        for conta_criada in contas_criadas:
            try:
                lancamento = LancamentoManual(
                    tipo='entrada',
                    valor=conta_criada.valor_original,
                    descricao=conta_criada.descricao,
                    data_lancamento=conta_criada.data_emissao,
                    data_prevista=conta_criada.data_vencimento,
                    data_efetivacao=None,  # Ainda não recebido
                    categoria_id=conta_criada.categoria_id,
                    conta_bancaria_id=None,
                    status='previsto',
                    observacoes=f"Gerado automaticamente da conta a receber #{conta_criada.id}",
                    gerado_automaticamente=True,
                    confianca_ia=None
                )
                db.add(lancamento)
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível criar lançamento para conta #{conta_criada.id}: {e}")
        
        db.commit()
        
        logger.info(f"✅ {len(contas_criadas)} conta(s) a receber criada(s)")
        
        return {
            "message": "Conta(s) criada(s) com sucesso",
            "total_contas": len(contas_criadas),
            "ids": [c.id for c in contas_criadas]
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar conta: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LISTAR CONTAS A RECEBER
# ============================================================================

@router.get("/", response_model=List[ContaReceberResponse])
def listar_contas_receber(
    status: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    categoria_id: Optional[int] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    apenas_vencidas: bool = Query(False),
    apenas_vencer: bool = Query(False),
    numero_venda: Optional[str] = Query(None),  # Filtro por número da venda
    limit: int = Query(500, le=1000),  # Aumentado para 500 registros por padrão
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista contas a receber com filtros
    """
    current_user, tenant_id = user_and_tenant
    
    query = db.query(ContaReceber).options(
        joinedload(ContaReceber.categoria)
    ).filter(ContaReceber.user_id == current_user.id)
    
    # Filtros
    if status:
        query = query.filter(ContaReceber.status == status)
    if cliente_id:
        query = query.filter(ContaReceber.cliente_id == cliente_id)
    if categoria_id:
        query = query.filter(ContaReceber.categoria_id == categoria_id)
    if data_inicio:
        query = query.filter(ContaReceber.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_vencimento <= data_fim)
    
    # Filtro por número de venda
    if numero_venda:
        from app.vendas_models import Venda
        vendas_ids = db.query(Venda.id).filter(
            Venda.user_id == current_user.id,
            Venda.numero_venda.like(f'%{numero_venda}%')
        ).subquery()
        query = query.filter(ContaReceber.venda_id.in_(vendas_ids))
    
    if apenas_vencidas:
        query = query.filter(
            and_(
                ContaReceber.status == 'pendente',
                ContaReceber.data_vencimento < date.today()
            )
        )
    if apenas_vencer:
        query = query.filter(
            and_(
                ContaReceber.status == 'pendente',
                ContaReceber.data_vencimento >= date.today()
            )
        )
    
    # Ordenar por ID DESC (mais recentes primeiro) e depois por data de vencimento
    query = query.order_by(desc(ContaReceber.id))
    contas = query.limit(limit).offset(offset).all()
    
    # Montar response
    resultado = []
    for conta in contas:
        # Calcular dias para vencimento
        dias_venc = None
        if conta.status == 'pendente':
            dias_venc = (conta.data_vencimento - date.today()).days
        
        # Buscar nome do cliente
        cliente_nome = None
        if conta.cliente_id:
            cliente = db.query(Cliente).filter(Cliente.id == conta.cliente_id).first()
            if cliente:
                cliente_nome = cliente.nome
        
        # Buscar número da venda se existir venda_id
        numero_venda = None
        if conta.venda_id:
            from app.vendas_models import Venda
            venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
            if venda:
                numero_venda = venda.numero_venda
        
        resultado.append({
            "id": conta.id,
            "descricao": conta.descricao,
            "cliente_nome": cliente_nome,
            "categoria_nome": conta.categoria.nome if conta.categoria else None,
            "valor_original": float(conta.valor_original),
            "valor_recebido": float(conta.valor_recebido),
            "valor_final": float(conta.valor_final),
            "data_emissao": conta.data_emissao,
            "data_vencimento": conta.data_vencimento,
            "data_recebimento": conta.data_recebimento,
            "status": conta.status,
            "dias_vencimento": dias_venc,
            "eh_parcelado": conta.eh_parcelado,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas,
            "documento": conta.documento,
            "venda_id": conta.venda_id,
            "numero_venda": numero_venda,
            "observacoes": conta.observacoes
        })
    
    return resultado


# ============================================================================
# BUSCAR CONTA ESPECÍFICA
# ============================================================================

@router.get("/{conta_id}")
def buscar_conta_receber(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Busca uma conta a receber específica com todos os detalhes
    """
    from .vendas_models import Venda
    from .financeiro_models import ContaBancaria
    
    conta = db.query(ContaReceber).options(
        joinedload(ContaReceber.categoria),
        joinedload(ContaReceber.recebimentos)
    ).filter(ContaReceber.id == conta_id).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Buscar cliente
    cliente = None
    if conta.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == conta.cliente_id).first()
    
    # Buscar venda (se houver)
    venda = None
    if conta.venda_id:
        venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
    
    # Buscar recebimentos com conta bancária
    recebimentos_detalhados = []
    for r in conta.recebimentos:
        conta_bancaria = None
        if r.conta_bancaria_id:
            conta_bancaria = db.query(ContaBancaria).filter(ContaBancaria.id == r.conta_bancaria_id).first()
        
        recebimentos_detalhados.append({
            "id": r.id,
            "valor": float(r.valor_recebido),
            "data": r.data_recebimento,
            "forma_pagamento_id": r.forma_pagamento_id,
            "conta_bancaria_id": r.conta_bancaria_id,
            "conta_bancaria_nome": conta_bancaria.nome if conta_bancaria else None,
            "observacoes": r.observacoes
        })
    
    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "cliente": {
            "id": cliente.id if cliente else None,
            "nome": cliente.nome if cliente else None,
            "cpf": cliente.cpf if cliente else None
        } if cliente else None,
        "venda": {
            "id": venda.id if venda else None,
            "numero_venda": venda.numero_venda if venda else None
        } if venda else None,
        "categoria": {
            "id": conta.categoria.id if conta.categoria else None,
            "nome": conta.categoria.nome if conta.categoria else None,
            "cor": conta.categoria.cor if conta.categoria else None
        } if conta.categoria else None,
        "valores": {
            "original": float(conta.valor_original),
            "recebido": float(conta.valor_recebido),
            "desconto": float(conta.valor_desconto),
            "juros": float(conta.valor_juros),
            "multa": float(conta.valor_multa),
            "final": float(conta.valor_final),
            "saldo": float(conta.valor_final - conta.valor_recebido)
        },
        "datas": {
            "emissao": conta.data_emissao,
            "vencimento": conta.data_vencimento,
            "recebimento": conta.data_recebimento
        },
        "status": conta.status,
        "parcelamento": {
            "eh_parcelado": conta.eh_parcelado,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas
        } if conta.eh_parcelado else None,
        "documento": conta.documento,
        "observacoes": conta.observacoes,
        "recebimentos": recebimentos_detalhados
    }


# ============================================================================
# REGISTRAR RECEBIMENTO
# ============================================================================

@router.post("/{conta_id}/receber")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita recebimento duplicado
async def registrar_recebimento(
    conta_id: int,
    recebimento: RecebimentoCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Registra um recebimento (baixa) de conta a receber
    """
    conta = db.query(ContaReceber).filter(ContaReceber.id == conta_id).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    if conta.status == 'recebido':
        raise HTTPException(status_code=400, detail="Conta já está recebida")
    
    # Atualizar valores
    conta.valor_recebido += Decimal(str(recebimento.valor_recebido))
    conta.valor_juros += Decimal(str(recebimento.valor_juros))
    conta.valor_multa += Decimal(str(recebimento.valor_multa))
    conta.valor_desconto += Decimal(str(recebimento.valor_desconto))
    
    # Recalcular valor final
    conta.valor_final = (
        conta.valor_original +
        conta.valor_juros +
        conta.valor_multa -
        conta.valor_desconto
    )
    
    # Verificar se recebeu tudo
    if conta.valor_recebido >= conta.valor_final:
        conta.status = 'recebido'
        conta.data_recebimento = recebimento.data_recebimento
    else:
        conta.status = 'parcial'
    
    # Registrar recebimento
    current_user, tenant_id = user_and_tenant
    novo_recebimento = Recebimento(
        conta_receber_id=conta.id,
        forma_pagamento_id=recebimento.forma_pagamento_id,
        valor_recebido=recebimento.valor_recebido,
        data_recebimento=recebimento.data_recebimento,
        observacoes=recebimento.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id  # ✅ Garantir isolamento multi-tenant
    )
    db.add(novo_recebimento)
    
    db.commit()
    
    logger.info(f"✅ Recebimento registrado: R$ {recebimento.valor_recebido} - Conta {conta_id}")
    
    # ============================================================================
    # 💰 GERAR COMISSÃO SE CONTA VINCULADA A VENDA
    # ============================================================================
    comissao_gerada = False
    comissao_info = None
    
    if conta.venda_id:
        try:
            from app.comissoes_service import gerar_comissoes_venda
            from app.vendas_models import Venda
            
            # Buscar venda para verificar se tem funcionário
            venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
            
            if venda and venda.funcionario_id:
                logger.info(f"💰 Gerando comissão para venda #{venda.numero_venda} (baixa de conta a receber)")
                
                # Gerar comissão proporcional ao valor recebido NESTA baixa
                resultado = gerar_comissoes_venda(
                    venda_id=venda.id,
                    funcionario_id=venda.funcionario_id,
                    valor_pago=Decimal(str(recebimento.valor_recebido)),  # Apenas o valor DESTA baixa
                    parcela_numero=1,  # Usar parcela 1 para pagamentos via contas a receber
                    db=db
                )
                
                if resultado.get('success'):
                    comissao_gerada = True
                    comissao_info = {
                        'venda_id': venda.id,
                        'numero_venda': venda.numero_venda,
                        'valor_comissao': resultado.get('total_comissao', 0)
                    }
                    logger.info(f"✅ Comissão gerada com sucesso: R$ {resultado.get('total_comissao', 0):.2f}")
                else:
                    logger.warning(f"⚠️ Falha ao gerar comissão: {resultado.get('error', 'Erro desconhecido')}")
            else:
                logger.info(f"ℹ️ Venda #{conta.venda_id} sem funcionário configurado, comissão não gerada")
                
        except Exception as e:
            logger.error(f"❌ Erro ao gerar comissão para venda #{conta.venda_id}: {e}")
            # Não falha o recebimento por erro na comissão
            pass
    
    response = {
        "message": "Recebimento registrado com sucesso",
        "conta_id": conta.id,
        "status": conta.status,
        "valor_recebido_total": float(conta.valor_recebido),
        "valor_final": float(conta.valor_final),
        "saldo_restante": float(conta.valor_final - conta.valor_recebido)
    }
    
    if comissao_gerada and comissao_info:
        response['comissao'] = comissao_info
    
    return response


# ============================================================================
# DASHBOARD / RESUMO
# ============================================================================

@router.get("/dashboard/resumo")
def dashboard_contas_receber(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Resumo financeiro de contas a receber
    """
    hoje = date.today()
    
    # Total pendente
    total_pendente = db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)).filter(
        ContaReceber.status.in_(['pendente', 'parcial', 'vencido'])
    ).scalar() or 0
    
    # Vencidas
    total_vencido = db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)).filter(
        and_(
            ContaReceber.status == 'pendente',
            ContaReceber.data_vencimento < hoje
        )
    ).scalar() or 0
    
    count_vencidas = db.query(func.count(ContaReceber.id)).filter(
        and_(
            ContaReceber.status == 'pendente',
            ContaReceber.data_vencimento < hoje
        )
    ).scalar()
    
    # Vence hoje
    total_vence_hoje = db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)).filter(
        and_(
            ContaReceber.status == 'pendente',
            ContaReceber.data_vencimento == hoje
        )
    ).scalar() or 0
    
    # Próximos 7 dias
    data_7dias = hoje + timedelta(days=7)
    total_7dias = db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)).filter(
        and_(
            ContaReceber.status == 'pendente',
            ContaReceber.data_vencimento.between(hoje, data_7dias)
        )
    ).scalar() or 0
    
    # Próximos 30 dias
    data_30dias = hoje + timedelta(days=30)
    total_30dias = db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido)).filter(
        and_(
            ContaReceber.status == 'pendente',
            ContaReceber.data_vencimento.between(hoje, data_30dias)
        )
    ).scalar() or 0
    
    # Recebido no mês
    primeiro_dia_mes = hoje.replace(day=1)
    total_recebido_mes = db.query(func.sum(ContaReceber.valor_recebido)).filter(
        and_(
            ContaReceber.data_recebimento >= primeiro_dia_mes,
            ContaReceber.data_recebimento <= hoje
        )
    ).scalar() or 0
    
    return {
        "total_pendente": float(total_pendente),
        "vencidas": {
            "total": float(total_vencido),
            "quantidade": count_vencidas
        },
        "vence_hoje": float(total_vence_hoje),
        "proximos_7_dias": float(total_7dias),
        "proximos_30_dias": float(total_30dias),
        "recebido_mes_atual": float(total_recebido_mes)
    }

# ============================================================================
# PROCESSAR RECORRÊNCIAS
# ============================================================================

@router.post("/processar-recorrencias")
async def processar_recorrencias_contas_receber(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Processa contas recorrentes e cria novas contas quando necessário
    Esta rota deve ser executada periodicamente (diariamente recomendado)
    """
    current_user, tenant_id = user_and_tenant
    hoje = date.today()
    contas_criadas = []
    
    # Buscar contas recorrentes que precisam gerar nova conta
    contas_recorrentes = db.query(ContaReceber).filter(
        and_(
            ContaReceber.eh_recorrente == True,
            ContaReceber.proxima_recorrencia <= hoje,
            or_(
                ContaReceber.data_fim_recorrencia.is_(None),
                ContaReceber.data_fim_recorrencia >= hoje
            )
        )
    ).all()
    
    for conta_origem in contas_recorrentes:
        try:
            # Verificar se já atingiu o número máximo de repetições
            if conta_origem.numero_repeticoes:
                # Contar quantas contas já foram geradas
                count_geradas = db.query(func.count(ContaReceber.id)).filter(
                    ContaReceber.conta_recorrencia_origem_id == conta_origem.id
                ).scalar()
                
                if count_geradas >= conta_origem.numero_repeticoes:
                    logger.info(f"📅 Conta #{conta_origem.id} atingiu o número máximo de repetições ({conta_origem.numero_repeticoes})")
                    continue
            
            # Criar nova conta baseada na recorrência
            nova_data_vencimento = conta_origem.proxima_recorrencia
            
            nova_conta = ContaReceber(
                descricao=f"{conta_origem.descricao} (Recorrência {nova_data_vencimento.strftime('%m/%Y')})",
                cliente_id=conta_origem.cliente_id,
                categoria_id=conta_origem.categoria_id,
                dre_subcategoria_id=conta_origem.dre_subcategoria_id,  # Herdar da conta origem
                canal=conta_origem.canal,  # Herdar da conta origem
                valor_original=conta_origem.valor_original,
                valor_final=conta_origem.valor_original,
                data_emissao=hoje,
                data_vencimento=nova_data_vencimento,
                status='pendente',
                documento=conta_origem.documento,
                observacoes=f"Gerada automaticamente da recorrência #{conta_origem.id}",
                conta_recorrencia_origem_id=conta_origem.id,
                user_id=conta_origem.user_id
            )
            
            db.add(nova_conta)
            contas_criadas.append(nova_conta)
            
            # Atualizar próxima recorrência da conta origem
            conta_origem.proxima_recorrencia = calcular_proxima_recorrencia(
                nova_data_vencimento,
                conta_origem.tipo_recorrencia,
                conta_origem.intervalo_dias
            )
            
            # Criar lançamento no fluxo de caixa
            try:
                lancamento = LancamentoManual(
                    tipo='entrada',
                    valor=nova_conta.valor_original,
                    descricao=nova_conta.descricao,
                    data_lancamento=hoje,
                    data_prevista=nova_data_vencimento,
                    data_efetivacao=None,
                    categoria_id=nova_conta.categoria_id,
                    status='previsto',
                    observacoes=f"Gerado automaticamente da recorrência #{conta_origem.id}",
                    gerado_automaticamente=True
                )
                db.add(lancamento)
            except Exception as e:
                logger.warning(f"⚠️  Erro ao criar lançamento para conta recorrente: {e}")
            
            logger.info(f"✅ Nova conta recorrente criada: #{nova_conta.id} - Vencimento: {nova_data_vencimento}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar recorrência da conta #{conta_origem.id}: {e}")
            continue
    
    db.commit()
    
    return {
        "message": f"{len(contas_criadas)} conta(s) recorrente(s) processada(s) com sucesso",
        "contas_criadas": len(contas_criadas),
        "ids": [c.id for c in contas_criadas]
    }