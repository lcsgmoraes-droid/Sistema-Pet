from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.tenant_onboarding_core import OnboardingResult
from app.services.tenant_onboarding_item_installs import (
    _ensure_known_target_table,
    _record_template_item_install,
    _mapped_template_row_id,
)
from app.services.tenant_onboarding_sql import _execute_insert, _scalar


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
