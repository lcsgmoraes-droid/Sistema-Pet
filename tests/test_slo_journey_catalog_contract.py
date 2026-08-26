from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "SLOS_INDICADORES_JORNADAS.md"
INDEX = ROOT / "docs" / "INDICE_OPERACIONAL.md"
GOVERNANCE = ROOT / "docs" / "GOVERNANCA_ENTERPRISE.md"
ARCHITECTURE = ROOT / "docs" / "ARQUITETURA.md"
STRUCTURE_VALIDATOR = ROOT / "scripts" / "validate_repository_structure.py"


def test_catalog_explains_objectives_without_claiming_a_contractual_sla():
    source = CATALOG.read_text(encoding="utf-8")

    for required in (
        "não são SLA contratual",
        "não há dados suficientes; nunca deve aparecer como verde",
        "numerador, denominador",
        "menos de 100 operações",
        "Indisponibilidade de fornecedor não desaparece",
        "Sem medição",
    ):
        assert required in source


def test_catalog_covers_platform_and_critical_journeys():
    source = CATALOG.read_text(encoding="utf-8")

    for objective in (
        "SLO-PLT-001",
        "SLO-PLT-002",
        "SLO-PLT-003",
        "SLO-DB-001",
        "SLO-DATA-001",
        "SLO-OPS-001",
        "SLO-DEP-001",
        "JRN-001 — Entrar e acessar a empresa correta",
        "JRN-002 — Finalizar venda no PDV",
        "JRN-003 — Criar e receber pedido do ecommerce/app",
        "JRN-004 — Emitir documento fiscal",
        "JRN-005 — Processar integração e webhook",
        "JRN-006 — Ativar uma nova empresa",
        "JRN-007 — Atender solicitação de privacidade",
        "JRN-008 — Recuperar o sistema e os dados",
    ):
        assert objective in source


def test_catalog_preserves_zero_tolerance_and_privacy_controls():
    source = CATALOG.read_text(encoding="utf-8")

    for required in (
        "cross-tenant",
        "Duplicação financeira = 0",
        "webhook sem autenticação aceito = 0",
        "Não devem copiar\n   nomes, mensagens, documentos, endereços",
        "Tolerância zero",
    ):
        assert required in source


def test_catalog_records_current_measurement_limits_and_next_instrumentation():
    source = CATALOG.read_text(encoding="utf-8")

    for required in (
        "não possui denominador de todas as requisições",
        "Falta evento padronizado",
        "Criar evento sanitizado por jornada",
        "30 dias de linha de base",
        "burn rate",
        "jornadas autenticadas em homologação",
    ):
        assert required in source


def test_official_navigation_references_the_slo_catalog():
    expected = "docs/SLOS_INDICADORES_JORNADAS.md"

    for document in (INDEX, GOVERNANCE, ARCHITECTURE, STRUCTURE_VALIDATOR):
        assert expected in document.read_text(encoding="utf-8")


def test_primary_code_evidence_referenced_by_the_catalog_exists():
    for relative_path in (
        "backend/app/health_router.py",
        "backend/app/middlewares/request_logging.py",
        "backend/app/services/error_event_reporter.py",
        "backend/app/services/ops_dashboard_service.py",
        "backend/app/services/ops_dashboard_actionable_alerts.py",
        "backend/app/services/ops_continuity_service.py",
        "backend/app/services/ops_tenants_service.py",
        "docs/TESTE_CAPACIDADE_SEGURO.md",
        "docs/GESTAO_INCIDENTES_SUSTENTACAO.md",
        "docs/CATALOGO_DADOS_CRITICOS_LGPD.md",
        "docs/CATALOGO_INTEGRACOES.md",
    ):
        assert (ROOT / relative_path).is_file(), relative_path
