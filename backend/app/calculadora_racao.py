"""
API para Calculadora de Ração - FASE 2
Calcula duração, custo/dia, custo/kg e compara produtos
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
import logging

from .db import get_session
from .auth import get_current_user, get_current_user_and_tenant
from .models import User
from .produtos_models import Produto

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/produtos", tags=["calculadora-racao"])


# ==================== SCHEMAS ====================

class CalculadoraRacaoRequest(BaseModel):
    """Request para calcular duração de ração"""
    produto_id: Optional[int] = None  # ID do produto (ração)
    peso_embalagem_kg: Optional[float] = None  # Se não tiver produto_id, passar manualmente
    preco: Optional[float] = None  # Preço manual
    
    # Dados do pet
    peso_pet_kg: float  # Peso do pet em kg
    idade_meses: Optional[int] = None  # Idade em meses (para ajustar quantidade)
    nivel_atividade: str = "normal"  # baixo, normal, alto
    
    # Opcional: usar tabela da embalagem ou quantidade personalizada
    quantidade_diaria_g: Optional[float] = None  # Se já souber a quantidade, passar aqui


class ResultadoCalculoRacao(BaseModel):
    """Resultado do cálculo"""
    # Dados do produto
    produto_id: Optional[int] = None
    produto_nome: Optional[str] = None
    classificacao: Optional[str] = None
    categoria_racao: Optional[str] = None  # filhote, adulto, senior
    peso_embalagem_kg: float
    preco: float
    
    # Resultados do cálculo
    quantidade_diaria_g: float  # Gramas por dia
    duracao_dias: float  # Quantos dias vai durar
    duracao_meses: float  # Quantos meses vai durar
    custo_por_kg: float  # R$ por kg
    custo_por_dia: float  # R$ por dia
    custo_mensal: float  # R$ por mês
    
    # Meta-info
    pet_peso_kg: float
    pet_nivel_atividade: str


class ComparativoRacoesResponse(BaseModel):
    """Comparativo entre múltiplas rações"""
    racoes: List[ResultadoCalculoRacao]
    melhor_custo_beneficio: Optional[int] = None  # produto_id
    maior_duracao: Optional[int] = None  # produto_id
    menor_custo_diario: Optional[int] = None  # produto_id


# ==================== FUNÇÕES AUXILIARES ====================

def calcular_quantidade_diaria(
    peso_pet_kg: float, 
    idade_meses: Optional[int], 
    nivel_atividade: str,
    tabela_consumo_json: Optional[str] = None
) -> float:
    """
    Calcula quantidade diária de ração.
    
    Ordem de prioridade:
    1. Usar tabela_consumo do produto (dados da embalagem)
    2. Fallback para fórmula genérica
    
    Args:
        peso_pet_kg: Peso do pet em kg
        idade_meses: Idade em meses (para filhotes)
        nivel_atividade: baixo, normal, alto
        tabela_consumo_json: JSON com tabela de consumo da embalagem
    
    Returns:
        Quantidade diária em gramas
    """
    # PRIORIDADE 1: Usar tabela da embalagem se disponível
    if tabela_consumo_json:
        try:
            logger.info(f"🔍 DEBUG: Processando tabela_consumo...")
            tabela = json.loads(tabela_consumo_json)
            logger.info(f"🔍 DEBUG: Tabela parseada: {tabela}")
            
            # Novo formato: {"tipo": "filhote_peso_adulto", "dados": {"5kg": {"4m": 125, "6m": 130}}}
            if "tipo" in tabela and "dados" in tabela:
                tipo_tabela = tabela["tipo"]
                dados = tabela["dados"]
                logger.info(f"🔍 DEBUG: Tipo={tipo_tabela}, Dados keys={list(dados.keys())}")
                
                # Encontrar peso mais próximo
                pesos_disponiveis = []
                for peso_str in dados.keys():
                    # Remover 'kg' e converter para float
                    peso_num = float(peso_str.replace('kg', '').replace('g', '').strip())
                    pesos_disponiveis.append(peso_num)
                
                logger.info(f"🔍 DEBUG: Pesos disponíveis na tabela: {pesos_disponiveis}")
                
                if not pesos_disponiveis:
                    raise ValueError("Nenhum peso encontrado na tabela")
                
                # Peso mais próximo
                peso_tabela = min(pesos_disponiveis, key=lambda x: abs(x - peso_pet_kg))
                
                # Buscar a chave correspondente ao peso (pode ser "5", "5kg", "5.0", etc)
                peso_key = None
                for k in dados.keys():
                    peso_k = float(k.replace('kg', '').replace('g', '').strip())
                    if peso_k == peso_tabela:
                        peso_key = k
                        break
                
                if not peso_key:
                    raise ValueError(f"Chave não encontrada para peso {peso_tabela}kg")
                
                logger.info(f"🔍 DEBUG: Pet {peso_pet_kg}kg -> Usando linha da tabela: {peso_key} ({peso_tabela}kg)")
                
                consumos = dados[peso_key]
                logger.info(f"🔍 DEBUG: Consumos disponíveis: {consumos}")
                
                quantidade = 0  # Inicializar
                
                # Para filhote: buscar pela idade (até 18 meses inclusive)
                if tipo_tabela == "filhote_peso_adulto" and idade_meses and idade_meses <= 18:
                    logger.info(f"🔍 DEBUG: Modo FILHOTE - idade {idade_meses}m")
                    # Buscar coluna de idade mais próxima
                    idade_key = f"{idade_meses}m"
                    if idade_key in consumos:
                        quantidade = consumos[idade_key]
                        logger.info(f"🔍 DEBUG: Encontrou idade exata {idade_key}: {quantidade}g")
                    else:
                        # Buscar idade mais próxima
                        idades_disponiveis = [int(k.replace('m', '')) for k in consumos.keys() if k != 'adulto' and 'm' in k]
                        if idades_disponiveis:
                            idade_proxima = min(idades_disponiveis, key=lambda x: abs(x - idade_meses))
                            quantidade = consumos[f"{idade_proxima}m"]
                            logger.info(f"🔍 DEBUG: Idade {idade_meses}m não encontrada. Usando {idade_proxima}m: {quantidade}g")
                        else:
                            # Fallback para adulto
                            quantidade = consumos.get('adulto', 0)
                            logger.info(f"🔍 DEBUG: Sem idades, usando adulto: {quantidade}g")
                
                # Para adulto: usar coluna 'adulto' ou primeira disponível
                else:
                    logger.info(f"🔍 DEBUG: Modo ADULTO")
                    quantidade = consumos.get('adulto', list(consumos.values())[0] if consumos else 0)
                    logger.info(f"🔍 DEBUG: Quantidade adulto: {quantidade}g")
                
                if quantidade and quantidade > 0:
                    logger.info(f"📊 Usando tabela da embalagem ({tipo_tabela}): {quantidade}g/dia para {peso_pet_kg}kg, idade {idade_meses}m")
                    
                    # Ajustar por nível de atividade
                    ajuste_antes = quantidade
                    if nivel_atividade == "alto":
                        quantidade *= 1.1  # +10%
                    elif nivel_atividade == "baixo":
                        quantidade *= 0.9  # -10%
                    
                    logger.info(f"🔍 DEBUG: Ajuste atividade {nivel_atividade}: {ajuste_antes}g -> {quantidade}g")
                    
                    return round(quantidade, 2)
                else:
                    logger.warning(f"⚠️ Quantidade não encontrada ou zero na tabela")
            
            # Formato antigo (compatibilidade)
            else:
                # Determinar a chave baseada na idade
                if idade_meses and idade_meses < 12:
                    # Filhote - tentar encontrar faixa etária mais próxima
                    chave = f"filhote_{idade_meses}m"
                    if chave not in tabela:
                        # Buscar a faixa mais próxima
                        faixas_filhote = [k for k in tabela.keys() if k.startswith('filhote_')]
                        if faixas_filhote:
                            chave = faixas_filhote[0]  # Usar primeira disponível
                        else:
                            chave = "peso_adulto"
                else:
                    chave = "peso_adulto"
                
                if chave in tabela:
                    # Encontrar peso mais próximo na tabela
                    pesos = sorted([float(p) for p in tabela[chave].keys()])
                    peso_tabela = min(pesos, key=lambda x: abs(x - peso_pet_kg))
                    quantidade = tabela[chave][str(int(peso_tabela))]
                    
                    logger.info(f"📊 Usando tabela da embalagem (formato antigo): {quantidade}g/dia para {peso_pet_kg}kg")
                    
                    # Ajustar por nível de atividade (pequeno ajuste)
                    if nivel_atividade == "alto":
                        quantidade *= 1.1  # +10%
                    elif nivel_atividade == "baixo":
                        quantidade *= 0.9  # -10%
                    
                    return round(quantidade, 2)
                    
        except Exception as e:
            logger.warning(f"⚠️ Erro ao ler tabela_consumo: {e}. Usando cálculo genérico.")
    
    # FALLBACK: Fórmula genérica (2.5% do peso corporal)
    quantidade_base = peso_pet_kg * 1000 * 0.025
    
    if idade_meses and idade_meses < 12:
        quantidade_base *= 1.5  # Filhotes
    elif idade_meses and idade_meses > 84:
        quantidade_base *= 0.9  # Idosos
    
    if nivel_atividade == "alto":
        quantidade_base *= 1.2
    elif nivel_atividade == "baixo":
        quantidade_base *= 0.8
    
    return round(quantidade_base, 2)


def calcular_resultado(
    peso_embalagem_kg: float,
    preco: float,
    quantidade_diaria_g: float,
    produto_id: Optional[int] = None,
    produto_nome: Optional[str] = None,
    classificacao: Optional[str] = None,
    categoria_racao: Optional[str] = None,
    peso_pet_kg: float = 0,
    nivel_atividade: str = "normal"
) -> ResultadoCalculoRacao:
    """Calcula todos os valores"""
    peso_embalagem_g = peso_embalagem_kg * 1000
    
    duracao_dias = peso_embalagem_g / quantidade_diaria_g
    duracao_meses = duracao_dias / 30
    custo_por_kg = preco / peso_embalagem_kg
    custo_por_dia = (preco / peso_embalagem_g) * quantidade_diaria_g
    custo_mensal = custo_por_dia * 30
    
    return ResultadoCalculoRacao(
        produto_id=produto_id,
        produto_nome=produto_nome,
        classificacao=classificacao,
        categoria_racao=categoria_racao,
        peso_embalagem_kg=peso_embalagem_kg,
        preco=preco,
        quantidade_diaria_g=quantidade_diaria_g,
        duracao_dias=round(duracao_dias, 1),
        duracao_meses=round(duracao_meses, 1),
        custo_por_kg=round(custo_por_kg, 2),
        custo_por_dia=round(custo_por_dia, 2),
        custo_mensal=round(custo_mensal, 2),
        pet_peso_kg=peso_pet_kg,
        pet_nivel_atividade=nivel_atividade
    )


# ==================== ENDPOINTS ====================

@router.post("/calculadora-racao", response_model=ResultadoCalculoRacao)
async def calcular_racao(
    req: CalculadoraRacaoRequest,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Calcula duração e custo de uma ração
    
    Exemplos:
    - Passar produto_id: busca dados do produto
    - Passar peso_embalagem_kg + preco: calcula manualmente
    - Passar quantidade_diaria_g: usa valor fornecido
    - Se não passar quantidade_diaria_g: calcula automaticamente
    """
    current_user, tenant_id = user_and_tenant
    
    try:
        # 1. Buscar dados do produto (se fornecido)
        produto = None
        peso_embalagem_kg = req.peso_embalagem_kg
        preco = req.preco
        produto_nome = None
        classificacao = None
        categoria_racao = None
        
        if req.produto_id:
            produto = db.query(Produto).filter(
                Produto.id == req.produto_id,
                Produto.tenant_id == tenant_id
            ).first()
            
            if not produto:
                raise HTTPException(status_code=404, detail="Produto não encontrado")
            
            peso_embalagem_kg = produto.peso_embalagem
            preco = produto.preco_venda
            produto_nome = produto.nome
            classificacao = produto.classificacao_racao
            categoria_racao = produto.categoria_racao
            
            logger.info(f"🔍 Produto {req.produto_id}: categoria={categoria_racao}, tabela_consumo length={len(produto.tabela_consumo or '')}")
            
            if not peso_embalagem_kg:
                raise HTTPException(status_code=400, detail="Produto não tem peso_embalagem cadastrado")
        
        # 2. Validações
        if not peso_embalagem_kg or not preco:
            raise HTTPException(status_code=400, detail="peso_embalagem_kg e preco são obrigatórios")
        
        # 3. Calcular quantidade diária
        quantidade_diaria_g = req.quantidade_diaria_g
        if not quantidade_diaria_g:
            # Passar tabela_consumo do produto se disponível
            tabela_consumo = produto.tabela_consumo if produto else None
            logger.info(f"📊 Calculando para pet {req.peso_pet_kg}kg, idade {req.idade_meses}m, atividade {req.nivel_atividade}")
            if tabela_consumo:
                logger.info(f"📋 Tabela consumo: {tabela_consumo[:200]}...")
            quantidade_diaria_g = calcular_quantidade_diaria(
                peso_pet_kg=req.peso_pet_kg,
                idade_meses=req.idade_meses,
                nivel_atividade=req.nivel_atividade,
                tabela_consumo_json=tabela_consumo
            )
            logger.info(f"✅ Quantidade calculada: {quantidade_diaria_g}g/dia")
        
        # 4. Calcular resultado
        resultado = calcular_resultado(
            peso_embalagem_kg=peso_embalagem_kg,
            preco=preco,
            quantidade_diaria_g=quantidade_diaria_g,
            produto_id=req.produto_id,
            produto_nome=produto_nome,
            classificacao=classificacao,
            categoria_racao=categoria_racao,
            peso_pet_kg=req.peso_pet_kg,
            nivel_atividade=req.nivel_atividade
        )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao calcular ração: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/comparar-racoes", response_model=ComparativoRacoesResponse)
async def comparar_racoes(
    peso_pet_kg: float = Query(..., description="Peso do pet em kg"),
    idade_meses: Optional[int] = Query(None, description="Idade do pet em meses"),
    nivel_atividade: str = Query("normal", description="baixo, normal, alto"),
    classificacao: Optional[str] = Query(None, description="Filtrar por classificação"),
    especies: Optional[str] = Query(None, description="dog, cat, both"),
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Compara todas as rações cadastradas e retorna ordenadas por custo-benefício
    """
    current_user, tenant_id = user_and_tenant
    
    try:
        # Buscar produtos que são rações
        query = db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.peso_embalagem.isnot(None),
            Produto.peso_embalagem > 0
        )
        
        # Filtros opcionais
        if classificacao:
            query = query.filter(Produto.classificacao_racao == classificacao)
        if especies:
            query = query.filter(Produto.especies_indicadas.in_([especies, 'both']))
        
        produtos = query.all()
        
        if not produtos:
            raise HTTPException(status_code=404, detail="Nenhuma ração encontrada com os filtros")
        
        # Calcular para cada produto
        resultados = []
        quantidade_diaria_g = calcular_quantidade_diaria(peso_pet_kg, idade_meses, nivel_atividade)
        
        for produto in produtos:
            resultado = calcular_resultado(
                peso_embalagem_kg=produto.peso_embalagem,
                preco=produto.preco_venda,
                quantidade_diaria_g=quantidade_diaria_g,
                produto_id=produto.id,
                produto_nome=produto.nome,
                classificacao=produto.classificacao_racao,
                peso_pet_kg=peso_pet_kg,
                nivel_atividade=nivel_atividade
            )
            resultados.append(resultado)
        
        # Ordenar por custo-benefício (menor custo diário)
        resultados.sort(key=lambda x: x.custo_por_dia)
        
        # Identificar melhores
        melhor_custo_beneficio = resultados[0].produto_id if resultados else None
        maior_duracao = max(resultados, key=lambda x: x.duracao_dias).produto_id if resultados else None
        menor_custo_diario = min(resultados, key=lambda x: x.custo_por_dia).produto_id if resultados else None
        
        return ComparativoRacoesResponse(
            racoes=resultados,
            melhor_custo_beneficio=melhor_custo_beneficio,
            maior_duracao=maior_duracao,
            menor_custo_diario=menor_custo_diario
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao comparar rações: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
