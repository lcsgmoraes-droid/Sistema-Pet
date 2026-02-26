"""
API Routes - Conciliação Bancária
Upload OFX, classificação automática, regras de aprendizado
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.exc import NoReferencedTableError
from typing import List, Optional, Dict
from datetime import datetime, date
from decimal import Decimal
import uuid
import json

from app.db import get_session as get_db
from app.models import User
from app.auth import get_current_user
from .financeiro_models import (
    ContaBancaria, ContaPagar, ContaReceber,
    ExtratoBancario, MovimentacaoBancaria, RegraConciliacao,
    ProvisaoAutomatica, TemplateAdquirente
)
from .parsers.ofx_parser import OFXParser, validar_extrato
from pydantic import BaseModel


router = APIRouter(prefix="/conciliacao", tags=["Conciliação Bancária"])


def ensure_regras_conciliacao_table_exists(db: Session) -> None:
    """Cria tabela de regras automaticamente em ambientes sem migrations."""
    try:
        # Garante metadados de tabelas referenciadas por FKs conhecidas.
        from app import models  # noqa: F401
        from app import financeiro_models  # noqa: F401
        RegraConciliacao.__table__.create(bind=db.get_bind(), checkfirst=True)
    except (NoReferencedTableError, ImportError):
        # Fallback legado: cria sem FKs para evitar erro 500.
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS regras_conciliacao (
                id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                tenant_id UUID NOT NULL,
                padrao_memo VARCHAR(255),
                tipo_operacao VARCHAR(50),
                descricao VARCHAR(255),
                fornecedor_id INTEGER NULL,
                categoria_dre_id INTEGER NULL,
                centro_custo_id INTEGER NULL,
                vezes_aplicada INTEGER NOT NULL DEFAULT 0,
                vezes_confirmada INTEGER NOT NULL DEFAULT 0,
                confianca INTEGER NULL,
                prioridade INTEGER NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
            );
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_regras_conciliacao_tenant_id ON regras_conciliacao (tenant_id);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_regras_conciliacao_ativo ON regras_conciliacao (ativo);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_regras_conciliacao_confianca ON regras_conciliacao (confianca);"))
        db.commit()


# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class UploadOFXResponse(BaseModel):
    extrato_id: str
    total_transacoes: int
    periodo_inicio: Optional[str]
    periodo_fim: Optional[str]
    pendentes: int
    status: str


class MovimentacaoResponse(BaseModel):
    id: int
    data_movimento: Optional[str]
    valor: float
    tipo: str
    memo: Optional[str]
    status_conciliacao: str
    confianca_sugestao: Optional[int]
    tipo_vinculo: Optional[str]
    fornecedor_nome: Optional[str]
    conta_pagar_id: Optional[int]
    conta_receber_id: Optional[int]
    regra_aplicada_id: Optional[int]


class ClassificarMovimentacaoRequest(BaseModel):
    tipo_vinculo: str  # 'fornecedor', 'transferencia', 'taxa', 'recebimento'
    fornecedor_id: Optional[int] = None
    conta_pagar_id: Optional[int] = None
    conta_receber_id: Optional[int] = None
    categoria_dre_id: Optional[int] = None
    criar_conta_pagar: bool = False
    criar_regra: bool = True
    recorrente: bool = False
    periodicidade: Optional[str] = None


class RegraResponse(BaseModel):
    id: int
    padrao_memo: str
    tipo_operacao: Optional[str]
    descricao: Optional[str]
    fornecedor_nome: Optional[str]
    vezes_aplicada: int
    vezes_confirmada: int
    confianca: Optional[int]
    ativa: bool


class TemplateResponse(BaseModel):
    id: int
    nome_adquirente: str
    tipo_relatorio: str
    auto_aplicar: bool
    vezes_usado: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/upload-ofx", response_model=UploadOFXResponse)
async def upload_ofx(
    arquivo: UploadFile = File(...),
    conta_bancaria_id: int = Query(..., description="ID da conta bancária"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload e parse de arquivo OFX
    - Extrai todas as transações
    - Aplica regras automáticas
    - Sugere classificações
    """
    
    ensure_regras_conciliacao_table_exists(db)

    # Valida conta bancária
    conta = db.query(ContaBancaria).filter(
        and_(
            ContaBancaria.id == conta_bancaria_id,
            ContaBancaria.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not conta:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada")
    
    # Lê arquivo
    conteudo = await arquivo.read()
    conteudo_str = conteudo.decode('utf-8', errors='ignore')
    
    # Parse OFX
    try:
        extrato_ofx = OFXParser.parse(conteudo_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar OFX: {str(e)}")
    
    # Valida
    validacao = validar_extrato(extrato_ofx)
    if not validacao['valido']:
        raise HTTPException(status_code=400, detail=f"OFX inválido: {validacao['erros']}")
    
    # Cria registro de extrato
    extrato = ExtratoBancario(
        tenant_id=current_user.tenant_id,
        conta_bancaria_id=conta_bancaria_id,
        arquivo_nome=arquivo.filename,
        data_upload=datetime.utcnow(),
        periodo_inicio=extrato_ofx.data_inicio,
        periodo_fim=extrato_ofx.data_fim,
        total_movimentacoes=len(extrato_ofx.transacoes),
        pendentes=len(extrato_ofx.transacoes),
        conciliadas=0,
        status='processando'
    )
    db.add(extrato)
    db.flush()  # Garante que o ID seja gerado
    
    # Carrega regras ativas
    regras = db.query(RegraConciliacao).filter(
        and_(
            RegraConciliacao.tenant_id == current_user.tenant_id,
            RegraConciliacao.ativo == True
        )
    ).all()
    
    # Processa cada transação
    movimentacoes_criadas = 0
    for transacao in extrato_ofx.transacoes:
        # Verifica se já existe (pelo FITID)
        existe = db.query(MovimentacaoBancaria).filter(
            and_(
                MovimentacaoBancaria.tenant_id == current_user.tenant_id,
                MovimentacaoBancaria.conta_bancaria_id == conta_bancaria_id,
                MovimentacaoBancaria.fitid == transacao.fitid
            )
        ).first()
        
        if existe:
            continue  # Pula duplicatas
        
        # Cria movimentação
        movimentacao = MovimentacaoBancaria(
            tenant_id=current_user.tenant_id,
            extrato_id=extrato.id,  # Usa o ID gerado pelo banco
            conta_bancaria_id=conta_bancaria_id,
            fitid=transacao.fitid,
            data_movimento=transacao.data_movimento,
            valor=transacao.valor,
            tipo=transacao.tipo,
            memo=transacao.memo,
            status_conciliacao='pendente',
            confianca_sugestao=0
        )
        
        # Aplica regras automáticas
        melhor_regra = None
        melhor_confianca = 0
        
        for regra in regras:
            # Verifica padrão MEMO
            if regra.padrao_memo and transacao.memo:
                padrao = regra.padrao_memo.replace('%', '.*')
                import re
                if re.search(padrao, transacao.memo, re.IGNORECASE):
                    confianca = regra.confianca or 0
                    if confianca > melhor_confianca:
                        melhor_confianca = confianca
                        melhor_regra = regra
            
            # Verifica range de valor
            if regra.valor_min and regra.valor_max:
                if regra.valor_min <= abs(transacao.valor) <= regra.valor_max:
                    confianca = (regra.confianca or 0) * 0.7  # Peso menor
                    if confianca > melhor_confianca:
                        melhor_confianca = confianca
                        melhor_regra = regra
        
        # Aplica sugestão
        if melhor_regra:
            movimentacao.confianca_sugestao = int(melhor_confianca)
            movimentacao.regra_aplicada_id = melhor_regra.id
            movimentacao.tipo_vinculo = melhor_regra.tipo_vinculo
            movimentacao.fornecedor_id = melhor_regra.fornecedor_id
            movimentacao.categoria_dre_id = melhor_regra.categoria_dre_id
            movimentacao.recorrente = melhor_regra.recorrente
            movimentacao.periodicidade = melhor_regra.periodicidade
            
            # Auto-aplicar se confiança > 80%
            if melhor_confianca >= 80:
                movimentacao.status_conciliacao = 'conciliado'
                extrato.conciliadas += 1
                extrato.pendentes -= 1
                
                # Atualiza estatísticas da regra
                melhor_regra.vezes_aplicada += 1
                melhor_regra.vezes_confirmada += 1  # Auto-confirmada
                melhor_regra.confianca = int((melhor_regra.vezes_confirmada / melhor_regra.vezes_aplicada) * 100)
            else:
                movimentacao.status_conciliacao = 'sugerido'
                melhor_regra.vezes_aplicada += 1
        
        db.add(movimentacao)
        movimentacoes_criadas += 1
    
    extrato.status = 'concluido'
    db.commit()
    
    return UploadOFXResponse(
        extrato_id=str(extrato.id),  # Converte ID gerado para string na resposta
        total_transacoes=movimentacoes_criadas,
        periodo_inicio=extrato_ofx.data_inicio.isoformat() if extrato_ofx.data_inicio else None,
        periodo_fim=extrato_ofx.data_fim.isoformat() if extrato_ofx.data_fim else None,
        pendentes=extrato.pendentes,
        status=extrato.status
    )


@router.get("/movimentacoes", response_model=List[MovimentacaoResponse])
async def listar_movimentacoes(
    conta_bancaria_id: Optional[int] = None,
    status: Optional[str] = Query(None, description="pendente, sugerido, conciliado"),
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    ocultar_conciliadas: bool = Query(True, description="Ocultar já conciliadas"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista movimentações bancárias com filtros"""
    
    query = db.query(MovimentacaoBancaria).filter(
        MovimentacaoBancaria.tenant_id == current_user.tenant_id
    )
    
    if conta_bancaria_id:
        query = query.filter(MovimentacaoBancaria.conta_bancaria_id == conta_bancaria_id)
    
    if status:
        query = query.filter(MovimentacaoBancaria.status_conciliacao == status)
    
    if ocultar_conciliadas:
        query = query.filter(MovimentacaoBancaria.status_conciliacao != 'conciliado')
    
    if data_inicio:
        query = query.filter(MovimentacaoBancaria.data_movimento >= data_inicio)
    
    if data_fim:
        query = query.filter(MovimentacaoBancaria.data_movimento <= data_fim)
    
    query = query.order_by(desc(MovimentacaoBancaria.data_movimento))
    movimentacoes = query.offset(offset).limit(limit).all()
    
    # Busca nomes de fornecedores
    resultado = []
    for mov in movimentacoes:
        fornecedor_nome = None
        if mov.fornecedor_id:
            from .models import Cliente
            fornecedor = db.query(Cliente).filter(Cliente.id == mov.fornecedor_id).first()
            if fornecedor:
                fornecedor_nome = fornecedor.nome
        
        resultado.append(MovimentacaoResponse(
            id=mov.id,
            data_movimento=mov.data_movimento.isoformat() if mov.data_movimento else None,
            valor=float(mov.valor) if mov.valor else 0.0,
            tipo=mov.tipo or '',
            memo=mov.memo,
            status_conciliacao=mov.status_conciliacao or 'pendente',
            confianca_sugestao=mov.confianca_sugestao,
            tipo_vinculo=mov.tipo_vinculo,
            fornecedor_nome=fornecedor_nome,
            conta_pagar_id=mov.conta_pagar_id,
            conta_receber_id=mov.conta_receber_id,
            regra_aplicada_id=mov.regra_aplicada_id
        ))
    
    return resultado


@router.post("/movimentacoes/{movimentacao_id}/classificar")
async def classificar_movimentacao(
    movimentacao_id: int,
    dados: ClassificarMovimentacaoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Classifica uma movimentação manualmente
    - Aprende com a decisão
    - Cria/atualiza regra se solicitado
    - APENAS vincula, NÃO cria contas automaticamente (evitar duplicação)
    """
    
    ensure_regras_conciliacao_table_exists(db)

    # Busca movimentação
    mov = db.query(MovimentacaoBancaria).filter(
        and_(
            MovimentacaoBancaria.id == movimentacao_id,
            MovimentacaoBancaria.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not mov:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")
    
    # Atualiza classificação
    mov.tipo_vinculo = dados.tipo_vinculo
    mov.fornecedor_id = dados.fornecedor_id
    mov.conta_pagar_id = dados.conta_pagar_id
    mov.conta_receber_id = dados.conta_receber_id
    mov.categoria_dre_id = dados.categoria_dre_id
    mov.recorrente = dados.recorrente
    mov.periodicidade = dados.periodicidade
    mov.status_conciliacao = 'conciliado'
    mov.classificado_por = current_user.id
    mov.classificado_em = datetime.utcnow()
    
    # Atualiza extrato
    if mov.extrato_id:
        extrato = db.query(ExtratoBancario).filter(ExtratoBancario.id == mov.extrato_id).first()
        if extrato:
            extrato.conciliadas += 1
            extrato.pendentes -= 1
    
    # Confirma regra aplicada
    if mov.regra_aplicada_id:
        regra = db.query(RegraConciliacao).filter(RegraConciliacao.id == mov.regra_aplicada_id).first()
        if regra:
            regra.vezes_confirmada += 1
            regra.confianca = int((regra.vezes_confirmada / regra.vezes_aplicada) * 100)
    
    # Cria nova regra se solicitado
    if dados.criar_regra and mov.memo:
        # Extrai padrão chave do memo
        palavras = mov.memo.split()
        palavra_chave = palavras[0] if palavras else mov.memo[:20]
        padrao = f"%{palavra_chave}%"
        
        # Verifica se já existe regra similar
        regra_existente = db.query(RegraConciliacao).filter(
            and_(
                RegraConciliacao.tenant_id == current_user.tenant_id,
                RegraConciliacao.padrao_memo == padrao
            )
        ).first()
        
        if not regra_existente:
            nova_regra = RegraConciliacao(
                tenant_id=current_user.tenant_id,
                padrao_memo=padrao,
                tipo_operacao=mov.tipo,
                tipo_vinculo=dados.tipo_vinculo,
                fornecedor_id=dados.fornecedor_id,
                categoria_dre_id=dados.categoria_dre_id,
                recorrente=dados.recorrente,
                periodicidade=dados.periodicidade,
                criar_conta_pagar=dados.criar_conta_pagar,
                vezes_aplicada=1,
                vezes_confirmada=1,
                confianca=100,
                ativa=True
            )
            db.add(nova_regra)
            db.flush()  # Garante que o ID seja gerado antes de usar
            mov.regra_aplicada_id = nova_regra.id
    
    db.commit()
    
    return {"success": True, "message": "Movimentação classificada com sucesso"}



@router.get("/regras", response_model=List[RegraResponse])
async def listar_regras(
    ativas_apenas: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista regras de conciliação"""
    ensure_regras_conciliacao_table_exists(db)
    
    query = db.query(RegraConciliacao).filter(
        RegraConciliacao.tenant_id == current_user.tenant_id
    )
    
    if ativas_apenas:
        query = query.filter(RegraConciliacao.ativo == True)
    
    query = query.order_by(desc(RegraConciliacao.confianca))
    regras = query.all()
    
    resultado = []
    for regra in regras:
        fornecedor_nome = None
        if regra.fornecedor_id:
            from .models import Cliente
            fornecedor = db.query(Cliente).filter(Cliente.id == regra.fornecedor_id).first()
            if fornecedor:
                fornecedor_nome = fornecedor.nome
        
        resultado.append(RegraResponse(
            id=regra.id,
            padrao_memo=regra.padrao_memo or '',
            tipo_operacao=regra.tipo_operacao,
            descricao=regra.descricao,
            fornecedor_nome=fornecedor_nome,
            vezes_aplicada=regra.vezes_aplicada or 0,
            vezes_confirmada=regra.vezes_confirmada or 0,
            confianca=regra.confianca,
            ativa=regra.ativo or False
        ))
    
    return resultado


@router.delete("/regras/{regra_id}")
async def deletar_regra(
    regra_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Desativa uma regra"""
    ensure_regras_conciliacao_table_exists(db)
    
    regra = db.query(RegraConciliacao).filter(
        and_(
            RegraConciliacao.id == regra_id,
            RegraConciliacao.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not regra:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    
    regra.ativo = False
    db.commit()
    
    return {"success": True}


@router.get("/templates", response_model=List[TemplateResponse])
async def listar_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista templates de adquirentes disponíveis"""
    
    templates = db.query(TemplateAdquirente).filter(
        TemplateAdquirente.tenant_id == current_user.tenant_id
    ).all()
    
    return [
        TemplateResponse(
            id=t.id,
            nome_adquirente=t.nome_adquirente or '',
            tipo_relatorio=t.tipo_relatorio or '',
            auto_aplicar=t.auto_aplicar or False,
            vezes_usado=t.vezes_usado or 0
        )
        for t in templates
    ]


@router.get("/estatisticas")
async def obter_estatisticas(
    conta_bancaria_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Estatísticas da conciliação"""
    ensure_regras_conciliacao_table_exists(db)
    
    query = db.query(MovimentacaoBancaria).filter(
        MovimentacaoBancaria.tenant_id == current_user.tenant_id
    )
    
    if conta_bancaria_id:
        query = query.filter(MovimentacaoBancaria.conta_bancaria_id == conta_bancaria_id)
    
    total = query.count()
    pendentes = query.filter(MovimentacaoBancaria.status_conciliacao == 'pendente').count()
    sugeridas = query.filter(MovimentacaoBancaria.status_conciliacao == 'sugerido').count()
    conciliadas = query.filter(MovimentacaoBancaria.status_conciliacao == 'conciliado').count()
    
    # Taxa de automação
    regras_ativas = db.query(RegraConciliacao).filter(
        and_(
            RegraConciliacao.tenant_id == current_user.tenant_id,
            RegraConciliacao.ativo == True
        )
    ).count()
    
    return {
        'total_movimentacoes': total,
        'pendentes': pendentes,
        'sugeridas': sugeridas,
        'conciliadas': conciliadas,
        'percentual_conciliado': round((conciliadas / total * 100) if total > 0 else 0, 1),
        'regras_ativas': regras_ativas,
        'taxa_automacao': round((conciliadas / total * 100) if total > 0 else 0, 1)
    }
