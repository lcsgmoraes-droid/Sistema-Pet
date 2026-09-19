"""Regras de negocio para o vinculo seguro entre empresas do CorePet."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.grupo_comercial_models import (
    GrupoComercial,
    GrupoComercialCodigo,
    GrupoComercialConvite,
    GrupoComercialEstoqueCompartilhado,
    GrupoComercialMembro,
)
from app.grupo_comercial_sql import empresa_id_igual
from app.models import Tenant, User
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.services.business_audit_service import log_business_event
from app.services.plan_catalog import resolve_signup_selection
from app.services.tenant_provisioning_service import provision_tenant


CODIGO_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODIGO_TAMANHO = 12
FUSO_NEGOCIO = ZoneInfo("America/Sao_Paulo")


def _agora_utc(agora: datetime | None = None) -> datetime:
    valor = agora or datetime.now(timezone.utc)
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _em_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _competencia_e_expiracao(agora: datetime) -> tuple[str, datetime]:
    local = agora.astimezone(FUSO_NEGOCIO)
    competencia = f"{local.year:04d}-{local.month:02d}"
    if local.month == 12:
        proximo_ano, proximo_mes = local.year + 1, 1
    else:
        proximo_ano, proximo_mes = local.year, local.month + 1
    expiracao_local = datetime(proximo_ano, proximo_mes, 1, tzinfo=FUSO_NEGOCIO)
    return competencia, expiracao_local.astimezone(timezone.utc)


def _normalizar_codigo(valor: str) -> str:
    codigo = re.sub(r"[\s-]+", "", str(valor or "")).upper()
    if len(codigo) != CODIGO_TAMANHO or any(
        caractere not in CODIGO_ALFABETO for caractere in codigo
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código da empresa inválido ou expirado.",
        )
    return codigo


def _formatar_codigo(codigo: str) -> str:
    return "-".join(codigo[indice : indice + 4] for indice in range(0, 12, 4))


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

    def _novo_codigo(self) -> str:
        for _tentativa in range(20):
            codigo = "".join(
                secrets.choice(CODIGO_ALFABETO) for _ in range(CODIGO_TAMANHO)
            )
            existente = (
                self.db.query(GrupoComercialCodigo.id)
                .filter(GrupoComercialCodigo.codigo == codigo)
                .first()
            )
            if existente is None:
                return codigo
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível gerar o código agora. Tente novamente.",
        )

    def obter_codigo(self, empresa_id, usuario_id: int) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        self._empresa_ativa(empresa_id)
        competencia, expira_em = _competencia_e_expiracao(self.agora)
        codigo = (
            self.db.query(GrupoComercialCodigo)
            .filter(
                GrupoComercialCodigo.empresa_id == empresa_id,
                GrupoComercialCodigo.competencia == competencia,
            )
            .first()
        )
        if codigo is None:
            codigo = GrupoComercialCodigo(
                empresa_id=empresa_id,
                competencia=competencia,
                codigo=self._novo_codigo(),
                criado_por_usuario_id=usuario_id,
                expira_em=expira_em,
            )
            self.db.add(codigo)
            try:
                self.db.commit()
            except IntegrityError as exc:
                self.db.rollback()
                codigo = (
                    self.db.query(GrupoComercialCodigo)
                    .filter(
                        GrupoComercialCodigo.empresa_id == empresa_id,
                        GrupoComercialCodigo.competencia == competencia,
                    )
                    .first()
                )
                if codigo is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="O código foi criado em outra sessão. Recarregue a página.",
                    ) from exc
            else:
                self.db.refresh(codigo)
        return {
            "codigo": _formatar_codigo(codigo.codigo),
            "competencia": codigo.competencia,
            "expira_em": codigo.expira_em,
        }

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
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento="grupo_comercial_criado",
            grupo_id=grupo.id,
        )
        if commit:
            self.db.commit()
            registrar_uso_funcionalidade(self.db, "grupos-comerciais-convites")
        return self._serializar_grupo(grupo, membro)

    def convidar(
        self,
        empresa_id,
        usuario_id: int,
        grupo_id: int,
        codigo_empresa: str,
    ) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        grupo = self._grupo_ativo(grupo_id, travar=True)
        self._membro_ativo(grupo.id, empresa_id, exigir_responsavel=True)
        codigo_normalizado = _normalizar_codigo(codigo_empresa)
        codigo = (
            self.db.query(GrupoComercialCodigo)
            .filter(
                GrupoComercialCodigo.codigo == codigo_normalizado,
                GrupoComercialCodigo.expira_em > self.agora,
            )
            .first()
        )
        if codigo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código da empresa inválido ou expirado.",
            )
        empresa_convidada_id = str(codigo.empresa_id)
        empresa_convidada = self._empresa_ativa(empresa_convidada_id)
        if empresa_convidada_id == empresa_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A empresa responsável já faz parte do grupo.",
            )
        membro = (
            self.db.query(GrupoComercialMembro)
            .filter(
                GrupoComercialMembro.grupo_id == grupo.id,
                GrupoComercialMembro.empresa_id == empresa_convidada_id,
                GrupoComercialMembro.status == "ativo",
            )
            .first()
        )
        if membro is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta empresa já participa do grupo.",
            )

        convite = (
            self.db.query(GrupoComercialConvite)
            .filter(
                GrupoComercialConvite.grupo_id == grupo.id,
                GrupoComercialConvite.empresa_convidada_id == empresa_convidada_id,
            )
            .with_for_update()
            .first()
        )
        if (
            convite is not None
            and convite.status == "pendente"
            and _em_utc(convite.expira_em) > self.agora
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um convite pendente para esta empresa.",
            )
        if convite is None:
            convite = GrupoComercialConvite(
                grupo_id=grupo.id,
                empresa_convidada_id=empresa_convidada_id,
                convidado_por_empresa_id=empresa_id,
                convidado_por_usuario_id=usuario_id,
                status="pendente",
                expira_em=codigo.expira_em,
            )
            self.db.add(convite)
        else:
            convite.convidado_por_empresa_id = empresa_id
            convite.convidado_por_usuario_id = usuario_id
            convite.respondido_por_usuario_id = None
            convite.status = "pendente"
            convite.criado_em = self.agora
            convite.expira_em = codigo.expira_em
            convite.respondido_em = None
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento="grupo_comercial_convite_enviado",
            grupo_id=grupo.id,
            metadados={"empresa_convidada_id": empresa_convidada_id},
        )
        self.db.commit()
        self.db.refresh(convite)
        return self._serializar_convite_enviado(convite, empresa_convidada)

    def _fechar_grupo_solo_se_necessario(self, empresa_id: str, usuario_id: int) -> None:
        """Fecha o grupo-de-1 antigo de uma empresa que está entrando em outro
        grupo agora — só age se a empresa participa hoje de exatamente 1
        grupo, sozinha, como responsável (um "grupo-de-1" puro); nunca mexe
        num grupo com outros membros ativos.
        """
        membros_ativos = (
            self.db.query(GrupoComercialMembro)
            .filter(
                GrupoComercialMembro.empresa_id == empresa_id,
                GrupoComercialMembro.status == "ativo",
            )
            .with_for_update()
            .all()
        )
        if len(membros_ativos) != 1:
            return
        membro_solo = membros_ativos[0]
        if membro_solo.papel != "responsavel":
            return
        outro_membro_no_grupo = (
            self.db.query(GrupoComercialMembro.id)
            .filter(
                GrupoComercialMembro.grupo_id == membro_solo.grupo_id,
                GrupoComercialMembro.status == "ativo",
                GrupoComercialMembro.id != membro_solo.id,
            )
            .first()
        )
        if outro_membro_no_grupo is not None:
            return

        grupo_solo = self._grupo_ativo(membro_solo.grupo_id, travar=True)
        membro_solo.status = "removido"
        membro_solo.removido_em = self.agora
        grupo_solo.status = "encerrado"
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento="grupo_comercial_solo_encerrado",
            grupo_id=grupo_solo.id,
        )

    def responder_convite(
        self,
        empresa_id,
        usuario_id: int,
        convite_id: int,
        *,
        aceitar: bool,
    ) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        convite = (
            self.db.query(GrupoComercialConvite)
            .filter(
                GrupoComercialConvite.id == convite_id,
                GrupoComercialConvite.empresa_convidada_id == empresa_id,
            )
            .with_for_update()
            .first()
        )
        if convite is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convite não encontrado para esta empresa.",
            )
        if convite.status != "pendente":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este convite já foi respondido.",
            )
        if _em_utc(convite.expira_em) <= self.agora:
            convite.status = "expirado"
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Este convite expirou. Solicite um novo convite.",
            )
        grupo = self._grupo_ativo(convite.grupo_id, travar=True)
        convite.respondido_por_usuario_id = usuario_id
        convite.respondido_em = self.agora
        if aceitar:
            self._fechar_grupo_solo_se_necessario(empresa_id, usuario_id)
            membro = (
                self.db.query(GrupoComercialMembro)
                .filter(
                    GrupoComercialMembro.grupo_id == grupo.id,
                    GrupoComercialMembro.empresa_id == empresa_id,
                )
                .with_for_update()
                .first()
            )
            if membro is None:
                membro = GrupoComercialMembro(
                    grupo_id=grupo.id,
                    empresa_id=empresa_id,
                    papel="membro",
                    status="ativo",
                    usuario_referencia_id=usuario_id,
                )
                self.db.add(membro)
            else:
                membro.papel = "membro"
                membro.status = "ativo"
                membro.entrou_em = self.agora
                membro.removido_em = None
                membro.usuario_referencia_id = usuario_id
            convite.status = "aceito"
            grupo.versao_membros = int(grupo.versao_membros or 1) + 1
            evento = "grupo_comercial_convite_aceito"
            mensagem = "Convite aceito. Sua empresa agora faz parte do grupo."
        else:
            convite.status = "recusado"
            evento = "grupo_comercial_convite_recusado"
            mensagem = "Convite recusado."
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento=evento,
            grupo_id=grupo.id,
        )
        self.db.commit()
        if aceitar:
            registrar_uso_funcionalidade(self.db, "grupos-comerciais-convites")
        return {"mensagem": mensagem, "grupo_id": grupo.id, "status": convite.status}

    def remover_membro(
        self,
        empresa_id,
        usuario_id: int,
        grupo_id: int,
        membro_empresa_id: str,
    ) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        grupo = self._grupo_ativo(grupo_id, travar=True)
        self._membro_ativo(grupo.id, empresa_id, exigir_responsavel=True)
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
            usuario_id=usuario_id,
            evento="grupo_comercial_membro_removido",
            grupo_id=grupo.id,
            metadados={"empresa_removida_id": str(membro_empresa_id)},
        )
        self.db.commit()
        return {"mensagem": "Empresa removida do grupo."}

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
        membro = GrupoComercialMembro(
            grupo_id=grupo.id,
            empresa_id=str(resultado.tenant_id),
            papel="membro",
            status="ativo",
            usuario_referencia_id=usuario.id,
        )
        self.db.add(membro)
        grupo.versao_membros = int(grupo.versao_membros or 1) + 1
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
        return {
            "tenant_id": str(resultado.tenant_id),
            "nome": resultado.tenant.name,
            "login_name": resultado.login_name,
            "grupo_id": grupo.id,
        }

    def listar_resumo(self, empresa_id, usuario_id: int) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        codigo = self.obter_codigo(empresa_id, usuario_id)
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
        convites = (
            self.db.query(GrupoComercialConvite, GrupoComercial)
            .join(GrupoComercial, GrupoComercial.id == GrupoComercialConvite.grupo_id)
            .filter(
                GrupoComercialConvite.empresa_convidada_id == empresa_id,
                GrupoComercialConvite.status == "pendente",
                GrupoComercialConvite.expira_em > self.agora,
                GrupoComercial.status == "ativo",
            )
            .order_by(GrupoComercialConvite.criado_em.desc())
            .all()
        )
        return {
            "empresa_atual_id": empresa_id,
            "codigo_empresa": codigo,
            "convites_pendentes": [
                self._serializar_convite_recebido(convite, grupo)
                for convite, grupo in convites
            ],
            "grupos": [
                self._serializar_grupo(grupo, membro) for grupo, membro in participacoes
            ],
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

    def _serializar_convite_enviado(
        self, convite: GrupoComercialConvite, empresa: Tenant
    ) -> dict:
        return {
            "id": convite.id,
            "empresa_id": str(convite.empresa_convidada_id),
            "empresa_nome": empresa.name,
            "status": convite.status,
            "criado_em": convite.criado_em,
            "expira_em": convite.expira_em,
        }

    def _convites_enviados(self, grupo_id: int) -> list[dict]:
        linhas = (
            self.db.query(GrupoComercialConvite, Tenant)
            .join(Tenant, Tenant.id == GrupoComercialConvite.empresa_convidada_id)
            .filter(
                GrupoComercialConvite.grupo_id == grupo_id,
                GrupoComercialConvite.status == "pendente",
                GrupoComercialConvite.expira_em > self.agora,
            )
            .order_by(GrupoComercialConvite.criado_em.desc())
            .all()
        )
        return [
            self._serializar_convite_enviado(convite, empresa)
            for convite, empresa in linhas
        ]

    def _serializar_grupo(
        self, grupo: GrupoComercial, participacao: GrupoComercialMembro
    ) -> dict:
        return {
            "id": grupo.id,
            "nome": grupo.nome,
            "papel": participacao.papel,
            "status": grupo.status,
            "versao_membros": grupo.versao_membros,
            "criado_em": grupo.criado_em,
            "membros": self._serializar_membros(grupo.id),
            "convites_enviados": (
                self._convites_enviados(grupo.id)
                if participacao.papel == "responsavel"
                else []
            ),
        }

    def _serializar_convite_recebido(
        self, convite: GrupoComercialConvite, grupo: GrupoComercial
    ) -> dict:
        empresa_origem = (
            self.db.query(Tenant)
            .filter(Tenant.id == convite.convidado_por_empresa_id)
            .first()
        )
        return {
            "id": convite.id,
            "grupo_id": grupo.id,
            "grupo_nome": grupo.nome,
            "empresa_origem_nome": empresa_origem.name if empresa_origem else "Empresa",
            "criado_em": convite.criado_em,
            "expira_em": convite.expira_em,
        }
