from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.tenant_onboarding_core import OnboardingResult, _db_enum_label
from app.services.tenant_onboarding_item_installs import (
    _record_template_item_install,
    _mapped_template_row_id,
)
from app.services.tenant_onboarding_sql import _execute_insert, _scalar
from app.services.tenant_onboarding_templates import (
    BASE_RATEIO_DB_LABELS,
    ESCOPO_RATEIO_DB_LABELS,
    TIPO_CUSTO_DB_LABELS,
)


def _copy_payment_methods(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "formas_pagamento"
        )
        if mapped_id:
            result.bump("skipped", "payment_methods")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM formas_pagamento
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "formas_pagamento",
                existing_id,
            )
            result.bump("skipped", "payment_methods")
            continue
        if result.dry_run:
            result.bump("would_create", "payment_methods")
            continue

        params = {
            **payload,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "taxa_percentual": payload.get("taxa_percentual", 0),
            "taxa_fixa": payload.get("taxa_fixa", 0),
            "prazo_dias": payload.get("prazo_dias", 0),
            "prazo_recebimento": payload.get(
                "prazo_recebimento", payload.get("prazo_dias", 0)
            ),
            "operadora": payload.get("operadora"),
            "gera_contas_receber": bool(payload.get("gera_contas_receber", False)),
            "split_parcelas": bool(payload.get("split_parcelas", False)),
            "requer_nsu": bool(payload.get("requer_nsu", False)),
            "tipo_cartao": payload.get("tipo_cartao"),
            "bandeira": payload.get("bandeira"),
            "ativo": bool(payload.get("ativo", True)),
            "permite_parcelamento": bool(payload.get("permite_parcelamento", False)),
            "max_parcelas": payload.get("max_parcelas", 1),
            "parcelas_maximas": payload.get(
                "parcelas_maximas", payload.get("max_parcelas", 1)
            ),
            "icone": payload.get("icone"),
            "cor": payload.get("cor"),
        }
        _execute_insert(
            db,
            """
            INSERT INTO formas_pagamento (
                tenant_id, user_id, nome, tipo, taxa_percentual, taxa_fixa,
                prazo_dias, prazo_recebimento, operadora, gera_contas_receber,
                split_parcelas, requer_nsu, tipo_cartao, bandeira, ativo,
                permite_parcelamento, max_parcelas, parcelas_maximas, icone, cor,
                created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :tipo, :taxa_percentual, :taxa_fixa,
                :prazo_dias, :prazo_recebimento, :operadora, :gera_contas_receber,
                :split_parcelas, :requer_nsu, :tipo_cartao, :bandeira, :ativo,
                :permite_parcelamento, :max_parcelas, :parcelas_maximas, :icone, :cor,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            params,
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM formas_pagamento
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "formas_pagamento",
            created_id,
        )
        result.bump("created", "payment_methods")


def _copy_bank_accounts(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "contas_bancarias"
        )
        if mapped_id:
            result.bump("skipped", "bank_accounts")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM contas_bancarias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "contas_bancarias",
                existing_id,
            )
            result.bump("skipped", "bank_accounts")
            continue
        if result.dry_run:
            result.bump("would_create", "bank_accounts")
            continue

        params = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "nome": payload["nome"],
            "tipo": payload["tipo"],
            "banco": payload.get("banco"),
            "agencia": payload.get("agencia"),
            "conta": payload.get("conta"),
            "saldo_inicial": payload.get("saldo_inicial", 0),
            "saldo_atual": payload.get("saldo_atual", 0),
            "cor": payload.get("cor"),
            "icone": payload.get("icone"),
            "instituicao_bancaria": bool(payload.get("instituicao_bancaria", False)),
            "ativa": bool(payload.get("ativa", True)),
            "observacoes": payload.get("observacoes"),
        }
        _execute_insert(
            db,
            """
            INSERT INTO contas_bancarias (
                tenant_id, user_id, nome, tipo, banco, agencia, conta,
                saldo_inicial, saldo_atual, cor, icone, instituicao_bancaria,
                ativa, observacoes, created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :tipo, :banco, :agencia, :conta,
                :saldo_inicial, :saldo_atual, :cor, :icone, :instituicao_bancaria,
                :ativa, :observacoes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            params,
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM contas_bancarias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "contas_bancarias",
            created_id,
        )
        result.bump("created", "bank_accounts")


def _copy_dre_categories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
) -> dict[str, int]:
    category_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "dre_categorias"
        )
        if mapped_id:
            category_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "dre_categories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_categorias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            category_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "dre_categorias",
                existing_id,
            )
            result.bump("skipped", "dre_categories")
            continue
        if result.dry_run:
            category_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "dre_categories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO dre_categorias (
                tenant_id, nome, ordem, natureza, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :ordem, :natureza, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "ordem": payload.get("ordem", 0),
                "natureza": payload["natureza"],
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_categorias
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        category_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "dre_categorias",
            created_id,
        )
        result.bump("created", "dre_categories")
    return category_ids


def _copy_dre_subcategories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
    category_ids: dict[str, int],
) -> dict[str, int]:
    subcategory_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        category_code = payload["categoria_code"]
        category_id = category_ids.get(category_code)
        if not category_id:
            result.warnings.append(
                f"Categoria DRE ausente para subcategoria {item['template_code']}."
            )
            continue

        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "dre_subcategorias"
        )
        if mapped_id:
            subcategory_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "dre_subcategories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_subcategorias
            WHERE {tenant_filter}
              AND categoria_id = :categoria_id
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"categoria_id": category_id, "nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            subcategory_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "dre_subcategorias",
                existing_id,
            )
            result.bump("skipped", "dre_subcategories")
            continue
        if result.dry_run:
            subcategory_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "dre_subcategories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO dre_subcategorias (
                tenant_id, categoria_id, nome, tipo_custo, base_rateio,
                escopo_rateio, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :categoria_id, :nome, :tipo_custo, :base_rateio,
                :escopo_rateio, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "categoria_id": category_id,
                "nome": payload["nome"],
                "tipo_custo": _db_enum_label(
                    payload["tipo_custo"], TIPO_CUSTO_DB_LABELS, "tipo_custo"
                ),
                "base_rateio": _db_enum_label(
                    payload.get("base_rateio"),
                    BASE_RATEIO_DB_LABELS,
                    "base_rateio",
                    allow_none=True,
                ),
                "escopo_rateio": _db_enum_label(
                    payload.get("escopo_rateio", "ambos"),
                    ESCOPO_RATEIO_DB_LABELS,
                    "escopo_rateio",
                ),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM dre_subcategorias
            WHERE {tenant_filter}
              AND categoria_id = :categoria_id
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"categoria_id": category_id, "nome": payload["nome"]},
            tenant_id,
        )
        subcategory_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "dre_subcategorias",
            created_id,
        )
        result.bump("created", "dre_subcategories")
    return subcategory_ids


def _copy_expense_types(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
    subcategory_ids: dict[str, int],
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "tipo_despesas"
        )
        if mapped_id:
            result.bump("skipped", "expense_types")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM tipo_despesas
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "tipo_despesas",
                existing_id,
            )
            result.bump("skipped", "expense_types")
            continue
        if result.dry_run:
            result.bump("would_create", "expense_types")
            continue

        dre_subcategory_id = subcategory_ids.get(payload.get("dre_subcategory_code"))
        if not dre_subcategory_id:
            result.warnings.append(
                f"Subcategoria DRE ausente para tipo de despesa {item['template_code']}."
            )
            continue

        _execute_insert(
            db,
            """
            INSERT INTO tipo_despesas (
                tenant_id, nome, e_custo_fixo, dre_subcategoria_id, ativo,
                created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :e_custo_fixo, :dre_subcategoria_id, :ativo,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "e_custo_fixo": bool(payload.get("e_custo_fixo", True)),
                "dre_subcategoria_id": dre_subcategory_id,
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM tipo_despesas
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "tipo_despesas",
            created_id,
        )
        result.bump("created", "expense_types")


def _copy_financial_categories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
    subcategory_ids: dict[str, int],
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "categorias_financeiras"
        )
        if mapped_id:
            result.bump("skipped", "financial_categories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias_financeiras
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "categorias_financeiras",
                existing_id,
            )
            result.bump("skipped", "financial_categories")
            continue
        if result.dry_run:
            result.bump("would_create", "financial_categories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO categorias_financeiras (
                tenant_id, user_id, nome, tipo, cor, icone, descricao,
                ativo, dre_subcategoria_id, tipo_custo, created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :tipo, :cor, :icone, :descricao,
                :ativo, :dre_subcategoria_id, :tipo_custo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "nome": payload["nome"],
                "tipo": payload["tipo"],
                "cor": payload.get("cor"),
                "icone": payload.get("icone"),
                "descricao": payload.get("descricao"),
                "ativo": bool(payload.get("ativo", True)),
                "dre_subcategoria_id": subcategory_ids.get(
                    payload.get("dre_subcategory_code")
                ),
                "tipo_custo": payload.get("tipo_custo"),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias_financeiras
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
              AND tipo = :tipo
            LIMIT 1
            """,
            {"nome": payload["nome"], "tipo": payload["tipo"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "categorias_financeiras",
            created_id,
        )
        result.bump("created", "financial_categories")
