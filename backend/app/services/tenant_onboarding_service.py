from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.tenant_onboarding_contract import (
    _load_template_items,
    ensure_builtin_templates,
    validate_onboarding_template_contract,
)
from app.services.tenant_onboarding_core import (
    OnboardingResult,
    TenantOnboardingError,
    _db_enum_label,
    _enforce_required_onboarding,
    _normalize_tenant_id,
    _normalize_user_id,
    _table_exists,
    _tables_ready_or_warn,
    _warn_missing_template_infra_for_strict,
)
from app.services.tenant_onboarding_templates import (
    BASE_RATEIO_DB_LABELS as BASE_RATEIO_DB_LABELS,
    DEFAULT_BUNDLE_CODE as DEFAULT_BUNDLE_CODE,
    DEFAULT_BUNDLE_VERSION as DEFAULT_BUNDLE_VERSION,
    ESCOPO_RATEIO_DB_LABELS as ESCOPO_RATEIO_DB_LABELS,
    INSERT_TABLE_PATTERN as INSERT_TABLE_PATTERN,
    ITEM_INSTALL_TARGET_TABLES as ITEM_INSTALL_TARGET_TABLES,
    NAME_RECEITAS_VENDAS as NAME_RECEITAS_VENDAS,
    NAME_TAXAS_CARTAO as NAME_TAXAS_CARTAO,
    PRODUCT_REFERENCE_DESCRIPTION as PRODUCT_REFERENCE_DESCRIPTION,
    REQUIRED_ONBOARDING_SECTIONS as REQUIRED_ONBOARDING_SECTIONS,
    TIPO_CUSTO_DB_LABELS as TIPO_CUSTO_DB_LABELS,
)
from app.template_models import (
    TenantTemplateInstall,
    TenantTemplateItemInstall,
)
from app.utils.tenant_safe_sql import (
    execute_tenant_safe,
    execute_tenant_safe_scalar,
)


__all__ = [
    "OnboardingResult",
    "REQUIRED_ONBOARDING_SECTIONS",
    "TenantOnboardingError",
    "onboard_tenant_defaults",
    "validate_onboarding_template_contract",
]


def _items_by_type(items: list[dict[str, Any]], item_type: str) -> list[dict[str, Any]]:
    return [item for item in items if item["item_type"] == item_type]


def _scalar(db: Session, sql: str, params: dict[str, Any], tenant_id: str) -> Any:
    return execute_tenant_safe_scalar(db, sql, params, tenant_id=tenant_id)


def _insert_target_table(sql: str) -> str | None:
    match = INSERT_TABLE_PATTERN.search(sql or "")
    if not match:
        return None
    table_name = match.group(1)
    if table_name not in ITEM_INSTALL_TARGET_TABLES:
        return None
    return table_name


def _sync_postgres_id_sequence(db: Session, table_name: str) -> None:
    """Keep legacy/imported rows from making nextval reuse an existing id."""
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    synced_tables = db.info.setdefault("tenant_onboarding_sequences_synced", set())
    if table_name in synced_tables:
        return

    sequence_name = db.execute(
        text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
        {"table_name": table_name},
    ).scalar()
    if not sequence_name:
        synced_tables.add(table_name)
        return

    db.execute(
        text(
            f"""
            SELECT CASE
                WHEN max_id IS NULL THEN setval(:sequence_name, 1, false)
                ELSE setval(:sequence_name, max_id, true)
            END
            FROM (SELECT MAX(id)::bigint AS max_id FROM {table_name}) seq_sync
            """
        ),
        {"sequence_name": sequence_name},
    )
    synced_tables.add(table_name)


def _execute_insert(
    db: Session, sql: str, params: dict[str, Any], tenant_id: str
) -> None:
    target_table = _insert_target_table(sql)
    if target_table:
        _sync_postgres_id_sequence(db, target_table)

    execute_tenant_safe(
        db,
        sql,
        params,
        tenant_id=tenant_id,
        require_tenant=False,
    )


def _item_install_tables_ready(db: Session) -> bool:
    return _table_exists(db, "tenant_template_item_installs")


def _ensure_known_target_table(target_table: str) -> None:
    if target_table not in ITEM_INSTALL_TARGET_TABLES:
        raise TenantOnboardingError(
            f"Tabela alvo de template nao permitida: {target_table}."
        )


def _get_template_item_install(
    db: Session,
    tenant_id: str,
    result: OnboardingResult,
    item: dict[str, Any],
) -> TenantTemplateItemInstall | None:
    if not _item_install_tables_ready(db):
        return None

    tenant_uuid = uuid.UUID(tenant_id)
    return (
        db.query(TenantTemplateItemInstall)
        .filter(
            TenantTemplateItemInstall.tenant_id == tenant_uuid,
            TenantTemplateItemInstall.bundle_code == result.bundle_code,
            TenantTemplateItemInstall.bundle_version == result.bundle_version,
            TenantTemplateItemInstall.item_type == item["item_type"],
            TenantTemplateItemInstall.template_code == item["template_code"],
        )
        .first()
    )


def _mapped_template_row_id(
    db: Session,
    tenant_id: str,
    result: OnboardingResult,
    item: dict[str, Any],
    target_table: str,
) -> int | None:
    _ensure_known_target_table(target_table)
    install = _get_template_item_install(db, tenant_id, result, item)
    if install is None or install.target_id is None:
        return None
    if install.target_table != target_table:
        result.warnings.append(
            f"Template {item['template_code']} aponta para tabela inesperada: {install.target_table}."
        )
        return None

    existing_id = _scalar(
        db,
        f"""
        SELECT id
        FROM {target_table}
        WHERE {{tenant_filter}}
          AND id = :target_id
        LIMIT 1
        """,
        {"target_id": install.target_id},
        tenant_id,
    )
    if existing_id:
        return int(existing_id)

    result.warnings.append(
        f"Template {item['template_code']} tinha vinculo sem registro alvo em {target_table}."
    )
    return None


def _record_template_item_install(
    db: Session,
    tenant_id: str,
    user_id: int | None,
    result: OnboardingResult,
    item: dict[str, Any],
    target_table: str,
    target_id: Any,
) -> None:
    if result.dry_run or not target_id or not _item_install_tables_ready(db):
        return

    _ensure_known_target_table(target_table)
    tenant_uuid = uuid.UUID(tenant_id)
    install = _get_template_item_install(db, tenant_id, result, item)
    if install is None:
        db.add(
            TenantTemplateItemInstall(
                tenant_id=tenant_uuid,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                item_type=item["item_type"],
                template_code=item["template_code"],
                target_table=target_table,
                target_id=int(target_id),
                status="active",
                created_by_user_id=user_id,
            )
        )
    else:
        install.target_table = target_table
        install.target_id = int(target_id)
        install.status = "active"
        install.created_by_user_id = user_id
    db.flush()


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


def _copy_pet_species(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
) -> dict[str, int]:
    species_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "especies")
        if mapped_id:
            species_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "pet_species")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM especies
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            species_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "especies",
                existing_id,
            )
            result.bump("skipped", "pet_species")
            continue
        if result.dry_run:
            species_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "pet_species")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO especies (
                tenant_id, nome, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM especies
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        species_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "especies",
            created_id,
        )
        result.bump("created", "pet_species")
    return species_ids


def _copy_pet_breeds(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
    species_ids: dict[str, int],
) -> None:
    for item in items:
        payload = item["payload"]
        species_id = species_ids.get(payload.get("species_code"))
        if not species_id:
            result.warnings.append(
                f"Especie ausente para raca {item['template_code']}."
            )
            continue

        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "racas")
        if mapped_id:
            result.bump("skipped", "pet_breeds")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM racas
            WHERE {tenant_filter}
              AND especie_id = :especie_id
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"especie_id": species_id, "nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "racas",
                existing_id,
            )
            result.bump("skipped", "pet_breeds")
            continue
        if result.dry_run:
            result.bump("would_create", "pet_breeds")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO racas (
                tenant_id, nome, especie, especie_id, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :especie, :especie_id, :ativo,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "especie": payload.get("especie"),
                "especie_id": species_id,
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM racas
            WHERE {tenant_filter}
              AND especie_id = :especie_id
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"especie_id": species_id, "nome": payload["nome"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "racas",
            created_id,
        )
        result.bump("created", "pet_breeds")


def _copy_named_options(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
    target_table: str,
    result_key: str,
) -> None:
    _ensure_known_target_table(target_table)
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, target_table)
        if mapped_id:
            result.bump("skipped", result_key)
            continue

        existing_id = _scalar(
            db,
            f"""
            SELECT id
            FROM {target_table}
            WHERE {{tenant_filter}}
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
                target_table,
                existing_id,
            )
            result.bump("skipped", result_key)
            continue
        if result.dry_run:
            result.bump("would_create", result_key)
            continue

        _execute_insert(
            db,
            f"""
            INSERT INTO {target_table} (
                tenant_id, nome, descricao, ordem, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :nome, :descricao, :ordem, :ativo,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "nome": payload["nome"],
                "descricao": payload.get("descricao"),
                "ordem": payload.get("ordem", 0),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            f"""
            SELECT id
            FROM {target_table}
            WHERE {{tenant_filter}}
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
            target_table,
            created_id,
        )
        result.bump("created", result_key)


def _copy_package_weights(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    result: OnboardingResult,
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "apresentacoes_peso"
        )
        if mapped_id:
            result.bump("skipped", "package_weights")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM apresentacoes_peso
            WHERE {tenant_filter}
              AND peso_kg = :peso_kg
            LIMIT 1
            """,
            {"peso_kg": payload["peso_kg"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                None,
                result,
                item,
                "apresentacoes_peso",
                existing_id,
            )
            result.bump("skipped", "package_weights")
            continue
        if result.dry_run:
            result.bump("would_create", "package_weights")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO apresentacoes_peso (
                tenant_id, peso_kg, descricao, ordem, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :peso_kg, :descricao, :ordem, :ativo,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "peso_kg": payload["peso_kg"],
                "descricao": payload.get("descricao"),
                "ordem": payload.get("ordem", 0),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM apresentacoes_peso
            WHERE {tenant_filter}
              AND peso_kg = :peso_kg
            LIMIT 1
            """,
            {"peso_kg": payload["peso_kg"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            None,
            result,
            item,
            "apresentacoes_peso",
            created_id,
        )
        result.bump("created", "package_weights")


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


def _copy_product_departments(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
) -> dict[str, int]:
    department_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(
            db, tenant_id, result, item, "departamentos"
        )
        if mapped_id:
            department_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "product_departments")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM departamentos
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        if existing_id:
            department_ids[item["template_code"]] = int(existing_id)
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "departamentos",
                existing_id,
            )
            result.bump("skipped", "product_departments")
            continue
        if result.dry_run:
            department_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "product_departments")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO departamentos (
                tenant_id, user_id, nome, descricao, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :descricao, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "nome": payload["nome"],
                "descricao": payload.get("descricao"),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM departamentos
            WHERE {tenant_filter}
              AND lower(nome) = lower(:nome)
            LIMIT 1
            """,
            {"nome": payload["nome"]},
            tenant_id,
        )
        department_ids[item["template_code"]] = int(created_id)
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "departamentos",
            created_id,
        )
        result.bump("created", "product_departments")
    return department_ids


def _copy_product_categories(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
    department_ids: dict[str, int],
) -> dict[str, int]:
    category_ids: dict[str, int] = {}
    for item in items:
        payload = item["payload"]
        department_id = department_ids.get(payload.get("departamento_code"))
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "categorias")
        if mapped_id:
            category_ids[item["template_code"]] = mapped_id
            result.bump("skipped", "product_categories")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias
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
                user_id,
                result,
                item,
                "categorias",
                existing_id,
            )
            result.bump("skipped", "product_categories")
            continue
        if result.dry_run:
            category_ids[item["template_code"]] = -int(item.get("sort_order") or 1)
            result.bump("would_create", "product_categories")
            continue

        _execute_insert(
            db,
            """
            INSERT INTO categorias (
                tenant_id, user_id, nome, departamento_id, descricao, icone,
                cor, ordem, ativo, created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :nome, :departamento_id, :descricao, :icone,
                :cor, :ordem, :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "nome": payload["nome"],
                "departamento_id": department_id,
                "descricao": payload.get("descricao"),
                "icone": payload.get("icone"),
                "cor": payload.get("cor"),
                "ordem": payload.get("ordem", 0),
                "ativo": bool(payload.get("ativo", True)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM categorias
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
            user_id,
            result,
            item,
            "categorias",
            created_id,
        )
        result.bump("created", "product_categories")
    return category_ids


def _copy_products(
    db: Session,
    items: list[dict[str, Any]],
    tenant_id: str,
    user_id: int,
    result: OnboardingResult,
    department_ids: dict[str, int],
    category_ids: dict[str, int],
) -> None:
    for item in items:
        payload = item["payload"]
        mapped_id = _mapped_template_row_id(db, tenant_id, result, item, "produtos")
        if mapped_id:
            result.bump("skipped", "product_references")
            continue

        existing_id = _scalar(
            db,
            """
            SELECT id
            FROM produtos
            WHERE {tenant_filter}
              AND lower(trim(codigo)) = lower(trim(:codigo))
            LIMIT 1
            """,
            {"codigo": payload["codigo"]},
            tenant_id,
        )
        if existing_id:
            _record_template_item_install(
                db,
                tenant_id,
                user_id,
                result,
                item,
                "produtos",
                existing_id,
            )
            result.bump("skipped", "product_references")
            continue
        if result.dry_run:
            result.bump("would_create", "product_references")
            continue

        category_id = category_ids.get(payload.get("categoria_code"))
        department_id = department_ids.get(payload.get("departamento_code"))
        if not category_id or not department_id:
            result.warnings.append(
                f"Categoria/departamento ausente para produto opcional {item['template_code']}."
            )
            continue

        _execute_insert(
            db,
            """
            INSERT INTO produtos (
                tenant_id, user_id, codigo, nome, tipo, situacao, tipo_produto,
                is_parent, is_sellable, descricao_curta, categoria_id,
                departamento_id, preco_custo, preco_venda, estoque_atual,
                estoque_minimo, estoque_maximo, unidade, condicao, ativo,
                created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :codigo, :nome, :tipo, :situacao, 'SIMPLES',
                :is_parent, :is_sellable, :descricao_curta, :categoria_id,
                :departamento_id, :preco_custo, :preco_venda, :estoque_atual,
                :estoque_minimo, :estoque_maximo, :unidade, :condicao, :ativo,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "codigo": payload["codigo"],
                "nome": payload["nome"],
                "tipo": payload.get("tipo", "produto"),
                "situacao": bool(payload.get("situacao", False)),
                "is_parent": False,
                "is_sellable": True,
                "descricao_curta": payload.get("descricao_curta"),
                "categoria_id": category_id,
                "departamento_id": department_id,
                "preco_custo": payload.get("preco_custo", 0),
                "preco_venda": payload.get("preco_venda", 0),
                "estoque_atual": payload.get("estoque_atual", 0),
                "estoque_minimo": payload.get("estoque_minimo", 0),
                "estoque_maximo": payload.get("estoque_maximo", 0),
                "unidade": payload.get("unidade", "UN"),
                "condicao": payload.get("condicao", "novo"),
                "ativo": bool(payload.get("ativo", False)),
            },
            tenant_id,
        )
        created_id = _scalar(
            db,
            """
            SELECT id
            FROM produtos
            WHERE {tenant_filter}
              AND lower(trim(codigo)) = lower(trim(:codigo))
            LIMIT 1
            """,
            {"codigo": payload["codigo"]},
            tenant_id,
        )
        _record_template_item_install(
            db,
            tenant_id,
            user_id,
            result,
            item,
            "produtos",
            created_id,
        )
        result.bump("created", "product_references")


def _record_install(
    db: Session, tenant_id: str, user_id: int, result: OnboardingResult
) -> None:
    if not _table_exists(db, "tenant_template_installs"):
        result.warnings.append(
            "Tabela tenant_template_installs ausente; auditoria de onboarding nao registrada."
        )
        return

    tenant_uuid = uuid.UUID(tenant_id)
    install = (
        db.query(TenantTemplateInstall)
        .filter(
            TenantTemplateInstall.tenant_id == tenant_uuid,
            TenantTemplateInstall.bundle_code == result.bundle_code,
            TenantTemplateInstall.bundle_version == result.bundle_version,
        )
        .first()
    )
    summary = result.to_dict()
    if install is None:
        db.add(
            TenantTemplateInstall(
                tenant_id=tenant_uuid,
                bundle_code=result.bundle_code,
                bundle_version=result.bundle_version,
                status="completed",
                dry_run=result.dry_run,
                created_by_user_id=user_id,
                summary=summary,
            )
        )
    else:
        install.status = "completed"
        install.dry_run = result.dry_run
        install.created_by_user_id = user_id
        install.summary = summary
    db.flush()


def _run_onboarding_steps(
    db: Session,
    tenant_id_str: str,
    user_id_int: int,
    bundle_code: str,
    bundle_version: str,
    dry_run: bool,
    include_products: bool,
    strict_required: bool,
    result: OnboardingResult,
) -> dict[str, Any]:
    if not dry_run:
        ensure_builtin_templates(db)
    if strict_required and not dry_run:
        _warn_missing_template_infra_for_strict(db, result)

    items, source = _load_template_items(db, bundle_code, bundle_version)
    result.template_source = source

    if _tables_ready_or_warn(db, result, "formas de pagamento", ("formas_pagamento",)):
        _copy_payment_methods(
            db,
            _items_by_type(items, "payment_method"),
            tenant_id_str,
            user_id_int,
            result,
        )

    if _tables_ready_or_warn(db, result, "contas bancarias", ("contas_bancarias",)):
        _copy_bank_accounts(
            db,
            _items_by_type(items, "bank_account"),
            tenant_id_str,
            user_id_int,
            result,
        )

    pet_species_ids: dict[str, int] = {}
    if _tables_ready_or_warn(db, result, "especies de pets", ("especies",)):
        pet_species_ids = _copy_pet_species(
            db,
            _items_by_type(items, "pet_species"),
            tenant_id_str,
            result,
        )
    if _tables_ready_or_warn(db, result, "racas de pets", ("racas", "especies")):
        _copy_pet_breeds(
            db,
            _items_by_type(items, "pet_breed"),
            tenant_id_str,
            result,
            pet_species_ids,
        )

    category_ids: dict[str, int] = {}
    subcategory_ids: dict[str, int] = {}
    if _tables_ready_or_warn(
        db,
        result,
        "estrutura DRE",
        ("dre_categorias", "dre_subcategorias"),
    ):
        category_ids = _copy_dre_categories(
            db,
            _items_by_type(items, "dre_category"),
            tenant_id_str,
            result,
        )
        subcategory_ids = _copy_dre_subcategories(
            db,
            _items_by_type(items, "dre_subcategory"),
            tenant_id_str,
            result,
            category_ids,
        )

    if _tables_ready_or_warn(
        db, result, "categorias financeiras", ("categorias_financeiras",)
    ):
        _copy_financial_categories(
            db,
            _items_by_type(items, "financial_category"),
            tenant_id_str,
            user_id_int,
            result,
            subcategory_ids,
        )
    if _tables_ready_or_warn(db, result, "tipos de despesa", ("tipo_despesas",)):
        _copy_expense_types(
            db,
            _items_by_type(items, "expense_type"),
            tenant_id_str,
            result,
            subcategory_ids,
        )

    department_ids: dict[str, int] = {}
    product_category_ids: dict[str, int] = {}
    if _tables_ready_or_warn(
        db, result, "departamentos de produtos", ("departamentos",)
    ):
        department_ids = _copy_product_departments(
            db,
            _items_by_type(items, "product_department"),
            tenant_id_str,
            user_id_int,
            result,
        )
    if _tables_ready_or_warn(db, result, "categorias de produtos", ("categorias",)):
        product_category_ids = _copy_product_categories(
            db,
            _items_by_type(items, "product_category"),
            tenant_id_str,
            user_id_int,
            result,
            department_ids,
        )

    ration_option_sections = (
        ("linhas de racao", "linhas_racao", "ration_line", "ration_lines"),
        ("portes de animal", "portes_animal", "animal_size", "animal_sizes"),
        ("fases/publicos de racao", "fases_publico", "life_stage", "life_stages"),
        (
            "tratamentos de racao",
            "tipos_tratamento",
            "treatment_type",
            "treatment_types",
        ),
        (
            "sabores/proteinas de racao",
            "sabores_proteina",
            "protein_flavor",
            "protein_flavors",
        ),
    )
    for section_name, table_name, item_type, result_key in ration_option_sections:
        if _tables_ready_or_warn(db, result, section_name, (table_name,)):
            _copy_named_options(
                db,
                _items_by_type(items, item_type),
                tenant_id_str,
                result,
                table_name,
                result_key,
            )

    if _tables_ready_or_warn(
        db, result, "apresentacoes de peso", ("apresentacoes_peso",)
    ):
        _copy_package_weights(
            db,
            _items_by_type(items, "package_weight"),
            tenant_id_str,
            result,
        )

    if include_products:
        if _tables_ready_or_warn(db, result, "produtos opcionais", ("produtos",)):
            _copy_products(
                db,
                _items_by_type(items, "product_reference"),
                tenant_id_str,
                user_id_int,
                result,
                department_ids,
                product_category_ids,
            )

    if not dry_run:
        _record_install(db, tenant_id_str, user_id_int, result)

    if strict_required and not dry_run:
        _enforce_required_onboarding(result)

    return result.to_dict()


def onboard_tenant_defaults(
    db: Session,
    tenant_id: Any,
    user_id: Any,
    bundle_code: str = DEFAULT_BUNDLE_CODE,
    bundle_version: str = DEFAULT_BUNDLE_VERSION,
    dry_run: bool = False,
    include_products: bool = False,
    strict_required: bool = False,
) -> dict[str, Any]:
    """
    Copy system templates into tenant-owned tables.

    The operation is idempotent: existing tenant records are skipped and missing
    records are created. Products are intentionally optional and not copied by
    default because catalog data is business-specific.
    """
    tenant_id_str = _normalize_tenant_id(tenant_id)
    user_id_int = _normalize_user_id(user_id)

    result = OnboardingResult(
        tenant_id=tenant_id_str,
        bundle_code=bundle_code,
        bundle_version=bundle_version,
        dry_run=dry_run,
    )

    # As tabelas de auditoria de onboarding (tenant_template_installs / _item_installs)
    # sao TenantScoped: as queries ORM internas exigem um tenant no contexto. Estabelecemos
    # o contexto do tenant alvo aqui (salvando o anterior e restaurando no fim), para que
    # TODO caller funcione sem setar manualmente: o signup (que ja seta o mesmo tenant) fica
    # intacto, e o CLI run_tenant_onboarding e os testes passam a ter contexto -- sem
    # perturbar o contexto de quem chamou.
    from uuid import UUID as _UUID
    from app.tenancy.context import (
        clear_current_tenant as _clear_tenant,
        get_current_tenant as _get_tenant,
        set_current_tenant as _set_tenant,
    )

    _tenant_anterior = _get_tenant()
    _set_tenant(_UUID(tenant_id_str))
    try:
        return _run_onboarding_steps(
            db,
            tenant_id_str,
            user_id_int,
            bundle_code,
            bundle_version,
            dry_run,
            include_products,
            strict_required,
            result,
        )
    except SQLAlchemyError as exc:
        raise TenantOnboardingError(
            f"Falha no onboarding do tenant {tenant_id_str}: {exc}"
        ) from exc
    finally:
        if _tenant_anterior is not None:
            _set_tenant(_tenant_anterior)
        else:
            _clear_tenant()
