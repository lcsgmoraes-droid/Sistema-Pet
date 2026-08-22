"""Formas de pagamento aceitas pelo PDV mobile."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.financeiro_models import FormaPagamento
from app.models import User
from app.operadoras_models import OperadoraCartao, OperadoraCartaoTaxa
from app.services.card_fee_service import (
    CardFeeConfigurationError,
    resolve_card_fee,
)
from app.routes.ecommerce_auth import _get_current_ecommerce_user

from .auth import _get_funcionario_operacional_or_403
from .schemas import (
    FuncionarioPdvFormaPagamentoResponse,
    FuncionarioPdvPagamentoRequest,
)

router = APIRouter()


def _normalizar_forma_pagamento_pdv(forma_pagamento: str) -> str:
    forma = (forma_pagamento or "").strip().lower()
    mapa = {
        "dinheiro": "Dinheiro",
        "pix": "PIX",
        "credito": "cartao_credito",
        "cartao_credito": "cartao_credito",
        "cartao de credito": "cartao_credito",
        "debito": "cartao_debito",
        "cartao_debito": "cartao_debito",
        "cartao de debito": "cartao_debito",
        "cashback": "Cashback",
        "crediario": "Crediário",
        "crediário": "Crediário",
    }
    if forma not in mapa:
        raise HTTPException(
            status_code=400, detail="Forma de pagamento invalida para o PDV mobile."
        )
    return mapa[forma]


def _forma_pagamento_key_funcionario_pdv(
    forma_pagamento: FormaPagamento,
) -> Optional[str]:
    texto = f"{forma_pagamento.tipo or ''} {forma_pagamento.nome or ''} {forma_pagamento.tipo_cartao or ''}".lower()
    if "credito" in texto or "crédito" in texto:
        return "credito"
    if "debito" in texto or "débito" in texto:
        return "debito"
    if "pix" in texto:
        return "pix"
    if "dinheiro" in texto:
        return "dinheiro"
    if "crediario" in texto or "crediário" in texto:
        return "crediario"
    return None


def _obter_ou_criar_forma_crediario_funcionario_pdv(
    db: Session, tenant_id: str, current_user: User
) -> FormaPagamento:
    forma = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo.is_(True),
            FormaPagamento.tipo == "crediario",
        )
        .first()
    )
    if forma:
        return forma
    forma = FormaPagamento(
        tenant_id=tenant_id,
        nome="Crediário",
        tipo="crediario",
        prazo_dias=30,
        prazo_recebimento=30,
        gera_contas_receber=True,
        ativo=True,
        permite_parcelamento=False,
        max_parcelas=1,
        parcelas_maximas=1,
        user_id=current_user.id,
    )
    db.add(forma)
    db.flush()
    return forma


def _resolver_forma_pagamento_cartao_funcionario_pdv(
    db: Session,
    tenant_id: str,
    pagamento: FuncionarioPdvPagamentoRequest,
) -> Optional[FormaPagamento]:
    forma_key = (pagamento.forma_pagamento or "").strip().lower()
    if forma_key not in {"credito", "debito", "cartao_credito", "cartao_debito"}:
        return None

    forma_normalizada = "credito" if "credito" in forma_key else "debito"
    query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id,
        FormaPagamento.ativo.is_(True),
    )

    if pagamento.forma_pagamento_id:
        forma = query.filter(FormaPagamento.id == pagamento.forma_pagamento_id).first()
        if not forma:
            raise HTTPException(
                status_code=400, detail="Forma de pagamento do cartao nao encontrada."
            )
        if _forma_pagamento_key_funcionario_pdv(forma) != forma_normalizada:
            raise HTTPException(
                status_code=400,
                detail="Forma de pagamento nao corresponde ao tipo de cartao selecionado.",
            )
    else:
        formas_cartao = [
            forma
            for forma in query.order_by(FormaPagamento.nome.asc()).all()
            if _forma_pagamento_key_funcionario_pdv(forma) == forma_normalizada
        ]
        if len(formas_cartao) != 1:
            raise HTTPException(
                status_code=400, detail="Selecione a bandeira/operadora do cartao."
            )
        forma = formas_cartao[0]

    max_parcelas = max(1, int(forma.parcelas_maximas or forma.max_parcelas or 1))
    if pagamento.operadora_id:
        operadora = (
            db.query(OperadoraCartao)
            .filter(
                OperadoraCartao.id == pagamento.operadora_id,
                OperadoraCartao.tenant_id == tenant_id,
                OperadoraCartao.ativo.is_(True),
            )
            .first()
        )
        if not operadora:
            raise HTTPException(status_code=400, detail="Operadora de cartao invalida.")
        max_parcelas = max(1, int(operadora.max_parcelas or 1))
    numero_parcelas = max(1, int(pagamento.numero_parcelas or 1))
    pode_parcelar = forma_normalizada == "credito" and (
        bool(forma.permite_parcelamento)
        or bool(forma.split_parcelas)
        or bool(pagamento.operadora_id)
    )

    if forma_normalizada == "debito" and numero_parcelas != 1:
        raise HTTPException(
            status_code=400, detail="Cartao de debito deve ser registrado em 1 parcela."
        )
    if forma_normalizada == "credito" and numero_parcelas > 1 and not pode_parcelar:
        raise HTTPException(
            status_code=400, detail="Esta forma de credito nao permite parcelamento."
        )
    if forma_normalizada == "credito" and numero_parcelas > max_parcelas:
        raise HTTPException(
            status_code=400,
            detail=f"Esta forma de credito permite no maximo {max_parcelas}x.",
        )

    if pagamento.operadora_id:
        try:
            resolve_card_fee(
                db,
                tenant_id=tenant_id,
                valor=pagamento.valor,
                forma_pagamento_id=forma.id,
                operadora_id=pagamento.operadora_id,
                bandeira=pagamento.bandeira,
                modalidade=forma_normalizada,
                parcelas=numero_parcelas,
                strict=True,
            )
        except CardFeeConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return forma


@router.get(
    "/funcionario/pdv/formas-pagamento",
    response_model=list[FuncionarioPdvFormaPagamentoResponse],
)
def listar_formas_pagamento_funcionario_pdv(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    formas = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo.is_(True),
        )
        .order_by(FormaPagamento.nome.asc())
        .all()
    )
    operadoras = (
        db.query(OperadoraCartao)
        .filter(
            OperadoraCartao.tenant_id == tenant_id,
            OperadoraCartao.ativo.is_(True),
        )
        .order_by(OperadoraCartao.padrao.desc(), OperadoraCartao.nome.asc())
        .all()
    )
    regras = (
        db.query(OperadoraCartaoTaxa)
        .filter(
            OperadoraCartaoTaxa.tenant_id == tenant_id,
            OperadoraCartaoTaxa.ativo.is_(True),
            OperadoraCartaoTaxa.operadora_id.in_(
                [operadora.id for operadora in operadoras]
            ),
        )
        .all()
    )

    resposta = []
    modalidades_cartao_adicionadas = set()
    for forma in formas:
        key = _forma_pagamento_key_funcionario_pdv(forma)
        if not key:
            continue
        if key in {"credito", "debito"}:
            if key in modalidades_cartao_adicionadas:
                continue
            modalidades_cartao_adicionadas.add(key)
        parcelas_maximas = int(forma.parcelas_maximas or forma.max_parcelas or 1)
        max_parcelas = int(forma.max_parcelas or parcelas_maximas or 1)
        numero_parcelas = max(1, parcelas_maximas, max_parcelas)
        permite_parcelamento = key == "credito" and (
            bool(forma.permite_parcelamento) or bool(forma.split_parcelas)
        )
        resposta_base = {
            "id": forma.id,
            "selection_id": f"forma:{forma.id}",
            "nome": forma.nome,
            "tipo": forma.tipo,
            "key": key,
            "taxa_percentual": float(forma.taxa_percentual or 0),
            "permite_parcelamento": permite_parcelamento,
            "numero_parcelas": numero_parcelas if permite_parcelamento else 1,
            "max_parcelas": numero_parcelas if permite_parcelamento else 1,
            "parcelas_maximas": numero_parcelas if permite_parcelamento else 1,
            "operadora": forma.operadora,
            "operadora_id": None,
            "requer_nsu": bool(forma.requer_nsu),
            "tipo_cartao": forma.tipo_cartao,
            "bandeira": forma.bandeira,
            "split_parcelas": bool(forma.split_parcelas),
            "parcelas_disponiveis": list(range(1, numero_parcelas + 1))
            if permite_parcelamento
            else [1],
        }

        if key not in {"credito", "debito"}:
            resposta.append(resposta_base)
            continue

        opcoes_estruturadas = []
        for operadora in operadoras:
            regras_modalidade = [
                regra
                for regra in regras
                if regra.operadora_id == operadora.id and regra.modalidade == key
            ]
            bandeiras = sorted(
                {
                    regra.bandeira
                    for regra in regras_modalidade
                    if regra.bandeira != "outros"
                },
                key=lambda bandeira: (
                    bandeira != operadora.bandeira_padrao,
                    bandeira,
                ),
            )
            if not bandeiras and any(
                regra.bandeira == "outros" for regra in regras_modalidade
            ):
                bandeiras = ["outros"]

            for bandeira in bandeiras:
                regras_bandeira = [
                    regra
                    for regra in regras_modalidade
                    if regra.bandeira in {bandeira, "outros"}
                ]
                parcelas = sorted({int(regra.parcelas) for regra in regras_bandeira})
                if key == "debito":
                    parcelas = [1] if 1 in parcelas else []
                if not parcelas:
                    continue
                regra_1x = next(
                    (
                        regra
                        for regra in regras_bandeira
                        if regra.bandeira == bandeira and regra.parcelas == 1
                    ),
                    next(
                        (regra for regra in regras_bandeira if regra.parcelas == 1),
                        regras_bandeira[0],
                    ),
                )
                opcoes_estruturadas.append(
                    {
                        **resposta_base,
                        "selection_id": (
                            f"forma:{forma.id}:operadora:{operadora.id}:bandeira:{bandeira}"
                        ),
                        "taxa_percentual": float(regra_1x.taxa_percentual or 0),
                        "numero_parcelas": max(parcelas),
                        "max_parcelas": max(parcelas),
                        "parcelas_maximas": max(parcelas),
                        "permite_parcelamento": key == "credito"
                        and any(parcela > 1 for parcela in parcelas),
                        "operadora": operadora.nome,
                        "operadora_id": operadora.id,
                        "bandeira": bandeira,
                        "parcelas_disponiveis": parcelas,
                    }
                )

        if opcoes_estruturadas:
            resposta.extend(opcoes_estruturadas)
        elif not regras:
            resposta.append(resposta_base)
    if not any(item["key"] == "crediario" for item in resposta):
        resposta.append(
            {
                "id": 0,
                "selection_id": "builtin:crediario",
                "nome": "Crediário",
                "tipo": "crediario",
                "key": "crediario",
                "taxa_percentual": 0,
                "permite_parcelamento": False,
                "numero_parcelas": 1,
                "max_parcelas": 1,
                "parcelas_maximas": 1,
                "operadora": None,
                "operadora_id": None,
                "requer_nsu": False,
                "tipo_cartao": None,
                "bandeira": None,
                "split_parcelas": False,
                "parcelas_disponiveis": [1],
            }
        )
    return resposta
