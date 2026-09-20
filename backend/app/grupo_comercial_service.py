"""Regras de negocio para o vinculo seguro entre empresas do CorePet."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialGestor,
    GrupoComercialMembro,
)
from app.grupo_comercial_sql import empresa_id_igual
from app.auth.auth_multitenant_support import grant_all_permissions_to_role
from app.models import Role, Tenant, User, UserTenant
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.services.business_audit_service import log_business_event
from app.services.plan_catalog import resolve_signup_selection
from app.services.tenant_provisioning_service import provision_tenant
from app.tenancy.context import (
    clear_tenant_context,
    get_current_tenant,
    set_tenant_context,
)


NOME_ROLE_MASTER = "Administrador (Grupo)"


def _agora_utc(agora: datetime | None = None) -> datetime:
    valor = agora or datetime.now(timezone.utc)
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


class GrupoComercialService:
    def __init__(self, db: Session, *, agora: datetime | None = None):
        self.db = db
        self.agora = _agora_utc(agora)

    @staticmethod
    def _empresa_id(empresa_id) -> str:
        return str(empresa_id)

    def _empresa_ativa(self, empresa_id: str) -> Tenant:
        empresa = (
            self.db.query(Tenant)
            .filter(Tenant.id == str(empresa_id), Tenant.status == "active")
            .first()
        )
        if empresa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada ou inativa.",
            )
        return empresa

    def _grupo_ativo(self, grupo_id: int, *, travar: bool = False) -> GrupoComercial:
        query = self.db.query(GrupoComercial).filter(
            GrupoComercial.id == grupo_id,
            GrupoComercial.status == "ativo",
        )
        if travar:
            query = query.with_for_update()
        grupo = query.first()
        if grupo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo Comercial não encontrado.",
            )
        return grupo

    def _membro_ativo(
        self, grupo_id: int, empresa_id: str, *, exigir_responsavel: bool = False
    ) -> GrupoComercialMembro:
        membro = (
            self.db.query(GrupoComercialMembro)
            .filter(
                GrupoComercialMembro.grupo_id == grupo_id,
                GrupoComercialMembro.empresa_id == str(empresa_id),
                GrupoComercialMembro.status == "ativo",
            )
            .first()
        )
        if membro is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sua empresa não participa deste grupo.",
            )
        if exigir_responsavel and membro.papel != "responsavel":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente a empresa responsável pelo grupo pode realizar esta ação.",
            )
        return membro

    def _auditar(
        self,
        *,
        empresa_id: str,
        usuario_id: int,
        evento: str,
        grupo_id: int,
        metadados: dict | None = None,
    ) -> None:
        log_business_event(
            db=self.db,
            tenant_id=empresa_id,
            user_id=usuario_id,
            event=evento,
            entity_type="grupo_comercial",
            entity_id=grupo_id,
            metadata=metadados or {},
            commit=False,
        )

    def criar_grupo(
        self, empresa_id, usuario_id: int, nome: str, *, commit: bool = True
    ) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        self._empresa_ativa(empresa_id)
        nome_limpo = " ".join(nome.split())
        grupo = GrupoComercial(
            nome=nome_limpo,
            criado_por_empresa_id=empresa_id,
            criado_por_usuario_id=usuario_id,
        )
        self.db.add(grupo)
        self.db.flush()
        membro = GrupoComercialMembro(
            grupo_id=grupo.id,
            empresa_id=empresa_id,
            papel="responsavel",
            status="ativo",
            usuario_referencia_id=usuario_id,
        )
        self.db.add(membro)
        # O usuario que cria o grupo vira o master permanente dele - acesso
        # total a todas as lojas do proprio grupo, nunca alterado por tela.
        # So marca se ainda nao for master de nenhum outro grupo (nao deveria
        # rodar duas vezes pro mesmo fundador, mas fica idempotente por
        # seguranca).
        usuario = self.db.query(User).filter(User.id == usuario_id).first()
        if usuario is not None and usuario.master_grupo_id is None:
            usuario.master_grupo_id = grupo.id
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento="grupo_comercial_criado",
            grupo_id=grupo.id,
        )
        if commit:
            self.db.commit()
            registrar_uso_funcionalidade(self.db, "grupos-comerciais-nova-loja")
        return self._serializar_grupo(grupo, membro, usuario)

    def remover_membro(
        self,
        empresa_id,
        usuario: User,
        grupo_id: int,
        membro_empresa_id: str,
    ) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        grupo = self._grupo_ativo(grupo_id, travar=True)
        self._membro_ativo(grupo.id, empresa_id, exigir_responsavel=True)
        self.exigir_acesso_gestao(grupo.id, usuario)
        membro = (
            self.db.query(GrupoComercialMembro)
            .filter(
                GrupoComercialMembro.grupo_id == grupo.id,
                GrupoComercialMembro.empresa_id == str(membro_empresa_id),
                GrupoComercialMembro.status == "ativo",
            )
            .with_for_update()
            .first()
        )
        if membro is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa membro não encontrada no grupo.",
            )
        if membro.papel == "responsavel":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A empresa responsável não pode ser removida do próprio grupo.",
            )
        membro.status = "removido"
        membro.removido_em = self.agora
        compartilhamentos = (
            self.db.query(GrupoComercialEstoqueCompartilhado)
            .filter(
                GrupoComercialEstoqueCompartilhado.grupo_id == grupo.id,
                GrupoComercialEstoqueCompartilhado.status == "ativo",
                empresa_id_igual(
                    GrupoComercialEstoqueCompartilhado.empresa_origem_id,
                    membro_empresa_id,
                )
                | empresa_id_igual(
                    GrupoComercialEstoqueCompartilhado.empresa_consumidora_id,
                    membro_empresa_id,
                ),
            )
            .all()
        )
        for compartilhamento in compartilhamentos:
            compartilhamento.status = "removido"
            compartilhamento.removido_em = self.agora
            compartilhamento.atualizado_em = self.agora
        grupo.versao_membros = int(grupo.versao_membros or 1) + 1
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario.id,
            evento="grupo_comercial_membro_removido",
            grupo_id=grupo.id,
            metadados={"empresa_removida_id": str(membro_empresa_id)},
        )
        self.db.commit()
        return {"mensagem": "Empresa removida do grupo."}

    def _garantir_acesso_master(self, *, grupo_id: int, tenant_id) -> None:
        """Garante que o usuario master do grupo (se existir) tenha acesso
        administrativo completo na loja que acabou de entrar no grupo - sem
        isso ele precisaria ser adicionado manualmente toda vez que uma loja
        nova nascer dentro do grupo, mesmo quando quem adicionou a loja nao
        foi o proprio master.

        A busca pelo master roda com o contexto de tenant temporariamente
        limpo: o filtro automatico de tenant (app/tenancy/filters.py) so
        enxerga um User de outra loja quando ja existe um UserTenant ativo
        dele la - exatamente o vinculo que este metodo ainda vai criar, entao
        com o contexto da loja nova ele nunca apareceria na busca.
        """
        contexto_anterior = get_current_tenant()
        clear_tenant_context()
        try:
            master = (
                self.db.query(User).filter(User.master_grupo_id == grupo_id).first()
            )
        finally:
            if contexto_anterior is not None:
                set_tenant_context(contexto_anterior)

        if master is None:
            return

        ja_tem_acesso = (
            self.db.query(UserTenant)
            .filter(
                UserTenant.user_id == master.id,
                UserTenant.tenant_id == tenant_id,
                UserTenant.is_active.is_(True),
            )
            .first()
        )
        if ja_tem_acesso is not None:
            return

        role = (
            self.db.query(Role)
            .filter(Role.tenant_id == tenant_id, Role.name == NOME_ROLE_MASTER)
            .first()
        )
        if role is None:
            role = Role(name=NOME_ROLE_MASTER, tenant_id=tenant_id)
            self.db.add(role)
            self.db.flush()
            grant_all_permissions_to_role(
                role_id=role.id, tenant_id=tenant_id, db=self.db
            )

        self.db.add(
            UserTenant(
                user_id=master.id,
                tenant_id=tenant_id,
                role_id=role.id,
                is_active=True,
            )
        )

    def _e_master(self, grupo_id: int, usuario: User) -> bool:
        return usuario.master_grupo_id == grupo_id

    def _e_gestor(self, grupo_id: int, user_id: int) -> bool:
        return (
            self.db.query(GrupoComercialGestor.id)
            .filter(
                GrupoComercialGestor.grupo_id == grupo_id,
                GrupoComercialGestor.user_id == user_id,
                GrupoComercialGestor.status == "ativo",
            )
            .first()
            is not None
        )

    def tem_acesso_gestao(self, grupo_id: int, usuario: User) -> bool:
        return self._e_master(grupo_id, usuario) or self._e_gestor(
            grupo_id, usuario.id
        )

    def exigir_acesso_gestao(self, grupo_id: int, usuario: User) -> None:
        if not self.tem_acesso_gestao(grupo_id, usuario):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Você não tem acesso à gestão deste grupo comercial. "
                    "Peça para o responsável do grupo liberar seu acesso."
                ),
            )

    def listar_gestores(self, grupo_id: int, usuario: User) -> list[dict]:
        self.exigir_acesso_gestao(grupo_id, usuario)
        linhas = (
            self.db.query(GrupoComercialGestor, User)
            .join(User, User.id == GrupoComercialGestor.user_id)
            .filter(
                GrupoComercialGestor.grupo_id == grupo_id,
                GrupoComercialGestor.status == "ativo",
            )
            .order_by(User.nome.asc())
            .all()
        )
        return [
            {
                "user_id": gestor.user_id,
                "nome": alvo.nome or alvo.email or alvo.username,
                "email": alvo.email,
                "concedido_em": gestor.concedido_em,
            }
            for gestor, alvo in linhas
        ]

    def conceder_gestor(
        self, grupo_id: int, empresa_id, master: User, user_id: int
    ) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        if not self._e_master(grupo_id, master):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente o usuário master do grupo pode conceder este acesso.",
            )
        self._grupo_ativo(grupo_id)
        alvo = self.db.query(User).filter(User.id == user_id).first()
        if alvo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
            )
        gestor = (
            self.db.query(GrupoComercialGestor)
            .filter(
                GrupoComercialGestor.grupo_id == grupo_id,
                GrupoComercialGestor.user_id == user_id,
            )
            .first()
        )
        if gestor is None:
            gestor = GrupoComercialGestor(
                grupo_id=grupo_id,
                user_id=user_id,
                concedido_por_user_id=master.id,
                status="ativo",
            )
            self.db.add(gestor)
        else:
            gestor.status = "ativo"
            gestor.concedido_por_user_id = master.id
            gestor.concedido_em = self.agora
            gestor.revogado_em = None
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=master.id,
            evento="grupo_comercial_gestor_concedido",
            grupo_id=grupo_id,
            metadados={"user_id": user_id},
        )
        self.db.commit()
        return {"mensagem": "Acesso de gestão concedido.", "user_id": user_id}

    def revogar_gestor(
        self, grupo_id: int, empresa_id, master: User, user_id: int
    ) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        if not self._e_master(grupo_id, master):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente o usuário master do grupo pode revogar este acesso.",
            )
        gestor = (
            self.db.query(GrupoComercialGestor)
            .filter(
                GrupoComercialGestor.grupo_id == grupo_id,
                GrupoComercialGestor.user_id == user_id,
                GrupoComercialGestor.status == "ativo",
            )
            .first()
        )
        if gestor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Este usuário não tem acesso de gestão neste grupo.",
            )
        gestor.status = "revogado"
        gestor.revogado_em = self.agora
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=master.id,
            evento="grupo_comercial_gestor_revogado",
            grupo_id=grupo_id,
            metadados={"user_id": user_id},
        )
        self.db.commit()
        return {"mensagem": "Acesso de gestão revogado.", "user_id": user_id}

    def adicionar_loja(
        self,
        *,
        grupo_id: int,
        usuario: User,
        nome_loja: str,
        nome_acesso: str | None = None,
        plan: str | None = None,
        organization_type: str | None = None,
        restore_tenant_id=None,
        empresa_acionadora_id: str | None = None,
        commit: bool = True,
    ) -> dict:
        """Provisiona uma loja nova e a anexa direto neste grupo, como
        `membro` — sem passar pelo fluxo de convite/código, porque é o
        mesmo dono legal adicionando mais uma loja própria, não duas
        empresas independentes se juntando depois. Usado tanto pela rota
        self-service (responsável do grupo autenticado) quanto pelo
        onboarding assistido de ops.

        `empresa_acionadora_id`: quando informado, exige que essa empresa
        seja a responsável pelo grupo (chamada self-service, via rota
        autenticada por tenant). Quando `None`, pula essa checagem — uso do
        onboarding assistido de ops, que já se autoriza via admin de
        plataforma, não via sessão de tenant.
        """
        grupo = self._grupo_ativo(grupo_id, travar=True)
        if empresa_acionadora_id is not None:
            self._membro_ativo(grupo.id, empresa_acionadora_id, exigir_responsavel=True)
            self.exigir_acesso_gestao(grupo.id, usuario)
        nome_limpo = " ".join(nome_loja.split())
        try:
            selected_plan, resolved_organization_type = resolve_signup_selection(
                plan, organization_type
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc

        resultado = provision_tenant(
            self.db,
            tenant_name=nome_limpo,
            login_name=nome_acesso or nome_limpo,
            plan_code=selected_plan.code,
            organization_type=resolved_organization_type,
            user=usuario,
            restore_tenant_id=restore_tenant_id,
        )
        # provision_tenant ja restaurou o contexto pro tenant chamador (ou
        # limpou, se nao houver) — mas o insert do membro e a auditoria
        # abaixo se referem ao tenant NOVO, entao o contexto precisa
        # apontar pra ele por um instante antes de voltar ao que era.
        set_tenant_context(resultado.tenant_id)
        try:
            membro = GrupoComercialMembro(
                grupo_id=grupo.id,
                empresa_id=str(resultado.tenant_id),
                papel="membro",
                status="ativo",
                usuario_referencia_id=usuario.id,
            )
            self.db.add(membro)
            grupo.versao_membros = int(grupo.versao_membros or 1) + 1
            self._garantir_acesso_master(
                grupo_id=grupo.id, tenant_id=resultado.tenant_id
            )
            self._auditar(
                empresa_id=str(resultado.tenant_id),
                usuario_id=usuario.id,
                evento="grupo_comercial_loja_adicionada",
                grupo_id=grupo.id,
                metadados={"adicionada_via_grupo_id": grupo.id},
            )
            if commit:
                self.db.commit()
                registrar_uso_funcionalidade(self.db, "grupos-comerciais-nova-loja")
        finally:
            if restore_tenant_id is not None:
                set_tenant_context(restore_tenant_id)
            else:
                clear_tenant_context()
        return {
            "tenant_id": str(resultado.tenant_id),
            "nome": resultado.tenant.name,
            "login_name": resultado.login_name,
            "grupo_id": grupo.id,
        }

    def listar_resumo(self, empresa_id, usuario: User) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        participacoes = (
            self.db.query(GrupoComercial, GrupoComercialMembro)
            .join(
                GrupoComercialMembro,
                GrupoComercialMembro.grupo_id == GrupoComercial.id,
            )
            .filter(
                GrupoComercialMembro.empresa_id == empresa_id,
                GrupoComercialMembro.status == "ativo",
                GrupoComercial.status == "ativo",
            )
            .order_by(GrupoComercial.nome.asc())
            .all()
        )
        grupos_visiveis = []
        tem_grupo_sem_acesso = False
        for grupo, membro in participacoes:
            if self.tem_acesso_gestao(grupo.id, usuario):
                grupos_visiveis.append(self._serializar_grupo(grupo, membro, usuario))
            else:
                tem_grupo_sem_acesso = True
        return {
            "empresa_atual_id": empresa_id,
            "grupos": grupos_visiveis,
            "tem_grupo_sem_acesso": tem_grupo_sem_acesso,
        }

    def _serializar_membros(self, grupo_id: int) -> list[dict]:
        linhas = (
            self.db.query(GrupoComercialMembro, Tenant)
            .join(Tenant, Tenant.id == GrupoComercialMembro.empresa_id)
            .filter(
                GrupoComercialMembro.grupo_id == grupo_id,
                GrupoComercialMembro.status == "ativo",
            )
            .order_by(GrupoComercialMembro.papel.desc(), Tenant.name.asc())
            .all()
        )
        return [
            {
                "empresa_id": str(membro.empresa_id),
                "empresa_nome": empresa.name,
                "papel": membro.papel,
                "entrou_em": membro.entrou_em,
            }
            for membro, empresa in linhas
        ]

    def _serializar_grupo(
        self,
        grupo: GrupoComercial,
        participacao: GrupoComercialMembro,
        usuario: User,
    ) -> dict:
        return {
            "id": grupo.id,
            "nome": grupo.nome,
            "papel": participacao.papel,
            "status": grupo.status,
            "versao_membros": grupo.versao_membros,
            "criado_em": grupo.criado_em,
            "sou_master": self._e_master(grupo.id, usuario),
            "sou_gestor": self.tem_acesso_gestao(grupo.id, usuario),
            "membros": self._serializar_membros(grupo.id),
        }
