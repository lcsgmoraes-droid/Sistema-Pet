"""Disputa real de saldo, opt-in em PostgreSQL DEV com schema descartável.

BANHO_TOSA_TEST_POSTGRES_URL deve apontar a uma instância de teste/local com as
migrations aplicadas. A suíte não escreve nas tabelas de negócio existentes.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.banho_tosa_pacote_reservas import reservar_creditos_agendamento
from app.tenancy.context import clear_current_tenant, set_current_tenant


@pytest.mark.integration
def test_duas_sessoes_disputam_ultimo_credito_sem_saldo_negativo():
    url = os.environ.get("BANHO_TOSA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip(
            "Ative explicitamente BANHO_TOSA_TEST_POSTGRES_URL em PostgreSQL de testes."
        )
    # Registra os mesmos modelos leves utilizados nos testes HTTP, sem iniciar app.
    from tests.conftest_infra import _get_db_dependencies
    from app import caixa_models, especie_raca_mestre_models, produto_identidade_models  # noqa: F401
    from app.banho_tosa_api import pacotes_routes  # noqa: F401

    _get_db_dependencies()
    esquema = "bt_reserva_qa_" + uuid4().hex
    tenant_id = uuid4()
    admin = create_engine(url)
    engine = None
    try:
        with admin.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA {esquema}"))
            for tabela in (
                "banho_tosa_pacote_creditos",
                "banho_tosa_pacote_movimentos",
            ):
                conn.execute(
                    text(
                        f"CREATE TABLE {esquema}.{tabela} (LIKE public.{tabela} INCLUDING ALL)"
                    )
                )
            credito_id = conn.execute(
                text(f"""
                INSERT INTO {esquema}.banho_tosa_pacote_creditos
                (tenant_id, pacote_id, cliente_id, pet_id, status,
                 creditos_total, creditos_usados, creditos_cancelados,
                 creditos_reservados, servicos, data_inicio, data_validade, valor_pacote)
                VALUES (:tenant, 1, 2, 3, 'ativo', 1, 0, 0, 0,
                        CAST(:servicos AS json), CURRENT_DATE-1, CURRENT_DATE+30, 50)
                RETURNING id
            """),
                {
                    "tenant": str(tenant_id),
                    "servicos": json.dumps(
                        [{"servico_id": 10, "quantidade_creditos": 1}]
                    ),
                },
            ).scalar_one()

        engine = create_engine(
            url,
            connect_args={
                "options": f"-csearch_path={esquema},public -clock_timeout=5000"
            },
        )
        sessao = sessionmaker(bind=engine)
        primeira_reservou, segunda_iniciou, segunda_terminou, liberar_primeira = (
            Event() for _ in range(4)
        )

        def reservar(numero):
            set_current_tenant(tenant_id)
            try:
                with sessao() as db:
                    item = SimpleNamespace(
                        id=numero,
                        servico_id=10,
                        quantidade=Decimal("1"),
                        pacote_credito_id=None,
                        pacote_quantidade=Decimal("0"),
                    )
                    agendamento = SimpleNamespace(
                        id=numero,
                        cliente_id=2,
                        pet_id=3,
                        data_hora_inicio=datetime.now(),
                        servicos=[item],
                    )
                    if numero == 2:
                        segunda_iniciou.set()
                    reservar_creditos_agendamento(db, tenant_id, agendamento)
                    if numero == 1:
                        primeira_reservou.set()
                        assert liberar_primeira.wait(10), (
                            "A sessão de controle não liberou a transação."
                        )
                    db.commit()
                    if numero == 2:
                        segunda_terminou.set()
                    return item.pacote_quantidade
            finally:
                clear_current_tenant()

        with ThreadPoolExecutor(max_workers=2) as pool:
            primeiro = pool.submit(reservar, 1)
            try:
                assert primeira_reservou.wait(10)
                segundo = pool.submit(reservar, 2)
                assert segunda_iniciou.wait(5)
                # A segunda transação precisa aguardar o bloqueio da primeira.
                assert not segunda_terminou.wait(0.2)
            finally:
                liberar_primeira.set()
            assert primeiro.result(timeout=10) == Decimal("1")
            assert segundo.result(timeout=10) == Decimal("0")
        with engine.connect() as conn:
            saldo = conn.execute(
                text(
                    "SELECT creditos_total-creditos_usados-creditos_cancelados-creditos_reservados FROM banho_tosa_pacote_creditos WHERE id=:id"
                ),
                {"id": credito_id},
            ).scalar_one()
            reservas = conn.execute(
                text(
                    "SELECT COUNT(*) FROM banho_tosa_pacote_movimentos WHERE tipo='reserva'"
                )
            ).scalar_one()
            assert saldo == 0
            assert reservas == 1
    finally:
        if engine is not None:
            engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {esquema} CASCADE"))
        admin.dispose()
