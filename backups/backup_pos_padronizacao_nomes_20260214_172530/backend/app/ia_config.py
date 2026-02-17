"""
Configuração da IA - Sistema Pet

Centraliza todas as configurações, chaves, modelos e constantes.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# OPENAI / LLM CONFIGURATION
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))

# ============================================================================
# WHATSAPP CONFIGURATION
# ============================================================================
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")

# ============================================================================
# GOOGLE MAPS CONFIGURATION (ABA 8)
# ============================================================================
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ============================================================================
# EMAIL CONFIGURATION (Notificações)
# ============================================================================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ============================================================================
# NLP CONFIGURATION (ABA 6)
# ============================================================================
# spaCy model - instalar com: python -m spacy download pt_core_news_sm
SPACY_MODEL = "pt_core_news_sm"

# ============================================================================
# FORECASTING CONFIGURATION (ABA 5)
# ============================================================================
PROPHET_SEASONALITY_MODE = os.getenv("PROPHET_SEASONALITY_MODE", "additive")
FORECAST_PERIODS = int(os.getenv("FORECAST_PERIODS", "15"))  # 15 dias
CONFIDENCE_INTERVAL = float(os.getenv("CONFIDENCE_INTERVAL", "0.95"))  # 95%

# ============================================================================
# ABA 5: FLUXO DE CAIXA - LIMIARES DE ALERTA
# ============================================================================
class Aba5Config:
    # Limiar de dias de caixa (dias de despesa)
    DIAS_CAIXA_CRITICO = 7  # < 7 dias = CRÍTICO
    DIAS_CAIXA_ALERTA = 15  # < 15 dias = ALERTA
    DIAS_CAIXA_OK = 30  # >= 30 dias = OK
    
    # Ciclo operacional (dias)
    CICLO_OPERACIONAL_MAXIMO = 45  # se > 45 = problema
    
    # Contas a receber
    MARGEM_CONTAS_RECEBER = 0.8  # considerar 80% do valor total
    
    # Cache de projeções (em horas)
    CACHE_PROJECTIONS_HOURS = 2

# ============================================================================
# ABA 6: CHAT IA - INTENÇÕES E MODELOS
# ============================================================================
class Aba6Config:
    # Tipos de intenção que a IA reconhece
    INTENCOES = {
        "fluxo_caixa": "Perguntas sobre fluxo de caixa, caixa, dinheiro",
        "vendas": "Perguntas sobre vendas, faturamento, receita",
        "estoque": "Perguntas sobre produtos, estoque, quantidade",
        "clientes": "Perguntas sobre clientes, base de clientes, volume",
        "dre": "Perguntas sobre lucro, despesas, margens",
        "produtos": "Perguntas sobre produtos específicos, categorias",
        "desempenho": "Perguntas sobre performance, KPIs, métricas",
        "ajuda": "Perguntas gerais, ajuda com sistema"
    }
    
    # Limiar de confiança para sugerir resposta
    CONFIDENCE_THRESHOLD = 0.7
    
    # Max mensagens guardadas por conversa
    MAX_HISTORY = 50

# ============================================================================
# ABA 7: DRE ANÁLISE COMPARATIVA
# ============================================================================
class Aba7Config:
    # Períodos para análise
    PERIODOS = {
        "mensal": 30,
        "trimestral": 90,
        "semestral": 180,
        "anual": 365
    }
    
    # Índices calculados
    INDICES = [
        "margem_liquida",
        "margem_bruta",
        "retorno_vendas",
        "giro_estoque",
        "ciclo_caixa"
    ]

# ============================================================================
# ABA 8: OTIMIZAÇÃO DE ENTREGAS
# ============================================================================
class Aba8Config:
    # Algoritmo padrão
    ALGORITMO_PADRAO = "greedy_2opt"  # "forca_bruta" ou "greedy_2opt"
    
    # Máximo de paradas para força bruta
    MAX_PARADAS_FORCA_BRUTA = 8
    
    # Raio máximo de entrega (km)
    RAIO_MAXIMO_ENTREGA = 50
    
    # Velocidade média (km/h) - com semáforos e trânsito
    VELOCIDADE_MEDIA = 30
    
    # Tempo médio por parada (minutos)
    TEMPO_PARADA = 5
    
    # Horário de início das entregas
    HORARIO_INICIO = "08:00"
    HORARIO_FIM = "18:00"

# ============================================================================
# ABA 9: ROBÔ WHATSAPP
# ============================================================================
class Aba9Config:
    # Limiares de confiança
    CONFIANCA_ALTA = 0.90  # >= 90%
    CONFIANCA_MEDIA = 0.70  # 70-89%
    CONFIANCA_BAIXA = 0.50  # 50-69%
    
    # Quando fazer handoff para atendente
    HANDOFF_THRESHOLD = 0.60  # < 60% confiança OU pergunta complexa
    
    # Máxima similitude fuzzy para desambiguação
    FUZZY_RATIO_MIN = 60  # >= 60%
    
    # Limite de opções a mostrar
    OPCOES_DESAMBIGUACAO_MAX = 5
    
    # Mensagens padrão
    MENSAGEM_INICIAL = "Olá! 👋 Bem-vindo ao Pet Shop! Como posso ajudar?"
    MENSAGEM_HANDOFF = "Deixa eu chamar um atendente para ajudar melhor... ⏳"
    MENSAGEM_SUCESSO = "✅ Venda criada com sucesso! Você receberá confirmação em breve! 🎉"

# ============================================================================
# ALERTAS E NOTIFICAÇÕES
# ============================================================================
class AlertasConfig:
    # Canais de notificação
    CANAIS = {
        "email": True,
        "whatsapp": True,
        "push": True,
        "sms": False,  # Ativar quando tiver Twilio
    }
    
    # Frequência mínima entre alertas (minutos)
    MIN_INTERVALO_ALERTAS = 60
    
    # Alertas críticos (urgentes)
    ALERTAS_CRITICOS = [
        "caixa_critico",
        "estoque_zerado",
        "venda_grande_recusada"
    ]

# ============================================================================
# LOGGING
# ============================================================================
LOGGING_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "file": "logs/ia.log",
    "max_size": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5,
}

# ============================================================================
# DATABASE
# ============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sistema_pet.db")
