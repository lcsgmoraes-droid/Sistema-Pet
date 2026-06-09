"""
Escopo multi-tenant para busca de DREPeriodo.
=============================================

`DREPeriodo` ainda herda Base direto (fora do filtro global de tenant) e tem
`tenant_id` nullable (backfill incompleto). Por isso a busca do período de uma
competência (mês/ano) NÃO pode ser feita só por mês/ano — isso devolveria o
período de qualquer loja (vazamento + risco de escrever imposto no DRE alheio).

Este helper centraliza o escopo correto: o período pertence à loja se o
`tenant_id` for o da loja OU se o dono (`usuario_id`) for um usuário da loja.
A segunda condição garante que períodos legados (com `tenant_id` ainda nulo)
continuem sendo encontrados pela própria loja — e só por ela.
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ia.aba7_models import DREPeriodo
from app.models import User


def buscar_periodo_dre_do_tenant(db: Session, tenant_id, mes: int, ano: int):
    """Retorna o DREPeriodo da competência (mes/ano) pertencente ao tenant, ou None.

    Escopo robusto a backfill incompleto de `DREPeriodo.tenant_id`:
    casa por `tenant_id` direto OU pelos `usuario_id` dos usuários do tenant.
    Nunca devolve período de outra loja.
    """
    usuarios_do_tenant = db.query(User.id).filter(User.tenant_id == tenant_id)
    return (
        db.query(DREPeriodo)
        .filter(
            DREPeriodo.mes == mes,
            DREPeriodo.ano == ano,
            or_(
                DREPeriodo.tenant_id == tenant_id,
                DREPeriodo.usuario_id.in_(usuarios_do_tenant),
            ),
        )
        .first()
    )
