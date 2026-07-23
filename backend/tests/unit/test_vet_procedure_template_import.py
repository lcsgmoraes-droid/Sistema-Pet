from uuid import uuid4

from app.services.tenant_onboarding_vet_copies import (
    import_missing_vet_procedure_templates,
    vet_procedure_template_status,
)


def test_existing_tenant_imports_procedure_model_only_on_explicit_action(
    db_session,
    tenant_context,
):
    tenant_id = uuid4()
    tenant_context(tenant_id)

    initial = vet_procedure_template_status(db_session, tenant_id)
    assert initial["total_modelo"] == 70
    assert initial["disponiveis_para_importar"] == 70

    imported = import_missing_vet_procedure_templates(db_session, tenant_id)
    db_session.flush()

    assert imported["criados"] == 70
    assert imported["reativados"] == 0
    assert (
        vet_procedure_template_status(db_session, tenant_id)[
            "disponiveis_para_importar"
        ]
        == 0
    )

    repeated = import_missing_vet_procedure_templates(db_session, tenant_id)
    assert repeated["criados"] == 0
    assert repeated["ignorados"] == 70
