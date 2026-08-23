"""Consultas detalhadas e vinculos da visao consolidada de grupos."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.empresa_grupo_analise_service import (
    STATUS_CONTAS_ABERTAS,
    EmpresaGrupoAnaliseService,
    _moeda,
    _numero,
    _quantidade,
)
from app.empresa_grupo_models import EmpresaGrupoProdutoVinculo
from app.financeiro_models import ContaPagar
from app.models_cadastros import Cliente
from app.produtos_models import PedidoCompra, PedidoCompraItem, Produto
from app.tenancy.context import tenant_context
from app.utils.timezone import now_brasilia
from app.vendas_models import Venda, VendaItem

STATUS_CONTAS_PAGAS = ("pago", "paga")
STATUS_CONTAS_CANCELADAS = ("cancelado", "cancelada")


def _texto(valor) -> str:
    return str(valor or "").strip()


def _normalizar_codigo(valor) -> str:
    return "".join(
        caractere for caractere in _texto(valor).upper() if caractere.isalnum()
    )


def _iso_data_hora(valor) -> str | None:
    return valor.isoformat() if valor else None


class _ConjuntosProdutos:
    def __init__(self, chaves):
        self.pais = {chave: chave for chave in chaves}

    def encontrar(self, chave):
        pai = self.pais.get(chave, chave)
        if pai != chave:
            pai = self.encontrar(pai)
            self.pais[chave] = pai
        return pai

    def unir(self, chave_a, chave_b):
        if chave_a not in self.pais or chave_b not in self.pais:
            return
        raiz_a = self.encontrar(chave_a)
        raiz_b = self.encontrar(chave_b)
        if raiz_a != raiz_b:
            self.pais[raiz_b] = raiz_a


class EmpresaGrupoAnaliseDetalhesService:
    """Expõe detalhes somente depois de validar o vínculo ativo do grupo."""

    def __init__(self, db: Session, *, agora: datetime | None = None):
        self.db = db
        self.agora = agora or now_brasilia()
        self.resumo = EmpresaGrupoAnaliseService(db, agora=self.agora)

    def _contexto(self, grupo_id: int, empresa_atual_id) -> tuple[object, list, dict]:
        grupo, membros = self.resumo._grupo_e_membros(grupo_id, empresa_atual_id)
        por_id = {
            str(membro.empresa_id): (membro, empresa) for membro, empresa in membros
        }
        return grupo, membros, por_id

    def _periodo(self, periodo_dias: int) -> tuple[datetime, datetime]:
        inicio_hoje = self.agora.replace(hour=0, minute=0, second=0, microsecond=0)
        return inicio_hoje - timedelta(days=periodo_dias - 1), inicio_hoje + timedelta(
            days=1
        )

    @staticmethod
    def _validar_empresa_filtro(empresa_id: str | None, membros_por_id: dict) -> None:
        if empresa_id and str(empresa_id) not in membros_por_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A empresa selecionada não participa deste grupo.",
            )

    def listar_pedidos(
        self,
        grupo_id: int,
        empresa_atual_id,
        *,
        periodo_dias: int = 30,
        busca: str = "",
        empresa_id: str | None = None,
        limite: int = 200,
    ) -> dict:
        grupo, membros, membros_por_id = self._contexto(grupo_id, empresa_atual_id)
        self._validar_empresa_filtro(empresa_id, membros_por_id)
        inicio, fim = self._periodo(periodo_dias)
        busca = _texto(busca)
        itens = []

        for membro, empresa in membros:
            membro_id = str(membro.empresa_id)
            if empresa_id and membro_id != str(empresa_id):
                continue
            empresa_uuid = UUID(membro_id)
            with tenant_context(empresa_uuid):
                query = (
                    self.db.query(
                        Venda,
                        Cliente.nome.label("cliente_nome"),
                        func.count(VendaItem.id).label("quantidade_itens"),
                        func.coalesce(func.sum(VendaItem.quantidade), 0).label(
                            "unidades"
                        ),
                    )
                    .outerjoin(
                        Cliente,
                        (Cliente.id == Venda.cliente_id)
                        & (Cliente.tenant_id == Venda.tenant_id),
                    )
                    .outerjoin(
                        VendaItem,
                        (VendaItem.venda_id == Venda.id)
                        & (VendaItem.tenant_id == Venda.tenant_id),
                    )
                    .filter(
                        Venda.tenant_id == empresa_uuid,
                        Venda.data_venda >= inicio,
                        Venda.data_venda < fim,
                        or_(Venda.status.is_(None), Venda.status != "cancelada"),
                    )
                )
                if busca:
                    termo = f"%{busca}%"
                    query = query.filter(
                        or_(
                            Venda.numero_venda.ilike(termo),
                            Venda.canal.ilike(termo),
                            Cliente.nome.ilike(termo),
                        )
                    )
                linhas = (
                    query.group_by(Venda.id, Cliente.nome)
                    .order_by(Venda.data_venda.desc(), Venda.id.desc())
                    .limit(limite)
                    .all()
                )
            for venda, cliente_nome, quantidade_itens, unidades in linhas:
                itens.append(
                    {
                        "empresa_id": membro_id,
                        "empresa_nome": empresa.name,
                        "venda_id": venda.id,
                        "numero_venda": venda.numero_venda,
                        "data_venda": _iso_data_hora(venda.data_venda),
                        "cliente_nome": cliente_nome or "Consumidor não identificado",
                        "canal": venda.canal or "loja_fisica",
                        "status": venda.status or "aberta",
                        "quantidade_itens": int(quantidade_itens or 0),
                        "unidades": _quantidade(unidades),
                        "valor_total": _moeda(venda.total),
                    }
                )

        itens.sort(
            key=lambda item: (item["data_venda"] or "", item["venda_id"]), reverse=True
        )
        total_valor = _moeda(sum(item["valor_total"] for item in itens))
        total_pedidos = len(itens)
        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "periodo": {
                "dias": periodo_dias,
                "data_inicio": inicio.date().isoformat(),
                "data_fim": (fim - timedelta(days=1)).date().isoformat(),
            },
            "resumo": {
                "pedidos": total_pedidos,
                "unidades": _quantidade(sum(item["unidades"] for item in itens)),
                "valor_total": total_valor,
                "ticket_medio": round(total_valor / total_pedidos, 2)
                if total_pedidos
                else 0,
            },
            "itens": itens[:limite],
            "limite": limite,
        }

    def listar_contas_pagar(
        self,
        grupo_id: int,
        empresa_atual_id,
        *,
        periodo_dias: int = 30,
        situacao: str = "abertas",
        busca: str = "",
        empresa_id: str | None = None,
        limite: int = 200,
    ) -> dict:
        grupo, membros, membros_por_id = self._contexto(grupo_id, empresa_atual_id)
        self._validar_empresa_filtro(empresa_id, membros_por_id)
        hoje = self.agora.date()
        inicio, fim = self._periodo(periodo_dias)
        busca = _texto(busca)
        itens = []

        for membro, empresa in membros:
            membro_id = str(membro.empresa_id)
            if empresa_id and membro_id != str(empresa_id):
                continue
            empresa_uuid = UUID(membro_id)
            with tenant_context(empresa_uuid):
                query = (
                    self.db.query(ContaPagar, Cliente.nome.label("fornecedor_nome"))
                    .outerjoin(
                        Cliente,
                        (Cliente.id == ContaPagar.fornecedor_id)
                        & (Cliente.tenant_id == ContaPagar.tenant_id),
                    )
                    .filter(ContaPagar.tenant_id == empresa_uuid)
                )
                if situacao == "abertas":
                    query = query.filter(ContaPagar.status.in_(STATUS_CONTAS_ABERTAS))
                elif situacao == "vencidas":
                    query = query.filter(
                        ContaPagar.status.in_(STATUS_CONTAS_ABERTAS),
                        ContaPagar.data_vencimento < hoje,
                    )
                elif situacao == "pagas":
                    query = query.filter(
                        ContaPagar.status.in_(STATUS_CONTAS_PAGAS),
                        ContaPagar.data_vencimento >= inicio.date(),
                        ContaPagar.data_vencimento < fim.date(),
                    )
                else:
                    query = query.filter(
                        ~ContaPagar.status.in_(STATUS_CONTAS_CANCELADAS),
                        ContaPagar.data_vencimento >= inicio.date(),
                        ContaPagar.data_vencimento < fim.date(),
                    )
                if busca:
                    termo = f"%{busca}%"
                    query = query.filter(
                        or_(
                            ContaPagar.descricao.ilike(termo),
                            ContaPagar.documento.ilike(termo),
                            ContaPagar.nfe_numero.ilike(termo),
                            Cliente.nome.ilike(termo),
                        )
                    )
                linhas = (
                    query.order_by(
                        ContaPagar.data_vencimento.asc(), ContaPagar.id.asc()
                    )
                    .limit(1000)
                    .all()
                )
            for conta, fornecedor_nome in linhas:
                saldo = max(_numero(conta.valor_final) - _numero(conta.valor_pago), 0)
                vencida = bool(
                    conta.status in STATUS_CONTAS_ABERTAS
                    and conta.data_vencimento
                    and conta.data_vencimento < hoje
                )
                itens.append(
                    {
                        "empresa_id": membro_id,
                        "empresa_nome": empresa.name,
                        "conta_id": conta.id,
                        "descricao": conta.descricao,
                        "fornecedor_nome": fornecedor_nome
                        or conta.beneficiario
                        or "Sem fornecedor",
                        "documento": conta.documento or conta.nfe_numero,
                        "data_emissao": conta.data_emissao.isoformat()
                        if conta.data_emissao
                        else None,
                        "data_vencimento": conta.data_vencimento.isoformat()
                        if conta.data_vencimento
                        else None,
                        "status": conta.status,
                        "vencida": vencida,
                        "valor_final": _moeda(conta.valor_final),
                        "valor_pago": _moeda(conta.valor_pago),
                        "saldo_aberto": _moeda(saldo),
                    }
                )

        itens.sort(
            key=lambda item: (
                item["data_vencimento"] or "9999-12-31",
                item["empresa_nome"],
            )
        )
        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "situacao": situacao,
            "periodo": {
                "dias": periodo_dias,
                "data_inicio": inicio.date().isoformat(),
                "data_fim": (fim - timedelta(days=1)).date().isoformat(),
                "aplicado": situacao in ("pagas", "todas"),
            },
            "resumo": {
                "contas": len(itens),
                "valor_total": _moeda(sum(item["valor_final"] for item in itens)),
                "valor_pago": _moeda(sum(item["valor_pago"] for item in itens)),
                "saldo_aberto": _moeda(sum(item["saldo_aberto"] for item in itens)),
                "saldo_vencido": _moeda(
                    sum(item["saldo_aberto"] for item in itens if item["vencida"])
                ),
            },
            "itens": itens[:limite],
            "limite": limite,
        }

    def listar_pedidos_compra(
        self,
        grupo_id: int,
        empresa_atual_id,
        *,
        periodo_dias: int = 30,
        busca: str = "",
        empresa_id: str | None = None,
        limite: int = 200,
    ) -> dict:
        grupo, membros, membros_por_id = self._contexto(grupo_id, empresa_atual_id)
        self._validar_empresa_filtro(empresa_id, membros_por_id)
        inicio, fim = self._periodo(periodo_dias)
        busca = _texto(busca)
        itens = []

        for membro, empresa in membros:
            membro_id = str(membro.empresa_id)
            if empresa_id and membro_id != str(empresa_id):
                continue
            empresa_uuid = UUID(membro_id)
            with tenant_context(empresa_uuid):
                query = (
                    self.db.query(
                        PedidoCompra,
                        Cliente.nome.label("fornecedor_nome"),
                        func.count(PedidoCompraItem.id).label("quantidade_itens"),
                        func.coalesce(
                            func.sum(PedidoCompraItem.quantidade_pedida), 0
                        ).label("quantidade_pedida"),
                        func.coalesce(
                            func.sum(PedidoCompraItem.quantidade_recebida), 0
                        ).label("quantidade_recebida"),
                    )
                    .outerjoin(
                        Cliente,
                        (Cliente.id == PedidoCompra.fornecedor_id)
                        & (Cliente.tenant_id == PedidoCompra.tenant_id),
                    )
                    .outerjoin(
                        PedidoCompraItem,
                        (PedidoCompraItem.pedido_compra_id == PedidoCompra.id)
                        & (PedidoCompraItem.tenant_id == PedidoCompra.tenant_id),
                    )
                    .filter(
                        PedidoCompra.tenant_id == empresa_uuid,
                        PedidoCompra.data_pedido >= inicio,
                        PedidoCompra.data_pedido < fim,
                    )
                )
                if busca:
                    termo = f"%{busca}%"
                    query = query.filter(
                        or_(
                            PedidoCompra.numero_pedido.ilike(termo),
                            PedidoCompra.observacoes.ilike(termo),
                            Cliente.nome.ilike(termo),
                        )
                    )
                linhas = (
                    query.group_by(PedidoCompra.id, Cliente.nome)
                    .order_by(PedidoCompra.data_pedido.desc(), PedidoCompra.id.desc())
                    .limit(limite)
                    .all()
                )
            for pedido, fornecedor_nome, quantidade_itens, pedida, recebida in linhas:
                itens.append(
                    {
                        "empresa_id": membro_id,
                        "empresa_nome": empresa.name,
                        "pedido_id": pedido.id,
                        "numero_pedido": pedido.numero_pedido,
                        "fornecedor_nome": fornecedor_nome
                        or "Fornecedor não identificado",
                        "status": pedido.status,
                        "data_pedido": _iso_data_hora(pedido.data_pedido),
                        "data_prevista_entrega": _iso_data_hora(
                            pedido.data_prevista_entrega
                        ),
                        "quantidade_itens": int(quantidade_itens or 0),
                        "quantidade_pedida": _quantidade(pedida),
                        "quantidade_recebida": _quantidade(recebida),
                        "valor_final": _moeda(pedido.valor_final),
                        "sugestao_ia": bool(pedido.sugestao_ia),
                    }
                )

        itens.sort(
            key=lambda item: (item["data_pedido"] or "", item["pedido_id"]),
            reverse=True,
        )
        em_andamento = {"rascunho", "enviado", "confirmado", "recebido_parcial"}
        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "periodo": {
                "dias": periodo_dias,
                "data_inicio": inicio.date().isoformat(),
                "data_fim": (fim - timedelta(days=1)).date().isoformat(),
            },
            "resumo": {
                "pedidos": len(itens),
                "em_andamento": sum(
                    1 for item in itens if item["status"] in em_andamento
                ),
                "sugeridos_ia": sum(1 for item in itens if item["sugestao_ia"]),
                "valor_total": _moeda(sum(item["valor_final"] for item in itens)),
            },
            "itens": itens[:limite],
            "limite": limite,
        }

    def _linhas_produtos_vendidos(self, membros: list, inicio: datetime, fim: datetime):
        linhas = []
        for membro, empresa in membros:
            empresa_id = str(membro.empresa_id)
            empresa_uuid = UUID(empresa_id)
            with tenant_context(empresa_uuid):
                resultados = (
                    self.db.query(
                        Produto.id,
                        Produto.nome,
                        Produto.codigo,
                        Produto.codigo_barras,
                        Produto.gtin_ean,
                        Produto.estoque_atual,
                        Produto.estoque_minimo,
                        Produto.preco_custo,
                        func.coalesce(func.sum(VendaItem.quantidade), 0).label(
                            "quantidade"
                        ),
                        func.coalesce(func.sum(VendaItem.subtotal), 0).label(
                            "valor_total"
                        ),
                        func.count(func.distinct(VendaItem.venda_id)).label("pedidos"),
                    )
                    .join(
                        VendaItem,
                        (VendaItem.produto_id == Produto.id)
                        & (VendaItem.tenant_id == Produto.tenant_id),
                    )
                    .join(
                        Venda,
                        (Venda.id == VendaItem.venda_id)
                        & (Venda.tenant_id == VendaItem.tenant_id),
                    )
                    .filter(
                        Produto.tenant_id == empresa_uuid,
                        Venda.data_venda >= inicio,
                        Venda.data_venda < fim,
                        or_(Venda.status.is_(None), Venda.status != "cancelada"),
                        VendaItem.tipo == "produto",
                    )
                    .group_by(
                        Produto.id,
                        Produto.nome,
                        Produto.codigo,
                        Produto.codigo_barras,
                        Produto.gtin_ean,
                        Produto.estoque_atual,
                        Produto.estoque_minimo,
                        Produto.preco_custo,
                    )
                    .all()
                )
            for resultado in resultados:
                linhas.append(
                    {
                        "empresa_id": empresa_id,
                        "empresa_nome": empresa.name,
                        "produto_id": resultado.id,
                        "produto_nome": resultado.nome,
                        "sku": resultado.codigo,
                        "ean": resultado.codigo_barras or resultado.gtin_ean,
                        "estoque": _quantidade(resultado.estoque_atual),
                        "estoque_minimo": _quantidade(resultado.estoque_minimo),
                        "preco_custo": _moeda(resultado.preco_custo),
                        "quantidade": _quantidade(resultado.quantidade),
                        "valor_total": _moeda(resultado.valor_total),
                        "pedidos": int(resultado.pedidos or 0),
                    }
                )
        return linhas

    def _catalogo_produtos_grupo(self, membros: list) -> list[dict]:
        catalogo = []
        for membro, empresa in membros:
            empresa_id = str(membro.empresa_id)
            empresa_uuid = UUID(empresa_id)
            with tenant_context(empresa_uuid):
                produtos = (
                    self.db.query(
                        Produto.id,
                        Produto.nome,
                        Produto.codigo,
                        Produto.codigo_barras,
                        Produto.gtin_ean,
                        Produto.estoque_atual,
                        Produto.estoque_minimo,
                        Produto.preco_custo,
                    )
                    .filter(Produto.tenant_id == empresa_uuid)
                    .all()
                )
            for produto in produtos:
                catalogo.append(
                    {
                        "empresa_id": empresa_id,
                        "empresa_nome": empresa.name,
                        "produto_id": produto.id,
                        "produto_nome": produto.nome,
                        "sku": produto.codigo,
                        "ean": produto.codigo_barras or produto.gtin_ean,
                        "estoque": _quantidade(produto.estoque_atual),
                        "estoque_minimo": _quantidade(produto.estoque_minimo),
                        "preco_custo": _moeda(produto.preco_custo),
                        "quantidade": 0.0,
                        "valor_total": 0.0,
                        "pedidos": 0,
                    }
                )
        return catalogo

    def _complementar_equivalentes_sem_venda(
        self,
        linhas: list[dict],
        membros: list,
        vinculos: list,
    ) -> list[dict]:
        if not linhas:
            return linhas

        catalogo = self._catalogo_produtos_grupo(membros)
        chaves_catalogo = {
            (item["empresa_id"], item["produto_id"]) for item in catalogo
        }
        equivalencias = _ConjuntosProdutos(chaves_catalogo)

        por_ean = defaultdict(list)
        for item in catalogo:
            ean = _normalizar_codigo(item["ean"])
            if ean:
                por_ean[ean].append((item["empresa_id"], item["produto_id"]))
        for equivalentes in por_ean.values():
            if len({chave[0] for chave in equivalentes}) < 2:
                continue
            primeira = equivalentes[0]
            for equivalente in equivalentes[1:]:
                equivalencias.unir(primeira, equivalente)

        for vinculo in vinculos:
            equivalencias.unir(
                (str(vinculo.empresa_a_id), vinculo.produto_a_id),
                (str(vinculo.empresa_b_id), vinculo.produto_b_id),
            )

        chaves_com_venda = {(item["empresa_id"], item["produto_id"]) for item in linhas}
        raizes_com_venda = {
            equivalencias.encontrar(chave)
            for chave in chaves_com_venda
            if chave in chaves_catalogo
        }
        complementares = [
            item
            for item in catalogo
            if (item["empresa_id"], item["produto_id"]) not in chaves_com_venda
            and equivalencias.encontrar((item["empresa_id"], item["produto_id"]))
            in raizes_com_venda
        ]
        return [*linhas, *complementares]

    def listar_produtos_vendidos(
        self,
        grupo_id: int,
        empresa_atual_id,
        *,
        periodo_dias: int = 30,
        busca: str = "",
        limite: int = 200,
    ) -> dict:
        grupo, membros, _membros_por_id = self._contexto(grupo_id, empresa_atual_id)
        inicio, fim = self._periodo(periodo_dias)
        linhas = self._linhas_produtos_vendidos(membros, inicio, fim)

        vinculos = (
            self.db.query(EmpresaGrupoProdutoVinculo)
            .filter(
                EmpresaGrupoProdutoVinculo.grupo_id == grupo.id,
                EmpresaGrupoProdutoVinculo.status == "ativo",
            )
            .all()
        )
        linhas = self._complementar_equivalentes_sem_venda(linhas, membros, vinculos)
        chaves = {(item["empresa_id"], item["produto_id"]) for item in linhas}
        conjuntos = _ConjuntosProdutos(chaves)

        chaves_vinculadas = set()
        for vinculo in vinculos:
            chave_a = (str(vinculo.empresa_a_id), vinculo.produto_a_id)
            chave_b = (str(vinculo.empresa_b_id), vinculo.produto_b_id)
            conjuntos.unir(chave_a, chave_b)
            chaves_vinculadas.update((chave_a, chave_b))

        por_ean = defaultdict(list)
        for item in linhas:
            ean = _normalizar_codigo(item["ean"])
            if ean:
                por_ean[ean].append((item["empresa_id"], item["produto_id"]))
        chaves_ean = set()
        for equivalentes in por_ean.values():
            empresas = {chave[0] for chave in equivalentes}
            if len(empresas) < 2:
                continue
            primeira = equivalentes[0]
            for equivalente in equivalentes[1:]:
                conjuntos.unir(primeira, equivalente)
                chaves_ean.update((primeira, equivalente))

        grupos = defaultdict(list)
        for item in linhas:
            chave = (item["empresa_id"], item["produto_id"])
            grupos[conjuntos.encontrar(chave)].append(item)

        busca_normalizada = _normalizar_codigo(busca)
        busca_texto = _texto(busca).casefold()
        itens = []
        for detalhes in grupos.values():
            if busca_texto or busca_normalizada:
                encontrado = any(
                    busca_texto in _texto(item["produto_nome"]).casefold()
                    or busca_normalizada in _normalizar_codigo(item["sku"])
                    or busca_normalizada in _normalizar_codigo(item["ean"])
                    or busca_texto in _texto(item["empresa_nome"]).casefold()
                    for item in detalhes
                )
                if not encontrado:
                    continue
            principal = max(detalhes, key=lambda item: item["valor_total"])
            quantidade = _quantidade(sum(item["quantidade"] for item in detalhes))
            estoque = _quantidade(sum(item["estoque"] for item in detalhes))
            estoque_disponivel = max(estoque, 0)
            valor_total = _moeda(sum(item["valor_total"] for item in detalhes))
            chaves_detalhes = {
                (item["empresa_id"], item["produto_id"]) for item in detalhes
            }
            tipo_vinculo = (
                "manual"
                if chaves_detalhes & chaves_vinculadas
                else ("ean" if chaves_detalhes & chaves_ean else "isolado")
            )
            media_diaria = quantidade / periodo_dias if periodo_dias else 0
            itens.append(
                {
                    "produto_nome": principal["produto_nome"],
                    "sku": principal["sku"],
                    "ean": principal["ean"],
                    "tipo_vinculo": tipo_vinculo,
                    "empresas": detalhes,
                    "quantidade": quantidade,
                    "valor_total": valor_total,
                    "pedidos": sum(item["pedidos"] for item in detalhes),
                    "estoque_grupo": estoque,
                    "estoque_minimo_grupo": _quantidade(
                        sum(item["estoque_minimo"] for item in detalhes)
                    ),
                    "cobertura_dias": round(estoque_disponivel / media_diaria, 1)
                    if media_diaria > 0
                    else None,
                    "preco_medio": round(valor_total / quantidade, 2)
                    if quantidade
                    else 0,
                }
            )

        itens.sort(
            key=lambda item: (item["valor_total"], item["quantidade"]), reverse=True
        )
        return {
            "grupo": {"id": grupo.id, "nome": grupo.nome},
            "periodo": {
                "dias": periodo_dias,
                "data_inicio": inicio.date().isoformat(),
                "data_fim": (fim - timedelta(days=1)).date().isoformat(),
            },
            "resumo": {
                "produtos": len(itens),
                "quantidade": _quantidade(sum(item["quantidade"] for item in itens)),
                "valor_total": _moeda(sum(item["valor_total"] for item in itens)),
                "estoque_grupo": _quantidade(
                    sum(item["estoque_grupo"] for item in itens)
                ),
            },
            "itens": itens[:limite],
            "limite": limite,
        }
