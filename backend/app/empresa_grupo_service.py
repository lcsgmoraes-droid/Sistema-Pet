"""Regras de negocio para o vinculo seguro entre empresas do CorePet."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.empresa_grupo_models import (
    EmpresaGrupo,
    EmpresaGrupoCodigo,
    EmpresaGrupoConvite,
    EmpresaGrupoMembro,
)
from app.models import Tenant
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.services.business_audit_service import log_business_event


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


class EmpresaGrupoService:
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

    def _grupo_ativo(self, grupo_id: int, *, travar: bool = False) -> EmpresaGrupo:
        query = self.db.query(EmpresaGrupo).filter(
            EmpresaGrupo.id == grupo_id,
            EmpresaGrupo.status == "ativo",
        )
        if travar:
            query = query.with_for_update()
        grupo = query.first()
        if grupo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de empresas não encontrado.",
            )
        return grupo

    def _membro_ativo(
        self, grupo_id: int, empresa_id: str, *, exigir_responsavel: bool = False
    ) -> EmpresaGrupoMembro:
        membro = (
            self.db.query(EmpresaGrupoMembro)
            .filter(
                EmpresaGrupoMembro.grupo_id == grupo_id,
                EmpresaGrupoMembro.empresa_id == str(empresa_id),
                EmpresaGrupoMembro.status == "ativo",
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
            entity_type="empresa_grupo",
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
                self.db.query(EmpresaGrupoCodigo.id)
                .filter(EmpresaGrupoCodigo.codigo == codigo)
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
            self.db.query(EmpresaGrupoCodigo)
            .filter(
                EmpresaGrupoCodigo.empresa_id == empresa_id,
                EmpresaGrupoCodigo.competencia == competencia,
            )
            .first()
        )
        if codigo is None:
            codigo = EmpresaGrupoCodigo(
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
                    self.db.query(EmpresaGrupoCodigo)
                    .filter(
                        EmpresaGrupoCodigo.empresa_id == empresa_id,
                        EmpresaGrupoCodigo.competencia == competencia,
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

    def criar_grupo(self, empresa_id, usuario_id: int, nome: str) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        self._empresa_ativa(empresa_id)
        nome_limpo = " ".join(nome.split())
        grupo = EmpresaGrupo(
            nome=nome_limpo,
            criado_por_empresa_id=empresa_id,
            criado_por_usuario_id=usuario_id,
        )
        self.db.add(grupo)
        self.db.flush()
        membro = EmpresaGrupoMembro(
            grupo_id=grupo.id,
            empresa_id=empresa_id,
            papel="responsavel",
            status="ativo",
        )
        self.db.add(membro)
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento="empresa_grupo_criado",
            grupo_id=grupo.id,
        )
        self.db.commit()
        registrar_uso_funcionalidade(self.db, "grupos-empresas-convites")
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
            self.db.query(EmpresaGrupoCodigo)
            .filter(
                EmpresaGrupoCodigo.codigo == codigo_normalizado,
                EmpresaGrupoCodigo.expira_em > self.agora,
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
            self.db.query(EmpresaGrupoMembro)
            .filter(
                EmpresaGrupoMembro.grupo_id == grupo.id,
                EmpresaGrupoMembro.empresa_id == empresa_convidada_id,
                EmpresaGrupoMembro.status == "ativo",
            )
            .first()
        )
        if membro is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta empresa já participa do grupo.",
            )

        convite = (
            self.db.query(EmpresaGrupoConvite)
            .filter(
                EmpresaGrupoConvite.grupo_id == grupo.id,
                EmpresaGrupoConvite.empresa_convidada_id == empresa_convidada_id,
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
            convite = EmpresaGrupoConvite(
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
            evento="empresa_grupo_convite_enviado",
            grupo_id=grupo.id,
            metadados={"empresa_convidada_id": empresa_convidada_id},
        )
        self.db.commit()
        self.db.refresh(convite)
        return self._serializar_convite_enviado(convite, empresa_convidada)

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
            self.db.query(EmpresaGrupoConvite)
            .filter(
                EmpresaGrupoConvite.id == convite_id,
                EmpresaGrupoConvite.empresa_convidada_id == empresa_id,
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
            membro = (
                self.db.query(EmpresaGrupoMembro)
                .filter(
                    EmpresaGrupoMembro.grupo_id == grupo.id,
                    EmpresaGrupoMembro.empresa_id == empresa_id,
                )
                .with_for_update()
                .first()
            )
            if membro is None:
                membro = EmpresaGrupoMembro(
                    grupo_id=grupo.id,
                    empresa_id=empresa_id,
                    papel="membro",
                    status="ativo",
                )
                self.db.add(membro)
            else:
                membro.papel = "membro"
                membro.status = "ativo"
                membro.entrou_em = self.agora
                membro.removido_em = None
            convite.status = "aceito"
            grupo.versao_membros = int(grupo.versao_membros or 1) + 1
            evento = "empresa_grupo_convite_aceito"
            mensagem = "Convite aceito. Sua empresa agora faz parte do grupo."
        else:
            convite.status = "recusado"
            evento = "empresa_grupo_convite_recusado"
            mensagem = "Convite recusado."
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento=evento,
            grupo_id=grupo.id,
        )
        self.db.commit()
        if aceitar:
            registrar_uso_funcionalidade(self.db, "grupos-empresas-convites")
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
            self.db.query(EmpresaGrupoMembro)
            .filter(
                EmpresaGrupoMembro.grupo_id == grupo.id,
                EmpresaGrupoMembro.empresa_id == str(membro_empresa_id),
                EmpresaGrupoMembro.status == "ativo",
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
        grupo.versao_membros = int(grupo.versao_membros or 1) + 1
        self._auditar(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            evento="empresa_grupo_membro_removido",
            grupo_id=grupo.id,
            metadados={"empresa_removida_id": str(membro_empresa_id)},
        )
        self.db.commit()
        return {"mensagem": "Empresa removida do grupo."}

    def listar_resumo(self, empresa_id, usuario_id: int) -> dict:
        empresa_id = self._empresa_id(empresa_id)
        codigo = self.obter_codigo(empresa_id, usuario_id)
        participacoes = (
            self.db.query(EmpresaGrupo, EmpresaGrupoMembro)
            .join(
                EmpresaGrupoMembro,
                EmpresaGrupoMembro.grupo_id == EmpresaGrupo.id,
            )
            .filter(
                EmpresaGrupoMembro.empresa_id == empresa_id,
                EmpresaGrupoMembro.status == "ativo",
                EmpresaGrupo.status == "ativo",
            )
            .order_by(EmpresaGrupo.nome.asc())
            .all()
        )
        convites = (
            self.db.query(EmpresaGrupoConvite, EmpresaGrupo)
            .join(EmpresaGrupo, EmpresaGrupo.id == EmpresaGrupoConvite.grupo_id)
            .filter(
                EmpresaGrupoConvite.empresa_convidada_id == empresa_id,
                EmpresaGrupoConvite.status == "pendente",
                EmpresaGrupoConvite.expira_em > self.agora,
                EmpresaGrupo.status == "ativo",
            )
            .order_by(EmpresaGrupoConvite.criado_em.desc())
            .all()
        )
        return {
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
            self.db.query(EmpresaGrupoMembro, Tenant)
            .join(Tenant, Tenant.id == EmpresaGrupoMembro.empresa_id)
            .filter(
                EmpresaGrupoMembro.grupo_id == grupo_id,
                EmpresaGrupoMembro.status == "ativo",
            )
            .order_by(EmpresaGrupoMembro.papel.desc(), Tenant.name.asc())
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
        self, convite: EmpresaGrupoConvite, empresa: Tenant
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
            self.db.query(EmpresaGrupoConvite, Tenant)
            .join(Tenant, Tenant.id == EmpresaGrupoConvite.empresa_convidada_id)
            .filter(
                EmpresaGrupoConvite.grupo_id == grupo_id,
                EmpresaGrupoConvite.status == "pendente",
                EmpresaGrupoConvite.expira_em > self.agora,
            )
            .order_by(EmpresaGrupoConvite.criado_em.desc())
            .all()
        )
        return [
            self._serializar_convite_enviado(convite, empresa)
            for convite, empresa in linhas
        ]

    def _serializar_grupo(
        self, grupo: EmpresaGrupo, participacao: EmpresaGrupoMembro
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
        self, convite: EmpresaGrupoConvite, grupo: EmpresaGrupo
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
