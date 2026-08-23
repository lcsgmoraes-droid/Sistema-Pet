"""Visao consolidada, somente leitura, para empresas de um mesmo grupo."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.empresa_grupo_models import EmpresaGrupo, EmpresaGrupoMembro
from app.financeiro_models import ContaPagar, ContaReceber
from app.models import Tenant
from app.produtos_models import Produto
from app.tenancy.context import tenant_context
from app.utils.timezone import now_brasilia
from app.vendas_models import Venda

STATUS_CONTAS_ABERTAS = ("pendente", "parcial", "vencido", "vencida")


def _numero(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _moeda(valor) -> float:
    return round(_numero(valor), 2)


def _quantidade(valor) -> float:
    return round(_numero(valor), 3)


class EmpresaGrupoAnaliseService:
    """Agrega indicadores sem expor cadastros ou lancamentos individuais."""

    def __init__(self, db: Session, *, agora: datetime | None = None):
        self.db = db
        self.agora = agora or now_brasilia()

    def _grupo_e_membros(self, grupo_id: int, empresa_atual_id) -> tuple:
        empresa_atual_id = str(empresa_atual_id)
        grupo = (
            self.db.query(EmpresaGrupo)
            .filter(
                EmpresaGrupo.id == grupo_id,
                EmpresaGrupo.status == "ativo",
            )
            .first()
        )
        if grupo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo de empresas não encontrado.",
            )

        participacao = (
            self.db.query(EmpresaGrupoMembro)
            .filter(
                EmpresaGrupoMembro.grupo_id == grupo.id,
                EmpresaGrupoMembro.empresa_id == empresa_atual_id,
                EmpresaGrupoMembro.status == "ativo",
            )
            .first()
        )
        if participacao is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sua empresa não participa deste grupo.",
            )

        membros = (
            self.db.query(EmpresaGrupoMembro, Tenant)
            .join(Tenant, Tenant.id == EmpresaGrupoMembro.empresa_id)
            .filter(
                EmpresaGrupoMembro.grupo_id == grupo.id,
                EmpresaGrupoMembro.status == "ativo",
                Tenant.status == "active",
            )
            .order_by(EmpresaGrupoMembro.papel.desc(), Tenant.name.asc())
            .all()
        )
        return grupo, membros

    def _vendas(self, tenant_id: UUID, inicio: datetime, fim: datetime) -> dict:
        quantidade, finalizadas, valor_total = (
            self.db.query(
                func.count(Venda.id),
                func.coalesce(
                    func.sum(case((Venda.status == "finalizada", 1), else_=0)),
                    0,
                ),
                func.coalesce(func.sum(Venda.total), 0),
            )
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.data_venda >= inicio,
                Venda.data_venda < fim,
                or_(Venda.status.is_(None), Venda.status != "cancelada"),
            )
            .one()
        )
        quantidade = int(quantidade or 0)
        valor_total = _moeda(valor_total)
        return {
            "quantidade": quantidade,
            "finalizadas": int(finalizadas or 0),
            "valor_total": valor_total,
            "ticket_medio": round(valor_total / quantidade, 2) if quantidade else 0,
        }

    def _estoque(self, tenant_id: UUID) -> dict:
        produtos_ativos, quantidade, valor_custo = (
            self.db.query(
                func.count(Produto.id),
                func.coalesce(
                    func.sum(
                        case(
                            (Produto.estoque_atual > 0, Produto.estoque_atual),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Produto.estoque_atual > 0,
                                Produto.estoque_atual
                                * func.coalesce(Produto.preco_custo, 0),
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .filter(
                Produto.tenant_id == tenant_id,
                or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
                or_(
                    Produto.tipo_produto.is_(None),
                    Produto.tipo_produto == "SIMPLES",
                    (
                        Produto.tipo_produto.in_(["KIT", "VARIACAO"])
                        & or_(Produto.tipo_kit.is_(None), Produto.tipo_kit != "VIRTUAL")
                    ),
                ),
            )
            .one()
        )
        return {
            "produtos_ativos": int(produtos_ativos or 0),
            "quantidade": _quantidade(quantidade),
            "valor_custo": _moeda(valor_custo),
        }

    def _financeiro(self, tenant_id: UUID, hoje) -> dict:
        receber_aberto, receber_vencido = (
            self.db.query(
                func.coalesce(
                    func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ContaReceber.data_vencimento < hoje,
                                ContaReceber.valor_final - ContaReceber.valor_recebido,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .filter(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status.in_(STATUS_CONTAS_ABERTAS),
            )
            .one()
        )
        pagar_aberto, pagar_vencido = (
            self.db.query(
                func.coalesce(
                    func.sum(ContaPagar.valor_final - ContaPagar.valor_pago),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                ContaPagar.data_vencimento < hoje,
                                ContaPagar.valor_final - ContaPagar.valor_pago,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status.in_(STATUS_CONTAS_ABERTAS),
            )
            .one()
        )
        return {
            "receber_aberto": _moeda(receber_aberto),
            "receber_vencido": _moeda(receber_vencido),
            "pagar_aberto": _moeda(pagar_aberto),
            "pagar_vencido": _moeda(pagar_vencido),
        }

    @staticmethod
    def _totais(empresas: list[dict]) -> dict:
        vendas = {
            "quantidade": sum(item["vendas"]["quantidade"] for item in empresas),
            "finalizadas": sum(item["vendas"]["finalizadas"] for item in empresas),
            "valor_total": _moeda(
                sum(item["vendas"]["valor_total"] for item in empresas)
            ),
            "ticket_medio": 0,
        }
        if vendas["quantidade"]:
            vendas["ticket_medio"] = round(
                vendas["valor_total"] / vendas["quantidade"], 2
            )
        return {
            "vendas": vendas,
            "estoque": {
                "produtos_ativos": sum(
                    item["estoque"]["produtos_ativos"] for item in empresas
                ),
                "quantidade": _quantidade(
                    sum(item["estoque"]["quantidade"] for item in empresas)
                ),
                "valor_custo": _moeda(
                    sum(item["estoque"]["valor_custo"] for item in empresas)
                ),
            },
            "financeiro": {
                chave: _moeda(sum(item["financeiro"][chave] for item in empresas))
                for chave in (
                    "receber_aberto",
                    "receber_vencido",
                    "pagar_aberto",
                    "pagar_vencido",
                )
            },
        }

    def obter(self, grupo_id: int, empresa_atual_id, periodo_dias: int = 30) -> dict:
        grupo, membros = self._grupo_e_membros(grupo_id, empresa_atual_id)
        inicio_hoje = self.agora.replace(hour=0, minute=0, second=0, microsecond=0)
        inicio = inicio_hoje - timedelta(days=periodo_dias - 1)
        fim = inicio_hoje + timedelta(days=1)
        hoje = inicio_hoje.date()

        empresas = []
        for membro, empresa in membros:
            empresa_id = str(membro.empresa_id)
            empresa_uuid = UUID(empresa_id)
            with tenant_context(empresa_uuid):
                empresas.append(
                    {
                        "empresa_id": empresa_id,
                        "empresa_nome": empresa.name,
                        "papel": membro.papel,
                        "vendas": self._vendas(empresa_uuid, inicio, fim),
                        "estoque": self._estoque(empresa_uuid),
                        "financeiro": self._financeiro(empresa_uuid, hoje),
                    }
                )

        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "periodo": {
                "dias": periodo_dias,
                "data_inicio": inicio.date().isoformat(),
                "data_fim": hoje.isoformat(),
            },
            "gerado_em": self.agora.isoformat(),
            "totais": self._totais(empresas),
            "empresas": empresas,
        }
