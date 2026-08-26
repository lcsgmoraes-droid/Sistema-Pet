from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "CATALOGO_INTEGRACOES.md"
INDEX = ROOT / "docs" / "INDICE_OPERACIONAL.md"
GOVERNANCE = ROOT / "docs" / "GOVERNANCA_ENTERPRISE.md"
STRUCTURE_VALIDATOR = ROOT / "scripts" / "validate_repository_structure.py"


def test_catalog_defines_the_minimum_integration_contract():
    source = CATALOG.read_text(encoding="utf-8")

    for required in (
        "Autenticação e segredos",
        "Timeout",
        "Retry",
        "Idempotência",
        "Fallback",
        "Reconciliação",
        "Observabilidade",
        "Responsável",
        "Lacuna",
        "não comprova que a integração está habilitada em\nprodução",
        "Nunca registrar segredo",
    ):
        assert required in source


def test_catalog_covers_the_external_integration_groups_found_in_source():
    source = CATALOG.read_text(encoding="utf-8")

    for integration in (
        "INT-001 — Bling",
        "INT-002 — iFood",
        "INT-003 — SEFAZ NF-e",
        "INT-004 — Mercado Pago",
        "INT-005 — Asaas",
        "INT-006 — WhatsApp, 360dialog e WAHA",
        "INT-007 — EcommerceAI",
        "INT-008 — Provedor de IA OpenAI",
        "INT-009 — E-mail SMTP",
        "INT-010 — Expo Push",
        "INT-011 — Google Maps",
        "INT-012 — Storage S3 compatível",
        "INT-013 — Webhook/e-mail de alertas Ops",
        "INT-014 — PubMed, DailyMed e VMD",
        "INT-015 — Operadoras e bancos por CSV/OFX",
        "INT-016 — XML/CSV fiscal, produtos e SimplesVet",
        "INT-017 — Pagar.me",
    ):
        assert integration in source


def test_catalog_keeps_remaining_webhook_risks_visible():
    source = CATALOG.read_text(encoding="utf-8")

    assert "X-Bling-Signature-256" in source
    assert "a autenticação agora é fail-closed" in source
    assert "deduplicação persistente por `wamid`" in source


def test_official_navigation_and_structure_reference_the_catalog():
    expected = "docs/CATALOGO_INTEGRACOES.md"

    assert expected in INDEX.read_text(encoding="utf-8")
    assert expected in GOVERNANCE.read_text(encoding="utf-8")
    assert expected in STRUCTURE_VALIDATOR.read_text(encoding="utf-8")


def test_primary_code_evidence_referenced_by_the_catalog_exists():
    for relative_path in (
        "backend/app/bling_integration_parts/core.py",
        "backend/app/integrations/ifood/client.py",
        "backend/app/services/sefaz_service.py",
        "backend/app/services/mercado_pago_checkout.py",
        "backend/app/services/asaas_billing_service.py",
        "backend/app/whatsapp/webhook.py",
        "backend/app/routes/ecommerceai_integration_routes.py",
        "backend/app/services/email_service.py",
        "backend/app/services/order_push_notifications.py",
        "backend/app/services/google_maps_service.py",
        "backend/app/services/product_image_storage.py",
        "backend/app/services/ops_alert_notifier.py",
        "backend/app/services/vet_clinical_evidence.py",
        "backend/app/conciliacao_services_importacao.py",
        "backend/app/notas_entrada/xml_parser.py",
    ):
        assert (ROOT / relative_path).is_file(), relative_path
