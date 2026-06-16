"""
Rotas para Classificação Automática DRE
APIs de sugestão, aplicação e gestão de lançamentos pendentes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.dre_classificacao_service import ClassificadorDRE
from app.utils.logger import logger


router = APIRouter(prefix="/dre/classificar", tags=["DRE - Classificação Automática"])


# ============================================================
# SCHEMAS
# ============================================================

class SugestaoResponse(BaseModel):
    """Sugestão de classificação DRE"""
    dre_subcategoria_id: int
    subcategoria_nome: str
    confianca: int  # 0-100
    regra_id: Optional[int]
    regra_nome: str
    motivo: str
    aplicar_automaticamente: bool


class AnalisarRequest(BaseModel):
    """Request para analisar um lançamento"""
    tipo: str = Field(..., description="'pagar' ou 'receber'")
    lancamento_id: int


class AplicarClassificacaoRequest(BaseModel):
    """Request para aplicar classificação"""
    tipo: str = Field(..., description="'pagar' ou 'receber'")
    lancamento_id: int
    dre_subcategoria_id: int
    canal: Optional[str] = Field(None, description="loja_fisica, mercado_livre, shopee, amazon")
    regra_id: Optional[int] = Field(None, description="ID da regra que originou (se aplicável)")
    forma_classificacao: str = Field('manual', description="manual, automatico_regra, sugestao_aceita")


class AplicarLoteRequest(BaseModel):
    """Request para aplicar classificação em lote"""
    classificacoes: List[AplicarClassificacaoRequest]


class LancamentoPendenteResponse(BaseModel):
    """Lançamento sem classificação DRE"""
    id: int
    descricao: str
    beneficiario: Optional[str]
    valor: float
    data_vencimento: Optional[str]
    tipo_documento: Optional[str]
    nota_entrada_id: Optional[int] = None
    venda_id: Optional[int] = None


class PendentesResponse(BaseModel):
    """Response com lançamentos pendentes"""
    total_pendentes: int
    contas_pagar: List[LancamentoPendenteResponse]
    contas_receber: List[LancamentoPendenteResponse]


class ResultadoAplicacao(BaseModel):
    """Resultado da aplicação de classificação"""
    sucesso: bool
    mensagem: str
    lancamento_id: int
    tipo: str


# ============================================================
# ROTAS
# ============================================================

@router.post("/sugerir", response_model=List[SugestaoResponse])
def sugerir_classificacao(
    request: AnalisarRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    **Analisa um lançamento e retorna sugestões de classificação DRE**
    
    Retorna lista ordenada por confiança (maior primeiro).
    
    O sistema analisa:
    - Regras específicas (vendas, notas entrada)
    - Beneficiário
    - Palavras-chave na descrição
    - Tipo de documento
    - Histórico de classificações similares
    
    **Exemplo:**
    ```json
    {
        "tipo": "pagar",
        "lancamento_id": 123
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    if request.tipo not in ['pagar', 'receber']:
        raise HTTPException(
            status_code=400,
            detail="Tipo deve ser 'pagar' ou 'receber'"
        )
    
    try:
        classificador = ClassificadorDRE(db, tenant_id)
        sugestoes = classificador.analisar_lancamento(
            tipo=request.tipo,
            lancamento_id=request.lancamento_id
        )
        
        logger.info(f"📋 {len(sugestoes)} sugestões encontradas para {request.tipo} #{request.lancamento_id}")
        
        return sugestoes
        
    except Exception as e:
        logger.error(f"❌ Erro ao sugerir classificação: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao analisar lançamento: {str(e)}"
        )


@router.post("/aplicar", response_model=ResultadoAplicacao)
def aplicar_classificacao(
    request: AplicarClassificacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    **Aplica uma classificação DRE a um lançamento**
    
    - Atualiza o campo `dre_subcategoria_id` do lançamento
    - Registra no histórico para aprendizado
    - Atualiza estatísticas da regra (se aplicável)
    - Pode criar regra automática se detectar padrão (3+ ocorrências)
    
    **Formas de classificação:**
    - `manual`: Usuário escolheu manualmente
    - `sugestao_aceita`: Usuário aceitou sugestão do sistema
    - `automatico_regra`: Sistema aplicou automaticamente (regra com confiança alta)
    
    **Exemplo:**
    ```json
    {
        "tipo": "pagar",
        "lancamento_id": 123,
        "dre_subcategoria_id": 5,
        "canal": "loja_fisica",
        "regra_id": 3,
        "forma_classificacao": "sugestao_aceita"
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    if request.tipo not in ['pagar', 'receber']:
        raise HTTPException(
            status_code=400,
            detail="Tipo deve ser 'pagar' ou 'receber'"
        )
    
    try:
        classificador = ClassificadorDRE(db, tenant_id)
        
        sucesso = classificador.aplicar_classificacao(
            tipo=request.tipo,
            lancamento_id=request.lancamento_id,
            dre_subcategoria_id=request.dre_subcategoria_id,
            canal=request.canal,
            regra_id=request.regra_id,
            forma_classificacao=request.forma_classificacao,
            user_id=current_user.id
        )
        
        if sucesso:
            return ResultadoAplicacao(
                sucesso=True,
                mensagem="Classificação aplicada com sucesso",
                lancamento_id=request.lancamento_id,
                tipo=request.tipo
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível aplicar a classificação"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar classificação: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao aplicar classificação: {str(e)}"
        )


@router.post("/aplicar-lote", response_model=List[ResultadoAplicacao])
def aplicar_classificacao_lote(
    request: AplicarLoteRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    **Aplica classificação DRE em múltiplos lançamentos de uma vez**
    
    Útil para:
    - Classificar histórico em massa
    - Aplicar regras em lote
    - Aceitar múltiplas sugestões de uma vez
    
    Retorna lista de resultados (sucesso/erro) para cada lançamento.
    
    **Exemplo:**
    ```json
    {
        "classificacoes": [
            {
                "tipo": "pagar",
                "lancamento_id": 123,
                "dre_subcategoria_id": 5,
                "forma_classificacao": "sugestao_aceita"
            },
            {
                "tipo": "pagar",
                "lancamento_id": 124,
                "dre_subcategoria_id": 5,
                "forma_classificacao": "manual"
            }
        ]
    }
    ```
    """
    current_user, tenant_id = user_and_tenant
    
    classificador = ClassificadorDRE(db, tenant_id)
    resultados = []
    
    for item in request.classificacoes:
        try:
            sucesso = classificador.aplicar_classificacao(
                tipo=item.tipo,
                lancamento_id=item.lancamento_id,
                dre_subcategoria_id=item.dre_subcategoria_id,
                canal=item.canal,
                regra_id=item.regra_id,
                forma_classificacao=item.forma_classificacao,
                user_id=current_user.id
            )
            
            resultados.append(ResultadoAplicacao(
                sucesso=sucesso,
                mensagem="Classificação aplicada" if sucesso else "Erro ao aplicar",
                lancamento_id=item.lancamento_id,
                tipo=item.tipo
            ))
            
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar classificação lote #{item.lancamento_id}: {e}")
            resultados.append(ResultadoAplicacao(
                sucesso=False,
                mensagem=f"Erro: {str(e)}",
                lancamento_id=item.lancamento_id,
                tipo=item.tipo
            ))
    
    logger.info(f"📦 Lote aplicado: {sum(1 for r in resultados if r.sucesso)}/{len(resultados)} sucessos")
    
    return resultados


@router.get("/pendentes", response_model=PendentesResponse)
def listar_pendentes(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: 'pagar', 'receber' ou None (ambos)"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de resultados"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    **Lista lançamentos sem classificação DRE**
    
    Retorna todos os lançamentos (contas a pagar/receber) que ainda não possuem
    `dre_subcategoria_id`, ou seja, não foram classificados contabilmente.
    
    **Parâmetros:**
    - `tipo`: Filtrar por 'pagar', 'receber' ou None (retorna ambos)
    - `limit`: Quantidade máxima de resultados (padrão: 100, máx: 1000)
    
    **Use Case:**
    Interface "Classificar Pendentes" que mostra todos lançamentos aguardando classificação,
    permitindo classificação em lote.
    """
    current_user, tenant_id = user_and_tenant
    
    if tipo and tipo not in ['pagar', 'receber']:
        raise HTTPException(
            status_code=400,
            detail="Tipo deve ser 'pagar', 'receber' ou None"
        )
    
    try:
        classificador = ClassificadorDRE(db, tenant_id)
        pendentes = classificador.listar_pendentes(tipo=tipo, limit=limit)
        
        logger.info(f"📋 Lançamentos pendentes: {pendentes['total_pendentes']} encontrados")
        
        return PendentesResponse(**pendentes)
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar pendentes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar pendentes: {str(e)}"
        )


@router.post("/auto-classificar-pendentes")
def auto_classificar_pendentes(
    tipo: Optional[str] = Query(None, description="'pagar', 'receber' ou None (ambos)"),
    apenas_alta_confianca: bool = Query(True, description="Aplicar apenas sugestões com confiança >= 90%"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    **Aplica classificação automática em todos os lançamentos pendentes**
    
    - Busca todos lançamentos sem classificação
    - Para cada um, busca sugestões
    - Aplica automaticamente se confiança >= 90% (ou conforme parâmetro)
    
    **CUIDADO:** Esta operação pode classificar muitos lançamentos de uma vez.
    
    **Retorna:**
    - Total processado
    - Total classificado automaticamente
    - Total ignorado (baixa confiança)
    """
    current_user, tenant_id = user_and_tenant
    
    classificador = ClassificadorDRE(db, tenant_id)
    
    # Buscar pendentes
    pendentes = classificador.listar_pendentes(tipo=tipo, limit=1000)
    
    total_processado = 0
    total_classificado = 0
    total_ignorado = 0
    
    # Processar contas a pagar
    for cp in pendentes['contas_pagar']:
        total_processado += 1
        
        sugestoes = classificador.analisar_lancamento('pagar', cp['id'])
        
        if sugestoes:
            melhor = sugestoes[0]  # Já vem ordenado por confiança
            
            threshold = 90 if apenas_alta_confianca else 70
            
            if melhor['confianca'] >= threshold and melhor['aplicar_automaticamente']:
                sucesso = classificador.aplicar_classificacao(
                    tipo='pagar',
                    lancamento_id=cp['id'],
                    dre_subcategoria_id=melhor['dre_subcategoria_id'],
                    regra_id=melhor['regra_id'],
                    forma_classificacao='automatico_regra',
                    user_id=current_user.id
                )
                
                if sucesso:
                    total_classificado += 1
                else:
                    total_ignorado += 1
            else:
                total_ignorado += 1
        else:
            total_ignorado += 1
    
    # Processar contas a receber
    for cr in pendentes['contas_receber']:
        total_processado += 1
        
        sugestoes = classificador.analisar_lancamento('receber', cr['id'])
        
        if sugestoes:
            melhor = sugestoes[0]
            
            threshold = 90 if apenas_alta_confianca else 70
            
            if melhor['confianca'] >= threshold and melhor['aplicar_automaticamente']:
                sucesso = classificador.aplicar_classificacao(
                    tipo='receber',
                    lancamento_id=cr['id'],
                    dre_subcategoria_id=melhor['dre_subcategoria_id'],
                    regra_id=melhor['regra_id'],
                    forma_classificacao='automatico_regra',
                    user_id=current_user.id
                )
                
                if sucesso:
                    total_classificado += 1
                else:
                    total_ignorado += 1
            else:
                total_ignorado += 1
        else:
            total_ignorado += 1
    
    logger.info(f"🤖 Auto-classificação: {total_classificado}/{total_processado} lançamentos")
    
    return {
        "total_processado": total_processado,
        "total_classificado": total_classificado,
        "total_ignorado": total_ignorado,
        "threshold_confianca": 90 if apenas_alta_confianca else 70,
        "mensagem": f"Classificação automática concluída. {total_classificado} lançamentos classificados com sucesso."
    }
