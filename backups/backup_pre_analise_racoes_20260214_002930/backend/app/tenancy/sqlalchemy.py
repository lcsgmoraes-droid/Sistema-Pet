from sqlalchemy.orm import with_loader_criteria
from sqlalchemy import event
from app.tenancy.context import get_current_tenant
from app.base_models import BaseTenantModel

def _add_tenant_criteria(execute_state):
    tenant_id = get_current_tenant()

    # Se o tenant ainda não foi definido, NÃO aplique filtro
    # Isso evita:
    # - WHERE tenant_id IS NULL
    # - RuntimeError em autenticação / bootstrap
    if tenant_id is None:
        return

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            BaseTenantModel,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
        )
    )

def setup_tenant_criteria(Session):
    event.listen(Session, "do_orm_execute", _add_tenant_criteria)