"""Helpers financeiros e de insumos do modulo veterinario."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from .financeiro_models import CategoriaFinanceira, ContaReceber
from .produtos_models import EstoqueMovimentacao, Produto
from .utils.timezone import to_brasilia
from .veterinario_models import (
    CatalogoProcedimento,
    ConsultaVet,
    ProcedimentoConsulta,
    VetPartnerLink,
)


def _as_float(value) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _serializar_datetime_vet(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        if getattr(value, "tzinfo", None):
            return to_brasilia(value).replace(tzinfo=None)
    except Exception:
        if getattr(value, "tzinfo", None):
            return value.replace(tzinfo=None)
    return value


def _normalizar_insumos(insumos: Optional[list]) -> list[dict]:
    normalizados = []
    if not isinstance(insumos, list):
        return normalizados

    for item in insumos:
        if not isinstance(item, dict):
            continue
        produto_id = item.get("produto_id")
        quantidade = _as_float(item.get("quantidade"))
        if not produto_id or not quantidade or quantidade <= 0:
            continue
        normalizados.append({
            "produto_id": int(produto_id),
            "quantidade": quantidade,
            "nome": (item.get("nome") or "").strip() or None,
            "unidade": (item.get("unidade") or "").strip() or None,
            "observacoes": (item.get("observacoes") or "").strip() or None,
            "baixar_estoque": bool(item.get("baixar_estoque", True)),
            "custo_unitario": _as_float(item.get("custo_unitario")) or 0.0,
            "custo_total": _as_float(item.get("custo_total")) or 0.0,
        })
    return normalizados


def _round_money(value: Optional[float]) -> float:
    return round(_as_float(value) or 0.0, 2)


def _buscar_produtos_por_ids(db: Session, tenant_id, produto_ids: list[int]) -> dict[int, Produto]:
    if not produto_ids:
        return {}

    produtos = db.query(Produto).filter(
        Produto.tenant_id == str(tenant_id),
        Produto.id.in_(produto_ids),
    ).all()
    return {produto.id: produto for produto in produtos}


def _enriquecer_insumos_com_custos(db: Session, tenant_id, insumos: Optional[list]) -> list[dict]:
    normalizados = _normalizar_insumos(insumos)
    produtos = _buscar_produtos_por_ids(db, tenant_id, [item["produto_id"] for item in normalizados])

    enriquecidos = []
    for item in normalizados:
        produto = produtos.get(item["produto_id"])
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")

        custo_unitario = _round_money(produto.preco_custo)
        enriquecidos.append({
            **item,
            "nome": item.get("nome") or produto.nome,
            "unidade": item.get("unidade") or produto.unidade,
            "custo_unitario": custo_unitario,
            "custo_total": _round_money(custo_unitario * item["quantidade"]),
        })

    return enriquecidos


def _aplicar_baixa_estoque_itens(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    itens: Optional[list],
    motivo: str,
    referencia_id: int,
    referencia_tipo: str,
    documento: str,
    observacao: str,
) -> tuple[list[dict], list[int]]:
    itens = _normalizar_insumos(itens)
    produtos = _buscar_produtos_por_ids(db, tenant_id, [item["produto_id"] for item in itens])
    movimentacoes_ids = []
    for item in itens:
        if not item["baixar_estoque"]:
            continue

        produto = produtos.get(item["produto_id"])
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")
        if not produto.ativo:
            raise HTTPException(status_code=404, detail=f"Produto {item['produto_id']} não encontrado para o procedimento")

        estoque_atual = float(produto.estoque_atual or 0)
        if estoque_atual < item["quantidade"]:
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para {produto.nome}. Disponível: {estoque_atual}, necessário: {item['quantidade']}",
            )

        quantidade_anterior = estoque_atual
        quantidade_nova = estoque_atual - item["quantidade"]
        produto.estoque_atual = quantidade_nova
        custo_unitario = _round_money(produto.preco_custo)
        custo_total = _round_money(custo_unitario * item["quantidade"])

        movimentacao = EstoqueMovimentacao(
            tenant_id=str(tenant_id),
            produto_id=produto.id,
            tipo="saida",
            motivo=motivo,
            quantidade=item["quantidade"],
            quantidade_anterior=quantidade_anterior,
            quantidade_nova=quantidade_nova,
            custo_unitario=custo_unitario,
            valor_total=custo_total,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            documento=documento,
            observacao=observacao,
            user_id=user_id,
        )
        db.add(movimentacao)
        db.flush()
        movimentacoes_ids.append(movimentacao.id)
        item["nome"] = item.get("nome") or produto.nome
        item["unidade"] = item.get("unidade") or produto.unidade
        item["custo_unitario"] = custo_unitario
        item["custo_total"] = custo_total

    return itens, movimentacoes_ids


def _aplicar_baixa_estoque_procedimento(db: Session, procedimento: ProcedimentoConsulta, tenant_id, user_id: int) -> None:
    if not procedimento.realizado or procedimento.estoque_baixado:
        return

    itens, movimentacoes_ids = _aplicar_baixa_estoque_itens(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        itens=procedimento.insumos,
        motivo="procedimento_veterinario",
        referencia_id=procedimento.id,
        referencia_tipo="procedimento_veterinario",
        documento=str(procedimento.consulta_id),
        observacao=f"Baixa automática do procedimento {procedimento.nome}",
    )

    procedimento.insumos = itens
    procedimento.estoque_baixado = bool(movimentacoes_ids) or procedimento.estoque_baixado
    procedimento.estoque_movimentacao_ids = movimentacoes_ids or procedimento.estoque_movimentacao_ids


def _resumo_financeiro_insumos(insumos: Optional[list]) -> dict:
    itens = _normalizar_insumos(insumos)
    custo_total = _round_money(sum((_as_float(item.get("custo_total")) or 0.0) for item in itens))
    return {
        "insumos": itens,
        "custo_total": custo_total,
    }


def _obter_regra_financeira_veterinaria(db: Session, tenant_id) -> dict:
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.vet_tenant_id == str(tenant_id),
        VetPartnerLink.ativo == True,
    ).order_by(VetPartnerLink.id.desc()).first()

    if link and link.tipo_relacao == "parceiro":
        return {
            "modo_operacional": "parceiro",
            "comissao_empresa_pct": _round_money(link.comissao_empresa_pct),
            "empresa_tenant_id": str(link.empresa_tenant_id),
            "tenant_recebedor_id": str(link.vet_tenant_id),
        }

    return {
        "modo_operacional": "funcionario",
        "comissao_empresa_pct": 0.0,
        "empresa_tenant_id": str(tenant_id),
        "tenant_recebedor_id": str(tenant_id),
    }


def _resumo_financeiro_procedimento(valor, insumos: Optional[list], regra_financeira: Optional[dict] = None) -> dict:
    valor_cobrado = _round_money(valor)
    resumo_insumos = _resumo_financeiro_insumos(insumos)
    custo_total = resumo_insumos["custo_total"]
    margem_valor = _round_money(valor_cobrado - custo_total)
    margem_percentual = round((margem_valor / valor_cobrado) * 100, 2) if valor_cobrado > 0 else 0.0
    regra = regra_financeira or {
        "modo_operacional": "funcionario",
        "comissao_empresa_pct": 0.0,
        "empresa_tenant_id": None,
        "tenant_recebedor_id": None,
    }
    repasse_empresa_valor = 0.0
    receita_tenant_valor = valor_cobrado
    entrada_empresa_valor = valor_cobrado
    if regra["modo_operacional"] == "parceiro":
        repasse_empresa_valor = _round_money(valor_cobrado * ((_as_float(regra.get("comissao_empresa_pct")) or 0.0) / 100))
        receita_tenant_valor = _round_money(valor_cobrado - repasse_empresa_valor)
        entrada_empresa_valor = repasse_empresa_valor

    return {
        "valor_cobrado": valor_cobrado,
        "custo_total": custo_total,
        "margem_valor": margem_valor,
        "margem_percentual": margem_percentual,
        "modo_operacional": regra["modo_operacional"],
        "comissao_empresa_pct": _round_money(regra.get("comissao_empresa_pct")),
        "repasse_empresa_valor": repasse_empresa_valor,
        "receita_tenant_valor": receita_tenant_valor,
        "entrada_empresa_valor": entrada_empresa_valor,
        "insumos": resumo_insumos["insumos"],
    }


def _obter_dre_subcategoria_receita_padrao(db: Session, tenant_id) -> int:
    subcategoria = db.query(DRESubcategoria).join(
        DRECategoria, DRECategoria.id == DRESubcategoria.categoria_id
    ).filter(
        DRESubcategoria.tenant_id == str(tenant_id),
        DRECategoria.tenant_id == str(tenant_id),
        DRESubcategoria.ativo == True,
        DRECategoria.ativo == True,
        DRECategoria.natureza == NaturezaDRE.RECEITA,
    ).order_by(DRECategoria.ordem.asc(), DRESubcategoria.id.asc()).first()
    return subcategoria.id if subcategoria else 1


def _obter_ou_criar_categoria_financeira_vet(
    db: Session,
    tenant_id,
    user_id: int,
    nome: str,
    descricao: str,
) -> CategoriaFinanceira:
    categoria = db.query(CategoriaFinanceira).filter(
        CategoriaFinanceira.tenant_id == str(tenant_id),
        CategoriaFinanceira.nome == nome,
        CategoriaFinanceira.tipo == "receita",
    ).first()
    if categoria:
        return categoria

    categoria = CategoriaFinanceira(
        tenant_id=str(tenant_id),
        nome=nome,
        tipo="receita",
        descricao=descricao,
        dre_subcategoria_id=_obter_dre_subcategoria_receita_padrao(db, tenant_id),
        ativo=True,
        user_id=user_id,
    )
    db.add(categoria)
    db.flush()
    return categoria


def _criar_conta_receber_procedimento(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    cliente_id: Optional[int],
    categoria_id: int,
    dre_subcategoria_id: int,
    descricao: str,
    valor: float,
    documento: str,
    observacoes: Optional[str] = None,
):
    existente = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento == documento,
    ).first()
    if existente:
        return existente

    conta = ContaReceber(
        tenant_id=str(tenant_id),
        descricao=descricao,
        cliente_id=cliente_id,
        categoria_id=categoria_id,
        dre_subcategoria_id=dre_subcategoria_id,
        canal="loja_fisica",
        valor_original=Decimal(str(_round_money(valor))),
        valor_recebido=Decimal("0"),
        valor_final=Decimal(str(_round_money(valor))),
        data_emissao=date.today(),
        data_vencimento=date.today(),
        status="pendente",
        documento=documento,
        observacoes=observacoes,
        user_id=user_id,
    )
    db.add(conta)
    db.flush()
    return conta


def _sincronizar_financeiro_procedimento(
    db: Session,
    procedimento: ProcedimentoConsulta,
    tenant_id,
    user_id: int,
) -> None:
    consulta = db.query(ConsultaVet).filter(
        ConsultaVet.id == procedimento.consulta_id,
        ConsultaVet.tenant_id == tenant_id,
    ).first()
    if not consulta:
        return

    regra = _obter_regra_financeira_veterinaria(db, tenant_id)
    resumo = _resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra)

    categoria_empresa = _obter_ou_criar_categoria_financeira_vet(
        db,
        regra["empresa_tenant_id"],
        user_id,
        "Veterinário - Procedimentos",
        "Receitas de procedimentos veterinários.",
    )

    if regra["modo_operacional"] == "parceiro":
        categoria_vet = _obter_ou_criar_categoria_financeira_vet(
            db,
            tenant_id,
            user_id,
            "Veterinário - Receita Líquida",
            "Receita líquida do veterinário após repasse da empresa.",
        )

        if resumo["receita_tenant_valor"] > 0:
            _criar_conta_receber_procedimento(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                cliente_id=consulta.cliente_id,
                categoria_id=categoria_vet.id,
                dre_subcategoria_id=categoria_vet.dre_subcategoria_id or _obter_dre_subcategoria_receita_padrao(db, tenant_id),
                descricao=f"Procedimento vet #{procedimento.id} - líquido {procedimento.nome}",
                valor=resumo["receita_tenant_valor"],
                documento=f"VET-PROC-{procedimento.id}-LIQUIDO-VET",
                observacoes=f"Receita líquida após repasse de {resumo['comissao_empresa_pct']}% para a empresa.",
            )

        if resumo["repasse_empresa_valor"] > 0:
            _criar_conta_receber_procedimento(
                db,
                tenant_id=regra["empresa_tenant_id"],
                user_id=user_id,
                cliente_id=None,
                categoria_id=categoria_empresa.id,
                dre_subcategoria_id=categoria_empresa.dre_subcategoria_id or _obter_dre_subcategoria_receita_padrao(db, regra["empresa_tenant_id"]),
                descricao=f"Repasse vet #{procedimento.id} - {procedimento.nome}",
                valor=resumo["repasse_empresa_valor"],
                documento=f"VET-PROC-{procedimento.id}-REPASSE-EMPRESA",
                observacoes=f"Base de repasse do parceiro veterinário ({resumo['comissao_empresa_pct']}%).",
            )
        return

    _criar_conta_receber_procedimento(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        cliente_id=consulta.cliente_id,
        categoria_id=categoria_empresa.id,
        dre_subcategoria_id=categoria_empresa.dre_subcategoria_id or _obter_dre_subcategoria_receita_padrao(db, tenant_id),
        descricao=f"Procedimento vet #{procedimento.id} - {procedimento.nome}",
        valor=resumo["entrada_empresa_valor"],
        documento=f"VET-PROC-{procedimento.id}-EMPRESA",
        observacoes="Receita gerada automaticamente a partir do procedimento veterinário.",
    )


def _serializar_procedimento(procedimento: ProcedimentoConsulta, db: Session, tenant_id) -> dict:
    regra = _obter_regra_financeira_veterinaria(db, tenant_id)
    resumo = _resumo_financeiro_procedimento(procedimento.valor, procedimento.insumos, regra)
    return {
        "id": procedimento.id,
        "consulta_id": procedimento.consulta_id,
        "catalogo_id": procedimento.catalogo_id,
        "nome": procedimento.nome,
        "descricao": procedimento.descricao,
        "valor": procedimento.valor,
        "valor_cobrado": resumo["valor_cobrado"],
        "realizado": procedimento.realizado,
        "observacoes": procedimento.observacoes,
        "insumos": resumo["insumos"],
        "custo_total": resumo["custo_total"],
        "margem_valor": resumo["margem_valor"],
        "margem_percentual": resumo["margem_percentual"],
        "modo_operacional": resumo["modo_operacional"],
        "comissao_empresa_pct": resumo["comissao_empresa_pct"],
        "repasse_empresa_valor": resumo["repasse_empresa_valor"],
        "receita_tenant_valor": resumo["receita_tenant_valor"],
        "entrada_empresa_valor": resumo["entrada_empresa_valor"],
        "estoque_baixado": bool(procedimento.estoque_baixado),
        "estoque_movimentacao_ids": procedimento.estoque_movimentacao_ids or [],
        "created_at": _serializar_datetime_vet(procedimento.created_at),
    }


def _serializar_catalogo(catalogo: CatalogoProcedimento, db: Session, tenant_id) -> dict:
    insumos = _enriquecer_insumos_com_custos(db, tenant_id, catalogo.insumos or []) if catalogo.insumos else []
    regra = _obter_regra_financeira_veterinaria(db, tenant_id)
    resumo = _resumo_financeiro_procedimento(catalogo.valor_padrao, insumos, regra)
    return {
        "id": catalogo.id,
        "nome": catalogo.nome,
        "descricao": catalogo.descricao,
        "categoria": catalogo.categoria,
        "valor_padrao": catalogo.valor_padrao,
        "duracao_minutos": catalogo.duracao_minutos,
        "requer_anestesia": catalogo.requer_anestesia,
        "observacoes": catalogo.observacoes,
        "insumos": resumo["insumos"],
        "custo_estimado": resumo["custo_total"],
        "margem_estimada": resumo["margem_valor"],
        "margem_percentual_estimada": resumo["margem_percentual"],
        "modo_operacional": resumo["modo_operacional"],
        "comissao_empresa_pct": resumo["comissao_empresa_pct"],
        "repasse_empresa_estimado": resumo["repasse_empresa_valor"],
        "receita_tenant_estimada": resumo["receita_tenant_valor"],
        "ativo": catalogo.ativo,
    }
