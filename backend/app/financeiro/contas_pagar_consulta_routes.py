"""Rotas de consulta e classificacao de contas a pagar."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.dre_plano_contas_models import DRESubcategoria
from app.financeiro.contas_pagar_classificacao import (
    aplicar_classificacao_similar_contas_pagar,
    registrar_regra_classificacao_conta_pagar,
)
from app.financeiro.contas_pagar_common import (
    _expressao_texto_busca,
    _normalizar_texto_busca,
)
from app.financeiro.contas_pagar_origem import (
    CAIXA_PDV_OBSERVACAO_MARKER,
    _identificar_origem_conta_pagar,
)
from app.financeiro.contas_pagar_schemas import (
    ContaPagarClassificacaoUpdate,
    ContaPagarResponse,
)
from app.financeiro_models import CategoriaFinanceira, ContaPagar, TipoDespesa
from app.models import Cliente

router = APIRouter()


# LISTAR CONTAS A PAGAR
# ============================================================================


@router.get("/", response_model=List[ContaPagarResponse])
def listar_contas_pagar(
    status: Optional[str] = Query(None),
    fornecedor_id: Optional[int] = Query(None),
    fornecedor_ids: Optional[List[int]] = Query(None),
    fornecedor_modo: str = Query("incluir", pattern="^(incluir|excluir)$"),
    categoria_id: Optional[int] = Query(None),
    tipo_despesa_id: Optional[int] = Query(None),
    tipo_custo: Optional[str] = Query(None),  # 'fixo', 'variavel'
    origem: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    fornecedor_nome: Optional[str] = Query(None),
    data_campo: str = Query("vencimento"),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    apenas_vencidas: bool = Query(False),
    apenas_vencer: bool = Query(False),
    ocultar_taxas_cartao: bool = Query(False),
    apenas_taxas_cartao: bool = Query(False),
    numero_nf: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista contas a pagar com filtros
    """
    current_user, tenant_id = user_and_tenant

    query = db.query(ContaPagar).filter(ContaPagar.tenant_id == tenant_id)

    # Filtros
    if status:
        status_normalizado = status.strip().lower()
        if status_normalizado == "vencido":
            query = query.filter(
                and_(
                    ContaPagar.status != "pago",
                    ContaPagar.data_vencimento < date.today(),
                )
            )
        else:
            query = query.filter(ContaPagar.status == status_normalizado)
    fornecedor_ids = list(
        dict.fromkeys(int(item) for item in fornecedor_ids or [] if item)
    )
    if fornecedor_id and fornecedor_id not in fornecedor_ids:
        fornecedor_ids.append(fornecedor_id)
    fornecedor_modo_normalizado = (fornecedor_modo or "incluir").strip().lower()
    if fornecedor_ids and fornecedor_modo_normalizado == "excluir":
        query = query.filter(
            or_(
                ContaPagar.fornecedor_id.is_(None),
                ContaPagar.fornecedor_id.notin_(fornecedor_ids),
            )
        )
    elif fornecedor_ids:
        query = query.filter(ContaPagar.fornecedor_id.in_(fornecedor_ids))
    elif fornecedor_id:
        query = query.filter(ContaPagar.fornecedor_id == fornecedor_id)
    termo_fornecedor = (fornecedor_nome or "").strip()
    if termo_fornecedor:
        fornecedor_pattern = f"%{_normalizar_texto_busca(termo_fornecedor)}%"
        fornecedores_match = select(Cliente.id).where(
            Cliente.tenant_id == tenant_id,
            or_(
                _expressao_texto_busca(Cliente.nome).like(fornecedor_pattern),
                _expressao_texto_busca(Cliente.nome_fantasia).like(fornecedor_pattern),
                _expressao_texto_busca(Cliente.razao_social).like(fornecedor_pattern),
                _expressao_texto_busca(Cliente.cnpj).like(fornecedor_pattern),
                _expressao_texto_busca(Cliente.cpf).like(fornecedor_pattern),
            ),
        )
        query = query.filter(ContaPagar.fornecedor_id.in_(fornecedores_match))
    if categoria_id:
        query = query.filter(ContaPagar.categoria_id == categoria_id)
    if tipo_despesa_id:
        query = query.filter(ContaPagar.tipo_despesa_id == tipo_despesa_id)

    origem_normalizada = (origem or "").strip().lower()
    caixa_pdv_condition = ContaPagar.observacoes.ilike(
        f"%{CAIXA_PDV_OBSERVACAO_MARKER}%"
    )
    if origem_normalizada == "caixa_pdv":
        query = query.filter(caixa_pdv_condition)
    elif origem_normalizada == "nota_entrada":
        query = query.filter(ContaPagar.nota_entrada_id.isnot(None))
    elif origem_normalizada == "manual":
        query = query.filter(
            ContaPagar.nota_entrada_id.is_(None),
            or_(ContaPagar.observacoes.is_(None), ~caixa_pdv_condition),
        )

    termo_busca = (busca or "").strip()
    if termo_busca:
        busca_pattern = f"%{_normalizar_texto_busca(termo_busca)}%"
        fornecedores_match = select(Cliente.id).where(
            Cliente.tenant_id == tenant_id,
            or_(
                _expressao_texto_busca(Cliente.nome).like(busca_pattern),
                _expressao_texto_busca(Cliente.nome_fantasia).like(busca_pattern),
                _expressao_texto_busca(Cliente.razao_social).like(busca_pattern),
            ),
        )
        query = query.filter(
            or_(
                _expressao_texto_busca(ContaPagar.descricao).like(busca_pattern),
                _expressao_texto_busca(ContaPagar.documento).like(busca_pattern),
                _expressao_texto_busca(ContaPagar.nfe_numero).like(busca_pattern),
                _expressao_texto_busca(ContaPagar.observacoes).like(busca_pattern),
                ContaPagar.fornecedor_id.in_(fornecedores_match),
            )
        )

    taxa_cartao_condition = or_(
        _expressao_texto_busca(ContaPagar.descricao).like("%taxa credito%"),
        _expressao_texto_busca(ContaPagar.descricao).like("%taxa debito%"),
        _expressao_texto_busca(ContaPagar.descricao).like("%taxa cartao%"),
        _expressao_texto_busca(ContaPagar.documento).like("%taxa credito%"),
        _expressao_texto_busca(ContaPagar.documento).like("%taxa debito%"),
        _expressao_texto_busca(ContaPagar.documento).like("%taxa cartao%"),
    )
    if apenas_taxas_cartao:
        query = query.filter(taxa_cartao_condition)
    elif ocultar_taxas_cartao:
        query = query.filter(~taxa_cartao_condition)

    data_column = ContaPagar.data_vencimento
    if data_campo == "pagamento":
        data_column = ContaPagar.data_pagamento
    elif data_campo == "emissao":
        data_column = ContaPagar.data_emissao

    if data_inicio:
        query = query.filter(data_column >= data_inicio)
    if data_fim:
        query = query.filter(data_column <= data_fim)
    if numero_nf:
        numero_nf_pattern = f"%{numero_nf}%"
        query = query.filter(
            or_(
                ContaPagar.nfe_numero.ilike(numero_nf_pattern),
                ContaPagar.documento.ilike(numero_nf_pattern),
            )
        )
    if tipo_custo in ("fixo", "variavel"):
        from app.financeiro_models import CategoriaFinanceira as CF

        query = query.join(CF, ContaPagar.categoria_id == CF.id, isouter=True).filter(
            CF.tipo_custo == tipo_custo
        )
    if apenas_vencidas:
        query = query.filter(
            and_(ContaPagar.status != "pago", ContaPagar.data_vencimento < date.today())
        )
    if apenas_vencer:
        query = query.filter(
            and_(
                ContaPagar.status != "pago", ContaPagar.data_vencimento >= date.today()
            )
        )

    query = query.order_by(ContaPagar.data_vencimento.asc())
    contas = query.limit(limit).offset(offset).all()

    # Montar response
    resultado = []
    for conta in contas:
        status_value = conta.status or "pendente"

        # Calcular dias para vencimento
        dias_venc = None
        if status_value == "pendente":
            dias_venc = (conta.data_vencimento - date.today()).days

        # Buscar nome do fornecedor
        fornecedor_nome = None
        if conta.fornecedor_id:
            fornecedor = (
                db.query(Cliente)
                .filter(
                    Cliente.id == conta.fornecedor_id, Cliente.tenant_id == tenant_id
                )
                .first()
            )
            if fornecedor:
                fornecedor_nome = fornecedor.nome

        item = {
            "id": conta.id,
            "descricao": conta.descricao,
            "fornecedor_id": conta.fornecedor_id,
            "fornecedor_nome": fornecedor_nome,
            "categoria_id": conta.categoria_id,
            "categoria_nome": conta.categoria.nome if conta.categoria else None,
            "valor_original": float(conta.valor_original)
            if conta.valor_original is not None
            else 0.0,
            "valor_pago": float(conta.valor_pago)
            if conta.valor_pago is not None
            else 0.0,
            "valor_final": float(conta.valor_final)
            if conta.valor_final is not None
            else 0.0,
            "data_emissao": conta.data_emissao,
            "data_vencimento": conta.data_vencimento,
            "data_pagamento": conta.data_pagamento,
            "status": status_value,
            "dias_vencimento": dias_venc,
            "eh_parcelado": conta.eh_parcelado
            if conta.eh_parcelado is not None
            else False,
            "eh_recorrente": conta.eh_recorrente
            if conta.eh_recorrente is not None
            else False,
            "tipo_recorrencia": conta.tipo_recorrencia,
            "intervalo_dias": conta.intervalo_dias,
            "data_inicio_recorrencia": conta.data_inicio_recorrencia,
            "data_fim_recorrencia": conta.data_fim_recorrencia,
            "numero_repeticoes": conta.numero_repeticoes,
            "proxima_recorrencia": conta.proxima_recorrencia,
            "conta_recorrencia_origem_id": conta.conta_recorrencia_origem_id,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas,
            "documento": conta.documento,
            "nfe_numero": conta.nfe_numero,
            "observacoes": conta.observacoes,
            "nota_entrada_id": conta.nota_entrada_id,
            "canal": conta.canal,
            "dre_subcategoria_id": conta.dre_subcategoria_id,
            "dre_subcategoria_nome": None,
            "tipo_despesa_id": conta.tipo_despesa_id,
            "tipo_despesa_nome": conta.tipo_despesa.nome
            if conta.tipo_despesa
            else None,
            "e_custo_fixo": (
                conta.categoria.tipo_custo == "fixo"
                if conta.categoria
                and conta.categoria.tipo_custo in ("fixo", "variavel")
                else None
            ),
            **_identificar_origem_conta_pagar(conta),
        }

        if conta.dre_subcategoria_id:
            sub = (
                db.query(DRESubcategoria)
                .filter(
                    DRESubcategoria.id == conta.dre_subcategoria_id,
                    DRESubcategoria.tenant_id == tenant_id,
                )
                .first()
            )
            if sub:
                item["dre_subcategoria_nome"] = sub.nome

        resultado.append(item)

    return resultado


@router.patch("/{conta_id}/classificacao")
def classificar_conta_pagar(
    conta_id: int,
    payload: ContaPagarClassificacaoUpdate,
    aplicar_fornecedor: bool = Query(False),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Permite classificar conta existente com categoria, subcategoria DRE e tipo de despesa."""
    current_user, tenant_id = user_and_tenant

    conta = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    if (
        payload.categoria_id is None
        and payload.dre_subcategoria_id is None
        and payload.tipo_despesa_id is None
        and payload.canal is None
    ):
        raise HTTPException(
            status_code=422, detail="Informe pelo menos um campo para classificar"
        )

    if payload.categoria_id is not None:
        categoria = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.id == payload.categoria_id,
                CategoriaFinanceira.tenant_id == tenant_id,
                CategoriaFinanceira.ativo.is_(True),
            )
            .first()
        )
        if not categoria:
            raise HTTPException(
                status_code=422, detail="Categoria financeira inválida para este tenant"
            )
        conta.categoria_id = payload.categoria_id

    if payload.dre_subcategoria_id is not None:
        sub = (
            db.query(DRESubcategoria)
            .filter(
                DRESubcategoria.id == payload.dre_subcategoria_id,
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.ativo.is_(True),
            )
            .first()
        )
        if not sub:
            raise HTTPException(
                status_code=422, detail="Subcategoria DRE inválida para este tenant"
            )
        conta.dre_subcategoria_id = payload.dre_subcategoria_id

    if payload.tipo_despesa_id is not None:
        tipo = (
            db.query(TipoDespesa)
            .filter(
                TipoDespesa.id == payload.tipo_despesa_id,
                TipoDespesa.tenant_id == tenant_id,
                TipoDespesa.ativo.is_(True),
            )
            .first()
        )
        if not tipo:
            raise HTTPException(
                status_code=422, detail="Tipo de despesa inválido para este tenant"
            )
        conta.tipo_despesa_id = payload.tipo_despesa_id

    if payload.canal is not None:
        conta.canal = payload.canal

    campos_classificacao = payload.model_fields_set
    regra_aprendida = registrar_regra_classificacao_conta_pagar(
        db,
        tenant_id,
        conta,
        user_id=current_user.id,
        campos=campos_classificacao,
    )
    similares_atualizadas = aplicar_classificacao_similar_contas_pagar(
        db,
        tenant_id,
        conta,
        campos=campos_classificacao,
        regra=regra_aprendida,
        user_id=current_user.id,
    )

    db.commit()
    db.refresh(conta)

    return {
        "ok": True,
        "mensagem": "Classificação atualizada com sucesso",
        "conta_id": conta.id,
        "categoria_id": conta.categoria_id,
        "dre_subcategoria_id": conta.dre_subcategoria_id,
        "tipo_despesa_id": conta.tipo_despesa_id,
        "canal": conta.canal,
        "fornecedor_atualizadas": similares_atualizadas,
        "similares_atualizadas": similares_atualizadas,
        "regra_aprendida": bool(regra_aprendida),
    }


# ============================================================================
# BUSCAR CONTA ESPECÍFICA
# ============================================================================
