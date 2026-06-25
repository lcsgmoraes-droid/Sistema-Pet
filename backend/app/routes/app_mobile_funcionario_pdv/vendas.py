"""Criacao e finalizacao de vendas do PDV mobile."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Cliente, User
from app.routes.ecommerce_auth import _get_current_ecommerce_user

from .auth import _get_funcionario_operacional_or_403
from .beneficios import _calcular_beneficios_funcionario_pdv
from .caixa import _obter_caixa_aberto_funcionario_pdv
from .pagamentos import (
    _normalizar_forma_pagamento_pdv,
    _resolver_forma_pagamento_cartao_funcionario_pdv,
)
from .schemas import (
    FuncionarioPdvFinalizarRequest,
    FuncionarioPdvFinalizarResponse,
    FuncionarioPdvSalvarRequest,
    FuncionarioPdvSalvarResponse,
)

router = APIRouter()


def _criar_payload_venda_funcionario_pdv(
    *,
    dados: FuncionarioPdvSalvarRequest | FuncionarioPdvFinalizarRequest,
    current_user: User,
    funcionario: Cliente,
    tenant_id: str,
    beneficios: dict,
) -> dict:
    return {
        "cliente_id": dados.cliente_id,
        "vendedor_id": current_user.id,
        "funcionario_id": funcionario.id,
        "itens": beneficios["itens_payload"],
        "desconto_valor": beneficios["desconto_cupom"],
        "desconto_percentual": 0,
        "cupom_code": beneficios["cupom_code"],
        "cupom_discount_applied": beneficios["desconto_cupom"],
        "tenant_id": tenant_id,
        "observacoes": dados.observacoes,
        "tem_entrega": False,
        "taxa_entrega": 0,
        "percentual_taxa_loja": 0,
        "percentual_taxa_entregador": 0,
        "canal": "app_funcionario",
    }


@router.post(
    "/funcionario/pdv/vendas/salvar", response_model=FuncionarioPdvSalvarResponse
)
def salvar_venda_funcionario_pdv(
    dados: FuncionarioPdvSalvarRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    from app.vendas import VendaService

    funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    if not dados.itens:
        raise HTTPException(
            status_code=400, detail="Adicione ao menos um item para vender."
        )

    caixa = _obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)
    if not caixa:
        raise HTTPException(
            status_code=400, detail="Abra um caixa no ERP web antes de salvar pelo app."
        )

    beneficios = _calcular_beneficios_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=dados.cliente_id,
        itens=dados.itens,
        cupom_codigo=dados.cupom_codigo,
        cashback_valor=0,
    )

    criar_payload = _criar_payload_venda_funcionario_pdv(
        dados=dados,
        current_user=current_user,
        funcionario=funcionario,
        tenant_id=tenant_id,
        beneficios=beneficios,
    )
    venda_criada = VendaService.criar_venda(
        payload=criar_payload, user_id=current_user.id, db=db
    )
    return {
        "status": "aberta",
        "venda_id": venda_criada["id"],
        "numero_venda": venda_criada.get("numero_venda") or str(venda_criada["id"]),
        "total": float(venda_criada.get("total") or beneficios["total_venda"]),
        "mensagem": "Venda salva em aberto para recebimento no caixa.",
    }


@router.post(
    "/funcionario/pdv/vendas/finalizar", response_model=FuncionarioPdvFinalizarResponse
)
def finalizar_venda_funcionario_pdv(
    dados: FuncionarioPdvFinalizarRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    from app.vendas import VendaService
    from app.vendas.service import processar_comissoes_venda

    funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    if not dados.itens:
        raise HTTPException(
            status_code=400, detail="Adicione ao menos um item para vender."
        )

    caixa = _obter_caixa_aberto_funcionario_pdv(db, tenant_id, current_user)
    if not caixa:
        raise HTTPException(
            status_code=400, detail="Abra um caixa no ERP web antes de vender pelo app."
        )

    beneficios = _calcular_beneficios_funcionario_pdv(
        db,
        tenant_id=tenant_id,
        cliente_id=dados.cliente_id,
        itens=dados.itens,
        cupom_codigo=dados.cupom_codigo,
        cashback_valor=dados.cashback_valor,
    )

    valor_pagamento = round(float(dados.pagamento.valor), 2)
    if abs(valor_pagamento - beneficios["valor_pagamento"]) > 0.01:
        raise HTTPException(
            status_code=400, detail="Valor do pagamento deve fechar o total da venda."
        )

    forma_pagamento = _normalizar_forma_pagamento_pdv(dados.pagamento.forma_pagamento)
    numero_parcelas = max(1, int(dados.pagamento.numero_parcelas or 1))
    forma_pagamento_selecionada = _resolver_forma_pagamento_cartao_funcionario_pdv(
        db, tenant_id, dados.pagamento
    )
    if forma_pagamento != "cartao_credito":
        numero_parcelas = max(1, min(numero_parcelas, 1))
    criar_payload = _criar_payload_venda_funcionario_pdv(
        dados=dados,
        current_user=current_user,
        funcionario=funcionario,
        tenant_id=tenant_id,
        beneficios=beneficios,
    )
    venda_criada = VendaService.criar_venda(
        payload=criar_payload, user_id=current_user.id, db=db
    )

    pagamentos_payload = []
    if valor_pagamento > 0:
        pagamento_payload = {
            "forma_pagamento": forma_pagamento,
            "valor": valor_pagamento,
            "numero_parcelas": numero_parcelas,
            "forma_pagamento_id": dados.pagamento.forma_pagamento_id,
            "bandeira": dados.pagamento.bandeira
            or (
                forma_pagamento_selecionada.bandeira
                if forma_pagamento_selecionada
                else None
            ),
            "operadora": dados.pagamento.operadora
            or (
                forma_pagamento_selecionada.operadora
                if forma_pagamento_selecionada
                else None
            ),
            "nsu_cartao": dados.pagamento.nsu_cartao,
        }
        if dados.pagamento.valor_recebido is not None:
            pagamento_payload["valor_recebido"] = float(dados.pagamento.valor_recebido)
        if dados.pagamento.troco is not None:
            pagamento_payload["troco"] = float(dados.pagamento.troco)
        pagamentos_payload.append(pagamento_payload)

    if beneficios["cashback_valor"] > 0:
        parcelas_cashback = max(1, 1)
        pagamentos_payload.append(
            {
                "forma_pagamento": "Cashback",
                "valor": beneficios["cashback_valor"],
                "numero_parcelas": parcelas_cashback,
            }
        )

    if not pagamentos_payload:
        raise HTTPException(
            status_code=400, detail="Informe uma forma de pagamento valida."
        )

    resultado = VendaService.finalizar_venda(
        venda_id=venda_criada["id"],
        pagamentos=pagamentos_payload,
        user_id=current_user.id,
        user_nome=current_user.nome or current_user.email or "Funcionario",
        tenant_id=tenant_id,
        db=db,
        cupom_code=beneficios["cupom_code"],
        cupom_discount_applied=beneficios["desconto_cupom"],
        caixa_id=caixa.id,
        permitir_caixa_tenant=True,
    )
    processar_comissoes_venda(
        venda_id=venda_criada["id"],
        funcionario_id=funcionario.id,
        valor_pago=beneficios["total_venda"],
        user_id=current_user.id,
        db=db,
    )
    venda_resultado = resultado.get("venda", {})
    return {
        "status": venda_resultado.get("status", "finalizada"),
        "venda_id": venda_criada["id"],
        "numero_venda": venda_resultado.get("numero_venda")
        or venda_criada.get("numero_venda"),
        "total": float(venda_resultado.get("total") or beneficios["total_venda"]),
        "total_pago": float(
            venda_resultado.get("total_pago") or beneficios["total_venda"]
        ),
        "forma_pagamento": " + ".join(p["forma_pagamento"] for p in pagamentos_payload),
        "mensagem": "Venda registrada pelo app.",
    }
