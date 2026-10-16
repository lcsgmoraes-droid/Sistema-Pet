# -*- coding: utf-8 -*-
"""Identidade de produto compartilhada entre lojas do grupo comercial (fase D).

Funil unico pra toda escrita de campo inerente de Produto (nome, codigo de
barras/GTIN, peso, dimensoes, foto, descricao, classificacao de racao) — tanto
o fluxo normal de criacao/edicao (app/produtos/cadastro_routes.py,
ProdutoService.create_produto) quanto o script de reconciliacao de dados
existentes (backend/scripts/backfill_produto_identidades.py) passam por aqui,
pra nunca divergir a logica entre os dois caminhos.

Produto continua com as mesmas colunas inerentes de sempre — elas funcionam
como espelho sincronizado da ProdutoIdentidade (fonte da verdade), nunca um
join: qualquer consumidor que ja le Produto.nome/codigo_barras/etc. direto
continua funcionando sem mudanca nenhuma. Ver Documentacao/Dominio/
Plano-Camada-Geral.md, Checkpoint 7.
"""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import Session

from ..grupo_comercial_contexto import listar_empresas_do_grupo, obter_grupo_id_ativo
from ..produto_identidade_models import (
    ProdutoIdentidade,
    ProdutoIdentidadeConflito,
    ProdutoIdentidadeHistoricoAlteracao,
)
from ..produtos_catalogo_models import Produto, ProdutoHistoricoAlteracao
from ..tenancy.context import tenant_context

# Campos que existem independente da loja — o que o produto FISICAMENTE e,
# nao como cada loja opera com ele. Preco/custo/estoque/lote/fornecedor
# continuam de fora por decisao explicita (ver plano) — tratados como "da
# loja" nesta primeira entrega. gtin_ean_tributario fica fora da CHAVE de
# correspondencia (ver _normalizar_chave) mas e um campo inerente normal,
# espelhado como qualquer outro.
INHERENT_FIELDS: frozenset[str] = frozenset(
    {
        "nome",
        "codigo_barras",
        "codigos_barras_alternativos",
        "gtin_ean",
        "gtin_ean_tributario",
        "peso_liquido",
        "peso_bruto",
        "largura",
        "altura",
        "profundidade",
        "volume",
        "itens_por_caixa",
        "descricao_curta",
        "descricao_completa",
        "tags",
        "imagem_principal",
        "unidade",
        "condicao",
        "e_granel",
        "producao",
        "especie_compativel",
        "classificacao_racao",
        "peso_embalagem",
        "tabela_nutricional",
        "categoria_racao",
        "especies_indicadas",
        "tabela_consumo",
        "porte_animal",
        "fase_publico",
        "tipo_tratamento",
        "sabor_proteina",
        "auto_classificar_nome",
    }
)


def normalizar_chave_matching(codigo_barras, gtin_ean) -> str | None:
    """codigo_barras ou, na falta dele, gtin_ean — nunca gtin_ean_tributario
    (GTIN da unidade tributaria pode legitimamente diferir do GTIN comercial
    do mesmo item; misturar os dois no match arrisca falso-positivo entre
    caixa e unidade)."""
    for valor in (codigo_barras, gtin_ean):
        texto = str(valor).strip() if valor is not None else ""
        if texto:
            return texto
    return None


def _copiar_campos(origem: Any, destino: Any, campos: Iterable[str]) -> None:
    for campo in campos:
        setattr(destino, campo, getattr(origem, campo))


def resolver_ou_vincular(produto: Produto, db: Session) -> ProdutoIdentidade | None:
    """Roda na criacao (e na edicao de codigo de barras de um produto ainda
    sem vinculo). Produto precisa ja ter `id` (pos db.flush()). Servico nunca
    entra — nao tem identidade fisica compartilhavel."""
    if getattr(produto, "tipo", None) == "servico":
        return None
    if produto.produto_identidade_id is not None:
        return None

    chave = normalizar_chave_matching(produto.codigo_barras, produto.gtin_ean)
    if not chave:
        return None

    candidatos = (
        db.query(ProdutoIdentidade)
        .filter(ProdutoIdentidade.chave_matching == chave)
        .all()
    )

    if not candidatos:
        identidade = ProdutoIdentidade(
            tenant_id=produto.tenant_id,
            origem_tenant_id=produto.tenant_id,
            chave_matching=chave,
        )
        _copiar_campos(produto, identidade, INHERENT_FIELDS)
        db.add(identidade)
        db.flush()
        produto.produto_identidade_id = identidade.id
        return identidade

    if len(candidatos) == 1:
        identidade = candidatos[0]
        produto.produto_identidade_id = identidade.id
        # Nao deixa o cadastro recem-digitado sobrescrever o que ja existe —
        # a identidade ja estabelecida e que vence.
        _copiar_campos(identidade, produto, INHERENT_FIELDS)
        return identidade

    _registrar_conflito(produto, candidatos, chave, db)
    return None


def _registrar_conflito(
    produto: Produto, candidatos: list[ProdutoIdentidade], chave: str, db: Session
) -> None:
    grupo_id = obter_grupo_id_ativo(db, produto.tenant_id)
    if grupo_id is None:
        return

    registros = [
        {
            "tenant_id": str(identidade.origem_tenant_id or identidade.tenant_id),
            "produto_id": None,
            "produto_identidade_id": identidade.id,
        }
        for identidade in candidatos
    ]
    registros.append(
        {
            "tenant_id": str(produto.tenant_id),
            "produto_id": produto.id,
            "produto_identidade_id": None,
        }
    )
    db.add(
        ProdutoIdentidadeConflito(
            grupo_id=grupo_id,
            chave_matching=chave,
            produto_ids=registros,
        )
    )


def aplicar_campos_compartilhados(
    identidade: ProdutoIdentidade,
    campos: dict[str, Any],
    db: Session,
    usuario_id: int | None = None,
) -> None:
    """Funil unico de escrita de campo inerente: grava na identidade (fonte da
    verdade), audita, e sobrescreve (nunca diff) o espelho em toda linha de
    Produto ligada a ela, em qualquer loja do grupo — cada uma dentro do seu
    proprio tenant_context(), nunca um UPDATE cross-tenant direto."""
    campos_inerentes = {k: v for k, v in campos.items() if k in INHERENT_FIELDS}
    alterados: dict[str, tuple[Any, Any]] = {}
    for campo, novo_valor in campos_inerentes.items():
        valor_anterior = getattr(identidade, campo)
        if valor_anterior == novo_valor:
            continue
        setattr(identidade, campo, novo_valor)
        alterados[campo] = (valor_anterior, novo_valor)

    if not alterados:
        return

    identidade.chave_matching = normalizar_chave_matching(
        identidade.codigo_barras, identidade.gtin_ean
    )
    db.flush()

    for campo, (valor_anterior, valor_novo) in alterados.items():
        db.add(
            ProdutoIdentidadeHistoricoAlteracao(
                tenant_id=identidade.tenant_id,
                produto_identidade_id=identidade.id,
                user_id=usuario_id,
                campo=campo,
                valor_anterior=_para_texto(valor_anterior),
                valor_novo=_para_texto(valor_novo),
            )
        )

    _propagar_para_produtos_vinculados(identidade, alterados, db, usuario_id)


def processar_alteracoes_inerentes(
    produto: Produto,
    campos_alterados: dict[str, Any],
    db: Session,
    usuario_id: int | None = None,
) -> None:
    """Chamada depois de aplicar `campos_alterados` localmente em `produto`
    (app/produtos/cadastro_routes.py::atualizar_produto). Decide se propaga pra
    identidade compartilhada (produto ja vinculado) ou tenta vincular agora
    (produto sem vinculo que acabou de ganhar/mudar codigo de barras/GTIN)."""
    campos_inerentes = {
        k: v for k, v in campos_alterados.items() if k in INHERENT_FIELDS
    }
    if not campos_inerentes:
        return

    if produto.produto_identidade_id is not None:
        identidade = (
            db.query(ProdutoIdentidade)
            .filter(ProdutoIdentidade.id == produto.produto_identidade_id)
            .first()
        )
        if identidade is not None:
            aplicar_campos_compartilhados(identidade, campos_inerentes, db, usuario_id)
        return

    if "codigo_barras" in campos_inerentes or "gtin_ean" in campos_inerentes:
        resolver_ou_vincular(produto, db)


def _propagar_para_produtos_vinculados(
    identidade: ProdutoIdentidade,
    alterados: dict[str, tuple[Any, Any]],
    db: Session,
    usuario_id: int | None,
) -> None:
    tenants_do_grupo = listar_empresas_do_grupo(db, identidade.tenant_id)
    for tenant_id_str in tenants_do_grupo:
        with tenant_context(tenant_id_str):
            produtos_locais = (
                db.query(Produto)
                .filter(Produto.produto_identidade_id == identidade.id)
                .all()
            )
            for produto in produtos_locais:
                for campo in alterados:
                    valor_novo = getattr(identidade, campo)
                    valor_atual = getattr(produto, campo)
                    if valor_atual == valor_novo:
                        continue
                    db.add(
                        ProdutoHistoricoAlteracao(
                            tenant_id=produto.tenant_id,
                            produto_id=produto.id,
                            user_id=usuario_id,
                            campo=campo,
                            valor_anterior=_para_texto(valor_atual),
                            valor_novo=_para_texto(valor_novo),
                        )
                    )
                    setattr(produto, campo, valor_novo)
            db.flush()


def _para_texto(valor: Any) -> str | None:
    if valor is None:
        return None
    return str(valor)
