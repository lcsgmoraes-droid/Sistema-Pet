"""
Helpers para Conciliação de Cartões - FASE 2

PRINCÍPIOS OBRIGATÓRIOS:
1. ✅ Tudo em transação
2. ✅ Rollback obrigatório
3. ✅ Nenhuma mudança sem log
4. ✅ Nunca confiar 100% no arquivo
5. ✅ Sempre permitir reversão

Funções auxiliares que NÃO alteram banco de dados diretamente.
Apenas calculam, validam e retornam resultados.
"""

import hashlib
import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import re


# ==============================================================================
# HELPER: Serialização JSON
# ==============================================================================


def serialize_for_json(obj: Any) -> Any:
    """
    Converte recursivamente objetos Python para formatos serializáveis em JSON.

    Trata especialmente:
    - date/datetime → string ISO
    - Decimal → float
    - dict → recursivo
    - list → recursivo
    """
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj


# ==============================================================================
# VALIDAÇÃO E SANITIZAÇÃO
# ==============================================================================


def sanitizar_valor_monetario(
    valor_str: str, default: Decimal = Decimal("0.00")
) -> Decimal:
    """
    Converte string monetária para Decimal de forma segura.

    PRINCÍPIO: Nunca confiar 100% no arquivo.

    Exemplos:
        "1.234,56" → Decimal('1234.56')
        "R$ 1.234,56" → Decimal('1234.56')
        "1,234.56" → Decimal('1234.56')
        "abc" → default (0.00)
    """
    if not valor_str:
        return default

    try:
        # Remover símbolos comuns
        valor_limpo = str(valor_str).strip()
        valor_limpo = valor_limpo.replace("R$", "").replace("$", "").strip()
        valor_limpo = valor_limpo.replace(" ", "")

        # Detectar formato
        if "," in valor_limpo and "." in valor_limpo:
            # Ambos presentes: determinar qual é decimal
            ultimo_ponto = valor_limpo.rfind(".")
            ultima_virgula = valor_limpo.rfind(",")

            if ultima_virgula > ultimo_ponto:
                # Formato brasileiro: 1.234,56
                valor_limpo = valor_limpo.replace(".", "").replace(",", ".")
            else:
                # Formato americano: 1,234.56
                valor_limpo = valor_limpo.replace(",", "")

        elif "," in valor_limpo:
            # Apenas vírgula: assumir formato brasileiro
            valor_limpo = valor_limpo.replace(",", ".")

        # Converter para Decimal
        return Decimal(valor_limpo)

    except (ValueError, InvalidOperation):
        return default


def sanitizar_data(data_str: str, formatos: List[str] = None) -> Optional[date]:
    """
    Converte string de data para date de forma segura.

    PRINCÍPIO: Nunca confiar 100% no arquivo.

    Formatos testados (em ordem):
        - %d/%m/%Y %H:%M (BR com hora - Stone)
        - %d/%m/%Y (BR)
        - %Y-%m-%d (ISO)
        - %d-%m-%Y
        - %m/%d/%Y (US)
    """
    if not data_str:
        return None

    if formatos is None:
        formatos = [
            "%d/%m/%Y %H:%M",  # 10/02/2026 18:19 (Stone)
            "%d/%m/%Y %H:%M:%S",  # 10/02/2026 18:19:30
            "%d/%m/%Y",  # 11/02/2026
            "%Y-%m-%d",  # 2026-02-11
            "%d-%m-%Y",  # 11-02-2026
            "%m/%d/%Y",  # 02/11/2026 (US)
            "%d/%m/%y",  # 11/02/26
            "%Y%m%d",  # 20260211
        ]

    data_limpa = str(data_str).strip()

    for formato in formatos:
        try:
            return datetime.strptime(data_limpa, formato).date()
        except ValueError:
            continue

    return None


def sanitizar_nsu(nsu_str: str) -> str:
    """
    Limpa e normaliza NSU (Número Sequencial Único).

    PRINCÍPIO: Nunca confiar 100% no arquivo.

    Remove espaços, zeros à esquerda, caracteres especiais.
    """
    if not nsu_str:
        return ""

    nsu_limpo = str(nsu_str).strip()
    nsu_limpo = re.sub(r"[^0-9A-Za-z]", "", nsu_limpo)  # Apenas alfanuméricos
    nsu_limpo = nsu_limpo.lstrip("0")  # Remove zeros à esquerda

    return nsu_limpo.upper()


# ==============================================================================
# DETECÇÃO DE DUPLICATAS
# ==============================================================================


def calcular_hash_arquivo(arquivo_bytes: bytes) -> Dict[str, str]:
    """
    Calcula hash MD5 e SHA256 do arquivo.

    PRINCÍPIO: Detectar arquivos duplicados ANTES de processar.

    Returns:
        {
            'md5': 'abc123...',
            'sha256': 'def456...'
        }
    """
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()

    md5_hash.update(arquivo_bytes)
    sha256_hash.update(arquivo_bytes)

    return {"md5": md5_hash.hexdigest(), "sha256": sha256_hash.hexdigest()}


def detectar_duplicata_por_hash(db, hash_md5: str, tipo_arquivo: str) -> Optional[int]:
    """
    Verifica se arquivo já foi importado anteriormente.

    PRINCÍPIO: Nunca processar arquivo duplicado.

    Args:
        db: Sessão do banco
        hash_md5: Hash MD5 do arquivo
        tipo_arquivo: Tipo (ofx, recebimentos, pagamentos)

    Returns:
        arquivo_evidencia_id se duplicado, None caso contrário
    """
    from .conciliacao_models import ArquivoEvidencia

    arquivo_existente = (
        db.query(ArquivoEvidencia)
        .filter(
            ArquivoEvidencia.hash_md5 == hash_md5,
            ArquivoEvidencia.tipo_arquivo == tipo_arquivo,
        )
        .first()
    )

    if arquivo_existente:
        return arquivo_existente.id

    return None


# ==============================================================================
# CLASSIFICAÇÃO DE CONFIANÇA
# ==============================================================================


def calcular_confianca(
    diferenca_total: Decimal,
    total_referencia: Decimal,
    tolerancia_automatica: Decimal,
    tolerancia_media: Decimal,
) -> Tuple[str, bool, bool]:
    """
    Classifica confiança da validação.

    PRINCÍPIO: Sistema NUNCA bloqueia - sempre permite com confirmação.

    Args:
        diferenca_total: Diferença absoluta encontrada
        total_referencia: Valor total de referência (para % divergência)
        tolerancia_automatica: Limite para processar automaticamente (ex: R$ 0.10)
        tolerancia_media: Limite para requerer confirmação simples (ex: R$ 10.00)

    Returns:
        (confianca, pode_processar, requer_confirmacao)

    Exemplos:
        diferenca = R$ 0.05, tolerancia_auto = R$ 0.10
        → ('ALTA', True, False) - Processa automaticamente

        diferenca = R$ 5.00, tolerancia_media = R$ 10.00
        → ('MEDIA', True, True) - Requer confirmação

        diferenca = R$ 50.00, tolerancia_media = R$ 10.00
        → ('BAIXA', True, True) - Requer confirmação explícita + justificativa
    """
    if diferenca_total <= tolerancia_automatica:
        return ("ALTA", True, False)

    elif diferenca_total <= tolerancia_media:
        return ("MEDIA", True, True)

    else:
        # BAIXA: divergência grande, mas NUNCA bloqueia (Ajuste #4)
        return ("BAIXA", True, True)


def calcular_percentual_divergencia(diferenca: Decimal, total: Decimal) -> Decimal:
    """
    Calcula percentual de divergência.

    Retorna 0 se total for zero (evita divisão por zero).
    """
    if not total or total == 0:
        return Decimal("0.00")

    return abs(diferenca / total * 100)


# ==============================================================================
# AGRUPAMENTO EM LOTES
# ==============================================================================


def agrupar_parcelas_por_lote(
    parcelas: List[Dict[str, Any]], criterio: str = "data_adquirente"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupa parcelas em lotes baseado em critério.

    Args:
        parcelas: Lista de dicts com dados das parcelas
        criterio:
            - 'data_adquirente': Agrupa por data_pagamento + adquirente
            - 'data_adquirente_bandeira': + bandeira
            - 'data_adquirente_modalidade': + modalidade

    Returns:
        {
            'Stone_2026-02-15': [parcela1, parcela2, ...],
            'Cielo_2026-02-15': [parcela3, parcela4, ...],
            ...
        }
    """
    lotes = {}

    for parcela in parcelas:
        # Gerar chave do lote
        if criterio == "data_adquirente":
            chave = f"{parcela['adquirente']}_{parcela['data_pagamento']}"

        elif criterio == "data_adquirente_bandeira":
            chave = f"{parcela['adquirente']}_{parcela['data_pagamento']}_{parcela.get('bandeira', 'N/A')}"

        elif criterio == "data_adquirente_modalidade":
            chave = f"{parcela['adquirente']}_{parcela['data_pagamento']}_{parcela.get('modalidade', 'N/A')}"

        else:
            chave = f"{parcela['adquirente']}_{parcela['data_pagamento']}"

        # Adicionar ao lote
        if chave not in lotes:
            lotes[chave] = []

        lotes[chave].append(parcela)

    return lotes


def calcular_totais_lote(parcelas: List[Dict[str, Any]]) -> Dict[str, Decimal]:
    """
    Calcula totais de um lote de parcelas.

    Returns:
        {
            'valor_bruto': Decimal,
            'valor_liquido': Decimal,
            'valor_descontos': Decimal,
            'quantidade': int
        }
    """
    valor_bruto = Decimal("0.00")
    valor_liquido = Decimal("0.00")

    for parcela in parcelas:
        valor_bruto += Decimal(str(parcela.get("valor_bruto", 0)))
        valor_liquido += Decimal(str(parcela.get("valor_liquido", 0)))

    return {
        "valor_bruto": valor_bruto,
        "valor_liquido": valor_liquido,
        "valor_descontos": valor_bruto - valor_liquido,
        "quantidade": len(parcelas),
    }


# ==============================================================================
# PARSER DE CSV COM TEMPLATE
# ==============================================================================


def aplicar_template_csv(
    arquivo_bytes: bytes, template: Dict[str, Any], validar_linhas: bool = True
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parseia CSV usando template configurado.

    PRINCÍPIO: Nunca confiar 100% no arquivo.
    Valida cada linha e retorna erros encontrados.

    Args:
        arquivo_bytes: Conteúdo do arquivo CSV
        template: Dict com configuração do template (AdquirenteTemplate.to_dict())
        validar_linhas: Se True, valida campos obrigatórios

    Returns:
        (linhas_validas, erros)

    Template example:
        {
            'separador': ';',
            'encoding': 'utf-8',
            'tem_header': True,
            'pular_linhas': 0,
            'mapeamento': {
                'nsu': 'NSU',
                'data_pagamento': 'Data Pagamento',
                'valor_bruto': 'Valor Bruto',
                'valor_liquido': 'Valor Líquido',
                'taxa_mdr': 'Taxa MDR %',
                ...
            },
            'transformacoes': {
                'valor_bruto': 'monetario_br',
                'taxa_mdr': 'percentual',
                'data_pagamento': 'data_br'
            }
        }
    """
    linhas_validas = []
    erros = []

    try:
        # Decodificar arquivo
        encoding = template.get("encoding", "utf-8")
        conteudo = arquivo_bytes.decode(encoding)

        # Configurar CSV reader
        separador = template.get("separador", ";")
        pular_linhas = template.get("pular_linhas", 0)
        tem_header = template.get("tem_header", True)

        reader = (
            csv.DictReader(io.StringIO(conteudo), delimiter=separador)
            if tem_header
            else csv.reader(io.StringIO(conteudo), delimiter=separador)
        )

        # Pular linhas iniciais
        for _ in range(pular_linhas):
            next(reader, None)

        # Processar linhas
        mapeamento = template.get("mapeamento", {})
        transformacoes = template.get("transformacoes", {})

        # 🔍 DEBUG: Log das colunas do CSV
        import logging

        logger = logging.getLogger(__name__)
        if tem_header:
            logger.info(
                f"🔍 DEBUG CSV - Colunas disponíveis no CSV: {reader.fieldnames}"
            )
        logger.info(f"🔍 DEBUG CSV - Mapeamento esperado: {list(mapeamento.items())}")

        for idx, linha in enumerate(reader, start=1):
            try:
                linha_processada = {}

                # 🔍 DEBUG: Log da primeira linha para diagnóstico
                if idx == 1:
                    logger.info(f"🔍 DEBUG CSV - Primeira linha RAW: {linha}")

                # Aplicar mapeamento
                for campo_destino, config_coluna in mapeamento.items():
                    # Suportar dois formatos:
                    # 1. Simples: {"nsu": "STONE ID"}
                    # 2. Completa: {"nsu": {"coluna": "STONE ID", "obrigatorio": true, "transformacao": "nsu"}}

                    if isinstance(config_coluna, dict):
                        # Formato completo
                        coluna_origem = config_coluna.get("coluna")
                        transformacao_campo = config_coluna.get("transformacao")
                    else:
                        # Formato simples (string)
                        coluna_origem = config_coluna
                        transformacao_campo = None

                    # Obter valor do CSV
                    valor_original = (
                        linha.get(coluna_origem, "")
                        if tem_header
                        else linha[int(coluna_origem)]
                    )

                    # 🔍 DEBUG: Log do NSU sendo capturado
                    if campo_destino == "nsu" and idx == 1:
                        logger.info(
                            f"🔍 DEBUG CSV - Campo NSU: coluna='{coluna_origem}', valor='{valor_original}'"
                        )

                    # Aplicar transformação (priorizar transformacao do campo, depois global)
                    transformacao = transformacao_campo or transformacoes.get(
                        campo_destino
                    )

                    if transformacao == "monetario_br":
                        linha_processada[campo_destino] = sanitizar_valor_monetario(
                            valor_original
                        )

                    elif transformacao == "percentual":
                        # "3.79%" → Decimal('3.79')
                        valor_limpo = str(valor_original).replace("%", "").strip()
                        linha_processada[campo_destino] = sanitizar_valor_monetario(
                            valor_limpo
                        )

                    elif transformacao == "data_br":
                        linha_processada[campo_destino] = sanitizar_data(valor_original)

                    elif transformacao == "nsu":
                        linha_processada[campo_destino] = sanitizar_nsu(valor_original)

                    elif transformacao == "inteiro":
                        # "3" → int(3)
                        try:
                            linha_processada[campo_destino] = (
                                int(valor_original) if valor_original else None
                            )
                        except (ValueError, TypeError):
                            linha_processada[campo_destino] = None

                    else:
                        # Sem transformação: manter original
                        linha_processada[campo_destino] = (
                            valor_original.strip()
                            if isinstance(valor_original, str)
                            else valor_original
                        )

                # Validar campos obrigatórios (dinâmico pelo mapeamento)
                if validar_linhas:
                    # Identificar campos obrigatórios do mapeamento
                    campos_obrigatorios = []
                    for campo, config in mapeamento.items():
                        if isinstance(config, dict) and config.get(
                            "obrigatorio", False
                        ):
                            campos_obrigatorios.append(campo)
                        elif isinstance(config, str):
                            # Se mapeamento é string simples, marcar campos críticos como obrigatórios
                            if campo in ["nsu", "valor_liquido"]:
                                campos_obrigatorios.append(campo)

                    # Fallback: se não houver campos obrigatórios definidos, usar validação mínima
                    if not campos_obrigatorios:
                        campos_obrigatorios = ["nsu", "valor_liquido"]

                    for campo in campos_obrigatorios:
                        if campo not in linha_processada or not linha_processada[campo]:
                            erros.append(
                                f"Linha {idx}: campo obrigatório '{campo}' ausente ou vazio"
                            )
                            continue

                linhas_validas.append(linha_processada)

            except Exception as e:
                erros.append(f"Linha {idx}: erro ao processar - {str(e)}")

    except Exception as e:
        erros.append(f"Erro ao parsear arquivo: {str(e)}")

    return linhas_validas, erros


# ==============================================================================
# GERAÇÃO DE ALERTAS
# ==============================================================================


def gerar_alertas_validacao(
    diferenca_ofx_pagamentos: Decimal,
    diferenca_pagamentos_recebimentos: Decimal,
    parcelas_orfas: int,
    total_parcelas: int,
    confianca: str,
) -> List[Dict[str, Any]]:
    """
    Gera lista de alertas para validação.

    Returns:
        [
            {
                'tipo': 'divergencia_alta',
                'gravidade': 'alta',
                'mensagem': 'Divergência entre OFX e Pagamentos: R$ 50.00',
                'valor': 50.00
            },
            ...
        ]
    """
    alertas = []

    # Alerta: Divergência OFX vs Pagamentos
    if abs(diferenca_ofx_pagamentos) > Decimal("0.01"):
        gravidade = (
            "alta" if abs(diferenca_ofx_pagamentos) > Decimal("10.00") else "media"
        )

        alertas.append(
            {
                "tipo": "divergencia_ofx_pagamentos",
                "gravidade": gravidade,
                "mensagem": f"Divergência entre OFX e Pagamentos: R$ {abs(diferenca_ofx_pagamentos):.2f}",
                "valor": float(abs(diferenca_ofx_pagamentos)),
            }
        )

    # Alerta: Divergência Pagamentos vs Recebimentos
    if abs(diferenca_pagamentos_recebimentos) > Decimal("0.01"):
        gravidade = (
            "alta"
            if abs(diferenca_pagamentos_recebimentos) > Decimal("10.00")
            else "media"
        )

        alertas.append(
            {
                "tipo": "divergencia_pagamentos_recebimentos",
                "gravidade": gravidade,
                "mensagem": f"Divergência entre Pagamentos e Recebimentos (PDV): R$ {abs(diferenca_pagamentos_recebimentos):.2f}",
                "valor": float(abs(diferenca_pagamentos_recebimentos)),
            }
        )

    # Alerta: Parcelas órfãs
    if parcelas_orfas > 0:
        percentual = (
            (parcelas_orfas / total_parcelas * 100) if total_parcelas > 0 else 0
        )
        gravidade = "alta" if percentual > 10 else "media"

        alertas.append(
            {
                "tipo": "parcelas_orfas",
                "gravidade": gravidade,
                "mensagem": f"{parcelas_orfas} parcelas sem match no arquivo da operadora ({percentual:.1f}%)",
                "quantidade": parcelas_orfas,
                "percentual": percentual,
            }
        )

    # Alerta: Confiança BAIXA
    if confianca == "BAIXA":
        alertas.append(
            {
                "tipo": "confianca_baixa",
                "gravidade": "alta",
                "mensagem": "Divergência alta detectada - requer confirmação explícita com justificativa",
                "requer_justificativa": True,
            }
        )

    return alertas


# ==============================================================================
# VALIDAÇÃO DE REGRAS DE NEGÓCIO
# ==============================================================================


def validar_duplicata_nsu(db, nsu: str, adquirente: str, tenant_id: str) -> bool:
    """
    Verifica se NSU já existe no sistema para este adquirente.

    PRINCÍPIO: Nunca confiar 100% no arquivo.
    Operadora pode enviar NSU duplicado por erro.
    """
    from .financeiro_models import ContaReceber

    duplicata = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.nsu == nsu,
            ContaReceber.adquirente == adquirente,
        )
        .first()
    )

    return duplicata is not None


def validar_data_futura(data: date, dias_tolerancia: int = 90) -> bool:
    """
    Valida se data não está muito no futuro.

    PRINCÍPIO: Nunca confiar 100% no arquivo.
    Data de pagamento 2 anos no futuro provavelmente é erro.
    """
    hoje = date.today()
    limite_futuro = hoje + timedelta(days=dias_tolerancia)

    return data <= limite_futuro


def validar_valor_razoavel(
    valor: Decimal,
    min_valor: Decimal = Decimal("0.01"),
    max_valor: Decimal = Decimal("1000000.00"),
) -> bool:
    """
    Valida se valor está em faixa razoável.

    PRINCÍPIO: Nunca confiar 100% no arquivo.
    Valor negativo ou R$ 10 milhões pode ser erro de parsing.
    """
    return min_valor <= valor <= max_valor
