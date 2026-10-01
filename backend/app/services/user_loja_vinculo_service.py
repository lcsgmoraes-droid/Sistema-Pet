"""Vinculo de um usuario existente a outra loja do MESMO grupo comercial.

Generaliza o que hoje so acontece automaticamente para o titular do grupo
(``GrupoComercialService._garantir_acesso_master``) — aqui, qualquer usuario
pode ganhar acesso a outra loja do grupo, escolhido manualmente na tela de
cadastro de usuario. O vinculo cross-tenant so e permitido dentro do mesmo
grupo comercial (nunca a uma loja de outro cliente, por seguranca).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.grupo_comercial_models import GrupoComercialMembro
from app.models import Role, Tenant, User, UserTenant
from app.tenancy.context import tenant_context


class VinculoLojaError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _mesmo_grupo_comercial(db: Session, tenant_origem_id: str, tenant_destino_id: str) -> bool:
    grupos_origem = {
        grupo_id
        for (grupo_id,) in db.query(GrupoComercialMembro.grupo_id).filter(
            GrupoComercialMembro.empresa_id == str(tenant_origem_id),
            GrupoComercialMembro.status == "ativo",
        )
    }
    if not grupos_origem:
        return False

    existe = (
        db.query(GrupoComercialMembro.id)
        .filter(
            GrupoComercialMembro.grupo_id.in_(grupos_origem),
            GrupoComercialMembro.empresa_id == str(tenant_destino_id),
            GrupoComercialMembro.status == "ativo",
        )
        .first()
    )
    return existe is not None


def vincular_usuario_a_loja_do_grupo(
    db: Session,
    *,
    usuario: User,
    tenant_origem_id: str,
    tenant_destino_id: str,
    commit: bool = True,
) -> UserTenant:
    """Cria um ``UserTenant`` ligando ``usuario`` a ``tenant_destino_id``.

    Valida, nessa ordem: a loja de destino pertence ao mesmo grupo comercial
    da loja de origem; a loja de destino existe e esta ativa; o usuario ja
    tem acesso ativo na loja de origem (de onde herda o NOME do perfil de
    acesso — ex. "Vendedor" — resolvido automaticamente para o perfil de
    mesmo nome na loja de destino, sem pedir esse dado de novo na tela); o
    usuario ainda nao tem acesso na loja de destino.
    """
    tenant_origem_id = str(tenant_origem_id)
    tenant_destino_id = str(tenant_destino_id)

    if tenant_destino_id == tenant_origem_id:
        raise VinculoLojaError(400, "O usuario ja tem acesso a esta loja.")

    if not _mesmo_grupo_comercial(db, tenant_origem_id, tenant_destino_id):
        raise VinculoLojaError(403, "Essa loja nao pertence ao mesmo grupo comercial.")

    tenant_destino = (
        db.query(Tenant)
        .filter(Tenant.id == tenant_destino_id, Tenant.status == "active")
        .first()
    )
    if tenant_destino is None:
        raise VinculoLojaError(404, "Loja de destino nao encontrada ou inativa.")

    # Contexto proprio pro lado da origem — nao depende do chamador ja estar
    # com o contexto de tenant certo ativo (AssinaturaModulo/UserTenant/Role
    # sao tenant-scoped e exigem contexto correspondente pra SELECT).
    with tenant_context(UUID(tenant_origem_id)):
        vinculo_origem = (
            db.query(UserTenant)
            .filter(
                UserTenant.user_id == usuario.id,
                UserTenant.tenant_id == UUID(tenant_origem_id),
                UserTenant.is_active.is_(True),
            )
            .first()
        )
        if vinculo_origem is None:
            raise VinculoLojaError(400, "Usuario nao tem acesso ativo na loja de origem.")

        role_origem = db.query(Role).filter(Role.id == vinculo_origem.role_id).first()
        nome_role = role_origem.name if role_origem else None

        # Flush aqui, ainda com o contexto da origem ativo: garante que
        # qualquer insert pendente de outra parte do fluxo (ex.: Cliente/
        # AppAccessProfile criados mais cedo em criar_usuario, ainda nao
        # flushados) nao acabe sendo pego pelo guard de tenant com o
        # contexto ja trocado pra loja de destino la embaixo.
        db.flush()

    tenant_uuid = UUID(tenant_destino_id)
    with tenant_context(tenant_uuid):
        role = (
            db.query(Role)
            .filter(Role.tenant_id == tenant_uuid, Role.name == nome_role)
            .first()
            if nome_role
            else None
        )
        if role is None:
            raise VinculoLojaError(
                400,
                "Nao existe um perfil de acesso equivalente nessa loja para "
                "vincular automaticamente.",
            )

        vinculo_existente = (
            db.query(UserTenant)
            .filter(
                UserTenant.user_id == usuario.id,
                UserTenant.tenant_id == tenant_uuid,
            )
            .first()
        )
        if vinculo_existente is not None:
            if vinculo_existente.is_active:
                raise VinculoLojaError(400, "Usuario ja vinculado a esta loja.")
            # Ja existia um vinculo aqui antes (desvinculado depois) — reativa
            # em vez de inserir outra linha pro mesmo par usuario+loja.
            vinculo_existente.is_active = True
            vinculo_existente.role_id = role.id
            db.flush()
            if commit:
                db.commit()
            return vinculo_existente

        vinculo = UserTenant(
            user_id=usuario.id,
            tenant_id=tenant_uuid,
            role_id=role.id,
            is_active=True,
        )
        db.add(vinculo)
        db.flush()
        if commit:
            db.commit()

    return vinculo


def vincular_usuario_a_qualquer_loja_do_grupo(
    db: Session,
    *,
    usuario: User,
    tenant_destino_id: str,
    commit: bool = True,
) -> UserTenant:
    """Igual ``vincular_usuario_a_loja_do_grupo``, mas resolve sozinho qual
    loja usar como origem (pra herdar o nome do perfil de acesso): a
    primeira loja do mesmo grupo onde o usuario ja tem acesso ativo — nao
    precisa ser a loja de quem esta operando a tela. Usado pela tela de
    arrastar-e-soltar, onde a loja atual de quem opera pode nem ser uma das
    lojas ja vinculadas do usuario sendo editado."""
    lojas = listar_lojas_do_grupo_com_vinculo(
        db, tenant_origem_id=tenant_destino_id, usuario_id=usuario.id
    )
    origem = next((loja["tenant_id"] for loja in lojas if loja["vinculado"]), None)
    if origem is None:
        raise VinculoLojaError(
            400, "Usuario nao tem acesso ativo em nenhuma loja deste grupo."
        )
    return vincular_usuario_a_loja_do_grupo(
        db,
        usuario=usuario,
        tenant_origem_id=origem,
        tenant_destino_id=tenant_destino_id,
        commit=commit,
    )


def listar_lojas_do_grupo_com_vinculo(
    db: Session,
    *,
    tenant_origem_id: str,
    usuario_id: int,
) -> list[dict]:
    """Lista todas as lojas ativas do mesmo grupo comercial da loja atual
    (incluindo a propria loja atual), dizendo pra cada uma se ``usuario_id``
    tem ``UserTenant`` ativo nela — base da tela de arrastar-e-soltar que
    gerencia o acesso do usuario a multiplas lojas do grupo."""
    tenant_origem_id = str(tenant_origem_id)

    grupos = {
        grupo_id
        for (grupo_id,) in db.query(GrupoComercialMembro.grupo_id).filter(
            GrupoComercialMembro.empresa_id == tenant_origem_id,
            GrupoComercialMembro.status == "ativo",
        )
    }

    membros_ids = {tenant_origem_id}
    if grupos:
        membros_ids |= {
            str(empresa_id)
            for (empresa_id,) in db.query(GrupoComercialMembro.empresa_id).filter(
                GrupoComercialMembro.grupo_id.in_(grupos),
                GrupoComercialMembro.status == "ativo",
            )
        }

    lojas = []
    for tenant_id in membros_ids:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.id == tenant_id, Tenant.status == "active")
            .first()
        )
        if tenant is None:
            continue
        tenant_uuid = UUID(tenant_id)
        with tenant_context(tenant_uuid):
            vinculo = (
                db.query(UserTenant)
                .filter(
                    UserTenant.user_id == usuario_id,
                    UserTenant.tenant_id == tenant_uuid,
                    UserTenant.is_active.is_(True),
                )
                .first()
            )
        lojas.append(
            {
                "tenant_id": tenant_id,
                "nome": tenant.name,
                "vinculado": vinculo is not None,
                "atual": tenant_id == tenant_origem_id,
            }
        )
    lojas.sort(key=lambda loja: loja["nome"].lower())
    return lojas


def desvincular_usuario_de_loja(
    db: Session,
    *,
    usuario: User,
    tenant_origem_id: str,
    tenant_destino_id: str,
    commit: bool = True,
) -> None:
    """Remove o acesso de ``usuario`` a ``tenant_destino_id`` (desativa o
    ``UserTenant``, nao apaga). Nunca deixa o usuario sem nenhuma loja ativa
    no grupo, e nunca remove o acesso do master do grupo comercial."""
    tenant_destino_id = str(tenant_destino_id)

    if usuario.master_grupo_id is not None:
        raise VinculoLojaError(
            403,
            "Este usuario e o master do grupo comercial — nao pode perder "
            "acesso a nenhuma loja.",
        )

    lojas = listar_lojas_do_grupo_com_vinculo(
        db, tenant_origem_id=tenant_origem_id, usuario_id=usuario.id
    )
    total_vinculadas = sum(1 for loja in lojas if loja["vinculado"])
    if total_vinculadas <= 1:
        raise VinculoLojaError(
            400, "O usuario precisa continuar com acesso a pelo menos uma loja."
        )

    tenant_uuid = UUID(tenant_destino_id)
    with tenant_context(tenant_uuid):
        vinculo = (
            db.query(UserTenant)
            .filter(
                UserTenant.user_id == usuario.id,
                UserTenant.tenant_id == tenant_uuid,
                UserTenant.is_active.is_(True),
            )
            .first()
        )
        if vinculo is None:
            raise VinculoLojaError(400, "Usuario ja nao tem acesso a esta loja.")
        vinculo.is_active = False
        db.flush()
        if commit:
            db.commit()
