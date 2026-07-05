"""Reparos conservadores de consistencia financeira por tenant."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.financeiro.contas_receber_service import ContasReceberService
from app.notas_entrada.xml_parser import parse_nfe_xml


CENT = Decimal("0.01")
CONFIRM_TOKEN_REPARO_FINANCEIRO = "REPARAR_FINANCEIRO_HISTORICO"


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _money_str(value: Any) -> str:
    return f"{_money(value):.2f}"


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text_value = str(value)
    return date.fromisoformat(text_value[:10])


def _date_str(value: Any) -> str | None:
    if value is None:
        return None
    return _as_date(value).isoformat()


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def _one(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def _resolve_forma_pagamento(
    db: Session, *, tenant_id: str, forma_pagamento: str
) -> dict[str, Any] | None:
    return _one(
        db,
        """
        SELECT id, nome, tipo, prazo_dias, prazo_recebimento
        FROM formas_pagamento
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND (
                lower(nome) = lower(:forma_pagamento)
             OR lower(tipo) = lower(:forma_pagamento)
          )
        ORDER BY
            CASE WHEN lower(nome) = lower(:forma_pagamento) THEN 0 ELSE 1 END,
            id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "forma_pagamento": forma_pagamento},
    )


def _resolve_dre_subcategoria_id(db: Session, *, tenant_id: str) -> int:
    row = _one(
        db,
        """
        SELECT dre_subcategoria_id
        FROM contas_receber
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND dre_subcategoria_id IS NOT NULL
        GROUP BY dre_subcategoria_id
        ORDER BY COUNT(*) DESC, dre_subcategoria_id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    return int(row["dre_subcategoria_id"]) if row else 1


def _resolve_tipo_produto_revenda_id(db: Session, *, tenant_id: str) -> int | None:
    row = _one(
        db,
        """
        SELECT id
        FROM tipo_despesas
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND lower(nome) IN (
                lower('Produto para Revenda'),
                lower('Fornecedor de Produto para Revenda')
          )
        ORDER BY id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    if row:
        return int(row["id"])

    row = _one(
        db,
        """
        SELECT id
        FROM tipo_despesas
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND lower(nome) LIKE '%produto%'
          AND lower(nome) LIKE '%revenda%'
        ORDER BY nome ASC, id ASC
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    return int(row["id"]) if row else None


def _prazo_forma(forma: dict[str, Any] | None) -> int:
    if not forma:
        return 0
    return int(forma.get("prazo_dias") or forma.get("prazo_recebimento") or 0)


def _is_recebimento_imediato(
    *, forma_nome: str, forma: dict[str, Any] | None, numero_parcelas: int
) -> bool:
    if numero_parcelas > 1:
        return False
    tipo = str((forma or {}).get("tipo") or forma_nome or "").lower()
    nome = str((forma or {}).get("nome") or forma_nome or "").lower()
    imediatos = {"pix", "dinheiro", "debito", "débito", "cartao_debito"}
    if tipo in imediatos or nome in imediatos:
        return True
    return forma is not None and _prazo_forma(forma) == 0


def _fetch_vendas_sem_contas_receber(
    db: Session, params: dict[str, Any]
) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            v.id AS venda_id,
            v.numero_venda AS numero_venda,
            v.cliente_id AS cliente_id,
            v.user_id AS user_id,
            v.data_venda AS data_venda,
            v.total AS total_venda,
            COALESCE(v.canal, 'loja_fisica') AS canal
        FROM vendas v
        WHERE CAST(v.tenant_id AS TEXT) = :tenant_id
          AND v.data_venda >= :data_inicio
          AND v.data_venda < :data_fim
          AND v.status = 'finalizada'
          AND NOT EXISTS (
              SELECT 1
              FROM contas_receber cr
              WHERE CAST(cr.tenant_id AS TEXT) = CAST(v.tenant_id AS TEXT)
                AND cr.venda_id = v.id
                AND COALESCE(cr.status, '') NOT IN ('cancelado', 'cancelada')
          )
        ORDER BY v.data_venda ASC, v.id ASC
        """,
        params,
    )


def _fetch_pagamentos_venda(
    db: Session, *, tenant_id: str, venda_id: int
) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            id AS venda_pagamento_id,
            forma_pagamento,
            valor,
            COALESCE(numero_parcelas, 1) AS numero_parcelas,
            status,
            data_pagamento
        FROM venda_pagamentos
        WHERE CAST(tenant_id AS TEXT) = :tenant_id
          AND venda_id = :venda_id
        ORDER BY id ASC
        """,
        {"tenant_id": tenant_id, "venda_id": venda_id},
    )


def _build_cr_missing_actions(
    db: Session, *, tenant_id: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    dre_subcategoria_id = _resolve_dre_subcategoria_id(db, tenant_id=tenant_id)

    for venda in _fetch_vendas_sem_contas_receber(db, params):
        pagamentos = _fetch_pagamentos_venda(
            db, tenant_id=tenant_id, venda_id=int(venda["venda_id"])
        )
        if not pagamentos:
            skipped.append(
                {
                    "tipo": "venda_sem_pagamento",
                    "venda_id": int(venda["venda_id"]),
                    "numero_venda": venda["numero_venda"],
                    "motivo": "Venda finalizada sem venda_pagamentos para reconstruir CR.",
                }
            )
            continue

        for pagamento in pagamentos:
            forma_nome = str(pagamento["forma_pagamento"])
            forma = _resolve_forma_pagamento(
                db, tenant_id=tenant_id, forma_pagamento=forma_nome
            )
            numero_parcelas = max(int(pagamento["numero_parcelas"] or 1), 1)
            valor_total = _money(pagamento["valor"])
            valores = ContasReceberService._distribuir_valor_parcelas(
                valor_total, numero_parcelas
            )
            pagamento_date = _as_date(
                pagamento["data_pagamento"] or venda["data_venda"]
            )
            emissao = _as_date(venda["data_venda"])
            prazo = _prazo_forma(forma)
            recebido = _is_recebimento_imediato(
                forma_nome=forma_nome,
                forma=forma,
                numero_parcelas=numero_parcelas,
            )

            for idx, valor_parcela in enumerate(valores, start=1):
                if numero_parcelas > 1:
                    vencimento = pagamento_date + timedelta(days=30 * idx)
                    status = "pendente"
                    valor_recebido = Decimal("0.00")
                    data_recebimento = None
                elif recebido:
                    vencimento = pagamento_date
                    status = "recebido"
                    valor_recebido = valor_parcela
                    data_recebimento = pagamento_date
                else:
                    vencimento = pagamento_date + timedelta(days=prazo)
                    status = "pendente"
                    valor_recebido = Decimal("0.00")
                    data_recebimento = None

                actions.append(
                    {
                        "tipo": "criar_conta_receber",
                        "venda_id": int(venda["venda_id"]),
                        "numero_venda": venda["numero_venda"],
                        "cliente_id": venda["cliente_id"],
                        "forma_pagamento_id": int(forma["id"]) if forma else None,
                        "dre_subcategoria_id": dre_subcategoria_id,
                        "canal": venda["canal"] or "loja_fisica",
                        "valor_original": _money_str(valor_parcela),
                        "valor_recebido": _money_str(valor_recebido),
                        "valor_final": _money_str(valor_parcela),
                        "data_emissao": emissao.isoformat(),
                        "data_vencimento": vencimento.isoformat(),
                        "data_recebimento": _date_str(data_recebimento),
                        "status": status,
                        "eh_parcelado": numero_parcelas > 1,
                        "numero_parcela": idx if numero_parcelas > 1 else None,
                        "total_parcelas": numero_parcelas
                        if numero_parcelas > 1
                        else None,
                        "documento": f"VENDA-{venda['venda_id']}",
                        "descricao": (
                            f"Venda {venda['numero_venda']} - {forma_nome}"
                            if numero_parcelas == 1
                            else (
                                f"Venda {venda['numero_venda']} - "
                                f"Parcela {idx}/{numero_parcelas}"
                            )
                        ),
                        "observacoes": (
                            "Reparo financeiro historico: CR reconstruido "
                            "a partir de venda_pagamentos."
                        ),
                        "user_id": int(venda["user_id"]),
                        "tenant_id": tenant_id,
                    }
                )

    return actions, skipped


def _fetch_centavo_rows(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        WITH vendas_periodo AS (
            SELECT id, numero_venda, total, data_venda
            FROM vendas
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND data_venda >= :data_inicio
              AND data_venda < :data_fim
              AND status = 'finalizada'
        ),
        cr_por_venda AS (
            SELECT venda_id, COUNT(*) AS qtd_cr, COALESCE(SUM(valor_final), 0) AS total_cr
            FROM contas_receber
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND venda_id IN (SELECT id FROM vendas_periodo)
              AND COALESCE(status, '') NOT IN ('cancelado', 'cancelada')
            GROUP BY venda_id
        )
        SELECT
            v.id AS venda_id,
            v.numero_venda AS numero_venda,
            v.total AS total_venda,
            c.total_cr AS total_cr,
            c.qtd_cr AS qtd_cr
        FROM vendas_periodo v
        JOIN cr_por_venda c ON c.venda_id = v.id
        WHERE c.qtd_cr > 0
          AND c.total_cr <> v.total
          AND ABS(c.total_cr - v.total) <= 0.05
        ORDER BY v.data_venda ASC, v.id ASC
        """,
        params,
    )


def _build_centavo_actions(
    db: Session, *, tenant_id: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for row in _fetch_centavo_rows(db, params):
        ajuste = _money(row["total_venda"]) - _money(row["total_cr"])
        target = _one(
            db,
            """
            SELECT id, valor_original, valor_final
            FROM contas_receber cr
            WHERE CAST(cr.tenant_id AS TEXT) = :tenant_id
              AND cr.venda_id = :venda_id
              AND cr.status = 'pendente'
              AND COALESCE(cr.valor_recebido, 0) = 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM recebimentos r
                  WHERE CAST(r.tenant_id AS TEXT) = CAST(cr.tenant_id AS TEXT)
                    AND r.conta_receber_id = cr.id
              )
            ORDER BY COALESCE(cr.numero_parcela, 0) DESC, cr.id DESC
            LIMIT 1
            """,
            {
                "tenant_id": tenant_id,
                "venda_id": int(row["venda_id"]),
            },
        )
        if not target:
            skipped.append(
                {
                    "tipo": "ajuste_centavos",
                    "venda_id": int(row["venda_id"]),
                    "numero_venda": row["numero_venda"],
                    "ajuste_sugerido": _money_str(ajuste),
                    "motivo": "Nenhuma parcela pendente e sem recebimento para ajuste seguro.",
                }
            )
            continue

        valor_original_depois = _money(target["valor_original"]) + ajuste
        valor_final_depois = _money(target["valor_final"]) + ajuste
        if valor_original_depois <= 0 or valor_final_depois <= 0:
            skipped.append(
                {
                    "tipo": "ajuste_centavos",
                    "venda_id": int(row["venda_id"]),
                    "numero_venda": row["numero_venda"],
                    "conta_receber_id": int(target["id"]),
                    "ajuste_sugerido": _money_str(ajuste),
                    "motivo": "Ajuste deixaria valor da parcela menor ou igual a zero.",
                }
            )
            continue

        actions.append(
            {
                "tipo": "ajustar_centavos_conta_receber",
                "venda_id": int(row["venda_id"]),
                "numero_venda": row["numero_venda"],
                "conta_receber_id": int(target["id"]),
                "total_venda": _money_str(row["total_venda"]),
                "total_cr_antes": _money_str(row["total_cr"]),
                "ajuste": _money_str(ajuste),
                "valor_original_antes": _money_str(target["valor_original"]),
                "valor_original_depois": _money_str(valor_original_depois),
                "valor_final_antes": _money_str(target["valor_final"]),
                "valor_final_depois": _money_str(valor_final_depois),
                "tenant_id": tenant_id,
            }
        )

    return actions, skipped


def _fetch_notas_sem_contas_pagar(
    db: Session, params: dict[str, Any]
) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
            ne.id AS nota_id,
            ne.numero_nota AS numero_nota,
            ne.fornecedor_id AS fornecedor_id,
            ne.data_emissao AS data_emissao,
            ne.data_entrada AS data_entrada,
            ne.valor_total AS valor_total,
            ne.xml_content AS xml_content,
            ne.status AS status,
            COALESCE(ne.percentual_online, 0) AS percentual_online,
            COALESCE(ne.percentual_loja, 100) AS percentual_loja,
            ne.user_id AS user_id
        FROM notas_entrada ne
        WHERE CAST(ne.tenant_id AS TEXT) = :tenant_id
          AND ne.data_entrada >= :data_inicio
          AND ne.data_entrada < :data_fim
          AND NOT EXISTS (
              SELECT 1
              FROM contas_pagar cp
              WHERE CAST(cp.tenant_id AS TEXT) = CAST(ne.tenant_id AS TEXT)
                AND cp.nota_entrada_id = ne.id
          )
        ORDER BY ne.data_entrada ASC, ne.id ASC
        """,
        params,
    )


def _duplicatas_nota(nota: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    xml_content = str(nota.get("xml_content") or "")
    if not xml_content.strip():
        return [], "Nota sem XML salvo para extrair duplicatas."

    try:
        dados_xml = parse_nfe_xml(xml_content)
    except Exception as exc:  # pragma: no cover - detalhe vem de XML real
        return [], f"XML da nota nao pode ser interpretado: {exc}"

    duplicatas = list(dados_xml.get("duplicatas") or [])
    if not duplicatas:
        data_base = _as_date(nota["data_emissao"] or nota["data_entrada"])
        duplicatas = [
            {
                "numero": f"{nota['numero_nota']}-1",
                "vencimento": data_base + timedelta(days=30),
                "valor": nota["valor_total"],
            }
        ]

    total_dup = sum((_money(dup.get("valor")) for dup in duplicatas), Decimal("0.00"))
    total_nota = _money(nota["valor_total"])
    if abs(total_dup - total_nota) > Decimal("0.05"):
        return [], (
            "Soma das duplicatas diverge do valor da nota: "
            f"{_money_str(total_dup)} vs {_money_str(total_nota)}."
        )

    return duplicatas, None


def _build_cp_missing_actions(
    db: Session, *, tenant_id: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    tipo_produto_revenda_id = _resolve_tipo_produto_revenda_id(db, tenant_id=tenant_id)

    for nota in _fetch_notas_sem_contas_pagar(db, params):
        if str(nota["status"]).lower() != "processada":
            skipped.append(
                {
                    "tipo": "nota_sem_conta_pagar",
                    "nota_id": int(nota["nota_id"]),
                    "numero_nota": nota["numero_nota"],
                    "status": nota["status"],
                    "motivo": "Nota ainda nao esta processada; CP nao foi criado automaticamente.",
                }
            )
            continue

        duplicatas, error = _duplicatas_nota(nota)
        if error:
            skipped.append(
                {
                    "tipo": "nota_sem_conta_pagar",
                    "nota_id": int(nota["nota_id"]),
                    "numero_nota": nota["numero_nota"],
                    "status": nota["status"],
                    "motivo": error,
                }
            )
            continue

        eh_parcelado = len(duplicatas) > 1
        for idx, dup in enumerate(duplicatas, start=1):
            valor = _money(dup.get("valor"))
            actions.append(
                {
                    "tipo": "criar_conta_pagar",
                    "nota_id": int(nota["nota_id"]),
                    "numero_nota": nota["numero_nota"],
                    "fornecedor_id": nota["fornecedor_id"],
                    "tipo_despesa_id": tipo_produto_revenda_id,
                    "descricao": f"NF-e {nota['numero_nota']} - Parcela {dup.get('numero', idx)}",
                    "valor_original": _money_str(valor),
                    "valor_final": _money_str(valor),
                    "data_emissao": _date_str(nota["data_emissao"]),
                    "data_vencimento": _date_str(dup.get("vencimento")),
                    "status": "pendente",
                    "eh_parcelado": eh_parcelado,
                    "numero_parcela": idx if eh_parcelado else None,
                    "total_parcelas": len(duplicatas) if eh_parcelado else None,
                    "nfe_numero": str(nota["numero_nota"]),
                    "documento": str(dup.get("numero") or ""),
                    "percentual_online": _money_str(nota["percentual_online"]),
                    "percentual_loja": _money_str(nota["percentual_loja"]),
                    "user_id": int(nota["user_id"]),
                    "tenant_id": tenant_id,
                }
            )

    return actions, skipped


def _insert_conta_receber(db: Session, action: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO contas_receber (
                descricao, cliente_id, categoria_id, forma_pagamento_id,
                dre_subcategoria_id, canal, valor_original, valor_recebido,
                valor_desconto, valor_juros, valor_multa, valor_final,
                data_emissao, data_vencimento, data_recebimento, status,
                conciliado, eh_parcelado, numero_parcela, total_parcelas, venda_id,
                documento, observacoes, user_id, tenant_id
            )
            VALUES (
                :descricao, :cliente_id, NULL, :forma_pagamento_id,
                :dre_subcategoria_id, :canal, :valor_original, :valor_recebido,
                0, 0, 0, :valor_final,
                :data_emissao, :data_vencimento, :data_recebimento, :status,
                false, :eh_parcelado, :numero_parcela, :total_parcelas, :venda_id,
                :documento, :observacoes, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        action,
    ).first()
    return int(row[0])


def _insert_recebimento(
    db: Session, action: dict[str, Any], *, conta_receber_id: int
) -> int | None:
    if action["status"] != "recebido":
        return None

    row = db.execute(
        text(
            """
            INSERT INTO recebimentos (
                conta_receber_id, forma_pagamento_id, valor_recebido,
                data_recebimento, observacoes, user_id, tenant_id
            )
            VALUES (
                :conta_receber_id, :forma_pagamento_id, :valor_recebido,
                :data_recebimento, :observacoes, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        {
            "conta_receber_id": conta_receber_id,
            "forma_pagamento_id": action["forma_pagamento_id"],
            "valor_recebido": action["valor_recebido"],
            "data_recebimento": action["data_recebimento"],
            "observacoes": (
                "Reparo financeiro historico: recebimento reconstruido "
                "a partir de venda_pagamentos."
            ),
            "user_id": action["user_id"],
            "tenant_id": action["tenant_id"],
        },
    ).first()
    return int(row[0])


def _apply_cr_actions(
    db: Session, actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for action in actions:
        conta_id = _insert_conta_receber(db, action)
        recebimento_id = _insert_recebimento(db, action, conta_receber_id=conta_id)
        applied.append(
            {
                **action,
                "conta_receber_id": conta_id,
                "recebimento_id": recebimento_id,
            }
        )
    return applied


def _apply_centavo_actions(
    db: Session, actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for action in actions:
        db.execute(
            text(
                """
                UPDATE contas_receber
                   SET valor_original = :valor_original_depois,
                       valor_final = :valor_final_depois
                 WHERE id = :conta_receber_id
                   AND CAST(tenant_id AS TEXT) = :tenant_id
                   AND status = 'pendente'
                   AND COALESCE(valor_recebido, 0) = 0
                """
            ),
            action,
        )
    return actions


def _insert_conta_pagar(db: Session, action: dict[str, Any]) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO contas_pagar (
                fornecedor_id, tipo_despesa_id, descricao,
                valor_original, valor_final, valor_pago,
                data_emissao, data_vencimento, status,
                eh_parcelado, numero_parcela, total_parcelas,
                nota_entrada_id, nfe_numero, documento,
                percentual_online, percentual_loja, user_id, tenant_id
            )
            VALUES (
                :fornecedor_id, :tipo_despesa_id, :descricao,
                :valor_original, :valor_final, 0,
                :data_emissao, :data_vencimento, :status,
                :eh_parcelado, :numero_parcela, :total_parcelas,
                :nota_id, :nfe_numero, :documento,
                :percentual_online, :percentual_loja, :user_id, :tenant_id
            )
            RETURNING id
            """
        ),
        action,
    ).first()
    return int(row[0])


def _apply_cp_actions(
    db: Session, actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for action in actions:
        conta_id = _insert_conta_pagar(db, action)
        applied.append({**action, "conta_pagar_id": conta_id})
    return applied


def _build_report(
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
    apply_changes: bool,
    cr_actions: list[dict[str, Any]],
    cr_applied: list[dict[str, Any]],
    cr_skipped: list[dict[str, Any]],
    centavo_actions: list[dict[str, Any]],
    centavo_skipped: list[dict[str, Any]],
    cp_actions: list[dict[str, Any]],
    cp_applied: list[dict[str, Any]],
    cp_skipped: list[dict[str, Any]],
) -> dict[str, Any]:
    received_actions = [
        action
        for action in (cr_applied or cr_actions)
        if action["status"] == "recebido"
    ]
    return {
        "ok": True,
        "applied": bool(apply_changes),
        "dry_run": not bool(apply_changes),
        "tenant_id": tenant_id,
        "periodo": {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
        },
        "resumo": {
            "contas_receber_criadas": len(cr_actions),
            "recebimentos_criados": len(received_actions),
            "ajustes_centavos_aplicaveis": len(centavo_actions),
            "ajustes_centavos_pulados": len(centavo_skipped),
            "contas_pagar_criadas": len(cp_actions),
            "notas_puladas": len(cp_skipped),
            "itens_pulados": len(cr_skipped) + len(centavo_skipped) + len(cp_skipped),
        },
        "contas_receber": {
            "planejadas": cr_actions,
            "aplicadas": cr_applied,
            "puladas": cr_skipped,
        },
        "ajustes_centavos": {
            "planejados": centavo_actions,
            "aplicados": centavo_actions if apply_changes else [],
            "pulados": centavo_skipped,
        },
        "contas_pagar": {
            "planejadas": cp_actions,
            "aplicadas": cp_applied,
            "puladas": cp_skipped,
        },
    }


def reparar_financeiro_consistencia(
    db: Session,
    *,
    tenant_id: str,
    data_inicio: date,
    data_fim: date,
    apply_changes: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Planeja ou aplica reparos financeiros historicos seguros.

    Escopo intencionalmente conservador:
    - cria contas a receber ausentes a partir de venda_pagamentos;
    - ajusta centavos apenas em parcelas pendentes e sem recebimento;
    - cria contas a pagar apenas para notas processadas sem CP.
    """

    if apply_changes and confirm_token != CONFIRM_TOKEN_REPARO_FINANCEIRO:
        db.rollback()
        return {
            "ok": False,
            "applied": False,
            "dry_run": False,
            "error": f"confirm_token deve ser {CONFIRM_TOKEN_REPARO_FINANCEIRO}",
        }

    params = {
        "tenant_id": str(tenant_id),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }

    cr_actions, cr_skipped = _build_cr_missing_actions(
        db, tenant_id=str(tenant_id), params=params
    )
    centavo_actions, centavo_skipped = _build_centavo_actions(
        db, tenant_id=str(tenant_id), params=params
    )
    cp_actions, cp_skipped = _build_cp_missing_actions(
        db, tenant_id=str(tenant_id), params=params
    )

    cr_applied: list[dict[str, Any]] = []
    cp_applied: list[dict[str, Any]] = []
    try:
        if apply_changes:
            cr_applied = _apply_cr_actions(db, cr_actions)
            _apply_centavo_actions(db, centavo_actions)
            cp_applied = _apply_cp_actions(db, cp_actions)
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise

    return _build_report(
        tenant_id=str(tenant_id),
        data_inicio=data_inicio,
        data_fim=data_fim,
        apply_changes=apply_changes,
        cr_actions=cr_actions,
        cr_applied=cr_applied,
        cr_skipped=cr_skipped,
        centavo_actions=centavo_actions,
        centavo_skipped=centavo_skipped,
        cp_actions=cp_actions,
        cp_applied=cp_applied,
        cp_skipped=cp_skipped,
    )
