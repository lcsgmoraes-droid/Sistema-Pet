from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "CATALOGO_DADOS_CRITICOS_LGPD.md"
INDEX = ROOT / "docs" / "INDICE_OPERACIONAL.md"
GOVERNANCE = ROOT / "docs" / "GOVERNANCA_ENTERPRISE.md"
STRUCTURE_VALIDATOR = ROOT / "scripts" / "validate_repository_structure.py"


def test_catalog_states_scope_and_does_not_claim_legal_certification():
    source = CATALOG.read_text(encoding="utf-8")

    for required in (
        "não um parecer jurídico",
        "certificação de conformidade",
        "propostas para validação",
        "controlador, operador ou controlador conjunto",
        "não deve ser prometido",
    ):
        assert required in source


def test_catalog_covers_the_critical_data_domains():
    source = CATALOG.read_text(encoding="utf-8")

    for domain in (
        "DAD-001 — Tenant, empresa e contrato SaaS",
        "DAD-002 — Usuários, autenticação, sessões e permissões",
        "DAD-003 — Clientes, tutores e contatos",
        "DAD-004 — Pets, agenda e prontuário veterinário",
        "DAD-005 — Vendas, pedidos, pagamentos e entregas",
        "DAD-006 — Financeiro, caixa, conciliação, DRE e comissões",
        "DAD-007 — Produtos, estoque, compras e fornecedores",
        "DAD-008 — Funcionários, parceiros e remuneração",
        "DAD-009 — Ecommerce, app, notificações e dispositivos",
        "DAD-010 — WhatsApp, campanhas e atendimento",
        "DAD-011 — Fiscal, XML e SEFAZ",
        "DAD-012 — Integrações, webhooks e identificadores externos",
        "DAD-013 — Auditoria, segurança e observabilidade",
        "DAD-014 — IA, sugestões e evidências clínicas externas",
        "DAD-015 — Preferências, consentimentos e solicitações LGPD",
        "DAD-016 — Backups, exports, imports e arquivos temporários",
    ):
        assert domain in source


def test_catalog_keeps_unapproved_controls_visible():
    source = CATALOG.read_text(encoding="utf-8")

    for required in (
        "RPO aprovado",
        "RTO aprovado",
        "Pendente negócio/jurídico",
        "operadores/suboperadores",
        "transferência internacional",
        "Automatizar purge/anonimização",
        "consolidar o caminho legado de exclusão",
    ):
        assert required in source


def test_catalog_records_existing_privacy_capabilities():
    source = CATALOG.read_text(encoding="utf-8")

    for required in (
        "dossiê/exportação",
        "anonimização automatizada de clientes/pets",
        "prazo operacional inicial de\n  15 dias",
        "restore smoke real registrado",
        "legal hold",
        "nunca devem aparecer em log",
    ):
        assert required in source


def test_official_navigation_and_structure_reference_the_catalog():
    expected = "docs/CATALOGO_DADOS_CRITICOS_LGPD.md"

    assert expected in INDEX.read_text(encoding="utf-8")
    assert expected in GOVERNANCE.read_text(encoding="utf-8")
    assert expected in STRUCTURE_VALIDATOR.read_text(encoding="utf-8")


def test_primary_code_evidence_referenced_by_the_catalog_exists():
    for relative_path in (
        "backend/app/models_cadastros.py",
        "backend/app/models.py",
        "backend/app/vendas_models.py",
        "backend/app/lgpd_models.py",
        "backend/app/services/lgpd_requests.py",
        "backend/app/services/lgpd_consents.py",
        "backend/app/services/lgpd_customer_data.py",
        "backend/app/lgpd_routes.py",
        "backend/app/routes/app_privacy_routes.py",
        "frontend/src/pages/LegalPage.jsx",
        "docs/RETENCAO_LOGS_AUDITORIA.md",
        "docs/PRODUCAO_BACKUP_RESTORE_TESTE.md",
    ):
        assert (ROOT / relative_path).is_file(), relative_path
