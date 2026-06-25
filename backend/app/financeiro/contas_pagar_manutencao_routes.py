"""Rotas de manutencao operacional de contas a pagar."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.dre_plano_contas_models import DRESubcategoria
from app.financeiro.contas_pagar_common import (
    _decimal_monetario,
    _registrar_observacao_operacao_conta_pagar,
)
from app.financeiro.contas_pagar_recorrencia import (
    _aplicar_edicao_recorrencia_futura,
    _garantir_janela_recorrencia_conta,
    calcular_proxima_recorrencia,
)
from app.financeiro.contas_pagar_schemas import (
    ContaPagarOperacaoRequest,
    ContaPagarUpdate,
)
from app.financeiro_models import (
    CategoriaFinanceira,
    ContaBancaria,
    ContaPagar,
    MovimentacaoFinanceira,
    TipoDespesa,
)
from app.models import Cliente
from app.produtos_models import NotaEntrada

router = APIRouter()


@router.patch("/{conta_id}")
def atualizar_conta_pagar(
    conta_id: int,
    payload: ContaPagarUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza dados operacionais de uma conta a pagar existente."""
    _, tenant_id = user_and_tenant
    campos = payload.model_fields_set
    campos_operacionais = set(campos) - {"aplicar_recorrencia_futura"}
    campos_recorrencia = {
        "eh_recorrente",
        "tipo_recorrencia",
        "intervalo_dias",
        "data_inicio_recorrencia",
        "data_fim_recorrencia",
        "numero_repeticoes",
    }
    recorrencia_alterada = bool(campos_recorrencia.intersection(campos))

    if not campos_operacionais:
        raise HTTPException(
            status_code=422, detail="Informe pelo menos um campo para atualizar"
        )

    conta = (
        db.query(ContaPagar)
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada")

    if "descricao" in campos:
        descricao = (payload.descricao or "").strip()
        if not descricao:
            raise HTTPException(status_code=422, detail="Descricao e obrigatoria")
        conta.descricao = descricao

    if "fornecedor_id" in campos:
        if payload.fornecedor_id is None:
            conta.fornecedor_id = None
        else:
            fornecedor = (
                db.query(Cliente)
                .filter(
                    Cliente.id == payload.fornecedor_id,
                    Cliente.tenant_id == tenant_id,
                )
                .first()
            )
            if not fornecedor:
                raise HTTPException(
                    status_code=422, detail="Fornecedor invalido para este tenant"
                )
            conta.fornecedor_id = payload.fornecedor_id

    if "categoria_id" in campos:
        if payload.categoria_id is None:
            conta.categoria_id = None
        else:
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
                    status_code=422,
                    detail="Categoria financeira invalida para este tenant",
                )
            conta.categoria_id = payload.categoria_id

    if "dre_subcategoria_id" in campos:
        if payload.dre_subcategoria_id is None:
            conta.dre_subcategoria_id = None
        else:
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
                    status_code=422, detail="Subcategoria DRE invalida para este tenant"
                )
            conta.dre_subcategoria_id = payload.dre_subcategoria_id

    if "tipo_despesa_id" in campos:
        if payload.tipo_despesa_id is None:
            conta.tipo_despesa_id = None
        else:
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
                    status_code=422, detail="Tipo de despesa invalido para este tenant"
                )
            conta.tipo_despesa_id = payload.tipo_despesa_id

    if "canal" in campos:
        conta.canal = payload.canal

    if "valor_original" in campos:
        if payload.valor_original is None or payload.valor_original <= 0:
            raise HTTPException(
                status_code=422, detail="Valor original deve ser maior que zero"
            )
        conta.valor_original = Decimal(str(payload.valor_original))

    if "data_emissao" in campos:
        if payload.data_emissao is None:
            raise HTTPException(status_code=422, detail="Data de emissao e obrigatoria")
        conta.data_emissao = payload.data_emissao

    if "data_vencimento" in campos:
        if payload.data_vencimento is None:
            raise HTTPException(
                status_code=422, detail="Data de vencimento e obrigatoria"
            )
        conta.data_vencimento = payload.data_vencimento

    if "documento" in campos:
        conta.documento = payload.documento

    if "observacoes" in campos:
        conta.observacoes = payload.observacoes

    if recorrencia_alterada:
        ativar_recorrencia = (
            bool(payload.eh_recorrente)
            if "eh_recorrente" in campos
            else bool(conta.eh_recorrente)
        )

        if not ativar_recorrencia:
            conta.eh_recorrente = False
            conta.tipo_recorrencia = None
            conta.intervalo_dias = None
            conta.data_inicio_recorrencia = None
            conta.data_fim_recorrencia = None
            conta.numero_repeticoes = None
            conta.proxima_recorrencia = None
        else:
            tipo_recorrencia = (
                payload.tipo_recorrencia
                if "tipo_recorrencia" in campos
                else conta.tipo_recorrencia
            ) or "mensal"
            if tipo_recorrencia not in {
                "semanal",
                "quinzenal",
                "mensal",
                "personalizado",
            }:
                raise HTTPException(
                    status_code=422, detail="Tipo de recorrencia invalido"
                )

            intervalo_dias = (
                payload.intervalo_dias
                if "intervalo_dias" in campos
                else conta.intervalo_dias
            )
            if tipo_recorrencia == "personalizado":
                if not intervalo_dias or intervalo_dias < 1:
                    raise HTTPException(
                        status_code=422,
                        detail="Intervalo em dias e obrigatorio para recorrencia personalizada",
                    )
            else:
                intervalo_dias = None

            data_inicio_recorrencia = (
                payload.data_inicio_recorrencia
                if "data_inicio_recorrencia" in campos
                else conta.data_inicio_recorrencia
            ) or conta.data_vencimento
            data_fim_recorrencia = (
                payload.data_fim_recorrencia
                if "data_fim_recorrencia" in campos
                else conta.data_fim_recorrencia
            )
            numero_repeticoes = (
                payload.numero_repeticoes
                if "numero_repeticoes" in campos
                else conta.numero_repeticoes
            )

            if data_fim_recorrencia and data_fim_recorrencia < data_inicio_recorrencia:
                raise HTTPException(
                    status_code=422,
                    detail="Data final da recorrencia deve ser maior ou igual a data inicial",
                )
            if numero_repeticoes is not None and numero_repeticoes < 1:
                raise HTTPException(
                    status_code=422,
                    detail="Numero de repeticoes deve ser maior que zero",
                )

            conta.eh_recorrente = True
            conta.tipo_recorrencia = tipo_recorrencia
            conta.intervalo_dias = intervalo_dias
            conta.data_inicio_recorrencia = data_inicio_recorrencia
            conta.data_fim_recorrencia = data_fim_recorrencia
            conta.numero_repeticoes = numero_repeticoes
            conta.proxima_recorrencia = calcular_proxima_recorrencia(
                conta.data_vencimento,
                conta.tipo_recorrencia,
                conta.intervalo_dias,
            )

    valor_original = conta.valor_original or Decimal("0")
    valor_juros = conta.valor_juros or Decimal("0")
    valor_multa = conta.valor_multa or Decimal("0")
    valor_desconto = conta.valor_desconto or Decimal("0")
    conta.valor_final = valor_original + valor_juros + valor_multa - valor_desconto

    valor_pago = conta.valor_pago or Decimal("0")
    if valor_pago <= 0:
        conta.status = "pendente"
        conta.data_pagamento = None
    elif valor_pago >= conta.valor_final:
        conta.status = "pago"
    else:
        conta.status = "parcial"

    recorrencias_criadas = []
    recorrencias_atualizadas = 0
    deve_garantir_janela_recorrencia = bool(
        conta.eh_recorrente or conta.conta_recorrencia_origem_id
    )
    if deve_garantir_janela_recorrencia:
        db.flush()
        recorrencias_criadas = _garantir_janela_recorrencia_conta(
            db=db,
            tenant_id=tenant_id,
            conta=conta,
        )
        if payload.aplicar_recorrencia_futura:
            recorrencias_atualizadas = _aplicar_edicao_recorrencia_futura(
                db=db,
                tenant_id=tenant_id,
                conta=conta,
                campos=campos,
            )

    db.commit()
    db.refresh(conta)

    return {
        "ok": True,
        "mensagem": "Conta a pagar atualizada com sucesso",
        "conta_id": conta.id,
        "descricao": conta.descricao,
        "fornecedor_id": conta.fornecedor_id,
        "categoria_id": conta.categoria_id,
        "dre_subcategoria_id": conta.dre_subcategoria_id,
        "tipo_despesa_id": conta.tipo_despesa_id,
        "canal": conta.canal,
        "valor_original": float(conta.valor_original),
        "valor_final": float(conta.valor_final),
        "data_emissao": conta.data_emissao,
        "data_vencimento": conta.data_vencimento,
        "documento": conta.documento,
        "observacoes": conta.observacoes,
        "status": conta.status,
        "eh_recorrente": conta.eh_recorrente,
        "tipo_recorrencia": conta.tipo_recorrencia,
        "intervalo_dias": conta.intervalo_dias,
        "data_inicio_recorrencia": conta.data_inicio_recorrencia,
        "data_fim_recorrencia": conta.data_fim_recorrencia,
        "numero_repeticoes": conta.numero_repeticoes,
        "proxima_recorrencia": conta.proxima_recorrencia,
        "recorrencias_criadas": len(recorrencias_criadas),
        "recorrencias_atualizadas": recorrencias_atualizadas,
    }


@router.delete("/{conta_id}")
def excluir_conta_pagar(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exclui uma conta a pagar sem pagamento registrado."""
    _, tenant_id = user_and_tenant

    conta = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.pagamentos))
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada")

    valor_pago = conta.valor_pago or Decimal("0")
    if conta.status == "pago" or valor_pago > 0 or conta.pagamentos:
        raise HTTPException(
            status_code=400,
            detail="Conta com pagamento registrado nao pode ser excluida",
        )

    recorrencias_filhas = (
        db.query(func.count(ContaPagar.id))
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.conta_recorrencia_origem_id == conta.id,
        )
        .scalar()
        or 0
    )
    if recorrencias_filhas:
        raise HTTPException(
            status_code=400,
            detail="Conta recorrente com lancamentos futuros nao pode ser excluida individualmente",
        )

    parcelas_filhas = (
        db.query(func.count(ContaPagar.id))
        .filter(
            ContaPagar.tenant_id == tenant_id,
            ContaPagar.conta_principal_id == conta.id,
        )
        .scalar()
        or 0
    )
    if parcelas_filhas:
        raise HTTPException(
            status_code=400,
            detail="Conta parcelada com parcelas futuras nao pode ser excluida individualmente",
        )

    db.delete(conta)
    db.commit()

    return {
        "ok": True,
        "mensagem": "Conta a pagar excluida com sucesso",
        "conta_id": conta_id,
    }


@router.post("/{conta_id}/estornar")
def estornar_pagamento_conta_pagar(
    conta_id: int,
    payload: ContaPagarOperacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Estorna os pagamentos registrados e reverte a movimentacao bancaria."""
    _, tenant_id = user_and_tenant

    conta = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.pagamentos))
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada")

    valor_pago = conta.valor_pago or Decimal("0")
    if valor_pago <= 0 and not conta.pagamentos:
        raise HTTPException(
            status_code=400,
            detail="Conta nao possui pagamento registrado para estornar",
        )

    movimentacoes = (
        db.query(MovimentacaoFinanceira)
        .filter(
            MovimentacaoFinanceira.tenant_id == tenant_id,
            MovimentacaoFinanceira.origem_tipo == "conta_pagar",
            MovimentacaoFinanceira.origem_id == conta.id,
        )
        .all()
    )

    movimentacoes_estornadas = 0
    for movimentacao in movimentacoes:
        conta_bancaria = (
            db.query(ContaBancaria)
            .filter(
                ContaBancaria.id == movimentacao.conta_bancaria_id,
                ContaBancaria.tenant_id == tenant_id,
            )
            .first()
        )

        if conta_bancaria:
            if movimentacao.tipo == "saida":
                conta_bancaria.saldo_atual += movimentacao.valor
            elif movimentacao.tipo == "entrada":
                conta_bancaria.saldo_atual -= movimentacao.valor

        db.delete(movimentacao)
        movimentacoes_estornadas += 1

    pagamentos_estornados = 0
    for pagamento in list(conta.pagamentos):
        db.delete(pagamento)
        pagamentos_estornados += 1

    conta.valor_pago = Decimal("0.00")
    conta.valor_juros = Decimal("0.00")
    conta.valor_multa = Decimal("0.00")
    conta.valor_desconto = Decimal("0.00")
    conta.valor_final = _decimal_monetario(conta.valor_original)
    conta.data_pagamento = None
    conta.status = "pendente"
    _registrar_observacao_operacao_conta_pagar(
        conta,
        "Pagamento estornado",
        payload.motivo,
    )

    db.commit()

    return {
        "ok": True,
        "mensagem": "Pagamento estornado com sucesso",
        "conta_id": conta.id,
        "pagamentos_estornados": pagamentos_estornados,
        "movimentacoes_estornadas": movimentacoes_estornadas,
    }


@router.post("/{conta_id}/cancelar")
def cancelar_conta_pagar(
    conta_id: int,
    payload: ContaPagarOperacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cancela uma conta a pagar sem apagar o historico do lancamento."""
    _, tenant_id = user_and_tenant

    conta = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.pagamentos))
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada")

    valor_pago = conta.valor_pago or Decimal("0")
    if valor_pago > 0 or conta.pagamentos:
        raise HTTPException(
            status_code=400,
            detail="Estorne o pagamento antes de cancelar o lancamento",
        )

    if conta.status != "cancelado":
        conta.status = "cancelado"
        _registrar_observacao_operacao_conta_pagar(
            conta,
            "Lancamento cancelado",
            payload.motivo,
        )

    db.commit()

    return {
        "ok": True,
        "mensagem": "Conta a pagar cancelada com sucesso",
        "conta_id": conta.id,
    }


@router.get("/{conta_id}")
def buscar_conta_pagar(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Busca uma conta a pagar específica com todos os detalhes
    """
    current_user, tenant_id = user_and_tenant

    conta = (
        db.query(ContaPagar)
        .options(joinedload(ContaPagar.categoria), joinedload(ContaPagar.pagamentos))
        .filter(
            ContaPagar.id == conta_id,
            ContaPagar.tenant_id == tenant_id,
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Buscar fornecedor
    fornecedor = None
    if conta.fornecedor_id:
        fornecedor = (
            db.query(Cliente)
            .filter(
                Cliente.id == conta.fornecedor_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )

    # Buscar nota de entrada se houver
    nota = None
    if conta.nota_entrada_id:
        nota = (
            db.query(NotaEntrada)
            .filter(
                NotaEntrada.id == conta.nota_entrada_id,
                NotaEntrada.tenant_id == tenant_id,
            )
            .first()
        )

    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "fornecedor": {
            "id": fornecedor.id if fornecedor else None,
            "nome": fornecedor.nome if fornecedor else None,
            "cnpj": fornecedor.cnpj if fornecedor else None,
        }
        if fornecedor
        else None,
        "categoria": {
            "id": conta.categoria.id if conta.categoria else None,
            "nome": conta.categoria.nome if conta.categoria else None,
            "cor": conta.categoria.cor if conta.categoria else None,
        }
        if conta.categoria
        else None,
        "categoria_id": conta.categoria_id,
        "dre_subcategoria_id": conta.dre_subcategoria_id,
        "tipo_despesa_id": conta.tipo_despesa_id,
        "canal": conta.canal,
        "valores": {
            "original": float(conta.valor_original),
            "pago": float(conta.valor_pago),
            "desconto": float(conta.valor_desconto),
            "juros": float(conta.valor_juros),
            "multa": float(conta.valor_multa),
            "final": float(conta.valor_final),
            "saldo": float(conta.valor_final - conta.valor_pago),
        },
        "datas": {
            "emissao": conta.data_emissao,
            "vencimento": conta.data_vencimento,
            "pagamento": conta.data_pagamento,
        },
        "status": conta.status,
        "parcelamento": {
            "eh_parcelado": conta.eh_parcelado
            if conta.eh_parcelado is not None
            else False,
            "numero_parcela": conta.numero_parcela,
            "total_parcelas": conta.total_parcelas,
        }
        if conta.eh_parcelado
        else None,
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
        "recorrencia": {
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
        },
        "nota_entrada": {
            "id": nota.id if nota else None,
            "numero": nota.numero_nota if nota else None,
            "chave": nota.chave_acesso if nota else None,
        }
        if nota
        else None,
        "documento": conta.documento,
        "observacoes": conta.observacoes,
        "pagamentos": [
            {
                "id": p.id,
                "valor": float(p.valor_pago),
                "data": p.data_pagamento,
                "forma_pagamento_id": p.forma_pagamento_id,
                "observacoes": p.observacoes,
            }
            for p in conta.pagamentos
        ],
    }


# ============================================================================
