"""
ROTAS DE CONTAS A PAGAR - Módulo Financeiro
Gestão completa de despesas e pagamentos a fornecedores
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, extract, select
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
    ContaPagar, Pagamento, CategoriaFinanceira, FormaPagamento, LancamentoManual,
    TipoDespesa,
    MovimentacaoFinanceira, ContaBancaria
)
from .produtos_models import NotaEntrada
from .domain.validators.dre_validator import validar_categoria_financeira_dre
from .domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from .dre_plano_contas_models import DRESubcategoria
from .financeiro.contas_pagar_origem import (
    CAIXA_PDV_OBSERVACAO_MARKER,
    _identificar_origem_conta_pagar,
)
from app.services.reconciliacao_simples_service import reconciliar_das_simples
from app.services.reconciliacao_provisao_service import reconciliar_provisao

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contas-pagar", tags=["Contas a Pagar"])

RECORRENCIA_JANELA_MESES_PADRAO = 12

# ============================================================================
# SCHEMAS
# ============================================================================

class ContaPagarCreate(BaseModel):
    descricao: str
    fornecedor_id: Optional[int] = None
    categoria_id: Optional[int] = None  # UX/Agrupamento
    
    # ============================
    # DRE - CAMPOS OBRIGATORIOS (com padrões)
    # ============================
    dre_subcategoria_id: Optional[int] = None  # Obrigatorio via categoria vinculada a DRE ou envio direto
    canal: str = 'loja_fisica'  # OBRIGATORIO - loja_fisica, mercado_livre, shopee, amazon
    tipo_despesa_id: Optional[int] = None  # FK para TipoDespesa (fixo/variável)
    
    valor_original: float
    data_emissao: date
    data_vencimento: date
    documento: Optional[str] = None
    observacoes: Optional[str] = None
    nota_entrada_id: Optional[int] = None
    
    # Parcelamento
    eh_parcelado: bool = False
    total_parcelas: int = 1
    
    # Recorrência
    eh_recorrente: bool = False
    tipo_recorrencia: Optional[str] = None  # 'semanal', 'quinzenal', 'mensal', 'personalizado'
    intervalo_dias: Optional[int] = None  # Para tipo 'personalizado'
    data_inicio_recorrencia: Optional[date] = None
    data_fim_recorrencia: Optional[date] = None  # OU
    numero_repeticoes: Optional[int] = None  # alternativa ao data_fim


class ContaPagarUpdate(BaseModel):
    descricao: Optional[str] = None
    categoria_id: Optional[int] = None
    dre_subcategoria_id: Optional[int] = None
    tipo_despesa_id: Optional[int] = None
    canal: Optional[str] = None
    valor_original: Optional[float] = None
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None


class ContaPagarClassificacaoUpdate(BaseModel):
    categoria_id: Optional[int] = None
    dre_subcategoria_id: Optional[int] = None
    tipo_despesa_id: Optional[int] = None
    canal: Optional[str] = None


class PagamentoCreate(BaseModel):
    valor_pago: float
    data_pagamento: date
    forma_pagamento_id: Optional[int] = None
    conta_bancaria_id: Optional[int] = None
    valor_juros: float = 0
    valor_multa: float = 0
    valor_desconto: float = 0
    observacoes: Optional[str] = None


class ContaPagarResponse(BaseModel):
    id: int
    descricao: str
    fornecedor_nome: Optional[str] = None
    categoria_id: Optional[int] = None
    categoria_nome: Optional[str] = None
    valor_original: float
    valor_pago: float
    valor_final: float
    data_emissao: date
    data_vencimento: date
    data_pagamento: Optional[date] = None
    status: str
    dias_vencimento: Optional[int] = None
    eh_parcelado: bool
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    documento: Optional[str] = None
    nfe_numero: Optional[str] = None
    observacoes: Optional[str] = None
    nota_entrada_id: Optional[int] = None
    canal: Optional[str] = None
    dre_subcategoria_id: Optional[int] = None
    dre_subcategoria_nome: Optional[str] = None
    tipo_despesa_id: Optional[int] = None
    tipo_despesa_nome: Optional[str] = None
    e_custo_fixo: Optional[bool] = None
    origem_lancamento: Optional[str] = None
    origem_lancamento_label: Optional[str] = None
    caixa_referencia: Optional[str] = None
    
    model_config = {"from_attributes": True}


def _obter_tipo_produto_revenda_id(db: Session, tenant_id) -> Optional[int]:
    nomes_prioritarios = [
        "Produto para Revenda",
        "Fornecedor de Produto para Revenda",
    ]
    for nome in nomes_prioritarios:
        tipo = db.query(TipoDespesa).filter(
            TipoDespesa.tenant_id == tenant_id,
            func.lower(TipoDespesa.nome) == nome.lower(),
            TipoDespesa.ativo.is_(True),
        ).first()
        if tipo:
            return tipo.id

    tipo = db.query(TipoDespesa).filter(
        TipoDespesa.tenant_id == tenant_id,
        TipoDespesa.nome.ilike("%produto%revenda%"),
        TipoDespesa.ativo.is_(True),
    ).order_by(TipoDespesa.nome.asc()).first()
    return tipo.id if tipo else None


def _resolver_dre_subcategoria_conta_pagar(
    db: Session,
    tenant_id,
    *,
    dre_subcategoria_id: Optional[int],
    categoria_id: Optional[int],
) -> int:
    if dre_subcategoria_id is not None:
        subcategoria = db.query(DRESubcategoria).filter(
            DRESubcategoria.id == dre_subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
        ).first()
        if not subcategoria:
            raise HTTPException(
                status_code=400,
                detail=f"Subcategoria DRE {dre_subcategoria_id} invalida ou nao pertence a este tenant",
            )
        return subcategoria.id

    if categoria_id is not None:
        categoria = db.query(CategoriaFinanceira).filter(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.tenant_id == tenant_id,
            CategoriaFinanceira.ativo.is_(True),
        ).first()
        if not categoria:
            raise HTTPException(
                status_code=400,
                detail="Categoria financeira invalida ou nao pertence a este tenant",
            )
        if categoria and categoria.dre_subcategoria_id:
            return _resolver_dre_subcategoria_conta_pagar(
                db,
                tenant_id,
                dre_subcategoria_id=categoria.dre_subcategoria_id,
                categoria_id=None,
            )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Categoria financeira '{categoria.nome}' nao possui vinculo com DRE. "
                "Vincule a categoria a uma subcategoria DRE antes de criar a conta a pagar."
            ),
        )

    raise HTTPException(
        status_code=400,
        detail=(
            "Informe uma categoria financeira vinculada a DRE ou uma subcategoria DRE valida "
            "para criar a conta a pagar."
        ),
    )


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


def adicionar_meses(data_base: date, meses_adicionar: int) -> date:
    mes = data_base.month + meses_adicionar
    ano = data_base.year
    while mes > 12:
        mes -= 12
        ano += 1

    try:
        return data_base.replace(year=ano, month=mes)
    except ValueError:
        import calendar
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        return date(ano, mes, ultimo_dia)


def calcular_limite_janela_recorrencia(
    hoje: date,
    meses: int = RECORRENCIA_JANELA_MESES_PADRAO,
) -> date:
    return adicionar_meses(hoje, meses)


def _gerar_contas_recorrentes_ate_janela(
    db: Session,
    tenant_id,
    conta_origem: ContaPagar,
    limite_recorrencia: date,
) -> List[ContaPagar]:
    contas_criadas: List[ContaPagar] = []

    while conta_origem.proxima_recorrencia and conta_origem.proxima_recorrencia <= limite_recorrencia:
        nova_data_vencimento = conta_origem.proxima_recorrencia

        if conta_origem.data_fim_recorrencia and nova_data_vencimento > conta_origem.data_fim_recorrencia:
            break

        if conta_origem.numero_repeticoes:
            count_geradas = db.query(func.count(ContaPagar.id)).filter(
                ContaPagar.conta_recorrencia_origem_id == conta_origem.id
            ).scalar()
            if count_geradas >= conta_origem.numero_repeticoes:
                logger.info(
                    f"Conta #{conta_origem.id} atingiu o numero maximo de repeticoes ({conta_origem.numero_repeticoes})"
                )
                break

        conta_existente = db.query(ContaPagar).filter(
            ContaPagar.conta_recorrencia_origem_id == conta_origem.id,
            ContaPagar.data_vencimento == nova_data_vencimento,
        ).first()
        if conta_existente:
            conta_origem.proxima_recorrencia = calcular_proxima_recorrencia(
                nova_data_vencimento,
                conta_origem.tipo_recorrencia,
                conta_origem.intervalo_dias,
            )
            continue

        nova_conta = ContaPagar(
            descricao=f"{conta_origem.descricao} (Recorrencia {nova_data_vencimento.strftime('%m/%Y')})",
            fornecedor_id=conta_origem.fornecedor_id,
            categoria_id=conta_origem.categoria_id,
            dre_subcategoria_id=conta_origem.dre_subcategoria_id,
            canal=conta_origem.canal,
            tipo_despesa_id=conta_origem.tipo_despesa_id,
            valor_original=conta_origem.valor_original,
            valor_final=conta_origem.valor_original,
            data_emissao=nova_data_vencimento,
            data_vencimento=nova_data_vencimento,
            status='pendente',
            nota_entrada_id=conta_origem.nota_entrada_id,
            documento=conta_origem.documento,
            observacoes=f"Gerada automaticamente da recorrencia #{conta_origem.id}",
            conta_recorrencia_origem_id=conta_origem.id,
            user_id=conta_origem.user_id,
            tenant_id=tenant_id,
        )

        db.add(nova_conta)
        contas_criadas.append(nova_conta)

        lancamento = LancamentoManual(
            tipo='saida',
            valor=nova_conta.valor_original,
            descricao=nova_conta.descricao,
            data_lancamento=nova_conta.data_vencimento,
            data_competencia=nova_conta.data_vencimento,
            categoria_id=nova_conta.categoria_id,
            status='previsto',
            documento=nova_conta.documento,
            observacoes=f"Gerado automaticamente da recorrencia #{conta_origem.id}",
            gerado_automaticamente=True,
            user_id=conta_origem.user_id,
            tenant_id=tenant_id,
        )
        db.add(lancamento)

        conta_origem.proxima_recorrencia = calcular_proxima_recorrencia(
            nova_data_vencimento,
            conta_origem.tipo_recorrencia,
            conta_origem.intervalo_dias,
        )
        db.flush()

    return contas_criadas


# ============================================================================
# CRIAR CONTA A PAGAR
# ============================================================================

@router.post("/", status_code=status.HTTP_201_CREATED)
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita criação duplicada de contas a pagar
async def criar_conta_pagar(
    conta: ContaPagarCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria uma ou mais contas a pagar (com parcelamento se necessário)
    + ATUALIZA DRE EM TEMPO REAL
    """
    current_user, tenant_id = user_and_tenant
    contas_criadas = []
    
    try:
        # ============================
        # CLASSIFICACAO DRE
        # ============================
        conta.dre_subcategoria_id = _resolver_dre_subcategoria_conta_pagar(
            db,
            tenant_id,
            dre_subcategoria_id=conta.dre_subcategoria_id,
            categoria_id=conta.categoria_id,
        )

        tipo_despesa_id = conta.tipo_despesa_id
        if conta.nota_entrada_id and not tipo_despesa_id:
            tipo_despesa_id = _obter_tipo_produto_revenda_id(db, tenant_id)
        
        # ============================
        # CRIAÇÃO DE CONTAS
        # ============================
        if conta.eh_parcelado and conta.total_parcelas > 1:
            # Criar conta principal (controle)
            conta_principal = ContaPagar(
                descricao=f"{conta.descricao} (Parcelado)",
                fornecedor_id=conta.fornecedor_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                tipo_despesa_id=tipo_despesa_id,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status='parcelado',
                eh_parcelado=True,
                total_parcelas=conta.total_parcelas,
                nota_entrada_id=conta.nota_entrada_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                user_id=current_user.id,
                tenant_id=tenant_id
            )
            db.add(conta_principal)
            db.flush()
            
            # Criar parcelas
            valor_parcela = conta.valor_original / conta.total_parcelas
            
            for i in range(1, conta.total_parcelas + 1):
                # Vencimento: soma i meses
                vencimento_parcela = conta.data_vencimento
                if i > 1:
                    # Adiciona meses
                    mes = vencimento_parcela.month + (i - 1)
                    ano = vencimento_parcela.year
                    while mes > 12:
                        mes -= 12
                        ano += 1
                    vencimento_parcela = vencimento_parcela.replace(year=ano, month=mes)
                
                parcela = ContaPagar(
                    descricao=f"{conta.descricao} - Parcela {i}/{conta.total_parcelas}",
                    fornecedor_id=conta.fornecedor_id,
                    categoria_id=conta.categoria_id,
                    dre_subcategoria_id=conta.dre_subcategoria_id,
                    canal=conta.canal,
                    tipo_despesa_id=tipo_despesa_id,
                    valor_original=valor_parcela,
                    valor_final=valor_parcela,
                    data_emissao=conta.data_emissao,
                    data_vencimento=vencimento_parcela,
                    status='pendente',
                    eh_parcelado=True,
                    numero_parcela=i,
                    total_parcelas=conta.total_parcelas,
                    conta_principal_id=conta_principal.id,
                    nota_entrada_id=conta.nota_entrada_id,
                    documento=conta.documento,
                    observacoes=f"Parcela {i} de {conta.total_parcelas}",
                    user_id=current_user.id,
                    tenant_id=tenant_id
                )
                db.add(parcela)
                contas_criadas.append(parcela)
        
        else:
            # Conta simples (não parcelada)
            nova_conta = ContaPagar(
                descricao=conta.descricao,
                fornecedor_id=conta.fornecedor_id,
                categoria_id=conta.categoria_id,
                dre_subcategoria_id=conta.dre_subcategoria_id,
                canal=conta.canal,
                tipo_despesa_id=tipo_despesa_id,
                valor_original=conta.valor_original,
                valor_final=conta.valor_original,
                data_emissao=conta.data_emissao,
                data_vencimento=conta.data_vencimento,
                status='pendente',
                nota_entrada_id=conta.nota_entrada_id,
                documento=conta.documento,
                observacoes=conta.observacoes,
                # Recorrência
                eh_recorrente=conta.eh_recorrente,
                tipo_recorrencia=conta.tipo_recorrencia,
                intervalo_dias=conta.intervalo_dias,
                data_inicio_recorrencia=conta.data_inicio_recorrencia or conta.data_vencimento,
                data_fim_recorrencia=conta.data_fim_recorrencia,
                numero_repeticoes=conta.numero_repeticoes,
                user_id=current_user.id,
                tenant_id=tenant_id
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

            if nova_conta.eh_recorrente and nova_conta.tipo_recorrencia and nova_conta.proxima_recorrencia:
                db.flush()
                limite_recorrencia = calcular_limite_janela_recorrencia(date.today())
                contas_criadas.extend(
                    _gerar_contas_recorrentes_ate_janela(
                        db=db,
                        tenant_id=tenant_id,
                        conta_origem=nova_conta,
                        limite_recorrencia=limite_recorrencia,
                    )
                )
        
        db.commit()
        
        # ============================
        # ATUALIZAR DRE EM TEMPO REAL
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
                    tipo_movimentacao='DESPESA'
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao atualizar DRE para conta #{conta_criada.id}: {e}")
        
        # ============================
        # RECONCILIAÇÃO DAS SIMPLES NACIONAL
        # ============================
        for conta_criada in contas_criadas:
            try:
                # Verificar se é DAS Simples Nacional
                categoria = db.query(CategoriaFinanceira).filter(
                    CategoriaFinanceira.id == conta_criada.categoria_id
                ).first()
                
                if categoria and "DAS" in categoria.nome.upper() and "SIMPLES" in categoria.nome.upper():
                    # Determinar competência pela data de emissão
                    mes_competencia = conta_criada.data_emissao.month
                    ano_competencia = conta_criada.data_emissao.year
                    
                    resultado = reconciliar_das_simples(
                        db=db,
                        tenant_id=tenant_id,
                        valor_das=conta_criada.valor_original,
                        mes_competencia=mes_competencia,
                        ano_competencia=ano_competencia,
                        usuario_id=current_user.id
                    )
                    
                    if resultado.get("sucesso"):
                        logger.info(
                            f"✅ DAS reconciliado: R$ {resultado['valor_das_real']:.2f} "
                            f"(Ajuste: R$ {abs(resultado['diferenca']):.2f})"
                        )
                        if resultado.get("sugestao_aliquota"):
                            logger.info(f"💡 Nova alíquota sugerida: {resultado['sugestao_aliquota']}%")
                    else:
                        logger.warning(f"⚠️ Reconciliação falhou: {resultado.get('motivo')}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao reconciliar DAS para conta #{conta_criada.id}: {e}")
                import traceback
                traceback.print_exc()
        
        # ============================
        # RECONCILIAÇÃO DE PROVISÕES TRABALHISTAS
        # ============================
        for conta_criada in contas_criadas:
            try:
                categoria = db.query(CategoriaFinanceira).filter(
                    CategoriaFinanceira.id == conta_criada.categoria_id
                ).first()
                
                if not categoria:
                    continue
                
                # Determinar competência pela data de emissão (ou vencimento)
                mes_competencia = conta_criada.data_emissao.month
                ano_competencia = conta_criada.data_emissao.year
                
                # Reconciliar INSS
                if categoria.nome == "INSS Patronal":
                    reconciliar_provisao(
                        db=db,
                        tenant_id=tenant_id,
                        nome_provisao="Provisão INSS Patronal",
                        nome_real="INSS Patronal",
                        valor_real=conta_criada.valor_original,
                        mes=mes_competencia,
                        ano=ano_competencia,
                        observacao_real="INSS Patronal (valor real)",
                    )
                    logger.info(f"✅ INSS reconciliado: R$ {conta_criada.valor_original:.2f}")
                    db.commit()
                
                # Reconciliar FGTS
                elif categoria.nome == "FGTS":
                    reconciliar_provisao(
                        db=db,
                        tenant_id=tenant_id,
                        nome_provisao="Provisão FGTS",
                        nome_real="FGTS",
                        valor_real=conta_criada.valor_original,
                        mes=mes_competencia,
                        ano=ano_competencia,
                        observacao_real="FGTS (valor real)",
                    )
                    logger.info(f"✅ FGTS reconciliado: R$ {conta_criada.valor_original:.2f}")
                    db.commit()
                
                # Reconciliar Folha de Pagamento
                elif categoria.nome == "Folha de Pagamento":
                    reconciliar_provisao(
                        db=db,
                        tenant_id=tenant_id,
                        nome_provisao="Provisão Folha de Pagamento",
                        nome_real="Folha de Pagamento",
                        valor_real=conta_criada.valor_original,
                        mes=mes_competencia,
                        ano=ano_competencia,
                        observacao_real="Folha de Pagamento (valor real)",
                    )
                    logger.info(f"✅ Folha reconciliada: R$ {conta_criada.valor_original:.2f}")
                    db.commit()
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao reconciliar provisão para conta #{conta_criada.id}: {e}")
                import traceback
                traceback.print_exc()
        
        # INTEGRAÇÃO REVERSA: Criar lançamentos manuais no fluxo de caixa
        for conta_criada in contas_criadas:
            try:
                lancamento = LancamentoManual(
                    tipo='saida',
                    valor=conta_criada.valor_original,
                    descricao=conta_criada.descricao,
                    data_lancamento=conta_criada.data_emissao,
                    data_prevista=conta_criada.data_vencimento,
                    data_efetivacao=None,  # Ainda não pago
                    categoria_id=conta_criada.categoria_id,
                    conta_bancaria_id=None,
                    status='previsto',
                    observacoes=f"Gerado automaticamente da conta a pagar #{conta_criada.id}",
                    gerado_automaticamente=True,
                    confianca_ia=None
                )
                db.add(lancamento)
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível criar lançamento para conta #{conta_criada.id}: {e}")
        
        db.commit()
        
        logger.info(f"✅ {len(contas_criadas)} conta(s) a pagar criada(s)")
        
        return {
            "message": "Conta(s) criada(s) com sucesso",
            "total_contas": len(contas_criadas),
            "ids": [c.id for c in contas_criadas]
        }

    except HTTPException as e:
        logger.warning(f"Erro validado ao criar conta: {e.detail}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao criar conta: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LISTAR CONTAS A PAGAR
# ============================================================================

@router.get("/", response_model=List[ContaPagarResponse])
def listar_contas_pagar(
    status: Optional[str] = Query(None),
    fornecedor_id: Optional[int] = Query(None),
    categoria_id: Optional[int] = Query(None),
    tipo_despesa_id: Optional[int] = Query(None),
    tipo_custo: Optional[str] = Query(None),  # 'fixo', 'variavel'
    origem: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    fornecedor_nome: Optional[str] = Query(None),
    data_campo: str = Query("vencimento"),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    apenas_vencidas: bool = Query(False),
    apenas_vencer: bool = Query(False),
    numero_nf: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista contas a pagar com filtros
    """
    current_user, tenant_id = user_and_tenant
    
    query = db.query(ContaPagar).filter(ContaPagar.tenant_id == tenant_id)
    
    # Filtros
    if status:
        status_normalizado = status.strip().lower()
        if status_normalizado == 'vencido':
            query = query.filter(
                and_(
                    ContaPagar.status != 'pago',
                    ContaPagar.data_vencimento < date.today(),
                )
            )
        else:
            query = query.filter(ContaPagar.status == status_normalizado)
    if fornecedor_id:
        query = query.filter(ContaPagar.fornecedor_id == fornecedor_id)
    termo_fornecedor = (fornecedor_nome or "").strip()
    if termo_fornecedor:
        fornecedor_pattern = f"%{termo_fornecedor}%"
        fornecedores_match = (
            select(Cliente.id)
            .where(
                Cliente.tenant_id == tenant_id,
                or_(
                    Cliente.nome.ilike(fornecedor_pattern),
                    Cliente.nome_fantasia.ilike(fornecedor_pattern),
                    Cliente.razao_social.ilike(fornecedor_pattern),
                    Cliente.cnpj.ilike(fornecedor_pattern),
                    Cliente.cpf.ilike(fornecedor_pattern),
                ),
            )
        )
        query = query.filter(ContaPagar.fornecedor_id.in_(fornecedores_match))
    if categoria_id:
        query = query.filter(ContaPagar.categoria_id == categoria_id)
    if tipo_despesa_id:
        query = query.filter(ContaPagar.tipo_despesa_id == tipo_despesa_id)

    origem_normalizada = (origem or "").strip().lower()
    caixa_pdv_condition = ContaPagar.observacoes.ilike(f"%{CAIXA_PDV_OBSERVACAO_MARKER}%")
    if origem_normalizada == "caixa_pdv":
        query = query.filter(caixa_pdv_condition)
    elif origem_normalizada == "nota_entrada":
        query = query.filter(ContaPagar.nota_entrada_id.isnot(None))
    elif origem_normalizada == "manual":
        query = query.filter(
            ContaPagar.nota_entrada_id.is_(None),
            or_(ContaPagar.observacoes.is_(None), ~caixa_pdv_condition),
        )

    termo_busca = (busca or "").strip()
    if termo_busca:
        busca_pattern = f"%{termo_busca}%"
        fornecedores_match = (
            select(Cliente.id)
            .where(
                Cliente.tenant_id == tenant_id,
                Cliente.nome.ilike(busca_pattern),
            )
        )
        query = query.filter(
            or_(
                ContaPagar.descricao.ilike(busca_pattern),
                ContaPagar.documento.ilike(busca_pattern),
                ContaPagar.nfe_numero.ilike(busca_pattern),
                ContaPagar.observacoes.ilike(busca_pattern),
                ContaPagar.fornecedor_id.in_(fornecedores_match),
            )
        )

    data_column = ContaPagar.data_vencimento
    if data_campo == "pagamento":
        data_column = ContaPagar.data_pagamento
    elif data_campo == "emissao":
        data_column = ContaPagar.data_emissao

    if data_inicio:
        query = query.filter(data_column >= data_inicio)
    if data_fim:
        query = query.filter(data_column <= data_fim)
    if numero_nf:
        numero_nf_pattern = f'%{numero_nf}%'
        query = query.filter(
            or_(
                ContaPagar.nfe_numero.ilike(numero_nf_pattern),
                ContaPagar.documento.ilike(numero_nf_pattern),
            )
        )
    if tipo_custo in ('fixo', 'variavel'):
        from .financeiro_models import CategoriaFinanceira as CF
        query = query.join(CF, ContaPagar.categoria_id == CF.id, isouter=True).filter(
            CF.tipo_custo == tipo_custo
        )
    if apenas_vencidas:
        query = query.filter(
            and_(
                ContaPagar.status != 'pago',
                ContaPagar.data_vencimento < date.today()
            )
        )
    if apenas_vencer:
        query = query.filter(
            and_(
                ContaPagar.status != 'pago',
                ContaPagar.data_vencimento >= date.today()
            )
        )
    
    query = query.order_by(ContaPagar.data_vencimento.asc())
    contas = query.limit(limit).offset(offset).all()
    
    # Montar response
    resultado = []
    for conta in contas:
        status_value = conta.status or 'pendente'

        # Calcular dias para vencimento
        dias_venc = None
        if status_value == 'pendente':
            dias_venc = (conta.data_vencimento - date.today()).days
        
        # Buscar nome do fornecedor
        fornecedor_nome = None
        if conta.fornecedor_id:
            fornecedor = db.query(Cliente).filter(
                Cliente.id == conta.fornecedor_id,
                Cliente.tenant_id == tenant_id
            ).first()
            if fornecedor:
                fornecedor_nome = fornecedor.nome
        
        item = {
            "id": conta.id,
            "descricao": conta.descricao,
            "fornecedor_nome": fornecedor_nome,
            "categoria_id": conta.categoria_id,
            "categoria_nome": conta.categoria.nome if conta.categoria else None,
            "valor_original": float(conta.valor_original) if conta.valor_original is not None else 0.0,
            "valor_pago": float(conta.valor_pago) if conta.valor_pago is not None else 0.0,
            "valor_final": float(conta.valor_final) if conta.valor_final is not None else 0.0,
            "data_emissao": conta.data_emissao,
            "data_vencimento": conta.data_vencimento,
            "data_pagamento": conta.data_pagamento,
            "status": status_value,
            "dias_vencimento": dias_venc,
            "eh_parcelado": conta.eh_parcelado if conta.eh_parcelado is not None else False,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas,
            "documento": conta.documento,
            "nfe_numero": conta.nfe_numero,
            "observacoes": conta.observacoes,
            "nota_entrada_id": conta.nota_entrada_id,
            "canal": conta.canal,
            "dre_subcategoria_id": conta.dre_subcategoria_id,
            "dre_subcategoria_nome": None,
            "tipo_despesa_id": conta.tipo_despesa_id,
            "tipo_despesa_nome": conta.tipo_despesa.nome if conta.tipo_despesa else None,
            "e_custo_fixo": (
                conta.categoria.tipo_custo == 'fixo' if conta.categoria and conta.categoria.tipo_custo in ('fixo', 'variavel')
                else None
            ),
            **_identificar_origem_conta_pagar(conta),
        }

        if conta.dre_subcategoria_id:
            sub = db.query(DRESubcategoria).filter(
                DRESubcategoria.id == conta.dre_subcategoria_id,
                DRESubcategoria.tenant_id == tenant_id,
            ).first()
            if sub:
                item["dre_subcategoria_nome"] = sub.nome

        resultado.append(item)
    
    return resultado


@router.patch("/{conta_id}/classificacao")
def classificar_conta_pagar(
    conta_id: int,
    payload: ContaPagarClassificacaoUpdate,
    aplicar_fornecedor: bool = Query(False),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Permite classificar conta existente com categoria, subcategoria DRE e tipo de despesa."""
    _, tenant_id = user_and_tenant

    conta = db.query(ContaPagar).filter(
        ContaPagar.id == conta_id,
        ContaPagar.tenant_id == tenant_id,
    ).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    if (
        payload.categoria_id is None
        and payload.dre_subcategoria_id is None
        and payload.tipo_despesa_id is None
        and payload.canal is None
    ):
        raise HTTPException(status_code=422, detail="Informe pelo menos um campo para classificar")

    if payload.categoria_id is not None:
        categoria = db.query(CategoriaFinanceira).filter(
            CategoriaFinanceira.id == payload.categoria_id,
            CategoriaFinanceira.tenant_id == tenant_id,
            CategoriaFinanceira.ativo.is_(True),
        ).first()
        if not categoria:
            raise HTTPException(status_code=422, detail="Categoria financeira inválida para este tenant")
        conta.categoria_id = payload.categoria_id

    if payload.dre_subcategoria_id is not None:
        sub = db.query(DRESubcategoria).filter(
            DRESubcategoria.id == payload.dre_subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
        ).first()
        if not sub:
            raise HTTPException(status_code=422, detail="Subcategoria DRE inválida para este tenant")
        conta.dre_subcategoria_id = payload.dre_subcategoria_id

    if payload.tipo_despesa_id is not None:
        tipo = db.query(TipoDespesa).filter(
            TipoDespesa.id == payload.tipo_despesa_id,
            TipoDespesa.tenant_id == tenant_id,
            TipoDespesa.ativo.is_(True),
        ).first()
        if not tipo:
            raise HTTPException(status_code=422, detail="Tipo de despesa inválido para este tenant")
        conta.tipo_despesa_id = payload.tipo_despesa_id

    if payload.canal is not None:
        conta.canal = payload.canal

    fornecedor_atualizadas = 0
    if aplicar_fornecedor and conta.fornecedor_id:
        outras_contas = db.query(ContaPagar).filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.fornecedor_id == conta.fornecedor_id,
            ContaPagar.id != conta.id,
        ).all()

        for outra_conta in outras_contas:
            if payload.categoria_id is not None:
                outra_conta.categoria_id = payload.categoria_id
            if payload.dre_subcategoria_id is not None:
                outra_conta.dre_subcategoria_id = payload.dre_subcategoria_id
            if payload.tipo_despesa_id is not None:
                outra_conta.tipo_despesa_id = payload.tipo_despesa_id
            if payload.canal is not None:
                outra_conta.canal = payload.canal
            fornecedor_atualizadas += 1

    db.commit()
    db.refresh(conta)

    return {
        "ok": True,
        "mensagem": "Classificação atualizada com sucesso",
        "conta_id": conta.id,
        "categoria_id": conta.categoria_id,
        "dre_subcategoria_id": conta.dre_subcategoria_id,
        "tipo_despesa_id": conta.tipo_despesa_id,
        "canal": conta.canal,
        "fornecedor_atualizadas": fornecedor_atualizadas,
    }


# ============================================================================
# BUSCAR CONTA ESPECÍFICA
# ============================================================================

@router.get("/{conta_id}")
def buscar_conta_pagar(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Busca uma conta a pagar específica com todos os detalhes
    """
    current_user, tenant_id = user_and_tenant
    
    conta = db.query(ContaPagar).options(
        joinedload(ContaPagar.categoria),
        joinedload(ContaPagar.pagamentos)
    ).filter(ContaPagar.id == conta_id).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    # Buscar fornecedor
    fornecedor = None
    if conta.fornecedor_id:
        fornecedor = db.query(Cliente).filter(Cliente.id == conta.fornecedor_id).first()
    
    # Buscar nota de entrada se houver
    nota = None
    if conta.nota_entrada_id:
        nota = db.query(NotaEntrada).filter(NotaEntrada.id == conta.nota_entrada_id).first()
    
    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "fornecedor": {
            "id": fornecedor.id if fornecedor else None,
            "nome": fornecedor.nome if fornecedor else None,
            "cnpj": fornecedor.cnpj if fornecedor else None
        } if fornecedor else None,
        "categoria": {
            "id": conta.categoria.id if conta.categoria else None,
            "nome": conta.categoria.nome if conta.categoria else None,
            "cor": conta.categoria.cor if conta.categoria else None
        } if conta.categoria else None,
        "valores": {
            "original": float(conta.valor_original),
            "pago": float(conta.valor_pago),
            "desconto": float(conta.valor_desconto),
            "juros": float(conta.valor_juros),
            "multa": float(conta.valor_multa),
            "final": float(conta.valor_final),
            "saldo": float(conta.valor_final - conta.valor_pago)
        },
        "datas": {
            "emissao": conta.data_emissao,
            "vencimento": conta.data_vencimento,
            "pagamento": conta.data_pagamento
        },
        "status": conta.status,
        "parcelamento": {
            "eh_parcelado": conta.eh_parcelado if conta.eh_parcelado is not None else False,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas
        } if conta.eh_parcelado else None,
        "nota_entrada": {
            "id": nota.id if nota else None,
            "numero": nota.numero_nota if nota else None,
            "chave": nota.chave_acesso if nota else None
        } if nota else None,
        "documento": conta.documento,
        "observacoes": conta.observacoes,
        "pagamentos": [
            {
                "id": p.id,
                "valor": float(p.valor_pago),
                "data": p.data_pagamento,
                "forma_pagamento_id": p.forma_pagamento_id,
                "observacoes": p.observacoes
            } for p in conta.pagamentos
        ]
    }


# ============================================================================
# REGISTRAR PAGAMENTO
# ============================================================================

@router.post("/{conta_id}/pagar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita pagamento duplicado
async def registrar_pagamento(
    conta_id: int,
    pagamento: PagamentoCreate,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Registra um pagamento (baixa) de conta a pagar
    """
    current_user, tenant_id = user_and_tenant
    
    conta = db.query(ContaPagar).filter(ContaPagar.id == conta_id).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    
    if conta.status == 'pago':
        raise HTTPException(status_code=400, detail="Conta já está paga")
    
    # Atualizar valores
    conta.valor_pago += Decimal(str(pagamento.valor_pago))
    conta.valor_juros += Decimal(str(pagamento.valor_juros))
    conta.valor_multa += Decimal(str(pagamento.valor_multa))
    conta.valor_desconto += Decimal(str(pagamento.valor_desconto))
    
    # Recalcular valor final
    conta.valor_final = (
        conta.valor_original +
        conta.valor_juros +
        conta.valor_multa -
        conta.valor_desconto
    )
    
    # Verificar se pagou tudo
    if conta.valor_pago >= conta.valor_final:
        conta.status = 'pago'
        conta.data_pagamento = pagamento.data_pagamento
    else:
        conta.status = 'parcial'
    
    # Registrar pagamento
    novo_pagamento = Pagamento(
        conta_pagar_id=conta.id,
        forma_pagamento_id=pagamento.forma_pagamento_id,
        valor_pago=pagamento.valor_pago,
        data_pagamento=pagamento.data_pagamento,
        observacoes=pagamento.observacoes,
        user_id=current_user.id,
        tenant_id=tenant_id
    )
    db.add(novo_pagamento)
    
    # ========================================
    # CRIAR MOVIMENTAÇÃO FINANCEIRA E ATUALIZAR SALDO
    # ========================================
    
    if pagamento.conta_bancaria_id:
        # Buscar conta bancária
        conta_bancaria = db.query(ContaBancaria).filter(
            ContaBancaria.id == pagamento.conta_bancaria_id
        ).first()
        
        if not conta_bancaria:
            raise HTTPException(
                status_code=404,
                detail=f"Conta bancária {pagamento.conta_bancaria_id} não encontrada"
            )
        
        if not conta_bancaria.ativa:
            raise HTTPException(
                status_code=400,
                detail=f"Conta bancária '{conta_bancaria.nome}' está inativa"
            )
        
        # Converter valor para centavos
        valor_centavos = int(pagamento.valor_pago * 100)
        
        # Criar movimentação financeira (SAÍDA)
        movimentacao = MovimentacaoFinanceira(
            conta_bancaria_id=conta_bancaria.id,
            tipo='saida',
            valor=valor_centavos,
            descricao=f"Pagamento: {conta.descricao}",
            data_movimento=pagamento.data_pagamento,
            categoria_id=conta.categoria_id,
            status='realizado',
            forma_pagamento_id=pagamento.forma_pagamento_id,
            documento=conta.documento,
            origem_tipo='conta_pagar',
            origem_id=conta.id,
            observacoes=pagamento.observacoes,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        db.add(movimentacao)
        
        # Atualizar saldo da conta bancária (DÉBITO)
        conta_bancaria.saldo_atual -= valor_centavos
        
        logger.info(
            f"🏦 Movimentação bancária criada: {conta_bancaria.nome} "
            f"-R$ {pagamento.valor_pago:.2f} (Saldo: R$ {conta_bancaria.saldo_atual/100:.2f})"
        )
    
    # ========================================
    # ATUALIZAR LANÇAMENTO MANUAL PREVISTO
    # ========================================
    
    # Buscar lançamento manual previsto relacionado a esta conta
    lancamento = db.query(LancamentoManual).filter(
        LancamentoManual.tipo == 'saida',
        LancamentoManual.status == 'previsto',
        LancamentoManual.valor == conta.valor_original,
        LancamentoManual.gerado_automaticamente == True
    ).order_by(LancamentoManual.id.desc()).first()
    
    if lancamento:
        lancamento.status = 'realizado'
        lancamento.realizado_em = datetime.now()
        logger.info(f"📊 Lançamento manual #{lancamento.id} atualizado para 'realizado'")
    
    db.commit()
    
    logger.info(f"✅ Pagamento registrado: R$ {pagamento.valor_pago} - Conta {conta_id}")
    
    return {
        "message": "Pagamento registrado com sucesso",
        "conta_id": conta.id,
        "status": conta.status,
        "valor_pago_total": float(conta.valor_pago),
        "valor_final": float(conta.valor_final),
        "saldo_restante": float(conta.valor_final - conta.valor_pago)
    }


# ============================================================================
# DASHBOARD / RESUMO
# ============================================================================

@router.get("/dashboard/resumo")
def dashboard_contas_pagar(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Resumo financeiro de contas a pagar
    """
    current_user, tenant_id = user_and_tenant
    
    hoje = date.today()
    
    # Total pendente
    total_pendente = db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)).filter(
        ContaPagar.status.in_(['pendente', 'parcial', 'vencido'])
    ).scalar() or 0
    
    # Vencidas
    total_vencido = db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)).filter(
        and_(
            ContaPagar.status == 'pendente',
            ContaPagar.data_vencimento < hoje
        )
    ).scalar() or 0
    
    count_vencidas = db.query(func.count(ContaPagar.id)).filter(
        and_(
            ContaPagar.status == 'pendente',
            ContaPagar.data_vencimento < hoje
        )
    ).scalar()
    
    # Vence hoje
    total_vence_hoje = db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)).filter(
        and_(
            ContaPagar.status == 'pendente',
            ContaPagar.data_vencimento == hoje
        )
    ).scalar() or 0
    
    # Próximos 7 dias
    data_7dias = hoje + timedelta(days=7)
    total_7dias = db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)).filter(
        and_(
            ContaPagar.status == 'pendente',
            ContaPagar.data_vencimento.between(hoje, data_7dias)
        )
    ).scalar() or 0
    
    # Próximos 30 dias
    data_30dias = hoje + timedelta(days=30)
    total_30dias = db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago)).filter(
        and_(
            ContaPagar.status == 'pendente',
            ContaPagar.data_vencimento.between(hoje, data_30dias)
        )
    ).scalar() or 0
    
    # Pago no mês
    primeiro_dia_mes = hoje.replace(day=1)
    total_pago_mes = db.query(func.sum(ContaPagar.valor_pago)).filter(
        and_(
            ContaPagar.data_pagamento >= primeiro_dia_mes,
            ContaPagar.data_pagamento <= hoje
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
        "pago_mes_atual": float(total_pago_mes)
    }


# ============================================================================
# PROCESSAR RECORRÊNCIAS
# ============================================================================

@router.post("/processar-recorrencias")
async def processar_recorrencias_contas_pagar(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Processa contas recorrentes e cria novas contas quando necessário
    Esta rota deve ser executada periodicamente (diariamente recomendado)
    """
    current_user, tenant_id = user_and_tenant
    hoje = date.today()
    limite_recorrencia = calcular_limite_janela_recorrencia(hoje)
    contas_criadas = []
    
    # Buscar contas recorrentes que precisam manter a janela futura preenchida
    contas_recorrentes = db.query(ContaPagar).filter(
        and_(
            ContaPagar.eh_recorrente == True,
            ContaPagar.proxima_recorrencia <= limite_recorrencia,
            or_(
                ContaPagar.data_fim_recorrencia.is_(None),
                ContaPagar.data_fim_recorrencia >= hoje
            )
        )
    ).all()
    
    for conta_origem in contas_recorrentes:
        try:
            novas_contas = _gerar_contas_recorrentes_ate_janela(
                db=db,
                tenant_id=tenant_id,
                conta_origem=conta_origem,
                limite_recorrencia=limite_recorrencia,
            )
            contas_criadas.extend(novas_contas)
            logger.info(f"Recorrencia #{conta_origem.id}: {len(novas_contas)} conta(s) gerada(s)")
            
        except Exception as e:
            logger.error(f"Erro ao processar recorrencia da conta #{conta_origem.id}: {e}")
            continue
    
    for conta_criada in contas_criadas:
        try:
            atualizar_dre_por_lancamento(
                db=db,
                tenant_id=tenant_id,
                dre_subcategoria_id=conta_criada.dre_subcategoria_id,
                canal=conta_criada.canal,
                valor=conta_criada.valor_original,
                data_lancamento=conta_criada.data_vencimento,
                tipo_movimentacao='DESPESA'
            )
        except Exception as e:
            logger.warning(f"Erro ao atualizar DRE para conta recorrente #{conta_criada.id}: {e}")

    db.commit()
    
    return {
        "message": f"{len(contas_criadas)} conta(s) recorrente(s) processada(s) com sucesso",
        "contas_criadas": len(contas_criadas),
        "ids": [c.id for c in contas_criadas]
    }
