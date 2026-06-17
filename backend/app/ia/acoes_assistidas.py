"""
Módulo de Ações Assistidas por IA.

A IA sugere ações, mas SEMPRE requer confirmação humana.

📌 Fluxo:
1. IA identifica oportunidade de ação
2. IA sugere e explica
3. Sistema pede confirmação ao usuário
4. Usuário confirma ou rejeita
5. Se confirmado, sistema executa via serviços normais
6. IA explica o resultado

📌 Limites importantes:
- IA NUNCA grava direto no banco
- Usuário SEMPRE confirma
- Execução via regras normais com log e auditoria
- Segurança e rastreabilidade mantidas
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class TipoAcao(str, Enum):
    """Tipos de ações que a IA pode sugerir."""

    SIMULAR_CONTRATACAO = "SIMULAR_CONTRATACAO"
    SIMULAR_DEMISSAO = "SIMULAR_DEMISSAO"
    AJUSTAR_SALARIO = "AJUSTAR_SALARIO"
    PROVISIONAR_BENEFICIO = "PROVISIONAR_BENEFICIO"
    RECALCULAR_DRE = "RECALCULAR_DRE"
    PROJETAR_FLUXO_CAIXA = "PROJETAR_FLUXO_CAIXA"
    CRIAR_CATEGORIA_DRE = "CRIAR_CATEGORIA_DRE"
    SIMULAR_AUMENTO_PRECO = "SIMULAR_AUMENTO_PRECO"
    SIMULAR_REDUCAO_CUSTO = "SIMULAR_REDUCAO_CUSTO"


def sugerir_acao(
    tipo: str,
    mensagem: str,
    parametros_necessarios: List[str],
    valores_sugeridos: Optional[Dict[str, Any]] = None,
    contexto: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cria uma sugestão de ação para confirmação do usuário.

    Args:
        tipo: Tipo da ação (usar TipoAcao)
        mensagem: Mensagem explicativa para o usuário
        parametros_necessarios: Lista de parâmetros que precisam ser fornecidos
        valores_sugeridos: Valores pré-preenchidos (opcional)
        contexto: Informações adicionais de contexto (opcional)

    Returns:
        Dicionário estruturado com a ação sugerida

    Exemplo:
        sugerir_acao(
            tipo="SIMULAR_CONTRATACAO",
            mensagem="Deseja simular uma nova contratação?",
            parametros_necessarios=["salario", "cargo"],
            valores_sugeridos={"salario": 3000, "cargo": "Vendedor"}
        )
    """
    return {
        "tipo": tipo,
        "mensagem": mensagem,
        "parametros_necessarios": parametros_necessarios,
        "valores_sugeridos": valores_sugeridos or {},
        "contexto": contexto or {},
        "confirmacao_obrigatoria": True,
        "executado": False,
        "timestamp": None,
    }


def criar_acao_contratacao(
    cargo: str, salario: Optional[float] = None
) -> Dict[str, Any]:
    """
    Cria sugestão de simulação de contratação.

    Args:
        cargo: Nome do cargo
        salario: Salário sugerido (opcional)

    Returns:
        Estrutura de ação assistida
    """
    valores = {"cargo": cargo}
    if salario:
        valores["salario"] = salario

    return sugerir_acao(
        tipo=TipoAcao.SIMULAR_CONTRATACAO,
        mensagem=f"Deseja simular a contratação de um(a) {cargo}?",
        parametros_necessarios=["cargo", "salario"],
        valores_sugeridos=valores,
        contexto={"impacto": "Afetará DRE, folha de pagamento e provisões"},
    )


def criar_acao_ajuste_salario(
    funcionario_id: int,
    nome_funcionario: str,
    salario_atual: float,
    salario_sugerido: float,
) -> Dict[str, Any]:
    """
    Cria sugestão de ajuste salarial.

    Args:
        funcionario_id: ID do funcionário
        nome_funcionario: Nome do funcionário
        salario_atual: Salário atual
        salario_sugerido: Salário sugerido

    Returns:
        Estrutura de ação assistida
    """
    percentual = ((salario_sugerido - salario_atual) / salario_atual) * 100

    return sugerir_acao(
        tipo=TipoAcao.AJUSTAR_SALARIO,
        mensagem=(
            f"Deseja simular um ajuste salarial de {percentual:.1f}% "
            f"para {nome_funcionario}?"
        ),
        parametros_necessarios=["funcionario_id", "novo_salario"],
        valores_sugeridos={
            "funcionario_id": funcionario_id,
            "novo_salario": salario_sugerido,
        },
        contexto={
            "salario_atual": salario_atual,
            "nome": nome_funcionario,
            "impacto_mensal": salario_sugerido - salario_atual,
        },
    )


def criar_acao_projecao_caixa(
    periodo_dias: int = 30,
    incluir_contas_a_pagar: bool = True,
    incluir_contas_a_receber: bool = True,
) -> Dict[str, Any]:
    """
    Cria sugestão de projeção de fluxo de caixa.

    Args:
        periodo_dias: Número de dias para projetar
        incluir_contas_a_pagar: Incluir contas a pagar
        incluir_contas_a_receber: Incluir contas a receber

    Returns:
        Estrutura de ação assistida
    """
    return sugerir_acao(
        tipo=TipoAcao.PROJETAR_FLUXO_CAIXA,
        mensagem=f"Deseja gerar uma projeção de caixa para os próximos {periodo_dias} dias?",
        parametros_necessarios=["periodo_dias"],
        valores_sugeridos={
            "periodo_dias": periodo_dias,
            "incluir_contas_a_pagar": incluir_contas_a_pagar,
            "incluir_contas_a_receber": incluir_contas_a_receber,
        },
        contexto={"tipo_analise": "preventiva"},
    )


def criar_acao_simular_aumento_preco(
    percentual: float, categoria_servico: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria sugestão de simulação de aumento de preço.

    Args:
        percentual: Percentual de aumento
        categoria_servico: Categoria específica (opcional)

    Returns:
        Estrutura de ação assistida
    """
    msg = f"Deseja simular um aumento de {percentual}% nos preços"
    if categoria_servico:
        msg += f" da categoria {categoria_servico}"
    msg += "?"

    return sugerir_acao(
        tipo=TipoAcao.SIMULAR_AUMENTO_PRECO,
        mensagem=msg,
        parametros_necessarios=["percentual"],
        valores_sugeridos={"percentual": percentual, "categoria": categoria_servico},
        contexto={
            "impacto": "Afetará margem de lucro e pode impactar volume de vendas"
        },
    )


def criar_acao_reducao_custo(
    categoria_custo: str, valor_atual: float, valor_alvo: float
) -> Dict[str, Any]:
    """
    Cria sugestão de redução de custo.

    Args:
        categoria_custo: Categoria do custo
        valor_atual: Valor atual do custo
        valor_alvo: Valor alvo após redução

    Returns:
        Estrutura de ação assistida
    """
    reducao = valor_atual - valor_alvo
    percentual = (reducao / valor_atual) * 100

    return sugerir_acao(
        tipo=TipoAcao.SIMULAR_REDUCAO_CUSTO,
        mensagem=(
            f"Deseja simular uma redução de {percentual:.1f}% em {categoria_custo}?"
        ),
        parametros_necessarios=["categoria", "valor_alvo"],
        valores_sugeridos={"categoria": categoria_custo, "valor_alvo": valor_alvo},
        contexto={
            "valor_atual": valor_atual,
            "economia_mensal": reducao,
            "economia_anual": reducao * 12,
        },
    )


def validar_parametros_acao(
    acao: Dict[str, Any], parametros_fornecidos: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Valida se todos os parâmetros necessários foram fornecidos.

    Args:
        acao: Estrutura da ação
        parametros_fornecidos: Parâmetros fornecidos pelo usuário

    Returns:
        Resultado da validação com lista de parâmetros faltantes
    """
    parametros_necessarios = acao.get("parametros_necessarios", [])
    parametros_faltantes = []

    for param in parametros_necessarios:
        if param not in parametros_fornecidos or parametros_fornecidos[param] is None:
            parametros_faltantes.append(param)

    return {
        "valido": len(parametros_faltantes) == 0,
        "parametros_faltantes": parametros_faltantes,
        "mensagem": (
            "Todos os parâmetros fornecidos"
            if not parametros_faltantes
            else f"Parâmetros faltantes: {', '.join(parametros_faltantes)}"
        ),
    }


def formatar_resposta_acao(acao: Dict[str, Any], resultado: Any) -> str:
    """
    Formata a resposta da IA após execução da ação.

    Args:
        acao: Estrutura da ação executada
        resultado: Resultado da execução

    Returns:
        Mensagem formatada para o usuário
    """
    tipo = acao.get("tipo", "")

    if tipo == TipoAcao.SIMULAR_CONTRATACAO:
        return (
            f"✅ Simulação concluída! \n\n"
            f"Impacto mensal estimado: R$ {resultado.get('impacto_mensal', 0):.2f}\n"
            f"Impacto anual: R$ {resultado.get('impacto_anual', 0):.2f}\n"
            f"Encargos totais: R$ {resultado.get('encargos_totais', 0):.2f}"
        )

    elif tipo == TipoAcao.PROJETAR_FLUXO_CAIXA:
        return (
            f"✅ Projeção gerada! \n\n"
            f"Saldo inicial: R$ {resultado.get('saldo_inicial', 0):.2f}\n"
            f"Saldo final projetado: R$ {resultado.get('saldo_final', 0):.2f}\n"
            f"{'⚠️ Atenção: caixa negativo previsto!' if resultado.get('alerta_negativo') else '✅ Fluxo saudável'}"
        )

    elif tipo == TipoAcao.SIMULAR_AUMENTO_PRECO:
        return (
            f"✅ Simulação concluída! \n\n"
            f"Aumento de receita estimado: R$ {resultado.get('aumento_receita', 0):.2f}/mês\n"
            f"Nova margem de lucro: {resultado.get('nova_margem', 0):.1f}%\n"
            f"Impacto anual: R$ {resultado.get('impacto_anual', 0):.2f}"
        )

    else:
        return f"✅ Ação executada com sucesso! Resultado: {resultado}"
