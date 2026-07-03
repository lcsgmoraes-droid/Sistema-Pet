"""Support data setup for the operational demo seed."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app.scripts.seed_demo_operacional_accounting import _ensure_accounting_setup
from app.scripts.seed_demo_operacional_db import _scalar
from app.scripts.seed_demo_operacional_payments import (
    _ensure_bank_account,
    _ensure_commission_configuration,
    _ensure_payment_method,
    _ensure_tax_configuration,
)


def _ensure_support_data(
    db, *, tenant_id: str, user_id: int, base_date: date
) -> dict[str, Any]:
    categories = _ensure_accounting_setup(db, tenant_id=tenant_id, user_id=user_id)

    bank_main_id = _ensure_bank_account(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        name="Conta Banco Demo",
        tipo="corrente",
        saldo=Decimal("2500.00"),
        color="#0F766E",
        icon="landmark",
    )
    bank_cash_id = _ensure_bank_account(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        name="Caixa Loja Demo",
        tipo="caixa_fisico",
        saldo=Decimal("600.00"),
        color="#EA580C",
        icon="wallet",
    )

    payment_methods = {
        "dinheiro": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="Dinheiro",
            tipo="dinheiro",
            taxa_percentual=Decimal("0"),
            taxa_fixa=Decimal("0"),
            prazo_dias=0,
            bank_id=bank_cash_id,
        ),
        "pix": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="PIX",
            tipo="pix",
            taxa_percentual=Decimal("0"),
            taxa_fixa=Decimal("0"),
            prazo_dias=0,
            bank_id=bank_main_id,
        ),
        "debito": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="Cartao de debito",
            tipo="cartao_debito",
            taxa_percentual=Decimal("1.89"),
            taxa_fixa=Decimal("0"),
            prazo_dias=1,
            bank_id=bank_main_id,
            operadora="Stone",
            tipo_cartao="debito",
            bandeira="visa",
            requer_nsu=True,
        ),
        "credito": _ensure_payment_method(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            name="Cartao de credito",
            tipo="cartao_credito",
            taxa_percentual=Decimal("3.49"),
            taxa_fixa=Decimal("0"),
            prazo_dias=30,
            bank_id=bank_main_id,
            operadora="Stone",
            tipo_cartao="credito",
            bandeira="master",
            requer_nsu=True,
            permite_parcelamento=True,
            max_parcelas=6,
        ),
    }

    cargo_vendedor_id = _ensure_cargo(
        db,
        tenant_id=tenant_id,
        name="Vendedor Demo",
        salary=Decimal("2500.00"),
        inss=Decimal("20.00"),
        fgts=Decimal("8.00"),
    )
    cargo_entregador_id = _ensure_cargo(
        db,
        tenant_id=tenant_id,
        name="Entregador Demo",
        salary=Decimal("1800.00"),
        inss=Decimal("20.00"),
        fgts=Decimal("8.00"),
    )

    clients = {
        "ana": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-CLI-001",
            name="Ana Costa",
            kind="cliente",
            email="ana.demo@sistemapet.local",
            phone="(11) 90000-1001",
            address="Rua das Palmeiras",
            number="120",
            district="Centro",
            city="Sao Paulo",
            state="SP",
        ),
        "joao": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-CLI-002",
            name="Joao Santos",
            kind="cliente",
            email="joao.demo@sistemapet.local",
            phone="(11) 90000-1002",
            address="Av. Pet Shop",
            number="455",
            district="Mooca",
            city="Sao Paulo",
            state="SP",
        ),
        "maria": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-CLI-003",
            name="Maria Oliveira",
            kind="cliente",
            email="maria.demo@sistemapet.local",
            phone="(11) 90000-1003",
            address="Rua dos Lirios",
            number="87",
            district="Tatuape",
            city="Sao Paulo",
            state="SP",
        ),
        "distribuidora": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-FOR-001",
            name="Distribuidora Pet Brasil",
            kind="fornecedor",
            email="compras.demo@sistemapet.local",
            phone="(11) 3333-0101",
            address="Rodovia dos Petiscos",
            number="1000",
            district="Industrial",
            city="Guarulhos",
            state="SP",
        ),
        "fornecedor": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-FOR-002",
            name="Fornecedor Demo Financeiro",
            kind="fornecedor",
            email="financeiro.fornecedor.demo@sistemapet.local",
            phone="(11) 3333-0202",
            address="Rua Financeira",
            number="42",
            district="Centro",
            city="Sao Paulo",
            state="SP",
        ),
        "funcionario_vendedor": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-FUNC-001",
            name="Beatriz Vendedora Demo",
            kind="funcionario",
            email="beatriz.vendas.demo@sistemapet.local",
            phone="(11) 95555-0101",
            address="Rua Equipe CorePet",
            number="10",
            district="Centro",
            city="Sao Paulo",
            state="SP",
            cargo_id=cargo_vendedor_id,
            salary=Decimal("2500.00"),
            controla_rh=True,
            commission_partner=True,
        ),
        "entregador": _ensure_person(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            code="DEMO-ENT-001",
            name="Carlos Entregador Demo",
            kind="funcionario",
            email="carlos.entrega.demo@sistemapet.local",
            phone="(11) 95555-0202",
            address="Rua das Rotas",
            number="77",
            district="Ipiranga",
            city="Sao Paulo",
            state="SP",
            cargo_id=cargo_entregador_id,
            salary=Decimal("1800.00"),
            controla_rh=True,
            is_entregador=True,
            valor_por_km=Decimal("2.20"),
        ),
    }

    _ensure_delivery_config(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        entregador_id=clients["entregador"],
    )
    _ensure_tax_configuration(db, tenant_id=tenant_id, user_id=user_id)
    commission_config_id = _ensure_commission_configuration(
        db,
        tenant_id=tenant_id,
        funcionario_id=clients["funcionario_vendedor"],
    )

    return {
        "categories": categories,
        "banks": {"main": bank_main_id, "cash": bank_cash_id},
        "payments": payment_methods,
        "people": clients,
        "commission_config_id": commission_config_id,
        "base_date": base_date,
    }


def _ensure_cargo(
    db,
    *,
    tenant_id: str,
    name: str,
    salary: Decimal,
    inss: Decimal,
    fgts: Decimal,
) -> int:
    existing = _scalar(
        db,
        "SELECT id FROM cargos WHERE tenant_id = :tenant_id AND lower(nome) = lower(:name) LIMIT 1",
        {"tenant_id": tenant_id, "name": name},
    )
    if existing:
        db.execute(
            text(
                """
                UPDATE cargos
                SET salario_base = :salary,
                    inss_patronal_percentual = :inss,
                    fgts_percentual = :fgts,
                    gera_ferias = true,
                    gera_decimo_terceiro = true,
                    ativo = true,
                    regime_remuneracao = 'clt',
                    gera_encargos = true,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {"id": existing, "salary": salary, "inss": inss, "fgts": fgts},
        )
        return int(existing)

    return int(
        _scalar(
            db,
            """
            INSERT INTO cargos (
                nome, descricao, salario_base, inss_patronal_percentual,
                fgts_percentual, gera_ferias, gera_decimo_terceiro, ativo,
                regime_remuneracao, gera_encargos, tenant_id, created_at, updated_at
            )
            VALUES (
                :name, 'Cargo demo operacional', :salary, :inss,
                :fgts, true, true, true, 'clt', true, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            {
                "name": name,
                "salary": salary,
                "inss": inss,
                "fgts": fgts,
                "tenant_id": tenant_id,
            },
        )
    )


def _ensure_person(
    db,
    *,
    tenant_id: str,
    user_id: int,
    code: str,
    name: str,
    kind: str,
    email: str,
    phone: str,
    address: str,
    number: str,
    district: str,
    city: str,
    state: str,
    cargo_id: int | None = None,
    salary: Decimal | None = None,
    controla_rh: bool = False,
    is_entregador: bool = False,
    valor_por_km: Decimal | None = None,
    commission_partner: bool = False,
) -> int:
    existing = _scalar(
        db,
        """
        SELECT id FROM clientes
        WHERE tenant_id = :tenant_id AND codigo = :code
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "code": code},
    )
    tipo_pessoa = "J" if kind == "fornecedor" else "F"
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "code": code,
        "kind": kind,
        "tipo_pessoa": tipo_pessoa,
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "number": number,
        "district": district,
        "city": city,
        "state": state,
        "cargo_id": cargo_id,
        "salary": salary,
        "controla_rh": controla_rh,
        "is_entregador": is_entregador,
        "valor_por_km": valor_por_km,
        "commission_partner": commission_partner,
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE clientes
                SET tipo_cadastro = :kind,
                    tipo_pessoa = :tipo_pessoa,
                    nome = :name,
                    email = :email,
                    telefone = :phone,
                    celular = :phone,
                    endereco = :address,
                    endereco_entrega = :address || ', ' || :number || ' - ' || :district,
                    numero = :number,
                    bairro = :district,
                    cidade = :city,
                    estado = :state,
                    cargo_id = :cargo_id,
                    salario_base_override = :salary,
                    liquido_combinado = :salary,
                    controla_rh = :controla_rh,
                    is_entregador = :is_entregador,
                    recebe_repasse = :is_entregador,
                    gera_conta_pagar = :is_entregador,
                    recebe_comissao_entrega = :is_entregador,
                    parceiro_ativo = :commission_partner,
                    parceiro_desde = CASE
                        WHEN :commission_partner THEN COALESCE(parceiro_desde, now())
                        ELSE parceiro_desde
                    END,
                    parceiro_observacoes = CASE
                        WHEN :commission_partner THEN 'Demo operacional - parceiro comissionado'
                        ELSE parceiro_observacoes
                    END,
                    data_fechamento_comissao = CASE
                        WHEN :commission_partner THEN 5
                        ELSE data_fechamento_comissao
                    END,
                    parceiro_tipo_acerto = CASE
                        WHEN :commission_partner THEN 'mensal'
                        ELSE parceiro_tipo_acerto
                    END,
                    parceiro_dia_acerto = CASE
                        WHEN :commission_partner THEN 5
                        ELSE parceiro_dia_acerto
                    END,
                    parceiro_notificar = CASE
                        WHEN :commission_partner THEN true
                        ELSE parceiro_notificar
                    END,
                    parceiro_email_principal = CASE
                        WHEN :commission_partner THEN :email
                        ELSE parceiro_email_principal
                    END,
                    entregador_ativo = :is_entregador,
                    entregador_padrao = :is_entregador,
                    gera_conta_pagar_custo_entrega = :is_entregador,
                    tipo_vinculo_entrega = CASE WHEN :is_entregador THEN 'interno' ELSE tipo_vinculo_entrega END,
                    valor_por_km = :valor_por_km,
                    valor_por_km_entrega = :valor_por_km,
                    moto_propria = :is_entregador,
                    modelo_custo_entrega = CASE WHEN :is_entregador THEN 'km' ELSE modelo_custo_entrega END,
                    tipo_acerto_entrega = CASE WHEN :is_entregador THEN 'semanal' ELSE tipo_acerto_entrega END,
                    ativo = true,
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
            INSERT INTO clientes (
                user_id, codigo, tipo_cadastro, tipo_pessoa, nome, email,
                telefone, celular, endereco, endereco_entrega, numero, bairro,
                cidade, estado, cargo_id, salario_base_override, liquido_combinado,
                controla_rh, is_entregador, is_terceirizado, recebe_repasse,
                gera_conta_pagar, recebe_comissao_entrega, parceiro_ativo,
                parceiro_desde, parceiro_observacoes, data_fechamento_comissao,
                parceiro_tipo_acerto, parceiro_dia_acerto, parceiro_notificar,
                parceiro_email_principal, entregador_ativo,
                entregador_padrao, gera_conta_pagar_custo_entrega,
                tipo_vinculo_entrega, valor_por_km, valor_por_km_entrega,
                modelo_custo_entrega, tipo_acerto_entrega, controla_dre,
                moto_propria, ativo, credito, tenant_id, created_at, updated_at
            )
            VALUES (
                :user_id, :code, :kind, :tipo_pessoa, :name, :email,
                :phone, :phone, :address,
                :address || ', ' || :number || ' - ' || :district,
                :number, :district, :city, :state, :cargo_id, :salary, :salary,
                :controla_rh, :is_entregador, false, :is_entregador,
                :is_entregador, :is_entregador, :commission_partner,
                CASE WHEN :commission_partner THEN now() ELSE NULL END,
                CASE
                    WHEN :commission_partner THEN 'Demo operacional - parceiro comissionado'
                    ELSE NULL
                END,
                CASE WHEN :commission_partner THEN 5 ELSE NULL END,
                CASE WHEN :commission_partner THEN 'mensal' ELSE 'mensal' END,
                CASE WHEN :commission_partner THEN 5 ELSE 1 END,
                true,
                CASE WHEN :commission_partner THEN :email ELSE NULL END,
                :is_entregador, :is_entregador, :is_entregador,
                CASE WHEN :is_entregador THEN 'interno' ELSE NULL END,
                :valor_por_km, :valor_por_km,
                CASE WHEN :is_entregador THEN 'km' ELSE NULL END,
                CASE WHEN :is_entregador THEN 'semanal' ELSE NULL END,
                true, :is_entregador, true, 0, :tenant_id, now(), now()
            )
            RETURNING id
            """,
            payload,
        )
    )


def _ensure_delivery_config(
    db, *, tenant_id: str, user_id: int, entregador_id: int
) -> None:
    existing = _scalar(
        db,
        """
        SELECT id FROM configuracoes_entrega
        WHERE tenant_id = :tenant_id AND user_id = :user_id
        LIMIT 1
        """,
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "entregador_id": entregador_id,
        "logradouro": "Av. CorePet Demo",
        "cep": "01001-000",
        "numero": "100",
        "complemento": "Loja demo",
        "bairro": "Centro",
        "cidade": "Sao Paulo",
        "estado": "SP",
    }
    if existing:
        db.execute(
            text(
                """
                UPDATE configuracoes_entrega
                SET entregador_padrao_id = :entregador_id,
                    logradouro = :logradouro,
                    cep = :cep,
                    numero = :numero,
                    complemento = :complemento,
                    bairro = :bairro,
                    cidade = :cidade,
                    estado = :estado,
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {**payload, "id": existing},
        )
        return

    db.execute(
        text(
            """
            INSERT INTO configuracoes_entrega (
                user_id, entregador_padrao_id, logradouro, cep, numero,
                complemento, bairro, cidade, estado, tenant_id, created_at, updated_at
            )
            VALUES (
                :user_id, :entregador_id, :logradouro, :cep, :numero,
                :complemento, :bairro, :cidade, :estado, :tenant_id, now(), now()
            )
            """
        ),
        payload,
    )
