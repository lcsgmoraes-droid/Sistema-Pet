# -*- coding: utf-8 -*-
"""
Endpoints FastAPI - ABA 7: Extrato Bancário com IA
Referência: ENDPOINTS_FASTAPI_ABA_5_6_7_8.md
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.auth import get_current_user_and_tenant, get_current_user
from app.db import get_session as get_db
from app.ia.extrato_service import ServicoImportacaoExtrato
from app.ia.extrato_ia import MotorCategorizacaoIA
from app.ia.aba7_extrato_models import PadraoCategoriacaoIA, ArquivoExtratoImportado


router = APIRouter(prefix="/api/ia/extrato", tags=["ABA 7 - Extrato Bancário IA"])


# ===== SCHEMAS =====

class ResultadoImportacao(BaseModel):
    arquivo_id: int
    total_transacoes: int
    categorizadas_automaticamente: int
    necessitam_revisao: int
    duplicadas_ignoradas: int
    tempo_processamento: float


class LancamentoPendente(BaseModel):
    id: int
    data: str
    descricao: str
    valor: float
    tipo: str
    beneficiario: Optional[str]
    tipo_transacao: Optional[str]
    categoria_sugerida: dict
    confianca: float
    alternativas: list
    linkado_com: dict


class ValidacaoRequest(BaseModel):
    lancamento_id: int
    aprovado: bool
    categoria_correta_id: Optional[int] = None


class ValidacaoLoteRequest(BaseModel):
    lancamento_ids: List[int]
    aprovar: bool = True


class PadraoIA(BaseModel):
    id: int
    tipo_transacao: Optional[str]
    beneficiario_pattern: Optional[str]
    cnpj_cpf: Optional[str]
    categoria_nome: str
    tipo_lancamento: str
    confianca_atual: float
    total_aplicacoes: int
    total_acertos: int
    total_erros: int
    ativo: bool
    frequencia: Optional[str]
    valor_medio: Optional[float]


class EstatisticasIA(BaseModel):
    total_padroes: int
    padroes_ativos: int
    total_lancamentos: int
    aprovados: int
    pendentes: int
    confianca_media: float
    taxa_acerto_global: float


class HistoricoImportacao(BaseModel):
    id: int
    nome_arquivo: str
    banco: Optional[str]
    data_upload: str
    total_transacoes: int
    categorizadas: int
    precisam_revisao: int
    tempo_processamento: Optional[float]
    status: str


# ===== ENDPOINTS =====

@router.post("/upload", response_model=ResultadoImportacao)
async def upload_extrato(
    arquivo: UploadFile = File(...),
    conta_bancaria_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Upload de extrato bancário.
    Suporta: Excel (XLS/XLSX), CSV, PDF (OCR), OFX.
    
    Processa automaticamente:
    - Detecção de formato e banco
    - Extração NLP (CNPJ, CPF, tipo transação)
    - Categorização com IA
    - Linkagem automática com contas a pagar/receber
    """
    current_user, tenant_id = user_and_tenant
    try:
        # Ler arquivo
        conteudo = await arquivo.read()
        
        if len(conteudo) == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio")
        
        if len(conteudo) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="Arquivo muito grande (máx 10MB)")
        
        # Processar
        servico = ServicoImportacaoExtrato(db)
        resultado = servico.importar_extrato(
            arquivo=conteudo,
            nome_arquivo=arquivo.filename,
            tenant_id=tenant_id,
            conta_bancaria_id=conta_bancaria_id
        )
        
        return resultado
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")


@router.get("/pendentes", response_model=List[LancamentoPendente])
def listar_pendentes(
    limite: int = 50,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Lista lançamentos importados que necessitam validação.
    Ordena por menor confiança primeiro (prioriza dúvidas).
    """
    current_user, tenant_id = user_and_tenant
    servico = ServicoImportacaoExtrato(db)
    lancamentos = servico.listar_lancamentos_pendentes(
        tenant_id=tenant_id,
        limite=limite
    )
    return lancamentos


@router.post("/validar")
def validar_lancamento(
    request: ValidacaoRequest,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Valida um lançamento (aprova ou corrige).
    
    - Se aprovado=True: incrementa acertos do padrão
    - Se aprovado=False + categoria_correta_id: aprende novo padrão
    """
    current_user, tenant_id = user_and_tenant
    try:
        ia = MotorCategorizacaoIA(db)
        ia.validar_categorizacao(
            lancamento_id=request.lancamento_id,
            aprovado=request.aprovado,
            categoria_correta_id=request.categoria_correta_id
        )
        return {"success": True, "message": "Validação registrada"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validar-lote")
def validar_lote(
    request: ValidacaoLoteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Valida múltiplos lançamentos de uma vez.
    Útil para aprovar todas sugestões com alta confiança.
    """
    try:
        servico = ServicoImportacaoExtrato(db)
        servico.validar_lote(
            lancamento_ids=request.lancamento_ids,
            user_id=current_user.id,
            aprovar=request.aprovar
        )
        return {
            "success": True,
            "message": f"{len(request.lancamento_ids)} lançamentos validados"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/padroes", response_model=List[PadraoIA])
def listar_padroes(
    apenas_ativos: bool = True,
    ordenar_por: str = "confianca",  # confianca, aplicacoes, nome
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Lista padrões de categorização aprendidos pela IA.
    Permite gerenciar (editar, desativar) padrões.
    """
    current_user, tenant_id = user_and_tenant
    query = db.query(PadraoCategoriacaoIA)
    
    if apenas_ativos:
        query = query.filter(PadraoCategoriacaoIA.ativo == True)
    
    # Ordenação
    if ordenar_por == "confianca":
        query = query.order_by(PadraoCategoriacaoIA.confianca_atual.desc())
    elif ordenar_por == "aplicacoes":
        query = query.order_by(PadraoCategoriacaoIA.total_aplicacoes.desc())
    else:
        query = query.order_by(PadraoCategoriacaoIA.categoria_nome)
    
    padroes = query.all()
    
    return [
        PadraoIA(
            id=p.id,
            tipo_transacao=p.tipo_transacao,
            beneficiario_pattern=p.beneficiario_pattern,
            cnpj_cpf=p.cnpj_cpf,
            categoria_nome=p.categoria_nome,
            tipo_lancamento=p.tipo_lancamento,
            confianca_atual=p.confianca_atual,
            total_aplicacoes=p.total_aplicacoes,
            total_acertos=p.total_acertos,
            total_erros=p.total_erros,
            ativo=p.ativo,
            frequencia=p.frequencia,
            valor_medio=float(p.valor_medio) if p.valor_medio else None
        )
        for p in padroes
    ]


@router.patch("/padroes/{padrao_id}/ativar")
def ativar_desativar_padrao(
    padrao_id: int,
    ativar: bool = True,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Ativa ou desativa um padrão de categorização.
    """
    current_user, tenant_id = user_and_tenant
    padrao = db.query(PadraoCategoriacaoIA).filter_by(id=padrao_id).first()
    
    if not padrao:
        raise HTTPException(status_code=404, detail="Padrão não encontrado")
    
    padrao.ativo = ativar
    db.commit()
    
    return {
        "success": True,
        "message": f"Padrão {'ativado' if ativar else 'desativado'}"
    }


@router.delete("/padroes/{padrao_id}")
def deletar_padrao(
    padrao_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Deleta um padrão de categorização.
    """
    current_user, tenant_id = user_and_tenant
    padrao = db.query(PadraoCategoriacaoIA).filter_by(id=padrao_id).first()
    
    if not padrao:
        raise HTTPException(status_code=404, detail="Padrão não encontrado")
    
    db.delete(padrao)
    db.commit()
    
    return {"success": True, "message": "Padrão deletado"}


@router.get("/estatisticas", response_model=EstatisticasIA)
def obter_estatisticas(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Estatísticas do sistema de IA.
    Mostra efetividade do aprendizado.
    """
    current_user, tenant_id = user_and_tenant
    ia = MotorCategorizacaoIA(db)
    stats = ia.obter_estatisticas()
    return EstatisticasIA(**stats)


@router.get("/historico", response_model=List[HistoricoImportacao])
def listar_historico(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Histórico de arquivos importados.
    """
    current_user, tenant_id = user_and_tenant
    servico = ServicoImportacaoExtrato(db)
    historico = servico.obter_historico_importacoes(tenant_id=tenant_id)
    return historico


@router.post("/lancamentos/{lancamento_id}/criar-manual")
def criar_lancamento_manual(
    lancamento_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Cria lançamento manual a partir de importado validado.
    Integra com módulo financeiro.
    """
    current_user, tenant_id = user_and_tenant
    try:
        servico = ServicoImportacaoExtrato(db)
        lancamento_manual_id = servico.criar_lancamento_financeiro(
            lancamento_importado_id=lancamento_id
        )
        return {
            "success": True,
            "lancamento_manual_id": lancamento_manual_id,
            "message": "Lançamento criado no módulo financeiro"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/teste-parser")
async def testar_parser(
    formato: str = "demo",
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Endpoint de teste para verificar parsers.
    Retorna exemplo de como o parser funciona.
    """
    current_user, tenant_id = user_and_tenant
    from app.ia.extrato_parser import ExtratoParser
    
    parser = ExtratoParser()
    
    exemplo = {
        "formatos_suportados": ["excel", "csv", "pdf", "ofx"],
        "bancos_detectados": list(parser.BANCOS_CONHECIDOS.keys()),
        "exemplo_uso": {
            "1": "Upload arquivo via POST /upload",
            "2": "Sistema detecta formato automaticamente",
            "3": "Extrai transações (data, descrição, valor)",
            "4": "NLP extrai CNPJ, CPF, beneficiário",
            "5": "IA categoriza automaticamente",
            "6": "Retorna lista para validação humana"
        }
    }
    
    return exemplo
