"""Dados de vitrine para calculadora, lembretes e analise da conta Demo."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.estoque_validade_service import EstoqueValidadeService
from app.models import Tenant
from app.scripts.seed_demo_operacional_catalog import _ensure_demo_product_category
from app.scripts.seed_demo_operacional_db import _scalar
from app.scripts.seed_demo_operacional_showcase_data import (
    DEMO_RATION_SHOWCASE_PRODUCTS,
    DEMO_REMINDER_SCENARIOS,
    DEMO_VALIDITY_SCENARIOS,
)
from app.tenancy.context import tenant_context


def _ensure_named_option(
    db,
    *,
    table_name: str,
    tenant_id: str,
    name: str,
    order: int,
) -> int:
    allowed_tables = {
        "linhas_racao",
        "portes_animal",
        "fases_publico",
        "sabores_proteina",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Tabela de opcao de racao nao permitida: {table_name}")

    existing = _scalar(
        db,
        f"""
        SELECT id FROM {table_name}
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        ORDER BY id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": name},
    )
    if existing:
        db.execute(
            text(
                f"""
                UPDATE {table_name}
                SET ativo = true, ordem = :order, updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :id
                """
            ),
            {"tenant_id": tenant_id, "id": int(existing), "order": order},
        )
        return int(existing)

    return int(
        _scalar(
            db,
            f"""
            INSERT INTO {table_name} (
                nome, descricao, ordem, ativo, tenant_id, created_at, updated_at
            ) VALUES (
                :name, 'Opcao preparada para a apresentacao da conta Demo',
                :order, true, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {"tenant_id": tenant_id, "name": name, "order": order},
        )
    )


def _ensure_weight_option(db, *, tenant_id: str, weight: Decimal) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM apresentacoes_peso
        WHERE tenant_id = :tenant_id AND abs(peso_kg - :weight) < 0.0001
        ORDER BY id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "weight": weight},
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE apresentacoes_peso
                SET ativo = true, descricao = :description, updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :id
                """
            ),
            {
                "tenant_id": tenant_id,
                "id": int(existing),
                "description": f"{weight:g} kg",
            },
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO apresentacoes_peso (
                peso_kg, descricao, ordem, ativo, tenant_id, created_at, updated_at
            ) VALUES (
                :weight, :description, :order, true, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "tenant_id": tenant_id,
                "weight": weight,
                "description": f"{weight:g} kg",
                "order": int(weight * 10),
            },
        )
    )


def _ensure_demo_brand(db, *, tenant_id: str, user_id: int, name: str) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM marcas
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        ORDER BY id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": name},
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE marcas
                SET ativo = true,
                    descricao = 'Marca ficticia para demonstracoes do CorePet',
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :id
                """
            ),
            {"tenant_id": tenant_id, "id": int(existing)},
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO marcas (
                nome, descricao, user_id, ativo, tenant_id, created_at, updated_at
            ) VALUES (
                :name, 'Marca ficticia para demonstracoes do CorePet',
                :user_id, true, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {"tenant_id": tenant_id, "user_id": user_id, "name": name},
        )
    )


def _consumption_table(product: dict[str, Any]) -> str:
    rows = {
        weight: (
            {"2m": amount, "4m": amount, "6m": amount, "12m": amount, "adulto": amount}
            if product["category"] == "filhote"
            else {"adulto": amount}
        )
        for weight, amount in product["consumption"].items()
    }
    return json.dumps(
        {
            "tipo": "filhote_peso_adulto"
            if product["category"] == "filhote"
            else "adulto_peso_atual",
            "dados": rows,
        },
        ensure_ascii=False,
    )


def _ensure_showcase_product(
    db,
    *,
    tenant_id: str,
    user_id: int,
    category_id: int,
    product: dict[str, Any],
    brand_id: int,
    line_id: int,
    size_id: int,
    phase_id: int,
    flavor_id: int,
    weight_id: int,
) -> dict[str, Any]:
    existing = _scalar(
        db,
        """
        SELECT id FROM produtos
        WHERE tenant_id = :tenant_id AND lower(trim(codigo)) = lower(:code)
        ORDER BY id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "code": product["code"]},
    )
    payload = {
        **product,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "category_id": category_id,
        "brand_id": brand_id,
        "line_id": line_id,
        "size_id": size_id,
        "phase_id": phase_id,
        "flavor_id": flavor_id,
        "weight_id": weight_id,
        "size_json": json.dumps([product["size"]], ensure_ascii=False),
        "phase_json": json.dumps([product["phase"]], ensure_ascii=False),
        "consumption_table": _consumption_table(product),
        "nutrition_table": json.dumps(
            {"proteina": 28, "gordura": 14, "fibra": 4, "umidade": 10},
            ensure_ascii=False,
        ),
    }

    if existing:
        db.execute(
            text(
                """
                UPDATE produtos
                SET nome = :name, tipo = 'racao', situacao = true,
                    tipo_produto = 'SIMPLES', is_parent = false, is_sellable = true,
                    descricao_curta = 'Produto ficticio completo para a apresentacao do CorePet.',
                    categoria_id = :category_id, marca_id = :brand_id,
                    preco_custo = :cost, preco_venda = :price,
                    preco_ecommerce = :price, preco_app = :price,
                    estoque_atual = :stock, estoque_minimo = :minimum_stock,
                    estoque_fisico = :stock, estoque_ecommerce = 0,
                    unidade = 'UN', controle_lote = true,
                    tem_recorrencia = :recurring, tipo_recorrencia = 'monthly',
                    intervalo_dias = :interval_days,
                    observacoes_recorrencia = 'Reposicao programada para demonstracao da conta Demo.',
                    especie_compativel = :species,
                    classificacao_racao = :classification,
                    peso_embalagem = :weight, categoria_racao = :category,
                    especies_indicadas = :species,
                    tabela_consumo = :consumption_table,
                    tabela_nutricional = :nutrition_table,
                    porte_animal = CAST(:size_json AS jsonb),
                    fase_publico = CAST(:phase_json AS jsonb),
                    sabor_proteina = :flavor,
                    linha_racao_id = :line_id, porte_animal_id = :size_id,
                    fase_publico_id = :phase_id, sabor_proteina_id = :flavor_id,
                    apresentacao_peso_id = :weight_id,
                    auto_classificar_nome = false,
                    anunciar_ecommerce = false, anunciar_app = false,
                    ativo = true, deleted_at = NULL, updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :id
                """
            ),
            {**payload, "id": int(existing)},
        )
        product_id = int(existing)
    else:
        product_id = int(
            _scalar(
                db,
                """
                INSERT INTO produtos (
                    codigo, nome, tipo, situacao, tipo_produto, is_parent, is_sellable,
                    descricao_curta, categoria_id, marca_id, preco_custo, preco_venda,
                    preco_ecommerce, preco_app, estoque_atual, estoque_minimo,
                    estoque_fisico, estoque_ecommerce, unidade, controle_lote,
                    tem_recorrencia, tipo_recorrencia, intervalo_dias,
                    observacoes_recorrencia, especie_compativel,
                    classificacao_racao, peso_embalagem, categoria_racao,
                    especies_indicadas, tabela_consumo, tabela_nutricional,
                    porte_animal, fase_publico, sabor_proteina,
                    linha_racao_id, porte_animal_id, fase_publico_id,
                    sabor_proteina_id, apresentacao_peso_id,
                    auto_classificar_nome, anunciar_ecommerce, anunciar_app,
                    ativo, user_id, tenant_id, created_at, updated_at
                ) VALUES (
                    :code, :name, 'racao', true, 'SIMPLES', false, true,
                    'Produto ficticio completo para a apresentacao do CorePet.',
                    :category_id, :brand_id, :cost, :price,
                    :price, :price, :stock, :minimum_stock,
                    :stock, 0, 'UN', true,
                    :recurring, 'monthly', :interval_days,
                    'Reposicao programada para demonstracao da conta Demo.', :species,
                    :classification, :weight, :category,
                    :species, :consumption_table, :nutrition_table,
                    CAST(:size_json AS jsonb), CAST(:phase_json AS jsonb), :flavor,
                    :line_id, :size_id, :phase_id,
                    :flavor_id, :weight_id,
                    false, false, false,
                    true, :user_id, :tenant_id, now(), now()
                )
                RETURNING id
                """,
                payload,
            )
        )

    return {
        "id": product_id,
        "code": product["code"],
        "name": product["name"],
        "price": product["price"],
        "cost": product["cost"],
    }


def _ensure_showcase_products(
    db, *, tenant_id: str, user_id: int
) -> dict[str, dict[str, Any]]:
    category_id = _ensure_demo_product_category(
        db, tenant_id=tenant_id, user_id=user_id
    )
    option_cache: dict[tuple[str, str], int] = {}
    brand_cache: dict[str, int] = {}
    weight_cache: dict[Decimal, int] = {}
    result: dict[str, dict[str, Any]] = {}

    for index, product in enumerate(DEMO_RATION_SHOWCASE_PRODUCTS, start=1):

        def option(table_name: str, name: str) -> int:
            key = (table_name, name)
            if key not in option_cache:
                option_cache[key] = _ensure_named_option(
                    db,
                    table_name=table_name,
                    tenant_id=tenant_id,
                    name=name,
                    order=index,
                )
            return option_cache[key]

        if product["brand"] not in brand_cache:
            brand_cache[product["brand"]] = _ensure_demo_brand(
                db, tenant_id=tenant_id, user_id=user_id, name=product["brand"]
            )
        if product["weight"] not in weight_cache:
            weight_cache[product["weight"]] = _ensure_weight_option(
                db, tenant_id=tenant_id, weight=product["weight"]
            )

        saved = _ensure_showcase_product(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            category_id=category_id,
            product=product,
            brand_id=brand_cache[product["brand"]],
            line_id=option("linhas_racao", product["line"]),
            size_id=option("portes_animal", product["size"]),
            phase_id=option("fases_publico", product["phase"]),
            flavor_id=option("sabores_proteina", product["flavor"]),
            weight_id=weight_cache[product["weight"]],
        )
        result[product["code"]] = saved

    return result


def _ensure_demo_pets(
    db,
    *,
    tenant_id: str,
    user_id: int,
    people: dict[str, int],
    base_date: date,
) -> dict[str, dict[str, int]]:
    pet_profiles = (
        {
            "key": "thor",
            "code": "DEMO-PET-001",
            "name": "Thor",
            "client": "ana",
            "species": "Cao",
            "breed": "Vira-lata",
            "sex": "macho",
            "weight": 18.4,
            "size": "medio",
            "birth": datetime.combine(base_date - timedelta(days=4 * 365), time(12, 0)),
        },
        {
            "key": "luna",
            "code": "DEMO-PET-002",
            "name": "Luna",
            "client": "joao",
            "species": "Cao",
            "breed": "Shih-tzu",
            "sex": "femea",
            "weight": 7.2,
            "size": "pequeno",
            "birth": datetime.combine(base_date - timedelta(days=2 * 365), time(12, 0)),
        },
        {
            "key": "mia",
            "code": "DEMO-PET-003",
            "name": "Mia",
            "client": "maria",
            "species": "Gato",
            "breed": "Sem raca definida",
            "sex": "femea",
            "weight": 4.8,
            "size": "pequeno",
            "birth": datetime.combine(base_date - timedelta(days=3 * 365), time(12, 0)),
        },
    )
    result: dict[str, dict[str, int]] = {}
    for profile in pet_profiles:
        existing = _scalar(
            db,
            """
            SELECT id FROM pets
            WHERE tenant_id = :tenant_id AND codigo = :code
            ORDER BY id
            LIMIT 1
            """,
            {"tenant_id": tenant_id, "code": profile["code"]},
        )
        payload = {
            **profile,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "client_id": people[profile["client"]],
        }
        if existing:
            db.execute(
                text(
                    """
                    UPDATE pets
                    SET cliente_id = :client_id, user_id = :user_id,
                        nome = :name, especie = :species, raca = :breed,
                        sexo = :sex, peso = :weight, porte = :size,
                        data_nascimento = :birth, ativo = true, updated_at = now()
                    WHERE tenant_id = :tenant_id AND id = :id
                    """
                ),
                {**payload, "id": int(existing)},
            )
            pet_id = int(existing)
        else:
            pet_id = int(
                _scalar(
                    db,
                    """
                    INSERT INTO pets (
                        cliente_id, user_id, codigo, nome, especie, raca, sexo,
                        peso, porte, data_nascimento, ativo, tenant_id,
                        created_at, updated_at
                    ) VALUES (
                        :client_id, :user_id, :code, :name, :species, :breed, :sex,
                        :weight, :size, :birth, true, :tenant_id, now(), now()
                    )
                    RETURNING id
                    """,
                    payload,
                )
            )
        result[profile["key"]] = {"id": pet_id, "client_id": int(payload["client_id"])}

    return result


def _insert_demo_reminders(
    db,
    *,
    tenant_id: str,
    user_id: int,
    products: dict[str, dict[str, Any]],
    pets: dict[str, dict[str, int]],
    base_date: date,
) -> list[int]:
    ids: list[int] = []
    reference = datetime.combine(base_date, time(10, 0), tzinfo=timezone.utc)
    for index, scenario in enumerate(DEMO_REMINDER_SCENARIOS, start=1):
        product = products[scenario["product"]]
        pet = pets[scenario["pet"]]
        due_at = reference + timedelta(days=scenario["days"])
        reminder_id = _scalar(
            db,
            """
            INSERT INTO lembretes (
                user_id, cliente_id, pet_id, produto_id,
                data_compra, data_proxima_dose, data_notificacao_7_dias,
                status, metodo_notificacao, notificacao_enviada,
                origem_intervalo, intervalo_estimado_dias,
                confianca_recorrencia, amostras_recorrencia,
                observacoes, quantidade_recomendada, preco_estimado,
                dose_atual, dose_total, historico_doses,
                tenant_id, created_at, updated_at
            ) VALUES (
                :user_id, :client_id, :pet_id, :product_id,
                :purchase_at, :due_at, :notification_at,
                'pendente', 'app', false,
                'configurado', :interval_days,
                0.94, 4,
                :notes, 1, :price,
                1, NULL, :history,
                :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "client_id": pet["client_id"],
                "pet_id": pet["id"],
                "product_id": product["id"],
                "purchase_at": due_at - timedelta(days=30),
                "due_at": due_at,
                "notification_at": due_at - timedelta(days=7),
                "interval_days": 30,
                "notes": f"Demo operacional - lembrete recorrente {index}",
                "price": product["price"],
                "history": json.dumps(
                    [
                        {
                            "dose": 1,
                            "data": (due_at - timedelta(days=30)).isoformat(),
                            "comprou": True,
                        }
                    ],
                    ensure_ascii=False,
                ),
            },
        )
        ids.append(int(reminder_id))
    return ids


def _insert_demo_validity_alerts(
    db,
    *,
    tenant_id: str,
    user_id: int,
    products: dict[str, dict[str, Any]],
    base_date: date,
) -> dict[str, Any]:
    updated_tenant = db.execute(
        text(
            """
            UPDATE tenants
            SET protecao_validade_ativa = true, dias_alerta_validade = 15
            WHERE id = :tenant_id
            RETURNING id
            """
        ),
        {"tenant_id": tenant_id},
    ).scalar()
    if not updated_tenant:
        raise ValueError("Tenant da conta Demo nao encontrado")

    reference = datetime.combine(base_date, time(10, 0), tzinfo=timezone.utc)
    lot_ids: list[int] = []
    for index, scenario in enumerate(DEMO_VALIDITY_SCENARIOS, start=1):
        product = products[scenario["product"]]
        expiry_at = reference + timedelta(days=scenario["days"])
        lot_id = _scalar(
            db,
            """
            INSERT INTO produto_lotes (
                produto_id, nome_lote, data_fabricacao, data_validade,
                deposito, quantidade_inicial, quantidade_disponivel,
                quantidade_reservada, limite_dias, status, ordem_entrada,
                custo_unitario, tenant_id, created_at, updated_at
            ) VALUES (
                :product_id, :lot, :manufactured_at, :expiry_at,
                'Estoque Demo', :quantity, :quantity,
                0, 15, 'ativo', :entry_order,
                :cost, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "tenant_id": tenant_id,
                "product_id": product["id"],
                "lot": scenario["lot"],
                "manufactured_at": reference - timedelta(days=120),
                "expiry_at": expiry_at,
                "quantity": scenario["quantity"],
                "entry_order": int(reference.timestamp()) + index,
                "cost": product["cost"],
            },
        )
        lot_ids.append(int(lot_id))

    with tenant_context(tenant_id):
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        processed = EstoqueValidadeService.processar_lotes_em_risco(
            db=db,
            tenant=tenant,
            user_id=user_id,
            agora=reference,
            origem="demo_operacional",
        )
    return {
        "lots": lot_ids,
        "alerts": [int(item.id) for item in processed["bloqueios"]],
    }


def ensure_demo_showcase_data(
    db,
    *,
    tenant_id: str,
    user_id: int,
    people: dict[str, int],
    base_date: date,
) -> dict[str, Any]:
    """Monta uma vitrine idempotente, limitada ao tenant da conta Demo."""

    products = _ensure_showcase_products(db, tenant_id=tenant_id, user_id=user_id)
    pets = _ensure_demo_pets(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        people=people,
        base_date=base_date,
    )
    reminders = _insert_demo_reminders(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        products=products,
        pets=pets,
        base_date=base_date,
    )
    validity = _insert_demo_validity_alerts(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        products=products,
        base_date=base_date,
    )
    return {
        "products": [product["id"] for product in products.values()],
        "pets": [pet["id"] for pet in pets.values()],
        "reminders": reminders,
        "validity": validity,
    }
