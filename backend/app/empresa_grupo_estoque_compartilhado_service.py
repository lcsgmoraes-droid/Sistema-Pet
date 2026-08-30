"""Compartilhamento seletivo de estoque entre empresas do mesmo grupo."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import MetaData, Table, func, or_
from sqlalchemy.orm import Session, aliased

from app.empresa_grupo_models import (
    EmpresaGrupo,
    EmpresaGrupoEstoqueCompartilhado,
    EmpresaGrupoMembro,
)
from app.empresa_grupo_sql import empresa_id_igual, empresa_id_sql
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.models import Tenant
from app.produtos_models import Produto
from app.services.business_audit_service import log_business_event
from app.tenancy.context import tenant_context


@dataclass(frozen=True)
class ProdutoVendaResolvido:
    produto: Produto
    tenant_origem_id: str
    compartilhamento_id: int | None = None
    empresa_origem_nome: str | None = None
    compartilhamento_ativo: bool = True

    @property
    def compartilhado(self) -> bool:
        return self.compartilhamento_id is not None


def contexto_tenant_estoque(tenant_estoque_id, tenant_venda_id):
    """Troca o contexto somente quando o saldo pertence a outra empresa."""
    if str(tenant_estoque_id) == str(tenant_venda_id):
        return nullcontext(tenant_venda_id)
    return tenant_context(tenant_estoque_id)


def resolver_tenant_estoque_item(item, tenant_venda_id) -> tuple[str, bool]:
    """Lê o snapshot do item sem confundir atributos simulados com UUIDs reais."""
    origem = getattr(item, "estoque_origem_tenant_id", None)
    origem_valida = isinstance(origem, UUID) or (
        isinstance(origem, str) and bool(origem.strip())
    )
    if not origem_valida:
        return str(tenant_venda_id), False
    origem_id = str(origem)
    return origem_id, origem_id != str(tenant_venda_id)


class EmpresaGrupoEstoqueCompartilhadoService:
    TIPOS_COMPARTILHAVEIS = ("SIMPLES", "VARIACAO")

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _empresa_id(value) -> str:
        return str(value)

    @staticmethod
    def _produto_tenant_id(value):
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            # Compatibilidade com bancos/testes legados que ainda usam IDs inteiros.
            return value

    @staticmethod
    def _valor_empresa_para_coluna(value: str, coluna):
        """Adapta o ID ao tipo físico do banco (UUID ou VARCHAR legado)."""
        try:
            if coluna.type.python_type is UUID:
                return UUID(str(value))
        except (AttributeError, NotImplementedError):
            pass
        return str(value)

    def _inserir_novos_compartilhamentos(
        self,
        *,
        grupo_id: int,
        origem: str,
        consumidora: str,
        usuario_id: int,
        produto_ids: list[int],
    ) -> None:
        if not produto_ids:
            return
        tabela = Table(
            EmpresaGrupoEstoqueCompartilhado.__tablename__,
            MetaData(),
            autoload_with=self.db.get_bind(),
            resolve_fks=False,
        )
        origem_valor = self._valor_empresa_para_coluna(
            origem, tabela.c.empresa_origem_id
        )
        consumidora_valor = self._valor_empresa_para_coluna(
            consumidora, tabela.c.empresa_consumidora_id
        )
        self.db.execute(
            tabela.insert(),
            [
                {
                    "grupo_id": grupo_id,
                    "empresa_origem_id": origem_valor,
                    "produto_origem_id": produto_id,
                    "empresa_consumidora_id": consumidora_valor,
                    "status": "ativo",
                    "criado_por_usuario_id": usuario_id,
                }
                for produto_id in produto_ids
            ],
        )

    def _grupo_ativo(self, grupo_id: int) -> EmpresaGrupo:
        grupo = (
            self.db.query(EmpresaGrupo)
            .filter(EmpresaGrupo.id == grupo_id, EmpresaGrupo.status == "ativo")
            .first()
        )
        if grupo is None:
            raise HTTPException(
                status_code=404, detail="Grupo de empresas não encontrado."
            )
        return grupo

    def _membro_ativo(self, grupo_id: int, empresa_id: str) -> EmpresaGrupoMembro:
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
                detail="A empresa não participa ativamente deste grupo.",
            )
        return membro

    def _validar_par(
        self, grupo_id: int, empresa_origem_id: str, empresa_consumidora_id: str
    ) -> None:
        self._grupo_ativo(grupo_id)
        self._membro_ativo(grupo_id, empresa_origem_id)
        self._membro_ativo(grupo_id, empresa_consumidora_id)
        if str(empresa_origem_id) == str(empresa_consumidora_id):
            raise HTTPException(
                status_code=400,
                detail="Escolha outra empresa do grupo para usar este estoque.",
            )

    def buscar_produtos_compartilhaveis(
        self,
        grupo_id: int,
        empresa_origem_id,
        empresa_consumidora_id,
        *,
        busca: str = "",
        limite: int = 80,
    ) -> list[dict]:
        origem = self._empresa_id(empresa_origem_id)
        consumidora = self._empresa_id(empresa_consumidora_id)
        origem_uuid = self._produto_tenant_id(origem)
        self._validar_par(grupo_id, origem, consumidora)

        query = self.db.query(Produto).filter(
            Produto.tenant_id == origem_uuid,
            Produto.ativo.is_(True),
            or_(Produto.tipo.is_(None), func.lower(Produto.tipo) != "servico"),
            Produto.tipo_produto.in_(self.TIPOS_COMPARTILHAVEIS),
        )
        termo = " ".join(str(busca or "").split())
        if termo:
            padrao = f"%{termo}%"
            query = query.filter(
                or_(
                    Produto.nome.ilike(padrao),
                    Produto.codigo.ilike(padrao),
                    Produto.codigo_barras.ilike(padrao),
                )
            )
        produtos = query.order_by(Produto.nome.asc()).limit(limite).all()

        compartilhamentos = (
            self.db.query(EmpresaGrupoEstoqueCompartilhado)
            .filter(
                EmpresaGrupoEstoqueCompartilhado.grupo_id == grupo_id,
                empresa_id_igual(
                    EmpresaGrupoEstoqueCompartilhado.empresa_origem_id, origem
                ),
                empresa_id_igual(
                    EmpresaGrupoEstoqueCompartilhado.empresa_consumidora_id,
                    consumidora,
                ),
                EmpresaGrupoEstoqueCompartilhado.produto_origem_id.in_(
                    [produto.id for produto in produtos] or [-1]
                ),
                EmpresaGrupoEstoqueCompartilhado.status == "ativo",
            )
            .all()
        )
        por_produto = {
            int(item.produto_origem_id): item.id for item in compartilhamentos
        }
        return [
            {
                "id": produto.id,
                "nome": produto.nome,
                "codigo": produto.codigo,
                "codigo_barras": produto.codigo_barras,
                "estoque_atual": float(produto.estoque_atual or 0),
                "preco_venda": float(produto.preco_venda or 0),
                "compartilhado": produto.id in por_produto,
                "compartilhamento_id": por_produto.get(produto.id),
            }
            for produto in produtos
        ]

    def listar(self, grupo_id: int, empresa_atual_id) -> list[dict]:
        empresa_atual = self._empresa_id(empresa_atual_id)
        self._grupo_ativo(grupo_id)
        self._membro_ativo(grupo_id, empresa_atual)
        origem_tenant = aliased(Tenant)
        consumidora_tenant = aliased(Tenant)
        linhas = (
            self.db.query(
                EmpresaGrupoEstoqueCompartilhado,
                origem_tenant.name,
                consumidora_tenant.name,
            )
            .join(
                origem_tenant,
                empresa_id_sql(origem_tenant.id)
                == empresa_id_sql(EmpresaGrupoEstoqueCompartilhado.empresa_origem_id),
            )
            .join(
                consumidora_tenant,
                empresa_id_sql(consumidora_tenant.id)
                == empresa_id_sql(
                    EmpresaGrupoEstoqueCompartilhado.empresa_consumidora_id
                ),
            )
            .filter(
                EmpresaGrupoEstoqueCompartilhado.grupo_id == grupo_id,
                EmpresaGrupoEstoqueCompartilhado.status == "ativo",
                or_(
                    empresa_id_igual(
                        EmpresaGrupoEstoqueCompartilhado.empresa_origem_id,
                        empresa_atual,
                    ),
                    empresa_id_igual(
                        EmpresaGrupoEstoqueCompartilhado.empresa_consumidora_id,
                        empresa_atual,
                    ),
                ),
            )
            .order_by(EmpresaGrupoEstoqueCompartilhado.criado_em.desc())
            .all()
        )

        resultados: list[dict] = []
        for compartilhamento, origem_nome, consumidora_nome in linhas:
            with tenant_context(compartilhamento.empresa_origem_id) as tenant_origem:
                produto = (
                    self.db.query(Produto)
                    .filter(
                        Produto.id == compartilhamento.produto_origem_id,
                        Produto.tenant_id == tenant_origem,
                    )
                    .first()
                )
            if produto is None:
                continue
            resultados.append(
                {
                    "id": compartilhamento.id,
                    "grupo_id": compartilhamento.grupo_id,
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "produto_codigo": produto.codigo,
                    "estoque_atual": float(produto.estoque_atual or 0),
                    "empresa_origem_id": str(compartilhamento.empresa_origem_id),
                    "empresa_origem_nome": origem_nome,
                    "empresa_consumidora_id": str(
                        compartilhamento.empresa_consumidora_id
                    ),
                    "empresa_consumidora_nome": consumidora_nome,
                    "pode_remover": str(compartilhamento.empresa_origem_id)
                    == empresa_atual,
                }
            )
        return resultados

    def compartilhar(
        self,
        grupo_id: int,
        empresa_origem_id,
        usuario_id: int,
        empresa_consumidora_id,
        produto_ids: Iterable[int],
    ) -> dict:
        origem = self._empresa_id(empresa_origem_id)
        consumidora = self._empresa_id(empresa_consumidora_id)
        origem_uuid = self._produto_tenant_id(origem)
        self._validar_par(grupo_id, origem, consumidora)
        ids = sorted(
            {int(produto_id) for produto_id in produto_ids if int(produto_id) > 0}
        )
        if not ids:
            raise HTTPException(
                status_code=400, detail="Selecione ao menos um produto."
            )

        produtos = (
            self.db.query(Produto)
            .filter(
                Produto.id.in_(ids),
                Produto.tenant_id == origem_uuid,
                Produto.ativo.is_(True),
                or_(Produto.tipo.is_(None), func.lower(Produto.tipo) != "servico"),
                Produto.tipo_produto.in_(self.TIPOS_COMPARTILHAVEIS),
            )
            .all()
        )
        encontrados = {produto.id for produto in produtos}
        ausentes = sorted(set(ids) - encontrados)
        if ausentes:
            raise HTTPException(
                status_code=404,
                detail=f"Produtos inválidos ou não encontrados: {', '.join(map(str, ausentes))}.",
            )

        agora = datetime.now(timezone.utc)
        ativados = 0
        novos: list[int] = []
        for produto_id in ids:
            item = (
                self.db.query(EmpresaGrupoEstoqueCompartilhado)
                .filter(
                    EmpresaGrupoEstoqueCompartilhado.grupo_id == grupo_id,
                    empresa_id_igual(
                        EmpresaGrupoEstoqueCompartilhado.empresa_origem_id, origem
                    ),
                    EmpresaGrupoEstoqueCompartilhado.produto_origem_id == produto_id,
                    empresa_id_igual(
                        EmpresaGrupoEstoqueCompartilhado.empresa_consumidora_id,
                        consumidora,
                    ),
                )
                .first()
            )
            if item is None:
                novos.append(produto_id)
                ativados += 1
            elif item.status != "ativo":
                item.status = "ativo"
                item.removido_em = None
                item.atualizado_em = agora
                item.criado_por_usuario_id = usuario_id
                ativados += 1

        self._inserir_novos_compartilhamentos(
            grupo_id=grupo_id,
            origem=origem,
            consumidora=consumidora,
            usuario_id=usuario_id,
            produto_ids=novos,
        )

        log_business_event(
            db=self.db,
            tenant_id=origem,
            user_id=usuario_id,
            event="empresa_grupo_estoque_compartilhado_ativado",
            entity_type="empresa_grupo",
            entity_id=grupo_id,
            metadata={"empresa_consumidora_id": consumidora, "produto_ids": ids},
            commit=False,
        )
        self.db.commit()
        registrar_uso_funcionalidade(self.db, "grupos-empresas-estoque-compartilhado")
        return {"ativados": ativados, "selecionados": len(ids)}

    def remover(
        self,
        grupo_id: int,
        compartilhamento_id: int,
        empresa_origem_id,
        usuario_id: int,
    ) -> dict:
        origem = self._empresa_id(empresa_origem_id)
        self._grupo_ativo(grupo_id)
        self._membro_ativo(grupo_id, origem)
        item = (
            self.db.query(EmpresaGrupoEstoqueCompartilhado)
            .filter(
                EmpresaGrupoEstoqueCompartilhado.id == compartilhamento_id,
                EmpresaGrupoEstoqueCompartilhado.grupo_id == grupo_id,
                empresa_id_igual(
                    EmpresaGrupoEstoqueCompartilhado.empresa_origem_id, origem
                ),
                EmpresaGrupoEstoqueCompartilhado.status == "ativo",
            )
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=404, detail="Compartilhamento não encontrado."
            )
        item.status = "removido"
        item.removido_em = datetime.now(timezone.utc)
        log_business_event(
            db=self.db,
            tenant_id=origem,
            user_id=usuario_id,
            event="empresa_grupo_estoque_compartilhado_removido",
            entity_type="empresa_grupo_estoque_compartilhado",
            entity_id=item.id,
            metadata={"produto_id": item.produto_origem_id},
            commit=False,
        )
        self.db.commit()
        return {"mensagem": "Compartilhamento removido."}

    @classmethod
    def _consulta_compartilhamento_ativo(
        cls, db: Session, empresa_consumidora_id, produto_id: int | None = None
    ):
        membro_origem = aliased(EmpresaGrupoMembro)
        membro_consumidora = aliased(EmpresaGrupoMembro)
        query = (
            db.query(EmpresaGrupoEstoqueCompartilhado, Tenant.name)
            .join(
                EmpresaGrupo,
                EmpresaGrupo.id == EmpresaGrupoEstoqueCompartilhado.grupo_id,
            )
            .join(
                membro_origem,
                (membro_origem.grupo_id == EmpresaGrupoEstoqueCompartilhado.grupo_id)
                & (
                    empresa_id_sql(membro_origem.empresa_id)
                    == empresa_id_sql(
                        EmpresaGrupoEstoqueCompartilhado.empresa_origem_id
                    )
                ),
            )
            .join(
                membro_consumidora,
                (
                    membro_consumidora.grupo_id
                    == EmpresaGrupoEstoqueCompartilhado.grupo_id
                )
                & (
                    empresa_id_sql(membro_consumidora.empresa_id)
                    == empresa_id_sql(
                        EmpresaGrupoEstoqueCompartilhado.empresa_consumidora_id
                    )
                ),
            )
            .join(
                Tenant,
                empresa_id_sql(Tenant.id)
                == empresa_id_sql(EmpresaGrupoEstoqueCompartilhado.empresa_origem_id),
            )
            .filter(
                empresa_id_igual(
                    EmpresaGrupoEstoqueCompartilhado.empresa_consumidora_id,
                    empresa_consumidora_id,
                ),
                EmpresaGrupoEstoqueCompartilhado.status == "ativo",
                EmpresaGrupo.status == "ativo",
                membro_origem.status == "ativo",
                membro_consumidora.status == "ativo",
            )
        )
        if produto_id is not None:
            query = query.filter(
                EmpresaGrupoEstoqueCompartilhado.produto_origem_id == produto_id
            )
        return query

    @classmethod
    def resolver_produto_venda(
        cls, db: Session, empresa_consumidora_id, produto_id: int
    ) -> ProdutoVendaResolvido:
        consumidor = str(empresa_consumidora_id)
        produto_local = (
            db.query(Produto)
            .filter(
                Produto.id == produto_id,
                Produto.tenant_id == cls._produto_tenant_id(consumidor),
            )
            .first()
        )
        if produto_local is not None:
            return ProdutoVendaResolvido(
                produto=produto_local,
                tenant_origem_id=consumidor,
                empresa_origem_nome=None,
            )

        linha = cls._consulta_compartilhamento_ativo(db, consumidor, produto_id).first()
        if linha is None:
            raise HTTPException(
                status_code=404, detail=f"Produto ID {produto_id} não encontrado"
            )
        compartilhamento, origem_nome = linha
        with tenant_context(compartilhamento.empresa_origem_id) as tenant_origem:
            produto = (
                db.query(Produto)
                .filter(
                    Produto.id == produto_id,
                    Produto.tenant_id == tenant_origem,
                    Produto.ativo.is_(True),
                    or_(Produto.tipo.is_(None), func.lower(Produto.tipo) != "servico"),
                    Produto.tipo_produto.in_(cls.TIPOS_COMPARTILHAVEIS),
                )
                .first()
            )
        if produto is None:
            raise HTTPException(
                status_code=404, detail=f"Produto ID {produto_id} não encontrado"
            )
        return ProdutoVendaResolvido(
            produto=produto,
            tenant_origem_id=str(compartilhamento.empresa_origem_id),
            compartilhamento_id=compartilhamento.id,
            empresa_origem_nome=origem_nome,
        )

    @classmethod
    def carregar_produto_historico(
        cls,
        db: Session,
        *,
        produto_id: int,
        tenant_origem_id,
        compartilhamento_id: int | None = None,
        empresa_origem_nome: str | None = None,
    ) -> ProdutoVendaResolvido:
        origem = str(tenant_origem_id)
        with tenant_context(origem) as tenant_origem:
            produto = (
                db.query(Produto)
                .filter(Produto.id == produto_id, Produto.tenant_id == tenant_origem)
                .first()
            )
        if produto is None:
            raise HTTPException(
                status_code=404, detail=f"Produto ID {produto_id} não encontrado"
            )
        return ProdutoVendaResolvido(
            produto=produto,
            tenant_origem_id=origem,
            compartilhamento_id=compartilhamento_id,
            empresa_origem_nome=empresa_origem_nome,
            compartilhamento_ativo=False,
        )

    @classmethod
    def mapa_ativos_para_consumidora(
        cls, db: Session, empresa_consumidora_id, produto_ids: Iterable[int]
    ) -> dict[int, dict]:
        ids = sorted({int(produto_id) for produto_id in produto_ids})
        if not ids:
            return {}
        query = cls._consulta_compartilhamento_ativo(db, empresa_consumidora_id).filter(
            EmpresaGrupoEstoqueCompartilhado.produto_origem_id.in_(ids)
        )
        resultados: dict[int, dict] = {}
        for compartilhamento, origem_nome in query.all():
            resultados.setdefault(
                int(compartilhamento.produto_origem_id),
                {
                    "estoque_compartilhado": True,
                    "estoque_compartilhado_id": compartilhamento.id,
                    "estoque_origem_empresa_id": str(
                        compartilhamento.empresa_origem_id
                    ),
                    "estoque_origem_nome": origem_nome,
                },
            )
        return resultados
