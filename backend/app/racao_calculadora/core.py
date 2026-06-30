"""Regras puras de aptidao e calculo da calculadora de racao."""

import json
import logging
from typing import List, Optional

from app.produtos_models import Produto

from .schemas import ResultadoCalculoRacao


logger = logging.getLogger(__name__)


# ==================== FUNÇÕES AUXILIARES ====================


def _texto_preenchido(valor) -> bool:
    if valor is None:
        return False
    if isinstance(valor, (list, tuple, set, dict)):
        return len(valor) > 0

    texto = str(valor).strip()
    return texto.lower() not in {"", "{}", "[]", "null", "none", "undefined"}


def _json_preenchido(valor) -> bool:
    if not _texto_preenchido(valor):
        return False
    if isinstance(valor, (list, tuple, set, dict)):
        return len(valor) > 0

    try:
        parsed = json.loads(str(valor))
    except Exception:
        return _texto_preenchido(valor)

    if isinstance(parsed, dict):
        return any(_texto_preenchido(item) for item in parsed.values())
    if isinstance(parsed, list):
        return len(parsed) > 0
    return _texto_preenchido(parsed)


def _tabela_consumo_tem_linha_valida(valor) -> bool:
    if not _texto_preenchido(valor):
        return False

    try:
        tabela = json.loads(str(valor)) if isinstance(valor, str) else valor
    except Exception:
        return False

    if not isinstance(tabela, dict):
        return False

    dados = tabela.get("dados") if isinstance(tabela.get("dados"), dict) else tabela
    if not isinstance(dados, dict):
        return False

    for peso, consumos in dados.items():
        if not _texto_preenchido(peso) or not isinstance(consumos, dict):
            continue
        if any(_numero_positivo(valor_consumo) for valor_consumo in consumos.values()):
            return True

    return False


def _numero_positivo(valor) -> bool:
    try:
        return float(valor or 0) > 0
    except (TypeError, ValueError):
        return False


def _produto_tem_config_racao(produto: Produto) -> bool:
    tipo = (getattr(produto, "tipo", None) or "").strip().lower()
    classificacao = (
        (getattr(produto, "classificacao_racao", None) or "").strip().lower()
    )

    return (
        tipo.startswith("ra")
        or bool(getattr(produto, "linha_racao_id", None))
        or (bool(classificacao) and classificacao not in {"nao", "não"})
    )


def _avaliar_aptidao_calculadora(produto: Produto) -> List[str]:
    faltantes: List[str] = []

    if not _produto_tem_config_racao(produto):
        faltantes.append("aba Ração")
    if not _numero_positivo(getattr(produto, "peso_embalagem", None)):
        faltantes.append("peso da embalagem")
    if not _numero_positivo(getattr(produto, "preco_venda", None)):
        faltantes.append("preço de venda")
    if not _texto_preenchido(
        getattr(produto, "linha_racao_id", None)
        or getattr(produto, "classificacao_racao", None)
    ):
        faltantes.append("linha/classificação")
    if not _texto_preenchido(
        getattr(produto, "porte_animal_id", None)
        or getattr(produto, "porte_animal", None)
    ):
        faltantes.append("porte")
    if not _texto_preenchido(
        getattr(produto, "fase_publico_id", None)
        or getattr(produto, "fase_publico", None)
        or getattr(produto, "categoria_racao", None)
    ):
        faltantes.append("fase/público")
    if not _texto_preenchido(
        getattr(produto, "sabor_proteina_id", None)
        or getattr(produto, "sabor_proteina", None)
    ):
        faltantes.append("sabor/proteína")
    if not _texto_preenchido(getattr(produto, "especies_indicadas", None)):
        faltantes.append("espécie indicada")
    if not _tabela_consumo_tem_linha_valida(getattr(produto, "tabela_consumo", None)):
        faltantes.append("tabela de consumo")

    return faltantes


def _campos_bloqueantes_calculadora(
    produto: Produto,
    peso_fallback: Optional[float] = None,
    preco_fallback: Optional[float] = None,
    exigir_tabela_consumo: bool = True,
) -> List[str]:
    """Campos sem os quais o calculo nao deve seguir para produto cadastrado."""
    faltantes: List[str] = []

    if not _numero_positivo(getattr(produto, "peso_embalagem", None) or peso_fallback):
        faltantes.append("peso da embalagem")
    if not _numero_positivo(getattr(produto, "preco_venda", None) or preco_fallback):
        faltantes.append("preco de venda")
    if exigir_tabela_consumo and not _tabela_consumo_tem_linha_valida(
        getattr(produto, "tabela_consumo", None)
    ):
        faltantes.append("tabela de consumo")

    return faltantes


def calcular_quantidade_diaria(
    peso_pet_kg: float,
    idade_meses: Optional[int],
    nivel_atividade: str,
    tabela_consumo_json: Optional[str] = None,
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
            logger.info("🔍 DEBUG: Processando tabela_consumo...")
            tabela = json.loads(tabela_consumo_json)
            logger.info(f"🔍 DEBUG: Tabela parseada: {tabela}")

            # Novo formato: {"tipo": "filhote_peso_adulto", "dados": {"5kg": {"4m": 125, "6m": 130}}}
            if "tipo" in tabela and "dados" in tabela:
                tipo_tabela = tabela["tipo"]
                dados = tabela["dados"]
                logger.info(
                    f"🔍 DEBUG: Tipo={tipo_tabela}, Dados keys={list(dados.keys())}"
                )

                # Encontrar peso mais próximo
                pesos_disponiveis = []
                for peso_str in dados.keys():
                    # Remover 'kg' e converter para float
                    peso_num = float(
                        peso_str.replace("kg", "").replace("g", "").strip()
                    )
                    pesos_disponiveis.append(peso_num)

                logger.info(
                    f"🔍 DEBUG: Pesos disponíveis na tabela: {pesos_disponiveis}"
                )

                if not pesos_disponiveis:
                    raise ValueError("Nenhum peso encontrado na tabela")

                # Peso mais próximo
                peso_tabela = min(pesos_disponiveis, key=lambda x: abs(x - peso_pet_kg))

                # Buscar a chave correspondente ao peso (pode ser "5", "5kg", "5.0", etc)
                peso_key = None
                for k in dados.keys():
                    peso_k = float(k.replace("kg", "").replace("g", "").strip())
                    if peso_k == peso_tabela:
                        peso_key = k
                        break

                if not peso_key:
                    raise ValueError(f"Chave não encontrada para peso {peso_tabela}kg")

                logger.info(
                    f"🔍 DEBUG: Pet {peso_pet_kg}kg -> Usando linha da tabela: {peso_key} ({peso_tabela}kg)"
                )

                consumos = dados[peso_key]
                logger.info(f"🔍 DEBUG: Consumos disponíveis: {consumos}")

                quantidade = 0  # Inicializar

                # Para filhote: buscar pela idade (até 18 meses inclusive)
                if (
                    tipo_tabela == "filhote_peso_adulto"
                    and idade_meses
                    and idade_meses <= 18
                ):
                    logger.info(f"🔍 DEBUG: Modo FILHOTE - idade {idade_meses}m")
                    # Buscar coluna de idade mais próxima
                    idade_key = f"{idade_meses}m"
                    if idade_key in consumos:
                        quantidade = consumos[idade_key]
                        logger.info(
                            f"🔍 DEBUG: Encontrou idade exata {idade_key}: {quantidade}g"
                        )
                    else:
                        # Buscar idade mais próxima
                        idades_disponiveis = [
                            int(k.replace("m", ""))
                            for k in consumos.keys()
                            if k != "adulto" and "m" in k
                        ]
                        if idades_disponiveis:
                            idade_proxima = min(
                                idades_disponiveis, key=lambda x: abs(x - idade_meses)
                            )
                            quantidade = consumos[f"{idade_proxima}m"]
                            logger.info(
                                f"🔍 DEBUG: Idade {idade_meses}m não encontrada. Usando {idade_proxima}m: {quantidade}g"
                            )
                        else:
                            # Fallback para adulto
                            quantidade = consumos.get("adulto", 0)
                            logger.info(
                                f"🔍 DEBUG: Sem idades, usando adulto: {quantidade}g"
                            )

                # Para adulto: usar coluna 'adulto' ou primeira disponível
                else:
                    logger.info("🔍 DEBUG: Modo ADULTO")
                    quantidade = consumos.get(
                        "adulto", list(consumos.values())[0] if consumos else 0
                    )
                    logger.info(f"🔍 DEBUG: Quantidade adulto: {quantidade}g")

                if quantidade and quantidade > 0:
                    logger.info(
                        f"📊 Usando tabela da embalagem ({tipo_tabela}): {quantidade}g/dia para {peso_pet_kg}kg, idade {idade_meses}m"
                    )

                    # Ajustar por nível de atividade
                    ajuste_antes = quantidade
                    if nivel_atividade == "alto":
                        quantidade *= 1.1  # +10%
                    elif nivel_atividade == "baixo":
                        quantidade *= 0.9  # -10%

                    logger.info(
                        f"🔍 DEBUG: Ajuste atividade {nivel_atividade}: {ajuste_antes}g -> {quantidade}g"
                    )

                    return round(quantidade, 2)
                else:
                    logger.warning("⚠️ Quantidade não encontrada ou zero na tabela")

            # Formato antigo (compatibilidade)
            else:
                # Determinar a chave baseada na idade
                if idade_meses and idade_meses < 12:
                    # Filhote - tentar encontrar faixa etária mais próxima
                    chave = f"filhote_{idade_meses}m"
                    if chave not in tabela:
                        # Buscar a faixa mais próxima
                        faixas_filhote = [
                            k for k in tabela.keys() if k.startswith("filhote_")
                        ]
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

                    logger.info(
                        f"📊 Usando tabela da embalagem (formato antigo): {quantidade}g/dia para {peso_pet_kg}kg"
                    )

                    # Ajustar por nível de atividade (pequeno ajuste)
                    if nivel_atividade == "alto":
                        quantidade *= 1.1  # +10%
                    elif nivel_atividade == "baixo":
                        quantidade *= 0.9  # -10%

                    return round(quantidade, 2)

        except Exception as e:
            logger.warning(
                f"⚠️ Erro ao ler tabela_consumo: {e}. Usando cálculo genérico."
            )

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
    nivel_atividade: str = "normal",
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
        pet_nivel_atividade=nivel_atividade,
    )
