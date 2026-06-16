"""
Validação de Settings - Pré-Produção
====================================

Este módulo implementa validação rigorosa de variáveis de ambiente críticas
na inicialização do sistema, garantindo que:

1. Todas as variáveis obrigatórias estejam presentes
2. O ambiente (DEV/TEST/PROD) esteja configurado corretamente
3. Guard rails e logs estejam adequados para produção
4. A aplicação falhe imediatamente se algo estiver incorreto

Autor: Sistema Pet - Pré-Prod Block 1
Data: 2026-02-05
"""

import os
import logging
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


class EnvironmentValidationError(RuntimeError):
    """Erro levantado quando a validação de ambiente falha."""

    pass


def validate_settings(settings: Any) -> None:
    """
    Valida variáveis obrigatórias por ambiente.
    Falha imediatamente se algo estiver incorreto.

    Esta função DEVE ser chamada:
    - Na inicialização do app
    - Antes de aceitar qualquer request

    Args:
        settings: Objeto de configurações (geralmente config.Config ou similar)

    Raises:
        EnvironmentValidationError: Se alguma validação falhar

    Validações executadas:
    ----------------------

    1. VARIÁVEIS OBRIGATÓRIAS (todos os ambientes):
       - ENV
       - DATABASE_URL
       - SQL_AUDIT_ENFORCE
       - SQL_AUDIT_ENFORCE_LEVEL

    2. VALIDAÇÕES ESPECÍFICAS DE PRODUÇÃO (ENV == "production"):
       - Debug DESATIVADO
       - Guard rails DESATIVADOS
       - Logs >= INFO

    Exemplos de erro:
    ----------------

    >>> validate_settings(settings_sem_env)
    EnvironmentValidationError: [CRITICAL] Variável ENV não está definida

    >>> validate_settings(settings_prod_com_debug)
    EnvironmentValidationError: [PRODUCTION] Debug está ATIVADO em produção (valor: True)
    """

    errors: List[str] = []

    # ==================================================================
    # 1️⃣ VALIDAÇÃO DE VARIÁVEIS OBRIGATÓRIAS
    # ==================================================================

    required_vars = {
        "ENV": "Ambiente de execução (development/test/production)",
        "DATABASE_URL": "URL de conexão com o banco de dados",
        "SQL_AUDIT_ENFORCE": "Flag de enforcement de auditoria SQL",
        "SQL_AUDIT_ENFORCE_LEVEL": "Nível de enforcement (warn/error/strict)",
    }

    for var_name, description in required_vars.items():
        value = getattr(settings, var_name, None)

        # Verifica se a variável existe
        if value is None or value == "":
            errors.append(
                f"[CRITICAL] Variável {var_name} não está definida\n"
                f"           Descrição: {description}\n"
                f"           Esta variável é OBRIGATÓRIA para inicialização do sistema"
            )
            continue

        # Log da variável encontrada (sem expor valores sensíveis)
        if "URL" in var_name or "PASSWORD" in var_name or "SECRET" in var_name:
            logger.info(f"✓ {var_name}: [PRESENTE - valor oculto por segurança]")
        else:
            logger.info(f"✓ {var_name}: {value}")

    # ==================================================================
    # 2️⃣ VALIDAÇÕES ESPECÍFICAS POR AMBIENTE
    # ==================================================================

    env = getattr(settings, "ENV", "").lower()

    if env == "production":
        _validate_production_settings(settings, errors)
    elif env == "test":
        _validate_test_settings(settings, errors)
    elif env == "development":
        _validate_development_settings(settings, errors)
    else:
        errors.append(
            f"[CRITICAL] ENV inválido: '{env}'\n"
            f"           Valores permitidos: development, test, production"
        )

    # ==================================================================
    # 3️⃣ FALHA IMEDIATA SE HOUVER ERROS
    # ==================================================================

    if errors:
        error_message = _format_error_message(errors, env)
        logger.error(error_message)
        raise EnvironmentValidationError(error_message)

    # Sucesso
    logger.info(f"✅ Validação de settings concluída com sucesso (ENV: {env})")


def _validate_production_settings(settings: Any, errors: List[str]) -> None:
    """
    Validações específicas para ambiente de PRODUÇÃO.

    Regras obrigatórias:
    - Debug DESATIVADO
    - Guard rails DESATIVADOS
    - Logs >= INFO
    """

    # 1. Debug deve estar DESATIVADO
    debug = getattr(settings, "DEBUG", False)
    if debug:
        errors.append(
            f"[PRODUCTION] Debug está ATIVADO em produção (valor: {debug})\n"
            f"             Debug DEVE estar DESATIVADO em produção por segurança"
        )

    # 2. Guard rails devem estar DESATIVADOS
    guardrails_enabled = getattr(settings, "ENABLE_GUARDRAILS", False)
    if guardrails_enabled:
        errors.append(
            f"[PRODUCTION] Guard rails estão ATIVADOS em produção (valor: {guardrails_enabled})\n"
            f"             Guard rails DEVEM estar DESATIVADOS em produção"
        )

    # 3. Log level deve ser >= INFO
    log_level = getattr(settings, "LOG_LEVEL", "INFO").upper()
    if log_level in ["DEBUG", "TRACE", "NOTSET"]:
        errors.append(
            f"[PRODUCTION] Log level inadequado para produção (valor: {log_level})\n"
            f"             Log level em produção DEVE ser INFO, WARNING, ERROR ou CRITICAL"
        )

    # 4. SQL Audit deve estar em modo STRICT
    sql_audit_level = getattr(settings, "SQL_AUDIT_ENFORCE_LEVEL", "").upper()
    if sql_audit_level not in ["ERROR", "STRICT"]:
        errors.append(
            f"[PRODUCTION] SQL Audit level inadequado (valor: {sql_audit_level})\n"
            f"             Em produção, SQL_AUDIT_ENFORCE_LEVEL DEVE ser 'error' ou 'strict'"
        )

    # 5. Chave dedicada de criptografia de PAGAMENTO obrigatória
    payment_key = (
        os.getenv("PAYMENT_CONFIG_ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY") or ""
    ).strip()
    if not payment_key:
        errors.append(
            "[PRODUCTION] PAYMENT_CONFIG_ENCRYPTION_KEY ausente\n"
            "             Em produção a chave dedicada de criptografia de pagamento é\n"
            "             OBRIGATÓRIA (sem fallback para JWT_SECRET_KEY nem literal embutido)."
        )

    logger.info("🔒 Validação de produção executada")


def _validate_test_settings(settings: Any, errors: List[str]) -> None:
    """
    Validações específicas para ambiente de TESTE.

    Regras:
    - Database deve ser diferente de produção
    - Guard rails podem estar ativos
    """

    database_url = getattr(settings, "DATABASE_URL", "")

    # Verificar se não está usando banco de produção
    if "production" in database_url.lower() or "prod" in database_url.lower():
        errors.append(
            "[TEST] Ambiente de teste NÃO DEVE usar banco de produção\n"
            "       DATABASE_URL contém 'production' ou 'prod'"
        )

    logger.info("🧪 Validação de teste executada")


def _validate_development_settings(settings: Any, errors: List[str]) -> None:
    """
    Validações específicas para ambiente de DESENVOLVIMENTO.

    Regras:
    - Database deve ser diferente de produção
    - Guard rails PODEM estar ativos (para desenvolvimento seguro)
    - Debug pode estar ativo
    """

    database_url = getattr(settings, "DATABASE_URL", "")

    # Verificar se não está usando banco de produção
    if "production" in database_url.lower() or "prod" in database_url.lower():
        errors.append(
            "[DEVELOPMENT] Ambiente de desenvolvimento NÃO DEVE usar banco de produção\n"
            "              DATABASE_URL contém 'production' ou 'prod'"
        )

    logger.info("🛠️  Validação de desenvolvimento executada")


def _format_error_message(errors: List[str], env: str) -> str:
    """
    Formata mensagem de erro clara e direta.
    """
    separator = "=" * 80

    message = f"\n{separator}\n"
    message += "❌ FALHA NA VALIDAÇÃO DE SETTINGS\n"
    message += f"{separator}\n\n"
    message += f"Ambiente: {env or 'NÃO DEFINIDO'}\n"
    message += f"Total de erros: {len(errors)}\n\n"

    for i, error in enumerate(errors, 1):
        message += f"Erro {i}:\n{error}\n\n"

    message += f"{separator}\n"
    message += "⚠️  O sistema NÃO PODE iniciar com estes erros.\n"
    message += "    Corrija as configurações e tente novamente.\n"
    message += f"{separator}\n"

    return message


def get_validation_summary(settings: Any) -> Dict[str, Any]:
    """
    Retorna um resumo das validações sem levantar exceções.
    Útil para diagnósticos e health checks.

    Returns:
        Dict com status das validações
    """

    summary = {
        "environment": getattr(settings, "ENV", "UNKNOWN"),
        "validations": {},
        "warnings": [],
        "is_valid": True,
    }

    # Verificar variáveis obrigatórias
    required_vars = [
        "ENV",
        "DATABASE_URL",
        "SQL_AUDIT_ENFORCE",
        "SQL_AUDIT_ENFORCE_LEVEL",
    ]
    for var in required_vars:
        value = getattr(settings, var, None)
        summary["validations"][var] = {
            "present": value is not None and value != "",
            "value": "[HIDDEN]" if "URL" in var or "PASSWORD" in var else value,
        }

        if not summary["validations"][var]["present"]:
            summary["is_valid"] = False

    # Verificar configurações de produção
    env = summary["environment"].lower()
    if env == "production":
        debug = getattr(settings, "DEBUG", False)
        guardrails = getattr(settings, "ENABLE_GUARDRAILS", False)

        if debug:
            summary["warnings"].append("Debug ativado em produção")
            summary["is_valid"] = False

        if guardrails:
            summary["warnings"].append("Guard rails ativados em produção")
            summary["is_valid"] = False

    return summary
