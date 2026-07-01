"""Fachada compativel da calculadora de racao.

A implementacao fica em ``app.racao_calculadora`` para manter schemas,
consultas e regras de calculo em arquivos menores.
"""

from .racao_calculadora.core import (
    _avaliar_aptidao_calculadora,
    _campos_bloqueantes_calculadora,
    _json_preenchido,
    _numero_positivo,
    _produto_tem_config_racao,
    _tabela_consumo_tem_linha_valida,
    _texto_preenchido,
    calcular_quantidade_diaria,
    calcular_resultado,
)
from .racao_calculadora.options import (
    _busca_ilike,
    _busca_racao_conditions,
    _float_ou_none,
    _produto_eh_racao_expr,
    _serializar_opcao_racao,
    _usar_unaccent,
)
from .racao_calculadora.routes import (
    calcular_racao,
    comparar_racoes,
    listar_opcoes_calculadora_racao,
    router,
)
from .racao_calculadora.schemas import (
    CalculadoraRacaoRequest,
    ComparativoRacoesResponse,
    RacaoCalculadoraOption,
    RacoesCalculadoraOptionsResponse,
    ResultadoCalculoRacao,
)


__all__ = [
    "CalculadoraRacaoRequest",
    "ComparativoRacoesResponse",
    "RacaoCalculadoraOption",
    "RacoesCalculadoraOptionsResponse",
    "ResultadoCalculoRacao",
    "_avaliar_aptidao_calculadora",
    "_busca_ilike",
    "_busca_racao_conditions",
    "_campos_bloqueantes_calculadora",
    "_float_ou_none",
    "_json_preenchido",
    "_numero_positivo",
    "_produto_eh_racao_expr",
    "_produto_tem_config_racao",
    "_serializar_opcao_racao",
    "_tabela_consumo_tem_linha_valida",
    "_texto_preenchido",
    "_usar_unaccent",
    "calcular_quantidade_diaria",
    "calcular_racao",
    "calcular_resultado",
    "comparar_racoes",
    "listar_opcoes_calculadora_racao",
    "router",
]
