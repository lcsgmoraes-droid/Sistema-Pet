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


def tenant_id_do_usuario(db: Session, usuario_id):
    """Resolve o ``tenant_id`` "casa" do usuário (mesma lógica do backfill de
    ``dre_periodos`` na migration ``of20260512a1``).

    Usado para GRAVAR ``tenant_id`` ao CRIAR um ``DREPeriodo`` a partir de fluxos que
    só conhecem ``usuario_id`` (aba7_dre / aba7_dre_canal) — assim novas linhas nascem
    com dono, em vez de ``tenant_id`` nulo. Retorna ``None`` se não resolver
    (``usuario_id`` nulo ou usuário sem tenant); nesse caso a linha segue como antes.
    """
    if usuario_id is None:
        return None
    return db.query(User.tenant_id).filter(User.id == usuario_id).scalar()


def tenant_id_para_escrita_dre(db: Session, usuario_id):
    """Tenant a GRAVAR ao criar um ``DREPeriodo``.

    Prefere o tenant ATIVO do contexto (o que a rota estabeleceu via
    ``get_current_user_and_tenant``) — assim a linha nasce com o MESMO tenant que a lê,
    evitando o descasamento ``users.tenant_id`` (loja "casa") vs. tenant ativo do JWT em
    usuários multi-loja (onde o DRE criado iria para a loja errada e "sumiria" do contexto
    que o criou, sob o filtro TenantScoped). Fallback: o tenant "casa" do usuário, para
    chamadas fora de request (sem contexto de tenant).
    """
    from app.tenancy.context import get_current_tenant

    contexto = get_current_tenant()
    if contexto is not None:
        return contexto
    return tenant_id_do_usuario(db, usuario_id)
