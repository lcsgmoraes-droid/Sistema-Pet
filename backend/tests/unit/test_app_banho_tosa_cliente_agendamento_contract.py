from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_app_cliente_cria_agendamento_real_no_erp_com_pet_da_propria_conta():
    route = read_repo("backend/app/routes/app_banho_tosa_routes.py")

    assert '@router.post("/agendamentos", status_code=201)' in route
    assert "_get_cliente_or_404(db, current_user)" in route
    assert "BanhoTosaServico.tenant_id == tenant_id" in route
    assert "_validar_slot_cliente(config, inicio, fim)" in route
    assert "_resolver_recurso_slot(db, tenant_id, inicio, fim)" in route
    assert 'origem="app"' in route
    assert "criar_agendamento_erp(" in route


def test_agendamento_cliente_respeita_calendario_e_impede_vaga_duplicada():
    route = read_repo("backend/app/routes/app_banho_tosa_routes.py")

    assert 'detail="A loja ainda nao liberou agendamentos pelo app."' in route
    assert ".with_for_update()" in route
    assert "STATUS_AGENDAMENTO_FINAIS" in route
    assert "sobrepostos.count() >= capacidade_total" in route
    assert 'detail="Este horario acabou de ser ocupado. Escolha outro."' in route
    assert "if cursor <= agora:" in route


def test_tela_mobile_confirma_e_grava_horario_sem_depender_do_whatsapp():
    screen = read_repo("app-mobile/src/screens/services/BanhoTosaScreen.tsx")
    service = read_repo("app-mobile/src/services/banhoTosa.service.ts")

    assert "criarAgendamentoBanhoTosa" in screen
    assert '"Confirmar agendamento"' in screen
    assert '"Agendamento realizado"' in screen
    assert "pet_id: pet.id" in screen
    assert "servico_id: servico.id" in screen
    assert 'api.post("/app/banho-tosa/agendamentos", payload)' in service
