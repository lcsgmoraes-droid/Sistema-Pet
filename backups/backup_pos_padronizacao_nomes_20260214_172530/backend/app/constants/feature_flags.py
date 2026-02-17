"""
Constantes de Feature Flags do Sistema.

Define todas as feature keys utilizadas no sistema para controle de funcionalidades
por tenant. Centralizar as constantes aqui evita typos e facilita manutenção.
"""

# ====================
# PDV - PONTO DE VENDA
# ====================

PDV_IA_OPORTUNIDADES = "PDV_IA_OPORTUNIDADES"
"""
Feature: IA de Oportunidades no PDV

Status Padrão: DESLIGADA

Quando ativa, habilita:
- Sugestões inteligentes de cross-sell
- Sugestões de up-sell baseadas em margem
- Detecção de oportunidades de recorrência
- Análise de contexto de venda em background
- Chat IA com histórico e comparações
- Calculadora de ração inteligente

Quando desligada:
- PDV funciona normalmente sem IA
- Nenhuma análise é executada
- Nenhum processamento em background
- Interface não exibe botão de oportunidades

Regra crítica: PDV NUNCA pode depender desta feature para funcionar.

Fases de implantação:
- FASE 0: Base e Segurança (preparação)
- FASE 1: UX do PDV (ajustes de interface)
- FASE 2: Métricas de Oportunidade (tracking)
- FASE 3: IA em Background (processamento passivo)
- FASE 4: Calculadora de Ração (integração)
- FASE 5: Aprendizado e Evolução (otimização)

Documentação: docs/roadmaps/ia_oportunidades_pdv_checklist.md
"""


# ====================
# LISTA DE TODAS AS FEATURES
# ====================

ALL_FEATURE_FLAGS = [
    PDV_IA_OPORTUNIDADES,
]
"""
Lista completa de todas as feature flags do sistema.
Útil para validação, documentação e administração.
"""


# ====================
# DEFAULTS
# ====================

DEFAULT_FEATURE_FLAGS = {
    PDV_IA_OPORTUNIDADES: False,
}
"""
Valores padrão para todas as features quando não existem no banco.
Sempre False para garantir que features novas não quebrem o sistema.
"""
