from pathlib import Path

import pytest

from app.banho_tosa_taxi_fluxo import (
    fluxo_status_taxi_dog,
    proximo_status_taxi_dog,
    validar_transicao_status_taxi_dog,
)
from app.scripts.seed_banho_tosa_ux import AGENDADOS, EM_PROCESSO


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def read_backend(path: str) -> str:
    return (BACKEND_ROOT / path).read_text(encoding="utf-8")


def test_app_funcionario_expoe_agenda_fila_checkin_e_avanco():
    source = read_backend("app/routes/app_banho_tosa_funcionario_routes.py")
    main = read_backend("app/main_routers.py")

    assert 'prefix="/app/funcionario/banho-tosa"' in source
    assert '@router.get("/agenda")' in source
    assert '@router.post("/agenda", status_code=201)' in source
    assert '@router.post("/agenda/{agendamento_id}/check-in")' in source
    assert '@router.get("/fila")' in source
    assert '@router.post("/fila/{atendimento_id}/mover-etapa")' in source
    assert "get_cliente_for_app_profile_or_none" in source
    assert "app_banho_tosa_funcionario_router" in main


def test_app_entregador_expoe_taxi_dog_atribuido_ao_motorista():
    source = read_backend("app/routes/app_banho_tosa_funcionario_routes.py")

    assert 'prefix="/app/entregador/taxi-dog"' in source
    assert "BanhoTosaTaxiDog.motorista_id == entregador.id" in source
    assert "sincronizar_chegada_taxi_dog" in source
    assert 'novo_status == "entregue_na_clinica"' in source


def test_perfis_dedicados_reaproveitam_rotas_sem_liberar_todo_o_app_operacional():
    source = read_backend("app/routes/app_banho_tosa_funcionario_routes.py")

    assert '{"funcionario", "banho_tosa"}' in source
    assert '{"entregador", "taxi_dog"}' in source
    assert 'get_cliente_for_app_profile_or_none(\n        db, current_user, active_profile' in source


def test_fluxo_taxi_dog_respeita_ida_volta_e_nao_pula_etapa():
    assert proximo_status_taxi_dog("agendado", "ida_volta") == "motorista_a_caminho"
    assert (
        proximo_status_taxi_dog("entregue_na_clinica", "ida_volta")
        == "aguardando_retorno"
    )
    assert fluxo_status_taxi_dog("ida")[-1] == "entregue_na_clinica"
    assert fluxo_status_taxi_dog("volta") == (
        "agendado",
        "aguardando_retorno",
        "retornando",
        "entregue_ao_tutor",
    )
    with pytest.raises(ValueError, match="Proxima etapa permitida"):
        validar_transicao_status_taxi_dog("agendado", "pet_coletado", "ida_volta")


def test_fluxo_taxi_dog_aceita_proxima_etapa_e_repeticao_idempotente():
    assert (
        validar_transicao_status_taxi_dog(
            "motorista_a_caminho",
            "pet_coletado",
            "ida_volta",
        )
        == "pet_coletado"
    )


def test_seed_de_ux_mantem_oito_agendados_e_oito_em_etapas_variadas():
    assert len(AGENDADOS) == 8
    assert len(EM_PROCESSO) == 8
    assert {cenario[3] for cenario in EM_PROCESSO} == {
        "chegou",
        "banho",
        "secagem",
        "tosa",
    }
    assert (
        validar_transicao_status_taxi_dog(
            "pet_coletado",
            "pet_coletado",
            "ida_volta",
        )
        == "pet_coletado"
    )
