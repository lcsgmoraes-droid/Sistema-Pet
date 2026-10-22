"""Composição comercial comum ao painel, app e conferência do PDV.

Não é rentabilidade nem liquidação bancária: taxas, CMV e comissões não
alteram o valor vendido. Os históricos permanecem intactos.
"""

from decimal import Decimal
import unicodedata

from app.caixa.conferencia import moeda
from app.utils.pagamento_vinculos import pagamento_da_observacao
from app.utils.timezone import as_brasilia_naive
from app.vendas.status_pagamento import pagamento_valido_para_saldo

ZERO = Decimal("0.00")
CAMPOS_VALORES = (
    "faturamento_bruto",
    "descontos",
    "devolucoes",
    "faturamento_liquido",
    "taxa_entrega",
    "total_vendas",
    "valor_pago",
    "creditos_utilizados",
    "crediario_receber",
    "em_aberto",
)


def normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "")).casefold()
    return " ".join(
        "".join(c for c in texto if not unicodedata.combining(c))
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def _forma_pagamento_venda(forma):
    texto = str(forma or "Não informada").strip() or "Não informada"
    # Mesmos aliases de cartão aceitos pelo PDV, sem interpretar IDs como
    # formas universais: os cadastros e seus IDs pertencem a cada tenant.
    aliases = {
        "dinheiro": "Dinheiro",
        "pix": "Pix",
        "debito": "Cartão de débito",
        "cartao debito": "Cartão de débito",
        "cartao de debito": "Cartão de débito",
        "credito": "Cartão de crédito",
        "cartao credito": "Cartão de crédito",
        "cartao de credito": "Cartão de crédito",
        "credito parcelado": "Cartão de crédito",
        "transferencia": "Transferência",
        "transferencia bancaria": "Transferência",
        "link": "Link de pagamento",
        "link pagamento": "Link de pagamento",
        "link de pagamento": "Link de pagamento",
    }
    return aliases.get(normalizar(texto), texto)


def eh_beneficio(forma):
    texto = normalizar(forma)
    return "cashback" in texto or ("credito" in texto and "cliente" in texto)


def eh_plano(pagamento):
    return normalizar(getattr(pagamento, "forma_pagamento", "")) in {
        "crediario",
        "boleto",
    } or bool(getattr(pagamento, "intervalo_crediario", None))


def mesmo_tenant(venda, filho):
    tenant = getattr(venda, "tenant_id", None)
    return tenant is None or str(getattr(filho, "tenant_id", tenant)) == str(tenant)


def data_local(valor):
    if hasattr(valor, "hour"):
        valor = as_brasilia_naive(valor)
    return valor.isoformat() if valor is not None else None


def _contas_planos(venda, pagamentos):
    contas = [
        c
        for c in (getattr(venda, "contas_receber", None) or [])
        if mesmo_tenant(venda, c)
        and normalizar(getattr(c, "status", "")) not in {"cancelada", "cancelado"}
    ]
    planos = [p for p in pagamentos if eh_plano(p)]
    if not (getattr(venda, "pagamentos", None) or []):
        return contas
    formas = {
        p.forma_pagamento_id
        for p in planos
        if getattr(p, "forma_pagamento_id", None) is not None
    }
    if formas:
        return [c for c in contas if getattr(c, "forma_pagamento_id", None) in formas]
    if planos and len(planos) == len(pagamentos):
        return contas
    return []


def _quitacao(venda, total, eventos, recebimentos_por_conta, espelhos):
    historico = [
        p for p in (getattr(venda, "pagamentos", None) or []) if mesmo_tenant(venda, p)
    ]
    pagamentos = [p for p in historico if pagamento_valido_para_saldo(p)]
    ids_historico = {p.id for p in historico if getattr(p, "id", None) is not None}
    dinheiro = sum(
        (
            moeda(p.valor)
            for p in pagamentos
            if not eh_plano(p) and not eh_beneficio(getattr(p, "forma_pagamento", ""))
        ),
        ZERO,
    )
    beneficios = sum(
        (
            moeda(p.valor)
            for p in pagamentos
            if not eh_plano(p) and eh_beneficio(getattr(p, "forma_pagamento", ""))
        ),
        ZERO,
    )
    planos = [p for p in pagamentos if eh_plano(p)]
    total_planos = max(sum((moeda(p.valor) for p in planos), ZERO), ZERO)
    contas = _contas_planos(venda, pagamentos)
    recebido_planos = ZERO
    detalhes_recibos = []
    for conta in contas:
        recibos = recebimentos_por_conta.get(getattr(conta, "id", None), [])
        total_recibos = sum((moeda(r.valor_recebido) for r in recibos), ZERO)
        # O valor agregado é fallback exclusivamente para o saldo legado sem
        # recibo. Uma baixa com recibos não pode aparecer novamente no agregado.
        legado = max(moeda(getattr(conta, "valor_recebido", 0)) - total_recibos, ZERO)
        if (
            pagamento_da_observacao(getattr(conta, "observacoes", None))
            in ids_historico
        ):
            legado = ZERO
        extra = legado
        if legado:
            detalhes_recibos.append(
                {
                    "id": f"conta-{getattr(conta, 'id', '')}",
                    "origem": "conta_legada",
                    "forma_pagamento": "Recebimento legado",
                    "valor": float(legado),
                    "data_pagamento": data_local(
                        getattr(conta, "data_recebimento", None)
                    ),
                    "status": getattr(conta, "status", None),
                    "tipo": "pagamento",
                }
            )
        for recibo in recibos:
            if not mesmo_tenant(venda, recibo):
                continue
            pagamento_id = pagamento_da_observacao(getattr(recibo, "observacoes", None))
            if pagamento_id in ids_historico or getattr(recibo, "id", None) in espelhos:
                continue
            valor = moeda(recibo.valor_recebido)
            forma = getattr(recibo, "forma_pagamento", None)
            if eh_beneficio(getattr(forma, "nome", "")):
                beneficios += valor
            else:
                extra += valor
            detalhes_recibos.append(
                {
                    "id": f"recebimento-{getattr(recibo, 'id', '')}",
                    "origem": "recebimento",
                    "forma_pagamento": getattr(forma, "nome", None)
                    or "Recebimento de parcela",
                    "valor": float(valor),
                    "data_pagamento": data_local(
                        getattr(recibo, "data_recebimento", None)
                    ),
                    "status": "recebido",
                    "tipo": "beneficio"
                    if eh_beneficio(getattr(forma, "nome", ""))
                    else "pagamento",
                }
            )
        dinheiro += extra
        recebido_planos += max(moeda(getattr(conta, "valor_recebido", 0)), ZERO)

    if not historico:
        # Compatibilidade comprovada pelo valor agregado da venda, quando ainda
        # não existia VendaPagamento. Nunca ressuscitar um pagamento inválido.
        legado = moeda(getattr(venda, "valor_recebido", 0))
        if legado > dinheiro:
            detalhes_recibos.append(
                {
                    "id": f"venda-legada-{getattr(venda, 'id', '')}",
                    "origem": "venda_legada",
                    "forma_pagamento": "Quitação legada (valor recebido salvo)",
                    "valor": float(legado - dinheiro),
                    "data_pagamento": None,
                    "status": getattr(venda, "status", None),
                    "tipo": "pagamento",
                }
            )
            dinheiro = legado
        if (
            not contas
            and dinheiro == ZERO
            and normalizar(getattr(venda, "status", ""))
            in {
                "finalizada",
                "pago nf",
                "baixada",
                "paga",
                "finalizada devolucao",
                "finalizada devolucao parcial",
                "devolvida total",
            }
        ):
            dinheiro = moeda(getattr(venda, "total", 0))
            if dinheiro > ZERO:
                detalhes_recibos.append(
                    {
                        "id": f"venda-legada-{getattr(venda, 'id', '')}",
                        "origem": "venda_legada",
                        "forma_pagamento": "Quitação legada pelo status da venda",
                        "valor": float(dinheiro),
                        "data_pagamento": None,
                        "status": getattr(venda, "status", None),
                        "tipo": "pagamento",
                    }
                )

    for evento in eventos:
        resposta = getattr(evento, "resposta", None) or {}
        restituicao = (
            resposta.get("restituicao", {}) if isinstance(resposta, dict) else {}
        )
        beneficios -= moeda(restituicao.get("cashback", 0))
        beneficios -= moeda(restituicao.get("credito_cliente", 0))
    beneficios = min(max(beneficios, ZERO), total)
    dinheiro = min(max(dinheiro, ZERO), max(total - beneficios, ZERO))
    restante = max(total - dinheiro - beneficios, ZERO)
    crediario = min(restante, max(total_planos - recebido_planos, ZERO))
    return {
        "valor_pago": dinheiro,
        "creditos_utilizados": beneficios,
        "crediario_receber": crediario,
        "em_aberto": restante - crediario,
        "pagamentos": [
            {
                "id": getattr(p, "id", None),
                "origem": "pagamento",
                "forma_pagamento": getattr(p, "forma_pagamento", "Não informada"),
                "valor": float(moeda(p.valor)),
                "data_pagamento": data_local(getattr(p, "data_pagamento", None)),
                "status": getattr(p, "status", None),
                "tipo": "crediario"
                if eh_plano(p)
                else "beneficio"
                if eh_beneficio(getattr(p, "forma_pagamento", ""))
                else "pagamento",
            }
            for p in pagamentos
        ]
        + detalhes_recibos,
    }


def _formas_pagamento_vendas(detalhes):
    """Resume a quitação deduplicada de todas as vendas, sem recortar a data do pagamento.

    O histórico preserva valores anteriores às devoluções. Quando não há uma
    contrapartida com forma rastreável, a diferença para a quitação atual fica
    explícita; não distribuir uma devolução entre dinheiro/cartão por suposição.
    """
    por_forma = {}
    total_pago = ZERO
    for venda in detalhes:
        total_pago += moeda(venda["valor_pago"])
        for pagamento in venda["pagamentos"]:
            if pagamento["tipo"] != "pagamento":
                continue
            valor = moeda(pagamento["valor"])
            if valor == ZERO:
                continue
            forma = _forma_pagamento_venda(pagamento["forma_pagamento"])
            chave = normalizar(forma)
            grupo = por_forma.setdefault(
                chave,
                {"forma_pagamento": forma, "total": ZERO, "quantidade": 0},
            )
            grupo["total"] += valor
            grupo["quantidade"] += 1
    total_registrado = sum((grupo["total"] for grupo in por_forma.values()), ZERO)
    return {
        "criterio_formas_pagamento": "quitacao_das_vendas_selecionadas",
        "formas_pagamento": [
            {**grupo, "total": float(grupo["total"])}
            for _chave, grupo in sorted(por_forma.items())
        ],
        "total_formas_pagamento": float(total_registrado),
        "ajustes_formas_pagamento": float(total_pago - total_registrado),
    }


def compor_vendas(
    vendas,
    *,
    data_inicio,
    data_fim,
    devolucoes_por_venda=None,
    recebimentos_por_conta=None,
    recebimentos_espelhados=None,
):
    devolucoes_por_venda = devolucoes_por_venda or {}
    recebimentos_por_conta = recebimentos_por_conta or {}
    espelhos = recebimentos_espelhados or set()
    totais = {campo: ZERO for campo in CAMPOS_VALORES}
    detalhes = []
    avisos = []
    for venda in vendas:
        if normalizar(getattr(venda, "status", "")) in {"cancelada", "cancelado"}:
            continue
        venda_id = getattr(venda, "id", None)
        eventos = devolucoes_por_venda.get(venda_id, [])
        total_original = max(moeda(getattr(venda, "total", 0)), ZERO)
        entrega = min(
            max(moeda(getattr(venda, "taxa_entrega", 0)), ZERO), total_original
        )
        desconto = max(moeda(getattr(venda, "desconto_valor", 0)), ZERO)
        # O total cobrado é a referência salva no pedido; não recalcular preços
        # atuais dos produtos nem subtrair despesas do snapshot de rentabilidade.
        liquido_original = total_original - entrega
        devolucao = min(
            sum((moeda(e.valor_devolvido) for e in eventos), ZERO), liquido_original
        )
        if (
            not eventos
            and normalizar(getattr(venda, "status", "")) == "devolvida total"
        ):
            devolucao = liquido_original
        elif not eventos and "devolucao" in normalizar(getattr(venda, "status", "")):
            avisos.append(
                f"Venda {getattr(venda, 'numero_venda', venda_id)}: devolução antiga sem valor rastreável."
            )
        valores = {
            "faturamento_bruto": liquido_original + desconto,
            "descontos": desconto,
            "devolucoes": devolucao,
            "faturamento_liquido": liquido_original - devolucao,
            "taxa_entrega": entrega,
            "total_vendas": total_original - devolucao,
        }
        quitacao = _quitacao(
            venda, valores["total_vendas"], eventos, recebimentos_por_conta, espelhos
        )
        valores.update(
            {
                campo: quitacao[campo]
                for campo in (
                    "valor_pago",
                    "creditos_utilizados",
                    "crediario_receber",
                    "em_aberto",
                )
            }
        )
        for campo in CAMPOS_VALORES:
            totais[campo] += valores[campo]
        detalhes.append(
            {
                "venda_id": venda_id,
                "numero_venda": getattr(venda, "numero_venda", None),
                "data_venda": data_local(getattr(venda, "data_venda", None)),
                "status": getattr(venda, "status", None),
                **{campo: float(valores[campo]) for campo in CAMPOS_VALORES},
                "pagamentos": quitacao["pagamentos"],
            }
        )
    return {
        "data_inicio": str(data_inicio),
        "data_fim": str(data_fim),
        "escopo": "empresa",
        "quantidade": len(detalhes),
        **{campo: float(valor) for campo, valor in totais.items()},
        **_formas_pagamento_vendas(detalhes),
        "detalhes": sorted(
            detalhes,
            key=lambda v: (v["data_venda"] or "", v["venda_id"] or 0),
            reverse=True,
        ),
        "avisos": list(dict.fromkeys(avisos)),
    }


def compor_recebimentos(eventos, *, data_inicio, data_fim):
    """Entradas positivas menos devoluções/contrapartidas, sem benefícios."""
    por_forma = {}
    total = ZERO
    beneficios = ZERO
    periodo = ZERO
    anteriores = ZERO
    devolucoes = ZERO
    detalhes = []
    detalhes_creditos = []
    for evento in eventos:
        valor = moeda(evento["valor"])
        if normalizar(evento["forma_pagamento"]) in {"crediario", "boleto"}:
            continue
        if eh_beneficio(evento["forma_pagamento"]):
            beneficios += valor
            if valor != ZERO:
                detalhes_creditos.append({**evento, "tipo": "beneficio"})
            continue
        if valor == ZERO:
            continue
        total += valor
        forma = evento["forma_pagamento"]
        grupo = por_forma.setdefault(
            forma, {"quantidade": 0, "total": 0.0, "tipo_contagem": "recebimento"}
        )
        grupo["quantidade"] += 1
        grupo["total"] = float(moeda(grupo["total"]) + valor)
        data_venda = (evento.get("data_venda") or "")[:10]
        if valor < ZERO:
            devolucoes -= valor
        elif str(data_inicio) <= data_venda <= str(data_fim):
            periodo += valor
        else:
            anteriores += valor
        detalhes.append(evento)
    return {
        "data_inicio": str(data_inicio),
        "data_fim": str(data_fim),
        "escopo": "caixa",
        "total_recebido": float(total),
        "vendas_periodo": float(periodo),
        "vendas_anteriores": float(anteriores),
        "devolucoes": float(devolucoes),
        "creditos_utilizados": float(beneficios),
        "por_forma_pagamento": por_forma,
        "detalhes_creditos": detalhes_creditos,
        "detalhes": sorted(
            detalhes,
            key=lambda e: (e.get("data_recebimento") or "", str(e["id"])),
            reverse=True,
        ),
    }
