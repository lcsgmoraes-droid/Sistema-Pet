# -*- coding: utf-8 -*-
"""
Rotas de Machine Learning para Rações
Sistema de feedback, aprendizado e previsão de demanda

Versão: 1.0.0 (2026-02-14)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import json

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .produtos_models import Produto, Marca
from .vendas_models import VendaItem, Venda

router = APIRouter(prefix="/racoes/ml", tags=["Machine Learning - Rações"])


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


# ============================================================================
# SCHEMAS
# ============================================================================

class FeedbackClassificacao(BaseModel):
    """Feedback de correção manual"""
    produto_id: int
    campo: str  # "porte_animal", "fase_publico", "sabor_proteina", etc
    valor_ia: Optional[str] = None  # Valor sugerido pela IA
    valor_correto: str  # Valor correto fornecido pelo usuário
    nome_produto: str
    razao_correcao: Optional[str] = None


class PadraoAprendido(BaseModel):
    """Padrão aprendido com feedbacks"""
    campo: str
    padrao: str  # Regex ou palavra-chave
    valor: str
    frequencia: int
    confianca: float
    exemplos: List[str]


class PrevisaoDemanda(BaseModel):
    """Previsão de demanda por segmento"""
    segmento_tipo: str
    segmento_valor: str
    demanda_media_mensal: float
    tendencia: str  # "crescente", "estável", "decrescente"
    percentual_tendencia: float
    projecao_proximo_mes: float
    recomendacao: str


# ============================================================================
# FUNÇÕES DO SISTEMA DE FEEDBACK
# ============================================================================

# Armazenar feedbacks em arquivo JSON (simples para MVP)
# Em produção, usar tabela no banco de dados
import os
from pathlib import Path

FEEDBACK_FILE = Path("data/feedback_classificacao.json")

def carregar_feedbacks():
    """Carrega feedbacks do arquivo"""
    if not FEEDBACK_FILE.exists():
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        return []
    
    try:
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def salvar_feedbacks(feedbacks):
    """Salva feedbacks no arquivo"""
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)


def extrair_palavras_chave(texto: str) -> List[str]:
    """Extrai palavras-chave de um texto"""
    import re
    # Remover caracteres especiais e números
    texto_limpo = re.sub(r'[^a-záàâãéèêíïóôõöúçñ\s]', '', texto.lower())
    # Dividir em palavras
    palavras = texto_limpo.split()
    # Filtrar palavras com mais de 3 caracteres
    return [p for p in palavras if len(p) > 3]


# ============================================================================
# ENDPOINTS - FEEDBACK E APRENDIZADO
# ============================================================================

@router.post("/feedback")
async def registrar_feedback(
    feedback: FeedbackClassificacao,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Registra feedback de correção manual do usuário
    
    Quando usuário corrige classificação automática:
    1. Salvar a correção
    2. Extrair padrões do nome do produto
    3. Incrementar confiança em padrões similares
    
    Uso:
    - Ao editar produto e corrigir campo classificado
    - Ao aplicar sugestão de padronização
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(
        Produto.id == feedback.produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(404, "Produto não encontrado")
    
    # Carregar feedbacks existentes
    feedbacks = carregar_feedbacks()
    
    # Adicionar novo feedback
    novo_feedback = {
        "timestamp": datetime.now().isoformat(),
        "tenant_id": tenant_id,
        "usuario_id": usuario.get('id'),
        "produto_id": feedback.produto_id,
        "campo": feedback.campo,
        "valor_ia": feedback.valor_ia,
        "valor_correto": feedback.valor_correto,
        "nome_produto": feedback.nome_produto,
        "razao_correcao": feedback.razao_correcao
    }
    
    feedbacks.append(novo_feedback)
    
    # Salvar
    salvar_feedbacks(feedbacks)
    
    # Extrair padrões do nome
    palavras_chave = extrair_palavras_chave(feedback.nome_produto)
    
    # Retornar confirmação
    return {
        "success": True,
        "mensagem": "Feedback registrado com sucesso",
        "feedback_id": len(feedbacks),
        "padroes_extraidos": palavras_chave[:5]  # Top 5 palavras
    }


@router.get("/padroes-aprendidos", response_model=List[PadraoAprendido])
async def obter_padroes_aprendidos(
    campo: Optional[str] = Query(None, description="Filtrar por campo"),
    min_frequencia: int = Query(3, ge=1, description="Frequência mínima"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna padrões aprendidos com feedbacks dos usuários
    
    Analisa correções e identifica:
    - Palavras-chave frequentes para cada valor
    - Padrões comuns em nomes corrigidos
    - Confiança baseada em frequência
    
    Útil para:
    - Debug do sistema de classificação
    - Melhorar algoritmo de IA
    - Adicionar novos padrões ao classificador
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Carregar feedbacks
    feedbacks = carregar_feedbacks()
    
    # Filtrar por tenant
    feedbacks_tenant = [f for f in feedbacks if f.get('tenant_id') == tenant_id]
    
    # Filtrar por campo se especificado
    if campo:
        feedbacks_tenant = [f for f in feedbacks_tenant if f.get('campo') == campo]
    
    # Agrupar por campo e valor
    padroes_dict = {}
    
    for feedback in feedbacks_tenant:
        campo_fb = feedback.get('campo')
        valor = feedback.get('valor_correto')
        nome = feedback.get('nome_produto', '')
        
        chave = f"{campo_fb}:{valor}"
        
        if chave not in padroes_dict:
            padroes_dict[chave] = {
                "campo": campo_fb,
                "valor": valor,
                "palavras": {},
                "exemplos": []
            }
        
        # Adicionar exemplo
        if nome not in padroes_dict[chave]["exemplos"]:
            padroes_dict[chave]["exemplos"].append(nome)
        
        # Contar palavras-chave
        palavras = extrair_palavras_chave(nome)
        for palavra in palavras:
            if palavra not in padroes_dict[chave]["palavras"]:
                padroes_dict[chave]["palavras"][palavra] = 0
            padroes_dict[chave]["palavras"][palavra] += 1
    
    # Montar resposta
    padroes_aprendidos = []
    
    for chave, dados in padroes_dict.items():
        # Ordenar palavras por frequência
        palavras_sorted = sorted(
            dados["palavras"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Pegar top 3 palavras mais frequentes
        for palavra, freq in palavras_sorted[:3]:
            if freq >= min_frequencia:
                # Calcular confiança (0-1)
                confianca = min(freq / 10, 1.0)
                
                padroes_aprendidos.append(PadraoAprendido(
                    campo=dados["campo"],
                    padrao=f"\\b{palavra}\\b",  # Regex word boundary
                    valor=dados["valor"],
                    frequencia=freq,
                    confianca=round(confianca, 2),
                    exemplos=dados["exemplos"][:3]
                ))
    
    # Ordenar por frequência decrescente
    padroes_aprendidos.sort(key=lambda x: x.frequencia, reverse=True)
    
    return padroes_aprendidos


@router.post("/aplicar-padroes-aprendidos")
async def aplicar_padroes_aprendidos(
    min_confianca: float = Query(0.7, ge=0.5, le=1.0),
    dry_run: bool = Query(True, description="Simulação sem aplicar mudanças"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Aplica padrões aprendidos ao classificador
    
    ATENÇÃO: Modifica arquivo classificador_racao.py!
    
    Recomendado:
    - Executar com dry_run=True primeiro
    - Revisar padrões sugeridos
    - Backup do código antes de aplicar
    """
    
    # Obter padrões
    padroes = await obter_padroes_aprendidos(
        campo=None,
        min_frequencia=5,
        usuario=usuario,
        db=db
    )
    
    # Filtrar por confiança
    padroes_confiaveis = [p for p in padroes if p.confianca >= min_confianca]
    
    if dry_run:
        return {
            "dry_run": True,
            "total_padroes": len(padroes_confiaveis),
            "padroes_sugeridos": [
                {
                    "campo": p.campo,
                    "padrao": p.padrao,
                    "valor": p.valor,
                    "confianca": p.confianca,
                    "frequencia": p.frequencia
                }
                for p in padroes_confiaveis[:20]
            ],
            "mensagem": "Simulação completa. Use dry_run=False para aplicar."
        }
    
    # TODO: Implementar lógica de modificação do classificador
    # Requer cuidado para não quebrar código existente
    
    return {
        "success": False,
        "mensagem": "Funcionalidade em desenvolvimento. Adicione padrões manualmente por segurança."
    }


# ============================================================================
# ENDPOINTS - PREVISÃO DE DEMANDA
# ============================================================================

@router.get("/previsao-demanda", response_model=List[PrevisaoDemanda])
async def prever_demanda(
    tipo_segmento: str = Query("porte", description="porte, fase, sabor"),
    meses_historico: int = Query(6, ge=3, le=24, description="Meses de histórico para análise"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Prevê demanda futura por segmento baseado em histórico
    
    Análise:
    - Vendas mensais dos últimos X meses
    - Tendência (crescente, estável, decrescente)
    - Sazonalidade
    - Projeção para próximo mês
    
    Útil para:
    - Planejamento de compras
    - Gestão de estoque
    - Identificar segmentos em crescimento
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Mapear tipo de segmento para campo
    campo_map = {
        "porte": "porte_animal",
        "fase": "fase_publico",
        "sabor": "sabor_proteina"
    }
    
    if tipo_segmento not in campo_map:
        raise HTTPException(400, "Tipo de segmento inválido")
    
    campo_nome = campo_map[tipo_segmento]
    
    # Data limite
    data_limite = datetime.now() - timedelta(days=meses_historico * 30)
    
    # Buscar produtos
    produtos = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.tipo == 'ração',
        Produto.ativo == True
    ).all()
    
    # Agrupar produtos por segmento
    segmentos_dict = {}
    
    for produto in produtos:
        valor_campo = getattr(produto, campo_nome)
        
        if isinstance(valor_campo, list):
            segmentos = valor_campo
        else:
            segmentos = [valor_campo] if valor_campo else []
        
        for segmento in segmentos:
            if not segmento:
                continue
            
            if segmento not in segmentos_dict:
                segmentos_dict[segmento] = []
            
            segmentos_dict[segmento].append(produto.id)
    
    # Analisar vendas por segmento
    previsoes = []
    
    for segmento, produto_ids in segmentos_dict.items():
        # Buscar vendas mensais
        vendas_mensais = db.execute(
            text("""
                SELECT 
                    DATE_TRUNC('month', v.data_venda) as mes,
                    SUM(vi.quantidade) as quantidade_total
                FROM vendas v
                INNER JOIN venda_itens vi ON vi.venda_id = v.id
                WHERE v.tenant_id = :tenant_id
                    AND vi.produto_id = ANY(:produto_ids)
                    AND v.data_venda >= :data_limite
                    AND v.status != 'cancelada'
                GROUP BY DATE_TRUNC('month', v.data_venda)
                ORDER BY mes ASC
            """),
            {
                "tenant_id": tenant_id,
                "produto_ids": produto_ids,
                "data_limite": data_limite
            }
        ).fetchall()
        
        if len(vendas_mensais) < 2:
            continue  # Dados insuficientes
        
        # Calcular média mensal
        quantidades = [float(v[1]) for v in vendas_mensais]
        demanda_media = sum(quantidades) / len(quantidades)
        
        # Calcular tendência (comparar primeira e segunda metade)
        meio = len(quantidades) // 2
        primeira_metade = sum(quantidades[:meio]) / meio
        segunda_metade = sum(quantidades[meio:]) / (len(quantidades) - meio)
        
        if segunda_metade > primeira_metade * 1.1:
            tendencia = "crescente"
            percentual = ((segunda_metade - primeira_metade) / primeira_metade) * 100
        elif segunda_metade < primeira_metade * 0.9:
            tendencia = "decrescente"
            percentual = ((primeira_metade - segunda_metade) / primeira_metade) * 100
        else:
            tendencia = "estável"
            percentual = 0
        
        # Projeção simples (média dos últimos 3 meses)
        ultimos_3 = quantidades[-3:] if len(quantidades) >= 3 else quantidades
        projecao = sum(ultimos_3) / len(ultimos_3)
        
        # Recomendação
        if tendencia == "crescente":
            recomendacao = f"📈 Segmento em crescimento! Aumentar estoque em {int(percentual)}%"
        elif tendencia == "decrescente":
            recomendacao = f"📉 Segmento em queda. Reduzir compras ou fazer promoções."
        else:
            recomendacao = "➡️ Segmento estável. Manter níveis atuais de estoque."
        
        previsoes.append(PrevisaoDemanda(
            segmento_tipo=tipo_segmento,
            segmento_valor=segmento,
            demanda_media_mensal=round(demanda_media, 2),
            tendencia=tendencia,
            percentual_tendencia=round(abs(percentual), 2),
            projecao_proximo_mes=round(projecao, 2),
            recomendacao=recomendacao
        ))
    
    # Ordenar por demanda média decrescente
    previsoes.sort(key=lambda x: x.demanda_media_mensal, reverse=True)
    
    return previsoes


@router.get("/estatisticas-ml")
async def obter_estatisticas_ml(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Estatísticas do sistema de Machine Learning
    
    Retorna:
    - Total de feedbacks registrados
    - Padrões aprendidos
    - Acurácia das previsões (futuro)
    - Melhorias sugeridas
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Carregar feedbacks
    feedbacks = carregar_feedbacks()
    feedbacks_tenant = [f for f in feedbacks if f.get('tenant_id') == tenant_id]
    
    # Contar por campo
    campos_dict = {}
    for fb in feedbacks_tenant:
        campo = fb.get('campo', 'Desconhecido')
        if campo not in campos_dict:
            campos_dict[campo] = 0
        campos_dict[campo] += 1
    
    # Obter padrões aprendidos
    padroes = await obter_padroes_aprendidos(
        campo=None,
        min_frequencia=2,
        usuario=usuario,
        db=db
    )
    
    return {
        "total_feedbacks": len(feedbacks_tenant),
        "feedbacks_por_campo": campos_dict,
        "total_padroes_aprendidos": len(padroes),
        "padroes_alta_confianca": len([p for p in padroes if p.confianca >= 0.8]),
        "ultimo_feedback": feedbacks_tenant[-1] if feedbacks_tenant else None,
        "status": "ativo" if len(feedbacks_tenant) > 0 else "aguardando_dados",
        "mensagem": f"Sistema aprendendo com {len(feedbacks_tenant)} correções"
    }
