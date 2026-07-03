"""Delivery route and order helpers for the operational demo seed."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_data import SaleScenario, money
from app.scripts.seed_demo_operacional_db import _scalar


def _insert_route(
    db,
    *,
    tenant_id: str,
    user_id: int,
    scenario: SaleScenario,
    sale_id: int,
    driver_id: int,
    sale_dt: datetime,
    address: str,
) -> None:
    started = sale_dt + timedelta(hours=1)
    finished = (
        started + timedelta(minutes=45)
        if scenario.route_status == "concluida"
        else None
    )
    route_id = int(
        _scalar(
            db,
            """
            INSERT INTO rotas_entrega (
                numero, venda_id, entregador_id, endereco_destino,
                ponto_inicial_rota, ponto_final_rota, retorna_origem,
                distancia_prevista, distancia_real, custo_previsto, custo_real,
                custo_moto, taxa_entrega_cliente, valor_repasse_entregador,
                tentativas, moto_da_loja, km_inicial, km_final, status,
                created_by, data_inicio, data_conclusao, observacoes,
                tenant_id, created_at, updated_at
            )
            VALUES (
                :number, :sale_id, :driver_id, :address,
                'Av. CorePet Demo, 100 - Centro',
                'Av. CorePet Demo, 100 - Centro', true,
                :distance, :distance_real, :cost, :cost_real,
                :moto_cost, :delivery_fee, :driver_share,
                1, true, 12450.0, :km_final, :status,
                :user_id, :started, :finished, :obs,
                :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "number": scenario.route_number,
                "sale_id": sale_id,
                "driver_id": driver_id,
                "address": address,
                "distance": scenario.delivery_km,
                "distance_real": scenario.delivery_km
                if scenario.route_status == "concluida"
                else None,
                "cost": money(scenario.delivery_km * Decimal("2.20")),
                "cost_real": money(scenario.delivery_km * Decimal("2.20"))
                if scenario.route_status == "concluida"
                else None,
                "moto_cost": money(scenario.delivery_km * Decimal("0.85")),
                "delivery_fee": scenario.delivery_fee,
                "driver_share": scenario.driver_share,
                "km_final": Decimal("12450.0") + scenario.delivery_km
                if scenario.route_status == "concluida"
                else None,
                "status": scenario.route_status,
                "user_id": user_id,
                "started": started
                if scenario.route_status in {"em_rota", "concluida"}
                else None,
                "finished": finished,
                "obs": f"Demo operacional - rota {scenario.route_status}",
                "tenant_id": tenant_id,
            },
        )
    )
    db.execute(
        text(
            """
            INSERT INTO rotas_entrega_paradas (
                rota_id, venda_id, ordem, endereco, distancia_acumulada,
                tempo_acumulado, status, data_entrega, observacoes,
                km_entrega, tenant_id, created_at, updated_at
            )
            VALUES (
                :route_id, :sale_id, 1, :address, :distance,
                :seconds, :stop_status, :delivered_at,
                'Demo operacional - parada de entrega',
                :km_entrega, :tenant_id, now(), now()
            )
            """
        ),
        {
            "route_id": route_id,
            "sale_id": sale_id,
            "address": address,
            "distance": scenario.delivery_km,
            "seconds": int(float(scenario.delivery_km) * 360),
            "stop_status": "entregue"
            if scenario.route_status == "concluida"
            else "pendente",
            "delivered_at": finished,
            "km_entrega": Decimal("12450.0") + scenario.delivery_km
            if scenario.route_status == "concluida"
            else None,
            "tenant_id": tenant_id,
        },
    )


def _insert_order(
    db,
    *,
    tenant_id: str,
    scenario: SaleScenario,
    client_id: int,
    total: Decimal,
    items: list[dict[str, Any]],
) -> None:
    db.execute(
        text(
            """
            INSERT INTO pedidos (
                pedido_id, cliente_id, tenant_id, total, origem, status,
                tipo_retirada, palavra_chave_retirada, is_drive,
                payment_provider, payment_preference_id, payment_url, created_at
            )
            VALUES (
                :order_id, :client_id, :tenant_id, :total, :origin, :status,
                :tipo_retirada, :palavra_chave, false,
                'demo', :preference, :payment_url, now()
            )
            """
        ),
        {
            "order_id": scenario.order_id,
            "client_id": client_id,
            "tenant_id": tenant_id,
            "total": float(total),
            "origin": scenario.order_origin,
            "status": scenario.order_status,
            "tipo_retirada": "proprio" if not scenario.delivery else None,
            "palavra_chave": "core-demo" if not scenario.delivery else None,
            "preference": f"PREF-{scenario.order_id}",
            "payment_url": f"https://corepet.com.br/demo/pay/{scenario.order_id}",
        },
    )
    for item in items:
        db.execute(
            text(
                """
                INSERT INTO pedido_itens (
                    pedido_id, produto_id, nome, quantidade, preco_unitario,
                    subtotal, tenant_id, created_at
                )
                VALUES (
                    :order_id, :product_id, :name, :qty, :unit_price,
                    :subtotal, :tenant_id, now()
                )
                """
            ),
            {
                "order_id": scenario.order_id,
                "product_id": item["product"]["id"],
                "name": item["product"]["nome"],
                "qty": int(item["qty"]),
                "unit_price": float(item["unit_price"]),
                "subtotal": float(item["subtotal"]),
                "tenant_id": tenant_id,
            },
        )
