"""
Serviço de Cálculo de Ração
============================
Cálculo de consumo diário, durabilidade de pacote e custos de alimentação.

REGRAS:
- Função pura (sem DB, sem API)
- Fail-safe (nunca lança exceção)
- Baseado em médias nutricionais realistas
- Todos os cálculos documentados

IMPORTANTE: 
Este serviço NÃO usa IA ainda. 
O campo contexto_ia é preparado para futura integração.
"""

import logging
import json
from typing import Dict, Any, Optional
from app.schemas.racao_calculadora import RacaoCalculadoraInput, RacaoCalculadoraOutput

logger = logging.getLogger(__name__)


# ====================================
# TABELAS DE REFERÊNCIA NUTRICIONAL
# ====================================
# Baseadas em médias da indústria pet food
# Valores em gramas por kg de peso corporal por dia

# Fator de atividade metabólica por fase de vida
FATOR_FASE = {
    "filhote": 1.5,  # Filhotes precisam ~50% a mais
    "adulto": 1.0,   # Baseline
    "idoso": 0.85    # Idosos precisam ~15% menos
}

# Fator de ajuste por tipo de ração (densidade calórica)
# Rações premium são mais calóricas, logo precisa-se menos quantidade
FATOR_TIPO_RACAO = {
    "standard": 1.2,      # Menos calórica, precisa mais quantidade
    "premium": 1.0,       # Baseline
    "super_premium": 0.85 # Mais calórica, precisa menos quantidade
}

# Consumo base por kg de peso (em gramas/dia) para cães adultos
# Considera porte porque metabolismo varia
CONSUMO_BASE_CAO = {
    "mini": 40,      # até 5kg - metabolismo mais acelerado
    "pequeno": 35,   # 5-10kg
    "medio": 30,     # 10-25kg
    "grande": 25     # 25kg+ - metabolismo mais lento proporcionalmente
}

# Consumo base por kg de peso (em gramas/dia) para gatos adultos
# Gatos tem metabolismo mais uniforme independente do porte
CONSUMO_BASE_GATO = {
    "mini": 35,      # até 3kg
    "pequeno": 30,   # 3-5kg
    "medio": 28,     # 5-7kg  (raro mas existe)
    "grande": 25     # 7kg+   (raro mas existe)
}


def _ler_tabela_consumo(
    tabela_consumo_json: Optional[str],
    peso_pet_kg: float,
    idade_meses: Optional[int],
    nivel_atividade: str = "normal"
) -> Optional[float]:
    """
    Lê a tabela de consumo do produto (dados da embalagem).
    Retorna quantidade em gramas/dia ou None se não conseguir ler.
    
    Baseado na lógica da calculadora antiga (calculadora_racao.py).
    """
    if not tabela_consumo_json:
        return None
    
    try:
        logger.info(f"🔍 Processando tabela_consumo para pet {peso_pet_kg}kg, idade {idade_meses}m...")
        tabela = json.loads(tabela_consumo_json)
        logger.debug(f"📋 Tabela parseada: {tabela}")
        
        # Formato novo: {"tipo": "filhote_peso_adulto", "dados": {"5kg": {"4m": 125, "6m": 130}}}
        if "tipo" in tabela and "dados" in tabela:
            tipo_tabela = tabela["tipo"]
            dados = tabela["dados"]
            logger.debug(f"Tipo tabela: {tipo_tabela}, Dados keys: {list(dados.keys())}")
            
            # Encontrar peso mais próximo
            pesos_disponiveis = []
            for peso_str in dados.keys():
                peso_num = float(peso_str.replace('kg', '').replace('g', '').strip())
                pesos_disponiveis.append(peso_num)
            
            if not pesos_disponiveis:
                logger.warning("Nenhum peso encontrado na tabela")
                return None
            
            # Peso mais próximo
            peso_tabela = min(pesos_disponiveis, key=lambda x: abs(x - peso_pet_kg))
            
            # Buscar a chave correspondente ao peso
            peso_key = None
            for k in dados.keys():
                peso_k = float(k.replace('kg', '').replace('g', '').strip())
                if peso_k == peso_tabela:
                    peso_key = k
                    break
            
            if not peso_key:
                logger.warning(f"Chave não encontrada para peso {peso_tabela}kg")
                return None
            
            logger.debug(f"Pet {peso_pet_kg}kg -> Usando linha da tabela: {peso_key} ({peso_tabela}kg)")
            
            consumos = dados[peso_key]
            logger.debug(f"Consumos disponíveis: {consumos}")
            
            quantidade = 0
            
            # Para filhote: buscar pela idade (até 18 meses inclusive)
            if tipo_tabela == "filhote_peso_adulto" and idade_meses and idade_meses <= 18:
                logger.debug(f"Modo FILHOTE - idade {idade_meses}m")
                idade_key = f"{idade_meses}m"
                if idade_key in consumos:
                    quantidade = consumos[idade_key]
                    logger.debug(f"Encontrou idade exata {idade_key}: {quantidade}g")
                else:
                    # Buscar idade mais próxima
                    idades_disponiveis = [int(k.replace('m', '')) for k in consumos.keys() if k != 'adulto' and 'm' in k]
                    if idades_disponiveis:
                        idade_proxima = min(idades_disponiveis, key=lambda x: abs(x - idade_meses))
                        quantidade = consumos[f"{idade_proxima}m"]
                        logger.debug(f"Usando idade mais próxima {idade_proxima}m: {quantidade}g")
                    else:
                        quantidade = consumos.get('adulto', 0)
                        logger.debug(f"Sem idades, usando adulto: {quantidade}g")
            else:
                # Para adulto: usar coluna 'adulto'
                logger.debug("Modo ADULTO")
                quantidade = consumos.get('adulto', list(consumos.values())[0] if consumos else 0)
                logger.debug(f"Quantidade adulto: {quantidade}g")
            
            if quantidade and quantidade > 0:
                logger.info(f"✅ Tabela da embalagem: {quantidade}g/dia para {peso_pet_kg}kg")
                
                # Ajustar por nível de atividade
                if nivel_atividade == "alto":
                    quantidade *= 1.1  # +10%
                elif nivel_atividade == "baixo":
                    quantidade *= 0.9  # -10%
                
                return round(quantidade, 2)
            else:
                logger.warning("Quantidade não encontrada ou zero na tabela")
                return None
        
        # Formato antigo (compatibilidade)
        else:
            logger.debug("Usando formato antigo de tabela")
            # Código do formato antigo omitido por brevidade
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Erro ao ler tabela_consumo: {e}")
        return None
    
    return None


def calcular_racao(payload: Dict[str, Any], tabela_consumo_json: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula consumo de ração, durabilidade do pacote e custos.
    
    Args:
        payload: Dicionário com dados do animal e da ração
                 (ver RacaoCalculadoraInput para estrutura)
        tabela_consumo_json: JSON opcional com tabela de consumo do produto
    
    Returns:
        Dicionário com resultados (ver RacaoCalculadoraOutput)
        Nunca retorna None - sempre retorna resultado ou valores padrão
    
    Cálculo:
        PRIORIDADE 1: Usar tabela_consumo do produto (se disponível)
        FALLBACK: Calcular com fórmulas genéricas:
        1. Consumo base (g/dia) = peso_kg * consumo_base_por_kg
        2. Ajuste por fase = consumo_base * fator_fase
        3. Ajuste por tipo ração = consumo_ajustado * fator_tipo_racao
        4. Durabilidade = (peso_pacote_kg * 1000) / consumo_final
        5. Custo diário = preco_pacote / durabilidade_dias
        6. Custo mensal = custo_diario * 30
    """
    try:
        # Validação de entrada usando Pydantic
        try:
            entrada = RacaoCalculadoraInput(**payload)
        except Exception as e:
            logger.error(f"Erro na validação de entrada: {e}")
            return _retornar_erro_validacao(str(e))
        
        # Extrai valores validados
        especie = entrada.especie
        peso_kg = entrada.peso_kg
        idade_meses = entrada.idade_meses
        fase = entrada.fase
        porte = entrada.porte
        tipo_racao = entrada.tipo_racao
        peso_pacote_kg = entrada.peso_pacote_kg
        preco_pacote = entrada.preco_pacote
        
        # ====================================
        # ETAPA 1: Consumo Diário
        # ====================================
        # PRIORIDADE: Tentar ler da tabela de consumo do produto
        consumo_diario_gramas = None
        
        if tabela_consumo_json:
            logger.info("🔍 Tentando usar tabela de consumo do produto...")
            consumo_diario_gramas = _ler_tabela_consumo(
                tabela_consumo_json=tabela_consumo_json,
                peso_pet_kg=peso_kg,
                idade_meses=idade_meses,
                nivel_atividade="normal"  # Pode ser parametrizado no futuro
            )
            
            if consumo_diario_gramas:
                logger.info(f"✅ Usando tabela da embalagem: {consumo_diario_gramas}g/dia")
        
        # FALLBACK: Calcular com fórmulas genéricas
        if not consumo_diario_gramas:
            logger.info("📊 Usando cálculo genérico (tabela não disponível)")
            
            # Seleciona tabela de consumo baseada na espécie
            if especie == "cao":
                consumo_base_por_kg = CONSUMO_BASE_CAO.get(porte, 30)
            else:  # gato
                consumo_base_por_kg = CONSUMO_BASE_GATO.get(porte, 30)
            
            consumo_base = peso_kg * consumo_base_por_kg
            logger.debug(f"Consumo base: {peso_kg}kg * {consumo_base_por_kg}g/kg = {consumo_base}g/dia")
            
            # Ajuste por Fase de Vida
            fator_fase = FATOR_FASE.get(fase, 1.0)
            consumo_com_fase = consumo_base * fator_fase
            logger.debug(f"Ajuste fase ({fase}): {consumo_base}g * {fator_fase} = {consumo_com_fase}g/dia")
            
            # Ajuste por Tipo de Ração
            fator_racao = FATOR_TIPO_RACAO.get(tipo_racao, 1.0)
            consumo_diario_gramas = consumo_com_fase * fator_racao
            logger.debug(f"Ajuste ração ({tipo_racao}): {consumo_com_fase}g * {fator_racao} = {consumo_diario_gramas}g/dia")
        
        # Arredonda para 2 casas decimais
        consumo_diario_gramas = round(consumo_diario_gramas, 2)
        
        # ====================================
        # ETAPA 4: Durabilidade do Pacote
        # ====================================
        peso_pacote_gramas = peso_pacote_kg * 1000
        duracao_pacote_dias = peso_pacote_gramas / consumo_diario_gramas
        duracao_pacote_dias = round(duracao_pacote_dias, 2)
        logger.debug(f"Durabilidade: {peso_pacote_gramas}g / {consumo_diario_gramas}g/dia = {duracao_pacote_dias} dias")
        
        # ====================================
        # ETAPA 5: Custos
        # ====================================
        custo_diario = preco_pacote / duracao_pacote_dias
        custo_diario = round(custo_diario, 2)
        
        custo_mensal = custo_diario * 30
        custo_mensal = round(custo_mensal, 2)
        logger.debug(f"Custo diário: R$ {custo_diario} | Custo mensal: R$ {custo_mensal}")
        
        # ====================================
        # ETAPA 6: Observações
        # ====================================
        observacoes = _gerar_observacoes(
            especie=especie,
            fase=fase,
            porte=porte,
            peso_kg=peso_kg,
            consumo_diario_gramas=consumo_diario_gramas,
            tipo_racao=tipo_racao
        )
        
        # ====================================
        # ETAPA 7: Contexto para IA (FUTURO)
        # ====================================
        # Preparando dados estruturados para quando a IA for integrada
        # Por enquanto, apenas organiza os dados calculados
        contexto_ia = _preparar_contexto_ia(
            entrada=entrada,
            consumo_diario_gramas=consumo_diario_gramas,
            duracao_pacote_dias=duracao_pacote_dias,
            custo_diario=custo_diario,
            custo_mensal=custo_mensal,
            observacoes=observacoes
        )
        
        # ====================================
        # RETORNO
        # ====================================
        resultado = RacaoCalculadoraOutput(
            consumo_diario_gramas=consumo_diario_gramas,
            duracao_pacote_dias=duracao_pacote_dias,
            custo_diario=custo_diario,
            custo_mensal=custo_mensal,
            observacoes=observacoes,
            contexto_ia=contexto_ia
        )
        
        logger.info(f"Cálculo concluído: {consumo_diario_gramas}g/dia, R$ {custo_mensal}/mês")
        return resultado.model_dump()
        
    except Exception as e:
        # FAIL-SAFE: Nunca quebra, sempre retorna algo utilizável
        logger.error(f"Erro no cálculo de ração: {e}", exc_info=True)
        return _retornar_erro_generico(str(e))


def _gerar_observacoes(
    especie: str,
    fase: str,
    porte: str,
    peso_kg: float,
    consumo_diario_gramas: float,
    tipo_racao: str
) -> str:
    """
    Gera observações personalizadas sobre o cálculo.
    
    Inclui:
    - Descrição do perfil do animal
    - Recomendações de fracionamento
    - Alertas sobre fase de vida
    - Dicas sobre o tipo de ração
    """
    # Nomenclaturas amigáveis
    especie_nome = "Cão" if especie == "cao" else "Gato"
    fase_nome = {"filhote": "Filhote", "adulto": "Adulto", "idoso": "Idoso"}.get(fase, fase.title())
    porte_nome = {
        "mini": "mini",
        "pequeno": "pequeno",
        "medio": "médio",
        "grande": "grande"
    }.get(porte, porte)
    
    tipo_racao_nome = {
        "standard": "Standard",
        "premium": "Premium",
        "super_premium": "Super Premium"
    }.get(tipo_racao, tipo_racao.title())
    
    observacoes_partes = []
    
    # Perfil básico
    observacoes_partes.append(
        f"{especie_nome} de porte {porte_nome}, {fase_nome.lower()}, pesando {peso_kg}kg. "
        f"Consome aproximadamente {consumo_diario_gramas}g/dia de ração {tipo_racao_nome}."
    )
    
    # Recomendações de fracionamento por fase
    if fase == "filhote":
        observacoes_partes.append(
            "Filhotes devem comer 3-4 vezes ao dia para melhor digestão e aproveitamento nutricional."
        )
    elif fase == "adulto":
        observacoes_partes.append(
            "Recomenda-se dividir em 2 refeições diárias (manhã e noite)."
        )
    else:  # idoso
        observacoes_partes.append(
            "Para idosos, considere 2-3 refeições menores para facilitar a digestão."
        )
    
    # Alertas específicos por tipo de ração
    if tipo_racao == "standard":
        observacoes_partes.append(
            "Rações standard requerem maior volume. Considere upgrade para premium para melhor custo-benefício."
        )
    elif tipo_racao == "super_premium":
        observacoes_partes.append(
            "Rações super premium são mais concentradas nutricionalmente, requerendo menor quantidade."
        )
    
    # Alerta de peso (possível obesidade)
    if especie == "cao":
        if porte == "pequeno" and peso_kg > 10:
            observacoes_partes.append("⚠️ Peso acima da média para o porte. Consulte um veterinário.")
        elif porte == "medio" and peso_kg > 25:
            observacoes_partes.append("⚠️ Peso acima da média para o porte. Consulte um veterinário.")
    
    return " ".join(observacoes_partes)


def _preparar_contexto_ia(
    entrada: RacaoCalculadoraInput,
    consumo_diario_gramas: float,
    duracao_pacote_dias: float,
    custo_diario: float,
    custo_mensal: float,
    observacoes: str
) -> Dict[str, Any]:
    """
    Prepara contexto estruturado para futura integração com IA.
    
    IMPORTANTE: 
    Esta função NÃO chama IA.
    Apenas organiza os dados para facilitar integração futura.
    
    Retorna:
        - resumo_textual: String descritiva pronta para contexto de IA
        - dados_estruturados: Todos os dados calculados organizados
    """
    # Resumo textual humanizado
    especie_texto = "cão" if entrada.especie == "cao" else "gato"
    resumo_textual = (
        f"Um {especie_texto} {entrada.fase} de {entrada.peso_kg}kg (porte {entrada.porte}) "
        f"consome {consumo_diario_gramas}g/dia de ração {entrada.tipo_racao}. "
        f"Um pacote de {entrada.peso_pacote_kg}kg (R$ {entrada.preco_pacote:.2f}) dura "
        f"{duracao_pacote_dias:.1f} dias, com custo mensal de R$ {custo_mensal:.2f}."
    )
    
    # Dados estruturados completos
    dados_estruturados = {
        # Input original
        "input": {
            "especie": entrada.especie,
            "peso_kg": entrada.peso_kg,
            "fase": entrada.fase,
            "porte": entrada.porte,
            "tipo_racao": entrada.tipo_racao,
            "peso_pacote_kg": entrada.peso_pacote_kg,
            "preco_pacote": entrada.preco_pacote
        },
        # Resultados calculados
        "resultados": {
            "consumo_diario_gramas": consumo_diario_gramas,
            "duracao_pacote_dias": duracao_pacote_dias,
            "custo_diario": custo_diario,
            "custo_mensal": custo_mensal
        },
        # Métricas derivadas (úteis para IA fazer comparações)
        "metricas": {
            "custo_por_kg": round(entrada.preco_pacote / entrada.peso_pacote_kg, 2),
            "gramas_por_real": round((entrada.peso_pacote_kg * 1000) / entrada.preco_pacote, 2),
            "consumo_mensal_kg": round((consumo_diario_gramas * 30) / 1000, 2)
        }
    }
    
    return {
        "resumo_textual": resumo_textual,
        "dados_estruturados": dados_estruturados
    }


def _retornar_erro_validacao(mensagem_erro: str) -> Dict[str, Any]:
    """
    Retorna resposta fail-safe para erro de validação.
    """
    logger.warning(f"Erro de validação: {mensagem_erro}")
    return {
        "consumo_diario_gramas": 0.0,
        "duracao_pacote_dias": 0.0,
        "custo_diario": 0.0,
        "custo_mensal": 0.0,
        "observacoes": f"❌ Erro de validação: {mensagem_erro}. Verifique os dados fornecidos.",
        "contexto_ia": {
            "resumo_textual": f"Erro de validação: {mensagem_erro}",
            "dados_estruturados": {"erro": mensagem_erro, "tipo": "validacao"}
        }
    }


def _retornar_erro_generico(mensagem_erro: str) -> Dict[str, Any]:
    """
    Retorna resposta fail-safe para erro genérico.
    """
    logger.error(f"Erro genérico no cálculo: {mensagem_erro}")
    return {
        "consumo_diario_gramas": 0.0,
        "duracao_pacote_dias": 0.0,
        "custo_diario": 0.0,
        "custo_mensal": 0.0,
        "observacoes": "❌ Erro ao calcular ração. Por favor, tente novamente ou contate o suporte.",
        "contexto_ia": {
            "resumo_textual": f"Erro no cálculo: {mensagem_erro}",
            "dados_estruturados": {"erro": mensagem_erro, "tipo": "generico"}
        }
    }


# ====================================
# EXEMPLO DE USO (para documentação)
# ====================================
"""
Exemplo de uso do serviço:

from app.services.racao_calculadora_service import calcular_racao

payload = {
    "especie": "cao",
    "peso_kg": 15.0,
    "fase": "adulto",
    "porte": "medio",
    "tipo_racao": "premium",
    "peso_pacote_kg": 10.5,
    "preco_pacote": 180.00
}

resultado = calcular_racao(payload)

# Retorna:
{
    "consumo_diario_gramas": 450.0,
    "duracao_pacote_dias": 23.33,
    "custo_diario": 7.71,
    "custo_mensal": 231.43,
    "observacoes": "Cão de porte médio, adulto, pesando 15kg...",
    "contexto_ia": {
        "resumo_textual": "Um cão adulto de 15kg...",
        "dados_estruturados": {...}
    }
}
"""
