from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_CI_WORKFLOW = ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_backend_ci_has_blocking_tenancy_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Tenancy lint (blocking)" in source
    assert "ruff check app/tenancy" in source


def test_backend_ci_has_blocking_auth_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Auth lint (blocking)" in source
    assert "ruff check app/auth app/auth_routes_multitenant.py app/usuarios_routes.py" in source


def test_backend_ci_has_blocking_db_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Database lint (blocking)" in source
    assert "ruff check app/db" in source


def test_backend_ci_has_blocking_schemas_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Schemas lint (blocking)" in source
    assert "ruff check app/schemas" in source


def test_backend_ci_has_blocking_security_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Security lint (blocking)" in source
    assert "ruff check app/security" in source


def test_backend_ci_has_blocking_core_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Core lint (blocking)" in source
    assert "ruff check app/core" in source


def test_backend_ci_has_blocking_events_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Events lint (blocking)" in source
    assert "ruff check app/events" in source


def test_backend_ci_has_blocking_utils_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Utils lint (blocking)" in source
    assert "ruff check app/utils" in source


def test_backend_ci_has_blocking_constants_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Constants lint (blocking)" in source
    assert "ruff check app/constants" in source


def test_backend_ci_has_blocking_cache_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Cache lint (blocking)" in source
    assert "ruff check app/cache" in source


def test_backend_ci_has_blocking_replay_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Replay lint (blocking)" in source
    assert "ruff check app/replay" in source


def test_backend_ci_has_blocking_application_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Application lint (blocking)" in source
    assert "ruff check app/application" in source


def test_backend_ci_has_blocking_analytics_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Analytics lint (blocking)" in source
    assert "ruff check app/analytics" in source


def test_backend_ci_has_blocking_fiscal_models_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Fiscal models lint (blocking)" in source
    assert "ruff check app/fiscal_models" in source


def test_backend_ci_has_blocking_caixa_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Caixa lint (blocking)" in source
    assert "ruff check app/caixa" in source


def test_backend_ci_has_blocking_caixa_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Caixa root lint (blocking)" in source
    assert "ruff check app/caixa_models.py app/caixa_routes.py app/calculadora_racao.py" in source


def test_backend_ci_has_blocking_parsers_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Parsers lint (blocking)" in source
    assert "ruff check app/parsers" in source


def test_backend_ci_has_blocking_scripts_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Scripts lint (blocking)" in source
    assert "ruff check app/scripts" in source


def test_backend_ci_has_blocking_middlewares_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Middlewares lint (blocking)" in source
    assert "ruff check app/middlewares" in source


def test_backend_ci_has_blocking_notas_entrada_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Notas entrada lint (blocking)" in source
    assert "ruff check app/notas_entrada" in source


def test_backend_ci_has_blocking_compras_fiscais_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Compras fiscais root lint (blocking)" in source
    assert (
        "ruff check app/notas_entrada_routes.py app/nfe_routes.py "
        "app/pedidos_compra_routes.py"
    ) in source


def test_backend_ci_has_blocking_fiscal_nf_rateio_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Fiscal NF rateio root lint (blocking)" in source
    assert (
        "ruff check app/fiscal_estado_padrao_models.py app/fiscal_patterns.py "
        "app/nf_item_rateio_canal_models.py app/nf_item_rateio_validator.py "
        "app/nf_rateio_canal_models.py app/nfe_cache_models.py "
        "app/nota_fiscal_item_rateio_routes.py "
        "app/nota_fiscal_rateio_helper.py app/nota_fiscal_rateio_routes.py "
        "app/nota_fiscal_tipos.py app/notas_entrada_pdf_parser.py"
    ) in source


def test_backend_ci_has_blocking_pedidos_pendencias_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Pedidos pendencias root lint (blocking)" in source
    assert (
        "ruff check app/compras_pendencias_models.py "
        "app/compras_pendencias_routes.py app/pedido_integrado_item_models.py "
        "app/pedido_integrado_models.py app/pedido_models.py "
        "app/pendencia_estoque_models.py app/pendencia_estoque_routes.py"
    ) in source


def test_backend_ci_has_blocking_admin_lgpd_simples_ops_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Admin LGPD simples ops root lint (blocking)" in source
    assert (
        "ruff check app/admin_fix_routes.py app/admin_routes.py "
        "app/lgpd_models.py app/lgpd_routes.py app/simples_nacional_models.py "
        "app/simples_routes.py app/opportunities_models.py "
        "app/opportunity_events_models.py app/ops_models.py"
    ) in source


def test_backend_ci_has_blocking_produtos_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Produtos lint (blocking)" in source
    assert "ruff check app/produtos" in source


def test_backend_ci_has_blocking_produtos_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Produtos root lint (blocking)" in source
    assert (
        "ruff check app/categorias_routes.py app/fiscal_catalogo_produtos_models.py "
        "app/importacao_produtos.py app/produto_config_fiscal_models.py "
        "app/produtos_models.py app/produtos_routes.py app/subcategorias_routes.py"
    ) in source


def test_backend_ci_has_blocking_insights_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Insights lint (blocking)" in source
    assert "ruff check app/insights" in source


def test_backend_ci_has_blocking_schedulers_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Schedulers lint (blocking)" in source
    assert "ruff check app/schedulers" in source


def test_backend_ci_has_blocking_audit_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Audit lint (blocking)" in source
    assert "ruff check app/audit" in source


def test_backend_ci_has_blocking_financeiro_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Financeiro lint (blocking)" in source
    assert "ruff check app/financeiro" in source


def test_backend_ci_has_blocking_conciliacao_financeiro_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Conciliacao financeiro root lint (blocking)" in source
    assert (
        "ruff check app/financeiro_routes.py app/conciliacao_routes.py "
        "app/conciliacao_aba1_routes.py app/conciliacao_bancaria_routes.py "
        "app/conciliacao_services.py app/conciliacao_historico_routes.py"
    ) in source


def test_backend_ci_has_blocking_conciliacao_adquirentes_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Conciliacao adquirentes root lint (blocking)" in source
    assert (
        "ruff check app/conciliacao_cartao_routes.py app/conciliacao_helpers.py "
        "app/conciliacao_models.py app/conciliacao_operadora_detector.py "
        "app/stone_models.py app/operadoras_cartao_models.py "
        "app/duplicatas_ignoradas_models.py app/controle_processamento_models.py"
    ) in source


def test_backend_ci_has_blocking_routers_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Routers lint (blocking)" in source
    assert "ruff check app/routers" in source


def test_backend_ci_has_blocking_domain_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Domain lint (blocking)" in source
    assert "ruff check app/domain" in source


def test_backend_ci_has_blocking_read_models_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Read models lint (blocking)" in source
    assert "ruff check app/read_models" in source


def test_backend_ci_has_blocking_banho_tosa_api_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Banho Tosa API lint (blocking)" in source
    assert "ruff check app/banho_tosa_api" in source


def test_backend_ci_has_blocking_banho_tosa_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Banho Tosa root lint (blocking)" in source
    assert (
        "ruff check app/banho_tosa_agenda_capacity.py "
        "app/banho_tosa_agenda_slots.py app/banho_tosa_avaliacoes_metrics.py "
        "app/banho_tosa_cancelamento.py app/banho_tosa_custos.py "
        "app/banho_tosa_custos_helpers.py app/banho_tosa_custos_reais.py "
        "app/banho_tosa_custos_reais_helpers.py app/banho_tosa_datetime.py "
        "app/banho_tosa_defaults.py app/banho_tosa_fechamento.py "
        "app/banho_tosa_fotos_storage.py app/banho_tosa_models.py "
        "app/banho_tosa_pacotes.py app/banho_tosa_pacotes_serializers.py "
        "app/banho_tosa_relatorios.py app/banho_tosa_relatorios_helpers.py "
        "app/banho_tosa_retornos.py app/banho_tosa_retornos_notificacoes.py "
        "app/banho_tosa_retornos_templates.py app/banho_tosa_routes.py "
        "app/banho_tosa_schemas.py app/banho_tosa_vendas.py"
    ) in source


def test_backend_ci_has_blocking_estoque_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Estoque lint (blocking)" in source
    assert "ruff check app/estoque" in source


def test_backend_ci_has_blocking_configuracoes_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Configuracoes lint (blocking)" in source
    assert "ruff check app/configuracoes" in source


def test_backend_ci_has_blocking_clean_package_lint_steps():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    expected_steps = [
        ("Database package lint (blocking)", "ruff check app/database"),
        ("DRE lint (blocking)", "ruff check app/dre"),
        ("Migrations lint (blocking)", "ruff check app/migrations"),
        (
            "Banho Tosa model parts lint (blocking)",
            "ruff check app/banho_tosa_model_parts",
        ),
        (
            "Banho Tosa schema parts lint (blocking)",
            "ruff check app/banho_tosa_schema_parts",
        ),
    ]

    for step_name, command in expected_steps:
        assert step_name in source
        assert command in source


def test_backend_ci_has_blocking_dre_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "DRE root lint (blocking)" in source
    assert (
        "ruff check app/dre_canais_routes.py app/dre_classificacao_routes.py "
        "app/dre_classificacao_service.py app/dre_ia_routes.py "
        "app/dre_plano_contas_models.py app/dre_plano_contas_routes.py "
        "app/dre_regras_models.py app/dre_routes.py"
    ) in source


def test_backend_ci_has_blocking_services_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Services lint (blocking)" in source
    assert "ruff check app/services" in source


def test_backend_ci_has_blocking_campaigns_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Campaigns lint (blocking)" in source
    assert "ruff check app/campaigns" in source


def test_backend_ci_has_blocking_vendas_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Vendas lint (blocking)" in source
    assert "ruff check app/vendas" in source


def test_backend_ci_has_blocking_whatsapp_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "WhatsApp lint (blocking)" in source
    assert "ruff check app/whatsapp" in source


def test_backend_ci_has_blocking_ia_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "IA lint (blocking)" in source
    assert "ruff check app/ia" in source


def test_backend_ci_has_blocking_ia_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "IA root lint (blocking)" in source
    assert "ruff check app/ia_config.py app/ia_fluxo_routes.py app/ia_routes.py" in source


def test_backend_ci_has_blocking_api_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "API lint (blocking)" in source
    assert "ruff check app/api" in source


def test_backend_ci_has_blocking_routes_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Routes lint (blocking)" in source
    assert "ruff check app/routes" in source


def test_backend_ci_has_blocking_bling_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Bling root lint (blocking)" in source
    assert (
        "ruff check app/bling_estoque_sync.py app/bling_flow_monitor_models.py "
        "app/bling_flow_monitor_routes.py app/bling_integration.py "
        "app/bling_oauth_routes.py app/bling_pedido_webhook_queue_models.py "
        "app/bling_routes.py app/bling_sync_routes.py app/integracao_bling_models.py "
        "app/integracao_bling_nf_routes.py app/integracao_bling_pedido_routes.py "
        "app/integracao_bling_webhook_routes.py"
    ) in source


def test_backend_ci_has_blocking_operational_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Operational root lint (blocking)" in source
    assert (
        "ruff check app/health_router.py app/session_manager.py app/idempotency.py "
        "app/idempotency_models.py app/encryption.py app/audit.py app/audit_log.py"
    ) in source


def test_backend_ci_has_blocking_main_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Main root lint (blocking)" in source
    assert "ruff check app/main.py" in source


def test_backend_ci_has_blocking_clientes_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Clientes root lint (blocking)" in source
    assert (
        "ruff check app/clientes_routes.py app/cliente_info_pdv.py "
        "app/pets_routes.py app/cadastros_routes.py app/importacao_pessoas.py"
    ) in source


def test_backend_ci_has_blocking_cadastros_operacionais_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Cadastros operacionais root lint (blocking)" in source
    assert (
        "ruff check app/fornecedor_grupos_routes.py app/funcionarios_routes.py "
        "app/tipo_despesa_routes.py app/tributacao_routes.py app/variacoes_routes.py"
    ) in source


def test_backend_ci_has_blocking_pdv_dashboard_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "PDV dashboard root lint (blocking)" in source
    assert (
        "ruff check app/dashboard_routes.py app/pdv_ai_routes.py "
        "app/pdv_indicadores_routes.py"
    ) in source


def test_backend_ci_has_blocking_empresa_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Empresa root lint (blocking)" in source
    assert (
        "ruff check app/empresa_routes.py app/empresa_config_routes.py "
        "app/empresa_config_fiscal_models.py app/empresa_config_geral_models.py "
        "app/config.py app/constants.py"
    ) in source


def test_backend_ci_has_blocking_access_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Access root lint (blocking)" in source
    assert (
        "ruff check app/canais.py app/partner_utils.py app/permissions_routes.py "
        "app/roles_routes.py app/cargos_routes.py app/cargo_models.py"
    ) in source


def test_backend_ci_has_blocking_financial_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Financial root lint (blocking)" in source
    assert (
        "ruff check app/financeiro_models.py app/contas_bancarias_routes.py "
        "app/contas_pagar_routes.py app/contas_receber_routes.py "
        "app/lancamentos_routes.py app/operadoras_models.py "
        "app/operadoras_routes.py app/formas_pagamento_models.py "
        "app/formas_pagamento_routes.py"
    ) in source


def test_backend_ci_has_blocking_estoque_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")
    estoque_files = sorted(
        f"app/{path.name}" for path in (ROOT / "backend" / "app").glob("estoque_*.py")
    )

    assert "Estoque root lint (blocking)" in source
    assert f"ruff check {' '.join(estoque_files)}" in source


def test_backend_ci_has_blocking_racoes_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")
    racoes_files = sorted(
        f"app/{path.name}"
        for path in (ROOT / "backend" / "app").glob("*.py")
        if any(token in path.name for token in ("_racao.", "_racao_", "_racoes_"))
        if path.name != "calculadora_racao.py"
    )

    assert "Racoes root lint (blocking)" in source
    assert f"ruff check {' '.join(racoes_files)}" in source


def test_backend_ci_has_blocking_comissoes_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Comissoes root lint (blocking)" in source
    assert (
        "ruff check app/comissoes_avancadas_models.py "
        "app/comissoes_avancadas_routes.py app/comissoes_demonstrativo_routes.py "
        "app/comissoes_diagnostico_routes.py app/comissoes_estorno.py "
        "app/comissoes_models.py app/comissoes_provisao.py "
        "app/comissoes_routes.py app/comissoes_service.py"
    ) in source


def test_backend_ci_has_blocking_veterinario_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Veterinario root lint (blocking)" in source
    assert (
        "ruff check app/veterinario_acompanhamento_routes.py "
        "app/veterinario_agenda_routes.py app/veterinario_agendamentos.py "
        "app/veterinario_calendar.py app/veterinario_catalogo_routes.py "
        "app/veterinario_clinico.py app/veterinario_consultas_routes.py "
        "app/veterinario_core.py app/veterinario_exames_arquivos.py "
        "app/veterinario_exames_ia.py app/veterinario_exames_routes.py "
        "app/veterinario_extratos.py app/veterinario_extratos_routes.py "
        "app/veterinario_financeiro.py app/veterinario_ia.py "
        "app/veterinario_ia_routes.py app/veterinario_internacao.py "
        "app/veterinario_internacao_routes.py app/veterinario_models.py "
        "app/veterinario_orcamentos.py app/veterinario_orcamentos_routes.py "
        "app/veterinario_parcerias_routes.py app/veterinario_preventivo.py "
        "app/veterinario_relatorios_routes.py app/veterinario_routes.py "
        "app/veterinario_schemas.py app/veterinario_serializers.py "
        "app/pdf_veterinario.py"
    ) in source


def test_backend_ci_has_blocking_residual_app_root_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Residual app root lint (blocking)" in source
    assert (
        "ruff check app/auditoria_provisoes_routes.py app/auth_routes.py "
        "app/chat_routes.py app/criar_tabelas_formas_pagamento.py "
        "app/lembretes.py app/models.py app/pdf_caixa.py "
        "app/projecao_caixa_routes.py app/relatorio_vendas_routes.py "
        "app/rotas_entrega_models.py app/simulacao_contratacao_routes.py "
        "app/template_models.py app/vendas_models.py"
    ) in source


def test_backend_ci_has_blocking_multi_tenant_tests_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Multi tenant tests lint (blocking)" in source
    assert "ruff check tests/multi_tenant" in source


def test_backend_ci_has_blocking_unit_tests_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Unit tests lint (blocking)" in source
    assert "ruff check tests/unit" in source


def test_backend_ci_has_blocking_domain_integration_tests_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Domain integration tests lint (blocking)" in source
    assert "ruff check tests/domain tests/integration" in source


def test_backend_ci_has_blocking_alembic_env_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Alembic env lint (blocking)" in source
    assert "ruff check alembic/env.py" in source


def test_backend_ci_has_blocking_ai_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "AI lint (blocking)" in source
    assert "ruff check app/ai" in source


def test_backend_ci_has_blocking_ai_core_lint_step():
    source = BACKEND_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "AI Core lint (blocking)" in source
    assert "ruff check app/ai_core" in source
