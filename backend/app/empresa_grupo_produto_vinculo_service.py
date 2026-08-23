"""Pesquisa e manutencao de equivalencias de produtos entre empresas do grupo."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_

from app.empresa_grupo_analise_detalhes_service import (
    EmpresaGrupoAnaliseDetalhesService,
    _iso_data_hora,
    _texto,
)
from app.empresa_grupo_analise_service import _moeda, _quantidade
from app.empresa_grupo_models import EmpresaGrupoProdutoVinculo
from app.produtos_models import Produto
from app.services.business_audit_service import log_business_event
from app.tenancy.context import tenant_context


class EmpresaGrupoProdutoVinculoService(EmpresaGrupoAnaliseDetalhesService):
    def buscar_produtos(
        self,
        grupo_id: int,
        empresa_atual_id,
        *,
        busca: str = "",
        empresa_id: str | None = None,
        limite: int = 60,
    ) -> dict:
        grupo, membros, membros_por_id = self._contexto(grupo_id, empresa_atual_id)
        self._validar_empresa_filtro(empresa_id, membros_por_id)
        busca = _texto(busca)
        itens = []
        for membro, empresa in membros:
            membro_id = str(membro.empresa_id)
            if empresa_id and membro_id != str(empresa_id):
                continue
            empresa_uuid = UUID(membro_id)
            with tenant_context(empresa_uuid):
                query = self.db.query(Produto).filter(
                    Produto.tenant_id == empresa_uuid,
                    or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
                )
                if busca:
                    termo = f"%{busca}%"
                    query = query.filter(
                        or_(
                            Produto.nome.ilike(termo),
                            Produto.codigo.ilike(termo),
                            Produto.codigo_barras.ilike(termo),
                            Produto.gtin_ean.ilike(termo),
                        )
                    )
                produtos = query.order_by(Produto.nome.asc()).limit(limite).all()
            itens.extend(
                {
                    "empresa_id": membro_id,
                    "empresa_nome": empresa.name,
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "sku": produto.codigo,
                    "ean": produto.codigo_barras or produto.gtin_ean,
                    "estoque": _quantidade(produto.estoque_atual),
                    "preco_venda": _moeda(produto.preco_venda),
                }
                for produto in produtos
            )
        itens.sort(key=lambda item: (item["empresa_nome"], item["produto_nome"]))
        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "itens": itens[:limite],
        }

    def _produto(
        self, empresa_id: str, produto_id: int, *, exigir_ativo: bool = True
    ) -> Produto:
        empresa_uuid = UUID(str(empresa_id))
        with tenant_context(empresa_uuid):
            query = self.db.query(Produto).filter(
                Produto.tenant_id == empresa_uuid,
                Produto.id == produto_id,
            )
            if exigir_ativo:
                query = query.filter(
                    or_(Produto.ativo.is_(True), Produto.ativo.is_(None))
                )
            produto = query.first()
        if produto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado ou inativo na empresa selecionada.",
            )
        return produto

    @staticmethod
    def _ordenar_par(produto_a, produto_b):
        chave_a = (str(produto_a.empresa_id), int(produto_a.produto_id))
        chave_b = (str(produto_b.empresa_id), int(produto_b.produto_id))
        return (produto_a, produto_b) if chave_a < chave_b else (produto_b, produto_a)

    def _exigir_responsavel(self, grupo_id: int, empresa_atual_id):
        grupo, _membros, membros_por_id = self._contexto(grupo_id, empresa_atual_id)
        atual = membros_por_id[str(empresa_atual_id)][0]
        if atual.papel != "responsavel":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente a empresa responsável pode alterar vínculos de produtos.",
            )
        return grupo, membros_por_id

    def _serializar_vinculo(self, vinculo, membros_por_id: dict) -> dict:
        produto_a = self._produto(
            str(vinculo.empresa_a_id), vinculo.produto_a_id, exigir_ativo=False
        )
        produto_b = self._produto(
            str(vinculo.empresa_b_id), vinculo.produto_b_id, exigir_ativo=False
        )
        empresa_a = membros_por_id[str(vinculo.empresa_a_id)][1]
        empresa_b = membros_por_id[str(vinculo.empresa_b_id)][1]
        return {
            "id": vinculo.id,
            "status": vinculo.status,
            "criado_em": _iso_data_hora(vinculo.criado_em),
            "produto_a": {
                "empresa_id": str(vinculo.empresa_a_id),
                "empresa_nome": empresa_a.name,
                "produto_id": produto_a.id,
                "produto_nome": produto_a.nome,
                "sku": produto_a.codigo,
                "ean": produto_a.codigo_barras or produto_a.gtin_ean,
            },
            "produto_b": {
                "empresa_id": str(vinculo.empresa_b_id),
                "empresa_nome": empresa_b.name,
                "produto_id": produto_b.id,
                "produto_nome": produto_b.nome,
                "sku": produto_b.codigo,
                "ean": produto_b.codigo_barras or produto_b.gtin_ean,
            },
        }

    def listar_vinculos(self, grupo_id: int, empresa_atual_id) -> dict:
        grupo, _membros, membros_por_id = self._contexto(grupo_id, empresa_atual_id)
        vinculos = (
            self.db.query(EmpresaGrupoProdutoVinculo)
            .filter(
                EmpresaGrupoProdutoVinculo.grupo_id == grupo.id,
                EmpresaGrupoProdutoVinculo.status == "ativo",
            )
            .order_by(EmpresaGrupoProdutoVinculo.criado_em.desc())
            .all()
        )
        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "pode_gerenciar": membros_por_id[str(empresa_atual_id)][0].papel
            == "responsavel",
            "itens": [
                self._serializar_vinculo(vinculo, membros_por_id)
                for vinculo in vinculos
            ],
        }

    def vincular_produtos(
        self,
        grupo_id: int,
        empresa_atual_id,
        usuario_id: int,
        produto_a,
        produto_b,
    ) -> dict:
        grupo, membros_por_id = self._exigir_responsavel(grupo_id, empresa_atual_id)
        if (
            str(produto_a.empresa_id) not in membros_por_id
            or str(produto_b.empresa_id) not in membros_por_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Os dois produtos precisam pertencer a empresas ativas do grupo.",
            )
        produto_a, produto_b = self._ordenar_par(produto_a, produto_b)
        self._produto(produto_a.empresa_id, produto_a.produto_id)
        self._produto(produto_b.empresa_id, produto_b.produto_id)

        conflitos = (
            self.db.query(EmpresaGrupoProdutoVinculo)
            .filter(
                EmpresaGrupoProdutoVinculo.grupo_id == grupo.id,
                EmpresaGrupoProdutoVinculo.status == "ativo",
            )
            .all()
        )
        chave_a = (str(produto_a.empresa_id), produto_a.produto_id)
        chave_b = (str(produto_b.empresa_id), produto_b.produto_id)
        for existente in conflitos:
            existente_a = (str(existente.empresa_a_id), existente.produto_a_id)
            existente_b = (str(existente.empresa_b_id), existente.produto_b_id)
            if {existente_a, existente_b} == {chave_a, chave_b}:
                return self._serializar_vinculo(existente, membros_por_id)
            if (
                chave_a in (existente_a, existente_b)
                and chave_b[0] in (existente_a[0], existente_b[0])
            ) or (
                chave_b in (existente_a, existente_b)
                and chave_a[0] in (existente_a[0], existente_b[0])
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Um dos produtos já está vinculado a outro produto da mesma empresa. "
                        "Remova o vínculo anterior antes de continuar."
                    ),
                )

        vinculo = (
            self.db.query(EmpresaGrupoProdutoVinculo)
            .filter(
                EmpresaGrupoProdutoVinculo.grupo_id == grupo.id,
                EmpresaGrupoProdutoVinculo.empresa_a_id == produto_a.empresa_id,
                EmpresaGrupoProdutoVinculo.produto_a_id == produto_a.produto_id,
                EmpresaGrupoProdutoVinculo.empresa_b_id == produto_b.empresa_id,
                EmpresaGrupoProdutoVinculo.produto_b_id == produto_b.produto_id,
            )
            .first()
        )
        if vinculo is None:
            vinculo = EmpresaGrupoProdutoVinculo(
                grupo_id=grupo.id,
                empresa_a_id=produto_a.empresa_id,
                produto_a_id=produto_a.produto_id,
                empresa_b_id=produto_b.empresa_id,
                produto_b_id=produto_b.produto_id,
                criado_por_empresa_id=str(empresa_atual_id),
                criado_por_usuario_id=usuario_id,
            )
            self.db.add(vinculo)
        else:
            vinculo.status = "ativo"
            vinculo.removido_em = None
            vinculo.criado_por_empresa_id = str(empresa_atual_id)
            vinculo.criado_por_usuario_id = usuario_id
        self.db.flush()
        log_business_event(
            db=self.db,
            tenant_id=str(empresa_atual_id),
            user_id=usuario_id,
            event="empresa_grupo_produtos_vinculados",
            entity_type="empresa_grupo_produto_vinculo",
            entity_id=vinculo.id,
            metadata={"grupo_id": grupo.id, "produto_a": chave_a, "produto_b": chave_b},
            commit=False,
        )
        self.db.commit()
        return self._serializar_vinculo(vinculo, membros_por_id)

    def remover_vinculo(
        self,
        grupo_id: int,
        vinculo_id: int,
        empresa_atual_id,
        usuario_id: int,
    ) -> dict:
        grupo, _membros_por_id = self._exigir_responsavel(grupo_id, empresa_atual_id)
        vinculo = (
            self.db.query(EmpresaGrupoProdutoVinculo)
            .filter(
                EmpresaGrupoProdutoVinculo.id == vinculo_id,
                EmpresaGrupoProdutoVinculo.grupo_id == grupo.id,
                EmpresaGrupoProdutoVinculo.status == "ativo",
            )
            .with_for_update()
            .first()
        )
        if vinculo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vínculo de produtos não encontrado.",
            )
        vinculo.status = "removido"
        vinculo.removido_em = self.agora
        log_business_event(
            db=self.db,
            tenant_id=str(empresa_atual_id),
            user_id=usuario_id,
            event="empresa_grupo_produtos_desvinculados",
            entity_type="empresa_grupo_produto_vinculo",
            entity_id=vinculo.id,
            metadata={"grupo_id": grupo.id},
            commit=False,
        )
        self.db.commit()
        return {"mensagem": "Vínculo removido. As vendas deixam de ser agrupadas."}
