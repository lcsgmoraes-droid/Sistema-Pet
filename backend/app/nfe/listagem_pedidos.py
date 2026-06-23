from sqlalchemy.orm import Session

from app.nfe.listagem_base import (
    _STATUS_MAP,
    _canal_label,
    _canal_slug,
    _coerce_float,
    _coerce_int,
    _dict,
    _extrair_valor_nota,
    _list,
    _parse_data_referencia,
    _primeiro_preenchido,
    _status_local_ultima_nf,
    _texto,
    _texto_relacionado,
)
from app.pedido_integrado_models import PedidoIntegrado


def _identificadores_pedido_integrado(pedido: PedidoIntegrado) -> set[str]:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    ultima_nf = _dict(
        _primeiro_preenchido(
            payload.get("ultima_nf"),
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    identificadores = {
        _texto(pedido.pedido_bling_id),
        _texto(pedido.pedido_bling_numero),
        _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoLoja"),
                pedido_payload.get("numeroLoja"),
                pedido_payload.get("numeroPedido"),
                pedido_payload.get("numero"),
            )
        ),
        _texto(_primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id"))),
        _texto(ultima_nf.get("numero")),
    }
    return {identificador for identificador in identificadores if identificador}


def _extrair_total_pedido_integrado(pedido: PedidoIntegrado) -> float:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    ultima_nf = _dict(
        _primeiro_preenchido(
            payload.get("ultima_nf"),
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    totais = _dict(
        _primeiro_preenchido(
            pedido_payload.get("totais"),
            pedido_payload.get("financeiro"),
            payload.get("totais"),
        )
    )

    valor_total = _extrair_valor_nota(ultima_nf)
    if valor_total > 0:
        return valor_total

    valor_total = _coerce_float(
        _primeiro_preenchido(
            pedido_payload.get("total"),
            pedido_payload.get("valorTotal"),
            pedido_payload.get("valor_total"),
            totais.get("valorTotal"),
            totais.get("total"),
        ),
        0.0,
    )
    if valor_total > 0:
        return valor_total

    itens = _list(
        _primeiro_preenchido(pedido_payload.get("itens"), payload.get("itens"))
    )
    total_itens = 0.0
    encontrou_item = False
    for item in itens:
        item_dict = _dict(_primeiro_preenchido(item.get("item"), item))
        quantidade = _coerce_float(
            _primeiro_preenchido(item_dict.get("quantidade"), item.get("quantidade")),
            0.0,
        )
        total_item = _coerce_float(
            _primeiro_preenchido(
                item_dict.get("total"),
                item_dict.get("valorTotal"),
                item.get("total"),
                item.get("valorTotal"),
            ),
            None,
        )
        if total_item is None:
            valor_unitario = _coerce_float(
                _primeiro_preenchido(
                    item_dict.get("valor"),
                    item_dict.get("preco"),
                    item.get("valor"),
                    item.get("preco"),
                ),
                0.0,
            )
            desconto_item = _coerce_float(
                _primeiro_preenchido(
                    item_dict.get("desconto"),
                    item.get("desconto"),
                    item_dict.get("valorDesconto"),
                    item.get("valorDesconto"),
                ),
                0.0,
            )
            total_item = max((valor_unitario * quantidade) - desconto_item, 0.0)
        if total_item > 0:
            encontrou_item = True
            total_itens += total_item

    if encontrou_item:
        frete = _coerce_float(
            _primeiro_preenchido(
                pedido_payload.get("frete"),
                _dict(pedido_payload.get("transporte")).get("frete"),
                totais.get("valorFrete"),
            ),
            0.0,
        )
        desconto = _coerce_float(
            _primeiro_preenchido(
                pedido_payload.get("desconto"),
                pedido_payload.get("valorDesconto"),
                totais.get("valorDesconto"),
            ),
            0.0,
        )
        return max(total_itens + frete - desconto, 0.0)

    return 0.0


def _resumo_pedido_integrado(pedido: PedidoIntegrado) -> dict:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    loja = _dict(pedido_payload.get("loja"))
    marketplace = _dict(pedido_payload.get("marketplace"))
    loja_nome = _texto_relacionado(loja, fallback_to_id=False)
    canal_base = _primeiro_preenchido(
        pedido_payload.get("canal"),
        pedido_payload.get("origem"),
        marketplace.get("nome"),
        marketplace.get("descricao"),
        loja_nome,
        pedido.canal,
    )
    canal = _canal_slug(canal_base)
    return {
        "canal": canal or _texto(pedido.canal),
        "canal_label": _canal_label(canal, canal_base),
        "valor_total": _extrair_total_pedido_integrado(pedido),
        "loja": {
            "id": loja.get("id"),
            "nome": loja_nome,
        },
        "numero_loja_virtual": _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoLoja"),
                pedido_payload.get("numeroLoja"),
                pedido_payload.get("numeroPedido"),
                pedido_payload.get("numero"),
            )
        ),
        "numero_pedido_loja": _texto(
            _primeiro_preenchido(
                pedido_payload.get("numeroPedidoLoja"),
                pedido_payload.get("numeroLoja"),
                pedido_payload.get("numeroPedido"),
                pedido_payload.get("numero"),
            )
        ),
        "origem_loja_virtual": _texto(
            _primeiro_preenchido(
                pedido_payload.get("origemLojaVirtual"),
                marketplace.get("nome"),
                marketplace.get("descricao"),
                loja_nome,
            )
        ),
        "origem_canal_venda": _texto(
            _primeiro_preenchido(
                pedido_payload.get("origemCanalVenda"),
                marketplace.get("nome"),
                marketplace.get("descricao"),
                _canal_label(canal, canal_base),
            )
        ),
    }


def _normalizar_nota_pedido_integrado(pedido: PedidoIntegrado) -> dict | None:
    payload = _dict(pedido.payload)
    pedido_payload = _dict(_primeiro_preenchido(payload.get("pedido"), payload))
    ultima_nf = _dict(
        _primeiro_preenchido(
            payload.get("ultima_nf"),
            pedido_payload.get("notaFiscal"),
            pedido_payload.get("nota"),
            pedido_payload.get("nfe"),
        )
    )
    resumo = _resumo_pedido_integrado(pedido)
    contato = _dict(
        _primeiro_preenchido(
            pedido_payload.get("contato"), pedido_payload.get("cliente")
        )
    )

    nf_bling_id = _texto(
        _primeiro_preenchido(ultima_nf.get("id"), ultima_nf.get("nfe_id"))
    )
    if nf_bling_id in {"-1", "0"}:
        nf_bling_id = None
    nf_numero = _texto(ultima_nf.get("numero"))

    if not nf_bling_id and not nf_numero:
        return None

    data_emissao = _primeiro_preenchido(
        ultima_nf.get("dataEmissao"),
        ultima_nf.get("data_emissao"),
        ultima_nf.get("dataEmissaoNf"),
        ultima_nf.get("data"),
        pedido.updated_at.isoformat() if getattr(pedido, "updated_at", None) else None,
        pedido.created_at.isoformat() if getattr(pedido, "created_at", None) else None,
    )

    return {
        "id": str(nf_bling_id or ""),
        "venda_id": None,
        "numero": nf_numero,
        "serie": _texto(ultima_nf.get("serie")),
        "tipo": "nfe",
        "tipo_codigo": 0,
        "modelo": 55,
        "chave": _texto(
            _primeiro_preenchido(ultima_nf.get("chave"), ultima_nf.get("chaveAcesso"))
        ),
        "status": _status_local_ultima_nf(ultima_nf),
        "data_emissao": data_emissao,
        "valor": _coerce_float(
            _primeiro_preenchido(
                ultima_nf.get("valor_total"), resumo.get("valor_total")
            ),
            0.0,
        ),
        "cliente": {
            "id": contato.get("id"),
            "nome": _texto_relacionado(contato, fallback_to_id=False),
            "cpf_cnpj": _texto(
                _primeiro_preenchido(
                    contato.get("cpf"), contato.get("cnpj"), contato.get("cpfCnpj")
                )
            ),
        },
        "canal": resumo.get("canal"),
        "canal_label": resumo.get("canal_label"),
        "loja": resumo.get("loja"),
        "unidade_negocio": {"id": None, "nome": None},
        "numero_loja_virtual": resumo.get("numero_loja_virtual"),
        "origem_loja_virtual": resumo.get("origem_loja_virtual"),
        "origem_canal_venda": resumo.get("origem_canal_venda"),
        "numero_pedido_loja": resumo.get("numero_pedido_loja"),
        "pedido_bling_id_ref": _texto(pedido.pedido_bling_id),
        "origem": "pedido_integrado",
    }


def _adicionar_notas_de_pedidos_integrados(
    db: Session,
    tenant_id,
    notas: list[dict],
    *,
    situacao: str | None = None,
    data_inicial: str | None = None,
    data_final: str | None = None,
    limite_scan: int = 3000,
) -> None:
    pedidos = (
        db.query(PedidoIntegrado)
        .filter(PedidoIntegrado.tenant_id == tenant_id)
        .order_by(PedidoIntegrado.updated_at.desc(), PedidoIntegrado.created_at.desc())
        .limit(limite_scan)
        .all()
    )

    data_inicial_ref = _parse_data_referencia(data_inicial)
    data_final_ref = _parse_data_referencia(data_final)
    chaves_existentes = {
        (
            _texto(nota.get("id")) or "",
            _texto(nota.get("numero")) or "",
        )
        for nota in notas
    }

    for pedido in pedidos:
        nota = _normalizar_nota_pedido_integrado(pedido)
        if not nota:
            continue

        chave_nota = (
            _texto(nota.get("id")) or "",
            _texto(nota.get("numero")) or "",
        )
        if chave_nota in chaves_existentes:
            continue

        if situacao and str(nota.get("status") or "").lower() != situacao.lower():
            continue

        data_nota = _parse_data_referencia(nota.get("data_emissao"))
        if (
            data_inicial_ref
            and data_nota
            and data_nota.date() < data_inicial_ref.date()
        ):
            continue
        if data_final_ref and data_nota and data_nota.date() > data_final_ref.date():
            continue

        notas.append(nota)
        chaves_existentes.add(chave_nota)


def _enriquecer_notas_com_pedidos_integrados(
    db: Session, tenant_id, notas: list[dict], limite_scan: int = 3000
) -> None:
    identificadores_desejados: set[str] = set()
    for nota in notas:
        for identificador in (
            _texto(nota.get("pedido_bling_id_ref")),
            _texto(nota.get("numero_pedido_loja")),
            _texto(nota.get("numero_loja_virtual")),
            _texto(nota.get("id")),
            _texto(nota.get("numero")),
        ):
            if identificador:
                identificadores_desejados.add(identificador)

    if not identificadores_desejados:
        return

    pedidos = (
        db.query(PedidoIntegrado)
        .filter(PedidoIntegrado.tenant_id == tenant_id)
        .order_by(PedidoIntegrado.created_at.desc())
        .limit(limite_scan)
        .all()
    )

    mapa_identificadores: dict[str, dict] = {}
    for pedido in pedidos:
        resumo = _resumo_pedido_integrado(pedido)
        for identificador in _identificadores_pedido_integrado(pedido):
            if identificador and identificador not in mapa_identificadores:
                mapa_identificadores[identificador] = resumo

    for nota in notas:
        candidatos = [
            _texto(nota.get("pedido_bling_id_ref")),
            _texto(nota.get("numero_pedido_loja")),
            _texto(nota.get("numero_loja_virtual")),
            _texto(nota.get("id")),
            _texto(nota.get("numero")),
        ]
        contexto = next(
            (
                mapa_identificadores.get(candidato)
                for candidato in candidatos
                if candidato and mapa_identificadores.get(candidato)
            ),
            None,
        )
        if not contexto:
            continue

        nota["canal"] = nota.get("canal") or contexto.get("canal")
        nota["canal_label"] = nota.get("canal_label") or contexto.get("canal_label")
        loja_atual = nota.get("loja") if isinstance(nota.get("loja"), dict) else {}
        if not loja_atual.get("nome"):
            nota["loja"] = contexto.get("loja")
        if not nota.get("valor") and contexto.get("valor_total"):
            nota["valor"] = float(contexto.get("valor_total") or 0)
        nota["numero_loja_virtual"] = nota.get("numero_loja_virtual") or contexto.get(
            "numero_loja_virtual"
        )
        nota["origem_loja_virtual"] = nota.get("origem_loja_virtual") or contexto.get(
            "origem_loja_virtual"
        )
        nota["origem_canal_venda"] = nota.get("origem_canal_venda") or contexto.get(
            "origem_canal_venda"
        )
        nota["numero_pedido_loja"] = nota.get("numero_pedido_loja") or contexto.get(
            "numero_pedido_loja"
        )
