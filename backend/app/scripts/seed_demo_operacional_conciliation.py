"""Create a safe, reversible Stone reconciliation scenario for the Demo tenant."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any

from app.scripts.seed_demo_operacional_db import _all_mappings, _scalar


def insert_demo_card_conciliation(
    db,
    *,
    tenant_id: str,
    user_id: int,
    operator_id: int,
    base_date: date,
) -> dict[str, Any]:
    """Mirror pending Demo card payments into a synthetic operator import.

    One NSU intentionally has a different installment count, and one is an
    operator orphan. This demonstrates matches, divergence and an exception
    without modifying a real tenant or importing real bank data.
    """

    sales = _all_mappings(
        db,
        """
        SELECT
            v.numero_venda,
            v.data_venda::date AS data_venda,
            vp.nsu_cartao AS nsu,
            vp.bandeira,
            COALESCE(vp.numero_parcelas, 1) AS parcelas,
            vp.valor AS valor_bruto
        FROM vendas v
        JOIN venda_pagamentos vp
          ON vp.venda_id = v.id AND vp.tenant_id = v.tenant_id
        WHERE v.tenant_id = :tenant_id
          AND v.numero_venda LIKE 'DEMO-VEN-%'
          AND v.status = 'finalizada'
          AND vp.operadora_id = :operator_id
          AND vp.status_conciliacao = 'nao_conciliado'
        ORDER BY v.numero_venda
        LIMIT 8
        """,
        {"tenant_id": tenant_id, "operator_id": operator_id},
    )

    rows: list[dict[str, Any]] = []
    for index, sale in enumerate(sales):
        gross = Decimal(str(sale["valor_bruto"] or 0))
        rows.append(
            {
                "nsu": sale["nsu"],
                "data_venda": sale["data_venda"].isoformat(),
                "bandeira": sale["bandeira"],
                "parcelas": int(sale["parcelas"] or 1) + (1 if index == 2 else 0),
                "valor_bruto": float(gross),
                "valor_liquido": float(
                    (gross * Decimal("0.9651")).quantize(Decimal("0.01"))
                ),
                "taxa_mdr": 3.49,
                "status_conciliacao": "nao_conciliado",
            }
        )

    rows.append(
        {
            "nsu": "DEMO-NSU-ORFAO-001",
            "data_venda": base_date.isoformat(),
            "bandeira": "visa",
            "parcelas": 1,
            "valor_bruto": 157.9,
            "valor_liquido": 152.39,
            "taxa_mdr": 3.49,
            "status_conciliacao": "nao_conciliado",
        }
    )

    digest = hashlib.md5(  # noqa: S324 - deduplication marker, not cryptography
        f"corepet-demo-stone-{tenant_id}".encode("utf-8")
    ).hexdigest()
    file_id = int(
        _scalar(
            db,
            """
            INSERT INTO arquivos_evidencia (
                nome_original, tipo_arquivo, adquirente, caminho_storage,
                tamanho_bytes, hash_md5, periodo_inicio, periodo_fim,
                total_linhas, total_registros_processados, criado_em,
                criado_por_id, tenant_id
            ) VALUES (
                'DEMO_STONE_VENDAS.csv', 'vendas', 'Stone Demo',
                'demo://conciliacao/stone-vendas.csv', 0, :digest,
                :base_date, :base_date, :total, :total, now(),
                :user_id, :tenant_id
            ) RETURNING id
            """,
            {
                "digest": digest,
                "base_date": base_date,
                "total": len(rows),
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )
    total_value = sum(Decimal(str(row["valor_bruto"])) for row in rows)
    import_id = int(
        _scalar(
            db,
            """
            INSERT INTO conciliacao_importacoes (
                arquivo_evidencia_id, adquirente_template_id, tipo_importacao,
                data_referencia, total_registros, total_valor,
                status_importacao, resumo, criado_em, criado_por_id, tenant_id
            ) VALUES (
                :file_id, NULL, 'vendas', :base_date, :total, :total_value,
                'processada', CAST(:summary AS JSONB), now(), :user_id, :tenant_id
            ) RETURNING id
            """,
            {
                "file_id": file_id,
                "base_date": base_date,
                "total": len(rows),
                "total_value": total_value,
                "summary": json.dumps(
                    {
                        "demo_operacional": True,
                        "conciliado": False,
                        "operadora_id": operator_id,
                        "total_linhas": len(rows),
                        "dados_parseados": rows,
                    }
                ),
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )
    return {
        "file_id": file_id,
        "import_id": import_id,
        "pending_card_sales": len(sales),
        "operator_rows": len(rows),
    }
