"""Payment, tax and commission setup for the operational demo seed."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from app.scripts.seed_demo_operacional_data import (
    DEFAULT_COMMISSION_PERCENT,
    DEFAULT_TAX_PERCENT,
    money,
)
from app.scripts.seed_demo_operacional_db import _scalar


_PAYMENT_PROFILES = {
    "dinheiro": {
        "label": "dinheiro",
        "fee_percent": Decimal("0"),
        "fee_fixed": Decimal("0"),
        "due_days": 0,
        "bank": "cash",
    },
    "pix": {
        "label": "pix",
        "fee_percent": Decimal("0"),
        "fee_fixed": Decimal("0"),
        "due_days": 0,
        "bank": "main",
    },
    "debito": {
        "label": "Cartao de debito",
        "fee_percent": Decimal("1.89"),
        "fee_fixed": Decimal("0"),
        "due_days": 1,
        "bank": "main",
    },
    "credito": {
        "label": "Cartao de credito",
        "fee_percent": Decimal("3.49"),
        "fee_fixed": Decimal("0"),
        "due_days": 30,
        "bank": "main",
    },
}


def _ensure_bank_account(
    db,
    *,
    tenant_id: str,
    user_id: int,
    name: str,
    tipo: str,
    saldo: Decimal,
    color: str,
    icon: str,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM contas_bancarias
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": name},
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE contas_bancarias
                SET tipo = :tipo,
                    saldo_inicial = :saldo,
                    saldo_atual = :saldo,
                    cor = :color,
                    icone = :icon,
                    ativa = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": existing,
                "tipo": tipo,
                "saldo": saldo,
                "color": color,
                "icon": icon,
            },
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO contas_bancarias (
                nome, tipo, saldo_inicial, saldo_atual, cor, icone,
                instituicao_bancaria, ativa, observacoes, user_id, tenant_id,
                created_at, updated_at
            )
            VALUES (
                :name, :tipo, :saldo, :saldo, :color, :icon,
                :institution, true, :obs, :user_id, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "name": name,
                "tipo": tipo,
                "saldo": saldo,
                "color": color,
                "icon": icon,
                "institution": tipo == "corrente",
                "obs": "Conta demo operacional",
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        )
    )


def _ensure_payment_method(
    db,
    *,
    tenant_id: str,
    user_id: int,
    name: str,
    tipo: str,
    taxa_percentual: Decimal,
    taxa_fixa: Decimal,
    prazo_dias: int,
    bank_id: int,
    operadora: str | None = None,
    tipo_cartao: str | None = None,
    bandeira: str | None = None,
    requer_nsu: bool = False,
    permite_parcelamento: bool = False,
    max_parcelas: int = 1,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM formas_pagamento
        WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name)
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "name": name},
    )
    payload = {
        "name": name,
        "tipo": tipo,
        "taxa_percentual": taxa_percentual,
        "taxa_fixa": taxa_fixa,
        "prazo_dias": prazo_dias,
        "bank_id": bank_id,
        "operadora": operadora,
        "tipo_cartao": tipo_cartao,
        "bandeira": bandeira,
        "requer_nsu": requer_nsu,
        "permite_parcelamento": permite_parcelamento,
        "max_parcelas": max_parcelas,
        "user_id": user_id,
        "tenant_id": tenant_id,
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE formas_pagamento
                SET tipo = :tipo,
                    taxa_percentual = :taxa_percentual,
                    taxa_fixa = :taxa_fixa,
                    prazo_dias = :prazo_dias,
                    prazo_recebimento = :prazo_dias,
                    operadora = :operadora,
                    gera_contas_receber = true,
                    split_parcelas = :permite_parcelamento,
                    conta_bancaria_destino_id = :bank_id,
                    requer_nsu = :requer_nsu,
                    tipo_cartao = :tipo_cartao,
                    bandeira = :bandeira,
                    ativo = true,
                    permite_parcelamento = :permite_parcelamento,
                    max_parcelas = :max_parcelas,
                    parcelas_maximas = :max_parcelas,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing},
        )
        payment_id = int(existing)
    else:
        payment_id = int(
            _scalar(
                db,
                """
                INSERT INTO formas_pagamento (
                    nome, tipo, taxa_percentual, taxa_fixa, prazo_dias,
                    prazo_recebimento, operadora, gera_contas_receber, split_parcelas,
                    conta_bancaria_destino_id, requer_nsu, tipo_cartao, bandeira,
                    ativo, permite_parcelamento, max_parcelas, parcelas_maximas,
                    user_id, tenant_id, created_at, updated_at
                )
                VALUES (
                    :name, :tipo, :taxa_percentual, :taxa_fixa, :prazo_dias,
                    :prazo_dias, :operadora, true, :permite_parcelamento,
                    :bank_id, :requer_nsu, :tipo_cartao, :bandeira,
                    true, :permite_parcelamento, :max_parcelas, :max_parcelas,
                    :user_id, :tenant_id, now(), now()
                )
                RETURNING id
                """,
                payload,
            )
        )

    db.execute(
        text(
            """
            DELETE FROM formas_pagamento_taxas
            WHERE tenant_id = :tenant_id AND forma_pagamento_id = :payment_id
            """
        ),
        {"tenant_id": tenant_id, "payment_id": payment_id},
    )
    if permite_parcelamento:
        for parcelas in range(1, max_parcelas + 1):
            taxa = taxa_percentual + Decimal("0.35") * Decimal(parcelas - 1)
            db.execute(
                text(
                    """
                    INSERT INTO formas_pagamento_taxas (
                        forma_pagamento_id, parcelas, taxa_percentual, descricao,
                        created_at, updated_at, tenant_id
                    )
                    VALUES (
                        :payment_id, :parcelas, :taxa, :descricao,
                        now(), now(), :tenant_id
                    )
                    """
                ),
                {
                    "payment_id": payment_id,
                    "parcelas": parcelas,
                    "taxa": money(taxa),
                    "descricao": f"{parcelas}x demo",
                    "tenant_id": tenant_id,
                },
            )

    return payment_id


def _ensure_tax_configuration(
    db,
    *,
    tenant_id: str,
    user_id: int,
    tax_percent: Decimal = DEFAULT_TAX_PERCENT,
) -> None:
    fiscal_exists = _scalar(
        db,
        """
        SELECT id FROM empresa_config_fiscal
        WHERE tenant_id = :tenant_id
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    fiscal_payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "tax_percent": tax_percent,
    }
    if fiscal_exists:
        db.execute(
            text(
                """
                UPDATE empresa_config_fiscal
                SET uf = 'SP',
                    regime_tributario = 'simples_nacional',
                    contribuinte_icms = true,
                    icms_aliquota_interna = 18.00,
                    icms_aliquota_interestadual = 12.00,
                    aplica_difal = false,
                    cfop_venda_interna = '5102',
                    cfop_venda_interestadual = '6102',
                    cfop_compra = '1102',
                    pis_cst_padrao = '49',
                    pis_aliquota = 0.65,
                    cofins_cst_padrao = '49',
                    cofins_aliquota = 3.00,
                    municipio_iss = 'Sao Paulo',
                    iss_aliquota = 2.00,
                    simples_ativo = true,
                    simples_anexo = 'I',
                    aliquota_simples_vigente = :tax_percent,
                    aliquota_simples_sugerida = :tax_percent,
                    folha_valor_base_mensal = 4300.00,
                    inss_patronal_percentual = 20.00,
                    fgts_percentual = 8.00,
                    cnae_principal = '4789-0/04',
                    cnae_descricao = 'Comercio varejista de animais vivos e artigos para animais',
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**fiscal_payload, "id": fiscal_exists},
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO empresa_config_fiscal (
                    tenant_id, uf, regime_tributario, contribuinte_icms,
                    icms_aliquota_interna, icms_aliquota_interestadual,
                    aplica_difal, cfop_venda_interna, cfop_venda_interestadual,
                    cfop_compra, pis_cst_padrao, pis_aliquota,
                    cofins_cst_padrao, cofins_aliquota, municipio_iss,
                    iss_aliquota, iss_retido, herdado_do_estado, simples_ativo,
                    simples_anexo, aliquota_simples_vigente,
                    aliquota_simples_sugerida, folha_valor_base_mensal,
                    inss_patronal_percentual, fgts_percentual, cnae_principal,
                    cnae_descricao, created_at, updated_at
                )
                VALUES (
                    :tenant_id, 'SP', 'simples_nacional', true,
                    18.00, 12.00,
                    false, '5102', '6102',
                    '1102', '49', 0.65,
                    '49', 3.00, 'Sao Paulo',
                    2.00, false, false, true,
                    'I', :tax_percent,
                    :tax_percent, 4300.00,
                    20.00, 8.00, '4789-0/04',
                    'Comercio varejista de animais vivos e artigos para animais',
                    now(), now()
                )
                """
            ),
            fiscal_payload,
        )

    tax_exists = _scalar(
        db,
        """
        SELECT id FROM configuracao_tributaria
        WHERE tenant_id = :tenant_id
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    )
    if tax_exists:
        db.execute(
            text(
                """
                UPDATE configuracao_tributaria
                SET usuario_id = :user_id,
                    regime = 'simples_nacional',
                    anexo_simples = 'I',
                    faixa_simples = 'Faixa 2 demo',
                    aliquota_efetiva_simples = :tax_percent,
                    estado = 'SP',
                    aliquota_icms = 18.00,
                    incluir_icms_dre = true,
                    aliquota_iss = 2.00,
                    incluir_iss_dre = true,
                    atualizado_em = now(),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**fiscal_payload, "id": tax_exists},
        )
        return

    db.execute(
        text(
            """
            INSERT INTO configuracao_tributaria (
                usuario_id, regime, anexo_simples, faixa_simples,
                aliquota_efetiva_simples, estado, aliquota_icms,
                incluir_icms_dre, aliquota_iss, incluir_iss_dre,
                criado_em, atualizado_em, tenant_id, created_at, updated_at
            )
            VALUES (
                :user_id, 'simples_nacional', 'I', 'Faixa 2 demo',
                :tax_percent, 'SP', 18.00,
                true, 2.00, true,
                now(), now(), :tenant_id, now(), now()
            )
            """
        ),
        fiscal_payload,
    )


def _ensure_commission_configuration(
    db,
    *,
    tenant_id: str,
    funcionario_id: int,
    percent: Decimal = DEFAULT_COMMISSION_PERCENT,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM comissoes_configuracao
        WHERE tenant_id = :tenant_id
          AND funcionario_id = :funcionario_id
          AND tipo = 'geral'
          AND referencia_id = 0
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "funcionario_id": funcionario_id},
    )
    payload = {
        "tenant_id": tenant_id,
        "funcionario_id": funcionario_id,
        "percent": percent,
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE comissoes_configuracao
                SET percentual = :percent,
                    ativo = true,
                    tipo_calculo = 'percentual_venda_liquida',
                    desconta_taxa_cartao = true,
                    desconta_impostos = true,
                    desconta_custo_entrega = true,
                    comissao_venda_parcial = true,
                    percentual_loja = 100,
                    permite_edicao_venda = true,
                    observacoes = 'Demo operacional - regra geral de comissao',
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing},
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO comissoes_configuracao (
                funcionario_id, tipo, referencia_id, percentual, ativo,
                tipo_calculo, desconta_taxa_cartao, desconta_impostos,
                desconta_custo_entrega, comissao_venda_parcial,
                percentual_loja, permite_edicao_venda, observacoes,
                created_at, updated_at, tenant_id
            )
            VALUES (
                :funcionario_id, 'geral', 0, :percent, true,
                'percentual_venda_liquida', true, true,
                true, true,
                100, true, 'Demo operacional - regra geral de comissao',
                now(), now(), :tenant_id
            )
            RETURNING id
            """,
            payload,
        )
    )
