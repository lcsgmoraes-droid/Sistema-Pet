from __future__ import annotations

from sqlalchemy.orm import Session

from app.veterinario_models import VeterinarioLembreteConfiguracao


def obter_ou_criar_configuracao_lembretes_vet(
    db: Session, tenant_id
) -> VeterinarioLembreteConfiguracao:
    config = (
        db.query(VeterinarioLembreteConfiguracao)
        .filter(VeterinarioLembreteConfiguracao.tenant_id == tenant_id)
        .first()
    )
    if config:
        return config

    config = VeterinarioLembreteConfiguracao(tenant_id=tenant_id)
    db.add(config)
    db.flush()
    return config
