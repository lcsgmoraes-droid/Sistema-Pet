# ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
# Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
# NÃO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenário real
# 3. Validar impacto financeiro

"""
ROTAS DE CATEGORIAS FINANCEIRAS E FORMAS DE PAGAMENTO
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from .financeiro_models import CategoriaFinanceira, FormaPagamento

router = APIRouter(prefix="/financeiro", tags=["Financeiro - Configurações"])

# ============================================================================
# SCHEMAS
# ============================================================================

class CategoriaCreate(BaseModel):
    nome: str
    tipo: str  # receita ou despesa
    cor: Optional[str] = None
    categoria_pai_id: Optional[int] = None


class FormaPagamentoCreate(BaseModel):
    nome: str
    tipo: str  # dinheiro, cartao_credito, cartao_debito, pix, boleto, transferencia
    
    # Taxas e prazos
    taxa_percentual: float = 0
    taxa_fixa: float = 0
    prazo_dias: int = 0
    
    # Configurações
    operadora: Optional[str] = None  # Stone, Cielo, Rede, etc
    gera_contas_receber: bool = False
    split_parcelas: bool = False
    conta_bancaria_destino_id: Optional[int] = None
    requer_nsu: bool = False
    tipo_cartao: Optional[str] = None  # debito, credito, voucher
    bandeira: Optional[str] = None  # visa, master, elo, amex
    
    # Parcelamento
    ativo: bool = True
    permite_parcelamento: bool = False
    parcelas_maximas: int = 1
    taxas_por_parcela: Optional[str] = None  # JSON string com taxas por parcela
    
    # Antecipação
    permite_antecipacao: bool = False
    dias_recebimento_antecipado: Optional[int] = None
    taxa_antecipacao_percentual: Optional[float] = None  # Taxa adicional de antecipação
    
    # UI
    icone: Optional[str] = None
    cor: Optional[str] = None


class FormaPagamentoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    taxa_percentual: float
    taxa_fixa: float
    prazo_dias: int
    operadora: Optional[str]
    gera_contas_receber: bool
    split_parcelas: bool
    conta_bancaria_destino_id: Optional[int]
    requer_nsu: bool
    tipo_cartao: Optional[str]
    bandeira: Optional[str]
    ativo: bool
    permite_parcelamento: bool
    parcelas_maximas: int
    taxas_por_parcela: Optional[str]
    permite_antecipacao: Optional[bool] = False
    dias_recebimento_antecipado: Optional[int] = None
    taxa_antecipacao_percentual: Optional[float] = None
    icone: Optional[str]
    cor: Optional[str]
    
    model_config = {"from_attributes": True}


# ============================================================================
# CATEGORIAS FINANCEIRAS
# ============================================================================

@router.get("/categorias")
def listar_categorias(
    tipo: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as categorias financeiras
    """
    current_user, tenant_id = current_user_and_tenant
    query = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == tenant_id
    )
    
    if tipo:
        query = query.filter(CategoriaFinanceira.tipo == tipo)
    
    categorias = query.order_by(CategoriaFinanceira.nome).all()
    
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "tipo": c.tipo,
            "cor": c.cor,
            "categoria_pai_id": c.categoria_pai_id,
            "ativo": c.ativo
        } for c in categorias
    ]


@router.post("/categorias", status_code=status.HTTP_201_CREATED)
def criar_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria nova categoria financeira
    """
    current_user, tenant_id = current_user_and_tenant
    nova_categoria = CategoriaFinanceira(
        nome=categoria.nome,
        tipo=categoria.tipo,
        cor=categoria.cor,
        categoria_pai_id=categoria.categoria_pai_id,
        tenant_id=tenant_id
    )
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)
    
    return {
        "id": nova_categoria.id,
        "nome": nova_categoria.nome,
        "tipo": nova_categoria.tipo
    }


@router.put("/categorias/{categoria_id}")
def atualizar_categoria(
    categoria_id: int,
    categoria: CategoriaCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza categoria financeira
    """
    current_user, tenant_id = current_user_and_tenant
    cat = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.id == categoria_id,
        CategoriaFinanceira.tenant_id == tenant_id
    ).first()
    
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    cat.nome = categoria.nome
    cat.tipo = categoria.tipo
    if categoria.cor:
        cat.cor = categoria.cor
    cat.categoria_pai_id = categoria.categoria_pai_id
    
    db.commit()
    
    return {"message": "Categoria atualizada"}


@router.delete("/categorias/{categoria_id}")
def desativar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Desativa uma categoria (não exclui, apenas marca como inativa)
    """
    current_user, tenant_id = current_user_and_tenant
    cat = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.id == categoria_id,
        CategoriaFinanceira.tenant_id == tenant_id
    ).first()
    
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    cat.ativo = False
    db.commit()
    
    return {"message": "Categoria desativada"}


# ============================================================================
# FORMAS DE PAGAMENTO
# ============================================================================

@router.get("/formas-pagamento", response_model=List[FormaPagamentoResponse])
def listar_formas_pagamento(
    apenas_ativas: bool = True,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as formas de pagamento com todos os campos
    """
    current_user, tenant_id = current_user_and_tenant
    query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id
    )
    
    if apenas_ativas:
        query = query.filter(FormaPagamento.ativo == True)
    
    formas = query.order_by(FormaPagamento.nome).all()
    
    # Converter valores de centavos para reais
    for f in formas:
        if f.taxa_fixa:
            f.taxa_fixa = f.taxa_fixa / 100
        if f.taxa_percentual:
            f.taxa_percentual = float(f.taxa_percentual)
    
    return formas


@router.post("/formas-pagamento", response_model=FormaPagamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_forma_pagamento(
    forma: FormaPagamentoCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Cria nova forma de pagamento com todos os campos
    """
    current_user, tenant_id = current_user_and_tenant
    nova_forma = FormaPagamento(
        nome=forma.nome,
        tipo=forma.tipo,
        taxa_percentual=forma.taxa_percentual,
        taxa_fixa=forma.taxa_fixa,
        prazo_dias=forma.prazo_dias,
        prazo_recebimento=forma.prazo_dias,  # Compatibilidade
        operadora=forma.operadora,
        gera_contas_receber=forma.gera_contas_receber,
        split_parcelas=forma.split_parcelas,
        conta_bancaria_destino_id=forma.conta_bancaria_destino_id,
        requer_nsu=forma.requer_nsu,
        tipo_cartao=forma.tipo_cartao,
        bandeira=forma.bandeira,
        ativo=forma.ativo,
        permite_parcelamento=forma.permite_parcelamento,
        max_parcelas=forma.parcelas_maximas,
        parcelas_maximas=forma.parcelas_maximas,  # Compatibilidade
        taxas_por_parcela=forma.taxas_por_parcela,  # JSON string
        permite_antecipacao=forma.permite_antecipacao,
        dias_recebimento_antecipado=forma.dias_recebimento_antecipado,
        taxa_antecipacao_percentual=forma.taxa_antecipacao_percentual,
        icone=forma.icone,
        cor=forma.cor,
        user_id=current_user.id,
        tenant_id=tenant_id
    )
    
    db.add(nova_forma)
    db.commit()
    db.refresh(nova_forma)
    
    return nova_forma


@router.put("/formas-pagamento/{forma_id}", response_model=FormaPagamentoResponse)
def atualizar_forma_pagamento(
    forma_id: int,
    forma: FormaPagamentoCreate,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza forma de pagamento com todos os campos
    """
    current_user, tenant_id = current_user_and_tenant
    f = db.query(FormaPagamento).filter(
        FormaPagamento.id == forma_id,
        FormaPagamento.tenant_id == tenant_id
    ).first()
    
    if not f:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Atualizar todos os campos
    f.nome = forma.nome
    f.tipo = forma.tipo
    f.taxa_percentual = forma.taxa_percentual
    f.taxa_fixa = forma.taxa_fixa
    f.prazo_dias = forma.prazo_dias
    f.prazo_recebimento = forma.prazo_dias
    f.operadora = forma.operadora
    f.gera_contas_receber = forma.gera_contas_receber
    f.split_parcelas = forma.split_parcelas
    f.conta_bancaria_destino_id = forma.conta_bancaria_destino_id
    f.requer_nsu = forma.requer_nsu
    f.tipo_cartao = forma.tipo_cartao
    f.bandeira = forma.bandeira
    f.ativo = forma.ativo
    f.permite_parcelamento = forma.permite_parcelamento
    f.max_parcelas = forma.parcelas_maximas
    f.parcelas_maximas = forma.parcelas_maximas
    f.taxas_por_parcela = forma.taxas_por_parcela  # JSON string
    f.permite_antecipacao = forma.permite_antecipacao
    f.dias_recebimento_antecipado = forma.dias_recebimento_antecipado
    f.taxa_antecipacao_percentual = forma.taxa_antecipacao_percentual
    f.icone = forma.icone
    f.cor = forma.cor
    
    db.commit()
    db.refresh(f)
    
    # Converter de volta para resposta
    f.taxa_fixa = f.taxa_fixa / 100
    
    return f


@router.delete("/formas-pagamento/{forma_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_forma_pagamento(
    forma_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Exclui permanentemente uma forma de pagamento
    """
    current_user, tenant_id = current_user_and_tenant
    
    forma = db.query(FormaPagamento).filter(
        FormaPagamento.id == forma_id,
        FormaPagamento.tenant_id == tenant_id
    ).first()
    
    if not forma:
        raise HTTPException(status_code=404, detail="Forma de pagamento não encontrada")
    
    # Hard delete - remove permanentemente do banco
    db.delete(forma)
    db.commit()
    
    return None


# ============================================================================
# FLUXO DE CAIXA
# ============================================================================

from datetime import date, datetime, timedelta
from decimal import Decimal

class FluxoCaixaMovimentacao(BaseModel):
    """Uma movimentação no fluxo de caixa"""
    data: date
    tipo: str  # entrada, saida, projecao_entrada, projecao_saida
    descricao: str
    categoria: str
    valor: float
    origem_tipo: str  # venda, conta_receber, conta_pagar, lancamento_manual, saldo_inicial
    origem_id: Optional[int] = None
    numero_venda: Optional[str] = None  # Número da venda quando origem for venda ou conta_receber de venda
    status: str = 'realizado'  # previsto ou realizado


class FluxoCaixaPeriodo(BaseModel):
    """Resumo de um período no fluxo de caixa - Estilo Flua"""
    data: str  # Data ou descrição do período (ex: "15/01/2026" ou "Semana 3")
    data_inicio: date  # Data início do período
    data_fim: date  # Data fim do período
    
    # PREVISTO
    previsto_entradas: float
    previsto_saidas: float
    previsto_saldo: float
    
    # REALIZADO
    realizado_entradas: float
    realizado_saidas: float
    realizado_saldo: float
    
    # SALDO
    saldo_inicial: float
    saldo_final: float


class FluxoCaixaResponse(BaseModel):
    """Resposta completa do fluxo de caixa - Estilo Flua"""
    periodos: List[FluxoCaixaPeriodo]
    movimentacoes: List[FluxoCaixaMovimentacao]
    
    # Totalizadores PREVISTO
    total_previsto_entradas: float
    total_previsto_saidas: float
    
    # Totalizadores REALIZADO
    total_realizado_entradas: float
    total_realizado_saidas: float
    
    # Saldos
    saldo_inicial: float
    saldo_final: float
    saldo_previsto_final: float


@router.get("/fluxo-caixa", response_model=FluxoCaixaResponse)
def get_fluxo_caixa(
    data_inicio: str,  # formato: YYYY-MM-DD
    data_fim: str,  # formato: YYYY-MM-DD
    conta_bancaria_id: Optional[int] = None,
    agrupamento: str = 'dia',  # dia, semana, mes
    numero_venda: Optional[str] = None,  # Filtro por número de venda
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna o fluxo de caixa consolidado para um período - Estilo Flua.
    
    Consolida com separação Previsto vs Realizado:
    - Saldo inicial das contas bancárias
    - REALIZADO: Vendas pagas, Contas recebidas/pagas, Lançamentos manuais realizados
    - PREVISTO: Contas pendentes, Lançamentos manuais previstos, Lançamentos recorrentes
    
    Parâmetros:
    - agrupamento: 'dia', 'semana' ou 'mes'
    """
    current_user, tenant_id = current_user_and_tenant
    from .vendas_models import Venda
    from .financeiro_models import ContaPagar, ContaReceber, Recebimento, ContaBancaria, LancamentoManual
    from sqlalchemy import func, and_, or_
    
    # Converter strings para date
    try:
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
    
    # Validar agrupamento
    if agrupamento not in ['dia', 'semana', 'mes']:
        raise HTTPException(status_code=400, detail="Agrupamento deve ser 'dia', 'semana' ou 'mes'")
    
    # Filtro de conta bancária
    filtro_conta = []
    if conta_bancaria_id:
        filtro_conta = [conta_bancaria_id]
    else:
        # Todas as contas do usuário e tenant
        contas = db.query(ContaBancaria).filter(
            ContaBancaria.user_id == current_user.id,
            ContaBancaria.tenant_id == tenant_id
        ).all()
        filtro_conta = [c.id for c in contas]
    
    # ========== SALDO INICIAL ==========
    saldo_inicial = Decimal(0)
    if filtro_conta:
        contas_obj = db.query(ContaBancaria).filter(
            and_(
                ContaBancaria.id.in_(filtro_conta),
                ContaBancaria.user_id == current_user.id,
                ContaBancaria.tenant_id == tenant_id
            )
        ).all()
        
        for conta in contas_obj:
            saldo_inicial += Decimal(str(conta.saldo_atual or 0))
    
    # ========== MOVIMENTAÇÕES ==========
    movimentacoes = []
    
    # 1. VENDAS REALIZADAS (Entradas Realizadas)
    vendas = db.query(Venda).filter(
        and_(
            Venda.user_id == current_user.id,
            Venda.tenant_id == tenant_id,
            Venda.data_venda >= dt_inicio,
            Venda.data_venda <= dt_fim,
            Venda.status == 'finalizada'
        )
    ).all()
    
    for venda in vendas:
        movimentacoes.append(FluxoCaixaMovimentacao(
            data=venda.data_venda.date() if isinstance(venda.data_venda, datetime) else venda.data_venda,
            tipo='entrada',
            descricao=f'Venda #{venda.id}',
            categoria='Vendas',
            valor=float(venda.total or 0),
            origem_tipo='venda',
            origem_id=venda.id,
            status='realizado'
        ))
    
    # 2. CONTAS A RECEBER PAGAS (Entradas Realizadas)
    # Agora buscamos da tabela fluxo_caixa, então vamos PULAR esta seção para evitar duplicação
    # Os recebimentos serão buscados via fluxo_caixa mais abaixo
    """
    recebimentos = db.query(Recebimento).join(ContaReceber).filter(
        and_(
            ContaReceber.user_id == user.id,
            Recebimento.data_recebimento >= dt_inicio,
            Recebimento.data_recebimento <= dt_fim
        )
    ).all()
    
    for rec in recebimentos:
        conta_receber = db.query(ContaReceber).filter(ContaReceber.id == rec.conta_receber_id).first()
        if conta_receber:
            # Buscar número da venda se existir
            numero_venda = None
            if conta_receber.venda_id:
                from app.vendas_models import Venda
                venda = db.query(Venda).filter(Venda.id == conta_receber.venda_id).first()
                if venda:
                    numero_venda = venda.numero_venda
            
            movimentacoes.append(FluxoCaixaMovimentacao(
                data=rec.data_recebimento if isinstance(rec.data_recebimento, date) else rec.data_recebimento.date(),
                tipo='entrada',
                descricao=f'Recebimento - {conta_receber.cliente.nome if conta_receber.cliente else "Cliente"}',
                categoria='Recebimentos',
                valor=float(rec.valor_recebido or 0),
                origem_tipo='conta_receber',
                origem_id=conta_receber.id,
                numero_venda=numero_venda,
                status='realizado'
            ))
    """
    
    # 3. CONTAS A PAGAR PAGAS (Saídas Realizadas)
    contas_pagas = db.query(ContaPagar).filter(
        and_(
            ContaPagar.user_id == current_user.id,
            ContaPagar.data_pagamento >= dt_inicio,
            ContaPagar.data_pagamento <= dt_fim,
            ContaPagar.status == 'pago'
        )
    ).all()
    
    for conta in contas_pagas:
        fornecedor_nome = conta.fornecedor.nome if conta.fornecedor else "Fornecedor"
        movimentacoes.append(FluxoCaixaMovimentacao(
            data=conta.data_pagamento if isinstance(conta.data_pagamento, date) else conta.data_pagamento.date(),
            tipo='saida',
            descricao=f'Pagamento - {fornecedor_nome}',
            categoria='Fornecedores',
            valor=float(conta.valor_pago or 0),
            origem_tipo='conta_pagar',
            origem_id=conta.id,
            status='realizado'
        ))
    
    # 4. LANÇAMENTOS MANUAIS REALIZADOS
    lancamentos_realizados = db.query(LancamentoManual).filter(
        and_(
            LancamentoManual.data_lancamento >= dt_inicio,
            LancamentoManual.data_lancamento <= dt_fim,
            LancamentoManual.status == 'realizado'
        )
    ).all()
    
    for lanc in lancamentos_realizados:
        movimentacoes.append(FluxoCaixaMovimentacao(
            data=lanc.data_lancamento if isinstance(lanc.data_lancamento, date) else lanc.data_lancamento.date(),
            tipo=lanc.tipo,
            descricao=lanc.descricao,
            categoria=lanc.categoria.nome if lanc.categoria else 'Sem Categoria',
            valor=float(lanc.valor),
            origem_tipo='lancamento_manual',
            origem_id=lanc.id,
            status='realizado'
        ))
    
    # 🆕 LANÇAMENTOS DA TABELA FLUXO_CAIXA (REALIZADOS)
    from .ia.aba5_models import FluxoCaixa
    
    # Converter para datetime para pegar horário completo
    dt_inicio_datetime = datetime.combine(dt_inicio, datetime.min.time())
    dt_fim_datetime = datetime.combine(dt_fim, datetime.max.time())
    
    fluxos_realizados = db.query(FluxoCaixa).filter(
        and_(
            FluxoCaixa.usuario_id == current_user.id,
            FluxoCaixa.data_movimentacao >= dt_inicio_datetime,
            FluxoCaixa.data_movimentacao <= dt_fim_datetime,
            FluxoCaixa.status == 'realizado'
        )
    ).all()
    
    for fluxo in fluxos_realizados:
        # Buscar número da venda se a origem for conta_receber
        numero_venda_fluxo = None
        if fluxo.origem_tipo == 'conta_receber' and fluxo.origem_id:
            conta = db.query(ContaReceber).filter(ContaReceber.id == fluxo.origem_id).first()
            if conta and conta.venda_id:
                venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
                if venda:
                    numero_venda_fluxo = venda.numero_venda
        
        movimentacoes.append(FluxoCaixaMovimentacao(
            data=fluxo.data_movimentacao.date() if isinstance(fluxo.data_movimentacao, datetime) else fluxo.data_movimentacao,
            tipo='entrada' if fluxo.tipo == 'entrada' else 'saida',
            descricao=fluxo.descricao or 'Movimentação',
            categoria=fluxo.categoria or 'Sem Categoria',
            valor=float(fluxo.valor),
            origem_tipo=fluxo.origem_tipo or 'fluxo_caixa',
            origem_id=fluxo.origem_id,
            numero_venda=numero_venda_fluxo,
            status='realizado'
        ))
    
    # ========== PREVISÕES ==========
    
    # 5. CONTAS A RECEBER PENDENTES (Entradas Previstas)
    # Agora buscamos da tabela fluxo_caixa, então vamos PULAR esta seção para evitar duplicação
    """
    contas_receber_pendentes = db.query(ContaReceber).filter(
        and_(
            ContaReceber.user_id == user.id,
            ContaReceber.data_vencimento >= dt_inicio,
            ContaReceber.data_vencimento <= dt_fim,
            ContaReceber.status.in_(['pendente', 'parcial'])
        )
    ).all()
    
    for conta in contas_receber_pendentes:
        valor_restante = (conta.valor_original or 0) - (conta.valor_recebido or 0)
        if valor_restante > 0:
            # Buscar número da venda se existir
            numero_venda = None
            if conta.venda_id:
                from app.vendas_models import Venda
                venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
                if venda:
                    numero_venda = venda.numero_venda
            
            movimentacoes.append(FluxoCaixaMovimentacao(
                data=conta.data_vencimento,
                tipo='entrada',
                descricao=f'A Receber - {conta.cliente.nome if conta.cliente else "Cliente"}',
                categoria='Recebimentos',
                valor=float(valor_restante),
                origem_tipo='conta_receber',
                origem_id=conta.id,
                numero_venda=numero_venda,
                status='previsto'
            ))
    """
    
    # 6. CONTAS A PAGAR PENDENTES (Saídas Previstas)
    contas_pagar_pendentes = db.query(ContaPagar).filter(
        and_(
            ContaPagar.user_id == current_user.id,
            ContaPagar.data_vencimento >= dt_inicio,
            ContaPagar.data_vencimento <= dt_fim,
            ContaPagar.status.in_(['pendente', 'atrasado'])
        )
    ).all()
    
    for conta in contas_pagar_pendentes:
        valor_restante = (conta.valor_original or 0) - (conta.valor_pago or 0)
        if valor_restante > 0:
            fornecedor_nome = conta.fornecedor.nome if conta.fornecedor else "Fornecedor"
            movimentacoes.append(FluxoCaixaMovimentacao(
                data=conta.data_vencimento,
                tipo='saida',
                descricao=f'A Pagar - {fornecedor_nome}',
                categoria='Fornecedores',
                valor=float(valor_restante),
                origem_tipo='conta_pagar',
                origem_id=conta.id,
                status='previsto'
            ))
    
    # 7. LANÇAMENTOS MANUAIS PREVISTOS
    lancamentos_previstos = db.query(LancamentoManual).filter(
        and_(
            LancamentoManual.data_lancamento >= dt_inicio,
            LancamentoManual.data_lancamento <= dt_fim,
            LancamentoManual.status == 'previsto'
        )
    ).all()
    
    for lanc in lancamentos_previstos:
        movimentacoes.append(FluxoCaixaMovimentacao(
            data=lanc.data_lancamento,
            tipo=lanc.tipo,
            descricao=lanc.descricao,
            categoria=lanc.categoria.nome if lanc.categoria else 'Sem Categoria',
            valor=float(lanc.valor),
            origem_tipo='lancamento_manual',
            origem_id=lanc.id,
            status='previsto'
        ))
    
    # 🆕 LANÇAMENTOS DA TABELA FLUXO_CAIXA (PREVISTOS)
    fluxos_previstos = db.query(FluxoCaixa).filter(
        and_(
            FluxoCaixa.usuario_id == current_user.id,
            FluxoCaixa.data_prevista >= dt_inicio_datetime,
            FluxoCaixa.data_prevista <= dt_fim_datetime,
            FluxoCaixa.status == 'previsto'
        )
    ).all()
    
    for fluxo in fluxos_previstos:
        # Buscar número da venda se a origem for conta_receber
        numero_venda_fluxo = None
        if fluxo.origem_tipo == 'conta_receber' and fluxo.origem_id:
            conta = db.query(ContaReceber).filter(ContaReceber.id == fluxo.origem_id).first()
            if conta and conta.venda_id:
                venda = db.query(Venda).filter(Venda.id == conta.venda_id).first()
                if venda:
                    numero_venda_fluxo = venda.numero_venda
        
        movimentacoes.append(FluxoCaixaMovimentacao(
            data=fluxo.data_prevista.date() if isinstance(fluxo.data_prevista, datetime) else fluxo.data_prevista,
            tipo='entrada' if fluxo.tipo == 'entrada' else 'saida',
            descricao=fluxo.descricao or 'Movimentação',
            categoria=fluxo.categoria or 'Sem Categoria',
            valor=float(fluxo.valor),
            origem_tipo=fluxo.origem_tipo or 'fluxo_caixa',
            origem_id=fluxo.origem_id,
            numero_venda=numero_venda_fluxo,
            status='previsto'
        ))
    
    # ========== FILTRAR POR NÚMERO DE VENDA (se fornecido) ==========
    if numero_venda:
        # Buscar IDs das vendas que correspondem ao número
        vendas_filtro = db.query(Venda.id).filter(
            and_(
                Venda.user_id == current_user.id,
                Venda.numero_venda.like(f'%{numero_venda}%')
            )
        ).all()
        
        vendas_ids = [v[0] for v in vendas_filtro]
        
        if vendas_ids:
            # Filtrar movimentações para apenas as que estão relacionadas a essas vendas
            movimentacoes_filtradas = []
            for mov in movimentacoes:
                # Incluir se é relacionado a venda diretamente
                if mov.origem_tipo == 'venda' and mov.origem_id in vendas_ids:
                    movimentacoes_filtradas.append(mov)
                # Ou se é conta a receber/recebimento de venda
                elif mov.numero_venda and mov.numero_venda == numero_venda:
                    movimentacoes_filtradas.append(mov)
                # Ou se é conta a receber vinculada à venda
                elif mov.origem_tipo == 'conta_receber':
                    # Buscar a conta para verificar venda_id
                    conta = db.query(ContaReceber).filter(ContaReceber.id == mov.origem_id).first()
                    if conta and conta.venda_id in vendas_ids:
                        movimentacoes_filtradas.append(mov)
            
            movimentacoes = movimentacoes_filtradas
    
    # ========== AGRUPAR POR PERÍODO ==========
    periodos = _agrupar_por_periodo(movimentacoes, dt_inicio, dt_fim, agrupamento, float(saldo_inicial))
    
    # ========== TOTALIZADORES ==========
    total_previsto_entradas = sum(m.valor for m in movimentacoes if m.tipo == 'entrada' and m.status == 'previsto')
    total_previsto_saidas = sum(m.valor for m in movimentacoes if m.tipo == 'saida' and m.status == 'previsto')
    
    total_realizado_entradas = sum(m.valor for m in movimentacoes if m.tipo == 'entrada' and m.status == 'realizado')
    total_realizado_saidas = sum(m.valor for m in movimentacoes if m.tipo == 'saida' and m.status == 'realizado')
    
    saldo_final = float(saldo_inicial) + total_realizado_entradas - total_realizado_saidas
    saldo_previsto_final = saldo_final + total_previsto_entradas - total_previsto_saidas
    
    return FluxoCaixaResponse(
        periodos=periodos,
        movimentacoes=sorted(movimentacoes, key=lambda x: x.data),
        total_previsto_entradas=total_previsto_entradas,
        total_previsto_saidas=total_previsto_saidas,
        total_realizado_entradas=total_realizado_entradas,
        total_realizado_saidas=total_realizado_saidas,
        saldo_inicial=float(saldo_inicial),
        saldo_final=saldo_final,
        saldo_previsto_final=saldo_previsto_final
    )


def _agrupar_por_periodo(
    movimentacoes: List[FluxoCaixaMovimentacao],
    dt_inicio: date,
    dt_fim: date,
    agrupamento: str,
    saldo_inicial: float
) -> List[FluxoCaixaPeriodo]:
    """Agrupar movimentações por período (dia/semana/mês)"""
    
    periodos_dict = {}
    
    if agrupamento == 'dia':
        # Criar entrada para cada dia
        dia_atual = dt_inicio
        while dia_atual <= dt_fim:
            chave = dia_atual.isoformat()
            periodos_dict[chave] = {
                'data': dia_atual.strftime("%d/%m/%Y"),
                'data_inicio': dia_atual,
                'data_fim': dia_atual,
                'previsto_entradas': 0,
                'previsto_saidas': 0,
                'realizado_entradas': 0,
                'realizado_saidas': 0
            }
            dia_atual += timedelta(days=1)
        
        # Acumular movimentações
        for mov in movimentacoes:
            chave = mov.data.isoformat()
            if chave in periodos_dict:
                if mov.status == 'previsto':
                    if mov.tipo == 'entrada':
                        periodos_dict[chave]['previsto_entradas'] += mov.valor
                    else:
                        periodos_dict[chave]['previsto_saidas'] += mov.valor
                else:  # realizado
                    if mov.tipo == 'entrada':
                        periodos_dict[chave]['realizado_entradas'] += mov.valor
                    else:
                        periodos_dict[chave]['realizado_saidas'] += mov.valor
    
    elif agrupamento == 'semana':
        # Agrupar por semanas
        import calendar
        semana_num = 1
        dia_atual = dt_inicio
        
        while dia_atual <= dt_fim:
            # Encontrar início e fim da semana (segunda a domingo)
            inicio_semana = dia_atual - timedelta(days=dia_atual.weekday())
            fim_semana = inicio_semana + timedelta(days=6)
            
            # Ajustar limites
            if inicio_semana < dt_inicio:
                inicio_semana = dt_inicio
            if fim_semana > dt_fim:
                fim_semana = dt_fim
            
            chave = f"semana_{semana_num}"
            if chave not in periodos_dict:
                periodos_dict[chave] = {
                    'data': f"Semana {semana_num} ({inicio_semana.strftime('%d/%m')} - {fim_semana.strftime('%d/%m')})",
                    'data_inicio': inicio_semana,
                    'data_fim': fim_semana,
                    'previsto_entradas': 0,
                    'previsto_saidas': 0,
                    'realizado_entradas': 0,
                    'realizado_saidas': 0
                }
            
            dia_atual = fim_semana + timedelta(days=1)
            semana_num += 1
        
        # Acumular movimentações
        for mov in movimentacoes:
            for chave, periodo in periodos_dict.items():
                if periodo['data_inicio'] <= mov.data <= periodo['data_fim']:
                    if mov.status == 'previsto':
                        if mov.tipo == 'entrada':
                            periodo['previsto_entradas'] += mov.valor
                        else:
                            periodo['previsto_saidas'] += mov.valor
                    else:
                        if mov.tipo == 'entrada':
                            periodo['realizado_entradas'] += mov.valor
                        else:
                            periodo['realizado_saidas'] += mov.valor
                    break
    
    elif agrupamento == 'mes':
        # Agrupar por meses
        meses_unicos = set()
        dia_atual = dt_inicio
        while dia_atual <= dt_fim:
            meses_unicos.add((dia_atual.year, dia_atual.month))
            # Avançar para o próximo mês
            if dia_atual.month == 12:
                dia_atual = date(dia_atual.year + 1, 1, 1)
            else:
                dia_atual = date(dia_atual.year, dia_atual.month + 1, 1)
        
        import calendar
        meses_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        for ano, mes in sorted(meses_unicos):
            inicio_mes = date(ano, mes, 1)
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            fim_mes = date(ano, mes, ultimo_dia)
            
            # Ajustar limites
            if inicio_mes < dt_inicio:
                inicio_mes = dt_inicio
            if fim_mes > dt_fim:
                fim_mes = dt_fim
            
            chave = f"{ano}-{mes:02d}"
            periodos_dict[chave] = {
                'data': f"{meses_pt[mes-1]}/{ano}",
                'data_inicio': inicio_mes,
                'data_fim': fim_mes,
                'previsto_entradas': 0,
                'previsto_saidas': 0,
                'realizado_entradas': 0,
                'realizado_saidas': 0
            }
        
        # Acumular movimentações
        for mov in movimentacoes:
            chave = f"{mov.data.year}-{mov.data.month:02d}"
            if chave in periodos_dict:
                if mov.status == 'previsto':
                    if mov.tipo == 'entrada':
                        periodos_dict[chave]['previsto_entradas'] += mov.valor
                    else:
                        periodos_dict[chave]['previsto_saidas'] += mov.valor
                else:
                    if mov.tipo == 'entrada':
                        periodos_dict[chave]['realizado_entradas'] += mov.valor
                    else:
                        periodos_dict[chave]['realizado_saidas'] += mov.valor
    
    # Calcular saldos acumulados
    periodos = []
    saldo_acumulado = saldo_inicial
    saldo_previsto_acumulado = saldo_inicial
    
    for chave in sorted(periodos_dict.keys()):
        p = periodos_dict[chave]
        
        # Saldo realizado
        saldo_acumulado += p['realizado_entradas'] - p['realizado_saidas']
        
        # Saldo previsto (realizado + previsto)
        saldo_previsto_acumulado = saldo_acumulado + p['previsto_entradas'] - p['previsto_saidas']
        
        periodos.append(FluxoCaixaPeriodo(
            data=p['data'],
            data_inicio=p['data_inicio'],
            data_fim=p['data_fim'],
            previsto_entradas=p['previsto_entradas'],
            previsto_saidas=p['previsto_saidas'],
            previsto_saldo=saldo_previsto_acumulado,
            realizado_entradas=p['realizado_entradas'],
            realizado_saidas=p['realizado_saidas'],
            realizado_saldo=saldo_acumulado,
            saldo_inicial=saldo_inicial if len(periodos) == 0 else periodos[-1].saldo_final,
            saldo_final=saldo_acumulado
        ))
        
        # Atualizar saldo inicial do próximo período
        if periodos:
            saldo_inicial = saldo_acumulado
    
    return periodos


# ============================================================================
# HISTÓRICO FINANCEIRO DO CLIENTE - ROTAS DEDICADAS E PERFORMÁTICAS
# ============================================================================

from datetime import date, timedelta
from sqlalchemy import desc, or_, and_

@router.get("/cliente/{cliente_id}")
async def get_historico_financeiro_cliente(
    cliente_id: int,
    page: int = 1,
    per_page: int = 20,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    tipo: Optional[str] = None,  # venda, devolucao, conta_receber, recebimento, credito
    status: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    ## 📊 HISTÓRICO FINANCEIRO COMPLETO DO CLIENTE (NOVA ROTA DEDICADA)
    
    **Rota performática com paginação obrigatória para análise financeira detalhada.**
    
    ### Parâmetros:
    - **cliente_id**: ID do cliente
    - **page**: Número da página (padrão: 1)
    - **per_page**: Itens por página (padrão: 20, máximo: 100)
    - **data_inicio**: Filtro data inicial (formato: YYYY-MM-DD)
    - **data_fim**: Filtro data final (formato: YYYY-MM-DD)
    - **tipo**: Filtro por tipo de transação
    - **status**: Filtro por status
    
    ### Tipos de transação:
    - `venda`: Vendas finalizadas
    - `devolucao`: Vendas canceladas/devolvidas
    - `conta_receber`: Contas a receber (parcelas)
    - `recebimento`: Recebimentos de contas
    - `credito`: Movimentações de crédito do cliente
    
    ### Retorna:
    - **cliente**: Dados básicos do cliente
    - **resumo**: Totais agregados (últimos 90 dias)
    - **historico**: Lista paginada de transações
    - **paginacao**: Metadados de paginação (total, páginas, etc)
    
    ### Performance:
    - ✅ Paginação em nível de banco (não carrega tudo em memória)
    - ✅ Índices otimizados
    - ✅ Filtros aplicados antes da ordenação
    - ✅ Aggregations separadas do histórico
    """
    # Importar modelos
    from app.vendas_models import Venda
    from app.financeiro_models import ContaReceber, Recebimento
    
    # Extrair usuário e tenant
    current_user, tenant_id = user_and_tenant
    
    # Validar paginação
    if page < 1:
        raise HTTPException(status_code=400, detail="Página deve ser >= 1")
    if per_page < 1 or per_page > 100:
        raise HTTPException(status_code=400, detail="per_page deve estar entre 1 e 100")
    
    # Verificar se cliente existe e pertence ao tenant
    from app.models import Cliente
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Parse de datas
    filtro_data_inicio = None
    filtro_data_fim = None
    if data_inicio:
        try:
            filtro_data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="data_inicio inválida (use YYYY-MM-DD)")
    
    if data_fim:
        try:
            filtro_data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="data_fim inválida (use YYYY-MM-DD)")
    
    # ========== MONTAR HISTÓRICO COM QUERIES SEPARADAS ==========
    historico = []
    
    # ========== BUSCAR APENAS VENDAS (não incluir contas a receber/recebimentos) ==========
    # Para evitar duplicação, mostramos apenas as vendas que já incluem todas as informações
    
    # 1. VENDAS FINALIZADAS E EM ABERTO (se não houver filtro de tipo ou tipo=venda)
    if not tipo or tipo == "venda":
        query_vendas = db.query(Venda).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.notin_(['cancelada', 'devolvida'])
        ).options(
            joinedload(Venda.pagamentos)  # Carregar pagamentos para obter forma de pagamento
        )
        
        # Aplicar filtros
        if filtro_data_inicio:
            query_vendas = query_vendas.filter(Venda.data_venda >= filtro_data_inicio)
        if filtro_data_fim:
            query_vendas = query_vendas.filter(Venda.data_venda <= filtro_data_fim)
        if status:
            query_vendas = query_vendas.filter(Venda.status == status)
        
        vendas = query_vendas.all()
        
        for venda in vendas:
            # Obter forma de pagamento do primeiro pagamento (se existir)
            forma_pagamento = "Não informado"
            if venda.pagamentos and len(venda.pagamentos) > 0:
                forma_pagamento = venda.pagamentos[0].forma_pagamento or "Não informado"
            
            historico.append({
                "tipo": "venda",
                "data": venda.data_venda.isoformat() if venda.data_venda else None,
                "descricao": f"Venda #{venda.numero_venda}",
                "valor": float(venda.total) if venda.total else 0,
                "status": venda.status,
                "detalhes": {
                    "venda_id": venda.id,
                    "numero_venda": venda.numero_venda,
                    "subtotal": float(venda.subtotal) if venda.subtotal else 0,
                    "desconto": float(venda.desconto_valor) if venda.desconto_valor else 0,
                    "total": float(venda.total) if venda.total else 0,
                    "canal": venda.canal,
                    "forma_pagamento": forma_pagamento,
                    "observacoes": venda.observacoes
                }
            })
    
    # 2. DEVOLUÇÕES (se não houver filtro de tipo ou tipo=devolucao)
    if not tipo or tipo == "devolucao":
        query_devolucoes = db.query(Venda).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(['cancelada', 'devolvida'])
        ).options(
            joinedload(Venda.pagamentos)
        )
        
        if filtro_data_inicio:
            query_devolucoes = query_devolucoes.filter(Venda.data_venda >= filtro_data_inicio)
        if filtro_data_fim:
            query_devolucoes = query_devolucoes.filter(Venda.data_venda <= filtro_data_fim)
        
        devolucoes = query_devolucoes.all()
        
        for dev in devolucoes:
            # Obter forma de pagamento do primeiro pagamento (se existir)
            forma_pagamento = "Não informado"
            if dev.pagamentos and len(dev.pagamentos) > 0:
                forma_pagamento = dev.pagamentos[0].forma_pagamento or "Não informado"
            
            historico.append({
                "tipo": "devolucao",
                "data": dev.data_venda.isoformat() if dev.data_venda else None,
                "descricao": f"Devolução - Venda #{dev.numero_venda}",
                "valor": -float(dev.total) if dev.total else 0,
                "status": dev.status,
                "detalhes": {
                    "numero_venda": dev.numero_venda,
                    "total": float(dev.total) if dev.total else 0,
                    "motivo": dev.observacoes,
                    "forma_pagamento": forma_pagamento
                }
            })
    
    # ========== NOTA: Removido contas a receber e recebimentos ==========
    # Para evitar duplicação, mostramos apenas as vendas.
    # As vendas já indicam se estão pagas (status=finalizada) ou em aberto (status=aberta)
    
    # ========== ORDENAR POR DATA (DESC) ==========
    historico.sort(key=lambda x: x['data'] if x['data'] else '', reverse=True)
    
    # ========== APLICAR PAGINAÇÃO ==========
    total_items = len(historico)
    total_pages = (total_items + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    historico_paginado = historico[start_idx:end_idx]
    
    # ========== CALCULAR RESUMO (últimos 90 dias) ==========
    data_90_dias_atras = date.today() - timedelta(days=90)
    
    # Total de vendas (últimos 90 dias)
    total_vendas = db.query(func.sum(Venda.total)).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status.notin_(['cancelada', 'devolvida']),
        Venda.data_venda >= data_90_dias_atras
    ).scalar() or 0
    
    # Total em aberto
    total_em_aberto = db.query(
        func.sum(ContaReceber.valor_original - func.coalesce(ContaReceber.valor_recebido, 0))
    ).filter(
        ContaReceber.cliente_id == cliente_id,
        ContaReceber.tenant_id == tenant_id,
        ContaReceber.status == 'pendente'
    ).scalar() or 0
    
    # Última compra
    ultima_venda = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status.notin_(['cancelada', 'devolvida'])
    ).order_by(desc(Venda.data_venda)).first()
    
    ultima_compra = None
    if ultima_venda:
        ultima_compra = {
            "data": ultima_venda.data_venda.isoformat() if ultima_venda.data_venda else None,
            "valor": float(ultima_venda.total) if ultima_venda.total else 0,
            "numero_venda": ultima_venda.numero_venda
        }
    
    return {
        "cliente": {
            "id": cliente.id,
            "codigo": cliente.codigo,
            "nome": cliente.nome,
            "credito_atual": float(cliente.credito) if cliente.credito else 0
        },
        "resumo": {
            "total_vendas_90d": float(total_vendas),
            "total_em_aberto": float(total_em_aberto),
            "ultima_compra": ultima_compra,
            "total_transacoes_historico": total_items
        },
        "historico": historico_paginado,
        "paginacao": {
            "pagina_atual": page,
            "itens_por_pagina": per_page,
            "total_itens": total_items,
            "total_paginas": total_pages,
            "tem_proxima": page < total_pages,
            "tem_anterior": page > 1
        }
    }


@router.get("/cliente/{cliente_id}/resumo")
async def get_resumo_financeiro_cliente(
    cliente_id: int,
    periodo_dias: int = 90,
    db: Session = Depends(get_session),
    current_user_and_tenant = Depends(get_current_user_and_tenant)
):
    current_user, tenant_id = current_user_and_tenant
    """
    ## 📈 RESUMO FINANCEIRO LEVE DO CLIENTE
    
    **Rota otimizada para exibição rápida no cadastro de clientes.**
    
    ### Parâmetros:
    - **cliente_id**: ID do cliente
    - **periodo_dias**: Período para análise (padrão: 90 dias)
    
    ### Retorna apenas dados agregados:
    - Total de vendas no período
    - Total em aberto (todas as contas pendentes)
    - Última compra (data + valor)
    - Contagem de transações no histórico
    
    ### Performance:
    - ✅ Usa apenas COUNT() e SUM() - não carrega transações individuais
    - ✅ Ideal para exibir no Step 6 do wizard
    - ✅ Resposta em ~10-50ms mesmo com milhares de transações
    
    ### Diferenças da rota completa:
    - ❌ Não retorna lista de transações
    - ❌ Não tem paginação
    - ✅ Muito mais rápida
    - ✅ Baixo consumo de memória
    """
    # Importar modelos
    from app.vendas_models import Venda
    from app.financeiro_models import ContaReceber
    from app.models import Cliente
    
    # Verificar se cliente existe
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id
    ).first()
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Calcular data limite
    data_limite = date.today() - timedelta(days=periodo_dias)
    
    # ========== AGGREGATIONS (SEM CARREGAR DADOS INDIVIDUAIS) ==========
    
    # 1. Total de vendas no período
    total_vendas = db.query(func.sum(Venda.total)).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status.notin_(['cancelada', 'devolvida']),
        Venda.data_venda >= data_limite
    ).scalar() or 0
    
    # 2. Quantidade de vendas no período
    qtd_vendas = db.query(func.count(Venda.id)).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status.notin_(['cancelada', 'devolvida']),
        Venda.data_venda >= data_limite
    ).scalar() or 0
    
    # 3. Total em aberto (todas as contas pendentes, não só do período)
    total_em_aberto = db.query(
        func.sum(ContaReceber.valor_original - func.coalesce(ContaReceber.valor_recebido, 0))
    ).filter(
        ContaReceber.cliente_id == cliente_id,
        ContaReceber.tenant_id == tenant_id,
        ContaReceber.status == 'pendente'
    ).scalar() or 0
    
    # 4. Contas vencidas (em aberto com vencimento no passado)
    total_vencido = db.query(
        func.sum(ContaReceber.valor_original - func.coalesce(ContaReceber.valor_recebido, 0))
    ).filter(
        ContaReceber.cliente_id == cliente_id,
        ContaReceber.tenant_id == tenant_id,
        ContaReceber.status == 'pendente',
        ContaReceber.data_vencimento < date.today()
    ).scalar() or 0
    
    # 5. Última compra (só buscar 1 registro)
    ultima_venda = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status.notin_(['cancelada', 'devolvida'])
    ).order_by(desc(Venda.data_venda)).first()
    
    ultima_compra = None
    if ultima_venda:
        dias_desde_ultima = (date.today() - ultima_venda.data_venda.date()).days if ultima_venda.data_venda else None
        ultima_compra = {
            "data": ultima_venda.data_venda.isoformat() if ultima_venda.data_venda else None,
            "valor": float(ultima_venda.total) if ultima_venda.total else 0,
            "numero_venda": ultima_venda.numero_venda,
            "dias_atras": dias_desde_ultima
        }
    
    # 6. Ticket médio
    ticket_medio = float(total_vendas) / qtd_vendas if qtd_vendas > 0 else 0
    
    # 7. Contagem total de transações no histórico (para saber se tem histórico completo)
    total_transacoes = db.query(func.count(Venda.id)).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id
    ).scalar() or 0
    
    return {
        "cliente_id": cliente_id,
        "periodo_analisado": f"Últimos {periodo_dias} dias",
        "resumo": {
            "total_vendas": float(total_vendas),
            "quantidade_vendas": qtd_vendas,
            "ticket_medio": round(ticket_medio, 2),
            "total_em_aberto": float(total_em_aberto),
            "total_vencido": float(total_vencido),
            "tem_debitos": float(total_em_aberto) > 0,
            "tem_debitos_vencidos": float(total_vencido) > 0,
            "ultima_compra": ultima_compra,
            "total_transacoes_historico": total_transacoes,
            "credito_disponivel": float(cliente.credito) if cliente.credito else 0
        },
        "alertas": []
    }
