from app.nfe.listagem_base import (
    _FINALIDADE_MAP,
    _INDICADOR_PRESENCA_MAP,
    _REGIME_TRIBUTARIO_MAP,
    _canal_label,
    _canal_slug,
    _coerce_float,
    _coerce_int,
    _dict,
    _extrair_campo_texto,
    _extrair_valor_nota,
    _formatar_data_iso,
    _formatar_endereco,
    _inferir_canal_por_loja_id,
    _inferir_canal_por_numero,
    _label_codigo,
    _list,
    _primeiro_preenchido,
    _separar_data_hora,
    _status_nota_bling,
    _texto,
    _texto_generico_baixo_valor,
    _texto_relacionado,
    _tipo_nota_label,
    _tipo_pessoa_label,
    _venda_usa_nfce,
)
from app.vendas_models import Venda


def _normalizar_resumo_canal(item: dict, venda: Venda | None = None) -> dict:
    loja = _dict(_primeiro_preenchido(item.get("loja"), item.get("lojaVirtual")))
    unidade_negocio = _dict(item.get("unidadeNegocio"))
    marketplace = _dict(item.get("marketplace"))
    info_adicionais = _dict(item.get("informacoesAdicionais"))
    intermediador = _dict(item.get("intermediador"))
    pedido_ref = _dict(
        _primeiro_preenchido(
            item.get("pedido"), item.get("pedidoVenda"), item.get("pedidoCompra")
        )
    )
    loja_nome = _texto_relacionado(loja, fallback_to_id=False)
    unidade_negocio_nome = _texto_relacionado(unidade_negocio, fallback_to_id=False)
    info_complementares = _texto(
        _primeiro_preenchido(
            info_adicionais.get("informacoesComplementares"),
            item.get("informacoesComplementares"),
            item.get("observacao"),
        )
    )
    numero_extraido_texto = _extrair_campo_texto(
        info_complementares,
        r"n[ºo°]?\s*pedido(?:\s*na\s*loja|\s*loja)?\s*:\s*([^\r\n|]+)",
        r"numero\s*loja\s*virtual\s*:\s*([^\r\n|]+)",
    )

    numero_loja_virtual = _texto(
        _primeiro_preenchido(
            item.get("numeroLojaVirtual"),
            item.get("numeroPedidoLoja"),
            item.get("numeroPedido"),
            pedido_ref.get("numeroPedidoLoja"),
            pedido_ref.get("numero"),
            info_adicionais.get("numeroLojaVirtual"),
            info_adicionais.get("numeroPedidoLoja"),
            numero_extraido_texto,
        )
    )
    canal_inferido = _primeiro_preenchido(
        _inferir_canal_por_numero(numero_loja_virtual),
        _inferir_canal_por_loja_id(loja.get("id")),
    )
    canal_inferido_label = _canal_label(canal_inferido)
    origem_loja_virtual = _texto(
        _primeiro_preenchido(
            item.get("origemLojaVirtual"),
            marketplace.get("nome"),
            marketplace.get("descricao"),
            info_adicionais.get("origemLojaVirtual"),
            canal_inferido_label,
            loja_nome,
        )
    )
    if _texto_generico_baixo_valor(origem_loja_virtual) and canal_inferido_label:
        origem_loja_virtual = canal_inferido_label

    origem_canal_venda = _texto(
        _primeiro_preenchido(
            item.get("origemCanalVenda"),
            info_adicionais.get("origemCanalVenda"),
            venda.canal if venda else None,
            canal_inferido_label,
        )
    )
    if _texto_generico_baixo_valor(origem_canal_venda) and canal_inferido_label:
        origem_canal_venda = canal_inferido_label

    canal_base = _primeiro_preenchido(
        origem_canal_venda,
        origem_loja_virtual,
        canal_inferido_label,
        loja_nome,
        venda.canal if venda else None,
    )
    canal = _canal_slug(canal_base)
    canal_label = _canal_label(canal, canal_base)

    return {
        "canal": canal or _texto(venda.canal if venda else None),
        "canal_label": canal_label,
        "loja": {
            "id": loja.get("id"),
            "nome": loja_nome or _texto(venda.loja_origem if venda else None),
        },
        "unidade_negocio": {
            "id": unidade_negocio.get("id"),
            "nome": unidade_negocio_nome,
        },
        "numero_loja_virtual": numero_loja_virtual,
        "origem_loja_virtual": origem_loja_virtual,
        "origem_canal_venda": origem_canal_venda,
        "numero_pedido_loja": numero_loja_virtual,
        "pedido_bling_id_ref": _texto(pedido_ref.get("id")),
        "intermediador": {
            "cnpj": _texto(
                _primeiro_preenchido(
                    intermediador.get("cnpj"), item.get("cnpjIntermediador")
                )
            ),
            "identificacao": _texto(
                _primeiro_preenchido(
                    intermediador.get("identificacao"),
                    intermediador.get("identificacaoIntermediador"),
                    item.get("identificacaoIntermediador"),
                )
            ),
        },
    }


def _normalizar_parcela(item: dict) -> dict:
    parcela = _dict(_primeiro_preenchido(item.get("parcela"), item))
    return {
        "dias": _coerce_int(
            _primeiro_preenchido(parcela.get("dias"), parcela.get("prazo")), 0
        ),
        "data": _texto(
            _primeiro_preenchido(parcela.get("data"), parcela.get("vencimento"))
        ),
        "valor": _coerce_float(
            _primeiro_preenchido(parcela.get("valor"), parcela.get("valorParcela")), 0.0
        ),
        "forma": _texto(
            _primeiro_preenchido(
                parcela.get("forma"),
                parcela.get("formaPagamento"),
                parcela.get("descricaoFormaPagamento"),
            )
        ),
        "observacao": _texto(
            _primeiro_preenchido(parcela.get("observacao"), parcela.get("descricao"))
        ),
    }


def _normalizar_item_nota(item: dict) -> dict:
    produto = _dict(item.get("produto"))
    return {
        "descricao": _texto(
            _primeiro_preenchido(
                item.get("descricao"), item.get("nome"), produto.get("nome")
            )
        ),
        "codigo": _texto(
            _primeiro_preenchido(
                item.get("codigo"),
                item.get("sku"),
                produto.get("codigo"),
                produto.get("id"),
            )
        ),
        "unidade": _texto(
            _primeiro_preenchido(
                item.get("unidade"), item.get("un"), item.get("siglaUnidade")
            )
        ),
        "quantidade": _coerce_float(item.get("quantidade"), 0.0),
        "valor_unitario": _coerce_float(
            _primeiro_preenchido(
                item.get("valor"),
                item.get("valorUnitario"),
                item.get("preco"),
                item.get("precoUnitario"),
            ),
            0.0,
        ),
        "valor_total": _coerce_float(
            _primeiro_preenchido(item.get("total"), item.get("valorTotal")), 0.0
        ),
        "ncm": _texto(
            _primeiro_preenchido(
                item.get("ncm"), item.get("classificacaoFiscal"), produto.get("ncm")
            )
        ),
    }


def _normalizar_detalhe_nota_bling(
    item: dict, modelo: int, venda: Venda | None = None
) -> dict:
    contato = _dict(
        _primeiro_preenchido(
            item.get("contato"), item.get("cliente"), item.get("destinatario")
        )
    )
    contato_endereco = _dict(contato.get("endereco"))
    endereco_entrega = _dict(
        _primeiro_preenchido(item.get("enderecoEntrega"), item.get("entrega"))
    )
    totais = _dict(item.get("totais"))
    transporte = _dict(
        _primeiro_preenchido(item.get("transporte"), item.get("transportador"))
    )
    pagamento = _dict(item.get("pagamento"))
    info_adicionais = _dict(item.get("informacoesAdicionais"))
    intermediador = _dict(item.get("intermediador"))
    resumo_canal = _normalizar_resumo_canal(item, venda=venda)
    pessoas_autorizadas = [
        _texto(
            _primeiro_preenchido(
                autorizada.get("nome"),
                autorizada.get("cpfCnpj"),
                autorizada.get("numeroDocumento"),
                autorizada.get("email"),
            )
        )
        for autorizada in _list(
            _primeiro_preenchido(
                item.get("pessoasAutorizadasAcessarXml"),
                item.get("pessoasAutorizadasXml"),
                item.get("pessoasAutorizadas"),
            )
        )
        if _texto(
            _primeiro_preenchido(
                autorizada.get("nome"),
                autorizada.get("cpfCnpj"),
                autorizada.get("numeroDocumento"),
                autorizada.get("email"),
            )
        )
    ]

    parcelas = [
        _normalizar_parcela(parcela)
        for parcela in _list(
            _primeiro_preenchido(
                pagamento.get("parcelas"),
                item.get("parcelas"),
            )
        )
    ]

    itens = [_normalizar_item_nota(item_nota) for item_nota in _list(item.get("itens"))]

    data_emissao_raw = _primeiro_preenchido(
        item.get("dataEmissao"), item.get("data_emissao")
    )
    data_saida_raw = _primeiro_preenchido(
        item.get("dataSaida"), item.get("dataOperacao"), item.get("data_saida")
    )
    data_emissao, hora_emissao_extra = _separar_data_hora(data_emissao_raw)
    data_saida, hora_saida_extra = _separar_data_hora(data_saida_raw)

    consumidor_final = _primeiro_preenchido(
        item.get("consumidorFinal"),
        contato.get("consumidorFinal"),
    )
    cpf_cnpj = _texto(
        _primeiro_preenchido(
            contato.get("cpf"),
            contato.get("cnpj"),
            contato.get("cpfCnpj"),
            contato.get("numeroDocumento"),
        )
    )

    cliente = {
        "nome": _texto(
            _primeiro_preenchido(
                contato.get("nome"),
                contato.get("descricao"),
                venda.cliente.nome if venda and venda.cliente else None,
            )
        ),
        "tipo_pessoa": _tipo_pessoa_label(
            _primeiro_preenchido(
                contato.get("tipoPessoa"),
                contato.get("tipo"),
                contato.get("tipoDocumento"),
            ),
            cpf_cnpj=cpf_cnpj,
        ),
        "cpf_cnpj": cpf_cnpj,
        "consumidor_final": bool(consumidor_final)
        if consumidor_final is not None
        else None,
        "cep": _texto(
            _primeiro_preenchido(contato.get("cep"), contato_endereco.get("cep"))
        ),
        "uf": _texto(
            _primeiro_preenchido(
                contato.get("uf"),
                contato.get("estado"),
                contato_endereco.get("uf"),
                contato_endereco.get("estado"),
            )
        ),
        "municipio": _texto(
            _primeiro_preenchido(
                contato.get("municipio"),
                contato.get("cidade"),
                contato_endereco.get("municipio"),
                contato_endereco.get("cidade"),
            )
        ),
        "bairro": _texto(
            _primeiro_preenchido(contato.get("bairro"), contato_endereco.get("bairro"))
        ),
        "endereco": _formatar_endereco(
            _primeiro_preenchido(
                contato.get("endereco"), contato.get("logradouro"), contato_endereco
            )
        ),
        "numero": _texto(
            _primeiro_preenchido(contato.get("numero"), contato_endereco.get("numero"))
        ),
        "complemento": _texto(
            _primeiro_preenchido(
                contato.get("complemento"), contato_endereco.get("complemento")
            )
        ),
        "telefone": _texto(
            _primeiro_preenchido(contato.get("telefone"), contato.get("celular"))
        ),
        "email": _texto(contato.get("email")),
        "vendedor": _texto_relacionado(
            _primeiro_preenchido(
                item.get("vendedor"),
                contato.get("vendedor"),
                venda.vendedor.nome if venda and venda.vendedor else None,
            ),
            "nome",
            "descricao",
            "apelido",
        ),
    }

    return {
        "id": str(item.get("id", "")),
        "venda_id": venda.id if venda else None,
        "numero": _texto(item.get("numero")),
        "serie": _texto(item.get("serie")),
        "modelo": int(modelo),
        "tipo": "nfce" if int(modelo) == 65 else "nfe",
        "tipo_label": _tipo_nota_label(modelo),
        "chave": _texto(
            _primeiro_preenchido(item.get("chaveAcesso"), item.get("chave"))
        ),
        "status": _status_nota_bling(item),
        "data_emissao": data_emissao or _formatar_data_iso(data_emissao_raw),
        "hora_emissao": _texto(
            _primeiro_preenchido(
                item.get("horaEmissao"), item.get("hora_emissao"), hora_emissao_extra
            )
        ),
        "data_saida": data_saida or _formatar_data_iso(data_saida_raw),
        "hora_saida": _texto(
            _primeiro_preenchido(
                item.get("horaSaida"),
                item.get("horaOperacao"),
                item.get("hora_saida"),
                hora_saida_extra,
            )
        ),
        "natureza_operacao": _texto(
            _primeiro_preenchido(
                _texto_relacionado(
                    item.get("naturezaOperacao"), "nome", "descricao", "descricaoPadrao"
                ),
                item.get("naturezaOperacaoDescricao"),
            )
        ),
        "codigo_regime_tributario": _texto(
            _primeiro_preenchido(
                _label_codigo(
                    _REGIME_TRIBUTARIO_MAP, item.get("codigoRegimeTributario")
                ),
                _label_codigo(_REGIME_TRIBUTARIO_MAP, item.get("regimeTributario")),
            )
        ),
        "finalidade": _texto(
            _primeiro_preenchido(
                _label_codigo(_FINALIDADE_MAP, item.get("finalidade")),
                item.get("finalidade"),
            )
        ),
        "indicador_presenca": _texto(
            _primeiro_preenchido(
                _label_codigo(_INDICADOR_PRESENCA_MAP, item.get("indicadorPresenca")),
                item.get("indicadorPresenca"),
            )
        ),
        "cliente": cliente,
        "itens": itens,
        "totais": {
            "valor_produtos": _coerce_float(
                _primeiro_preenchido(
                    totais.get("valorProdutos"), item.get("valorProdutos")
                ),
                0.0,
            ),
            "valor_frete": _coerce_float(
                _primeiro_preenchido(totais.get("valorFrete"), item.get("valorFrete")),
                0.0,
            ),
            "valor_seguro": _coerce_float(
                _primeiro_preenchido(
                    totais.get("valorSeguro"), item.get("valorSeguro")
                ),
                0.0,
            ),
            "outras_despesas": _coerce_float(
                _primeiro_preenchido(
                    totais.get("outrasDespesas"), item.get("outrasDespesas")
                ),
                0.0,
            ),
            "valor_desconto": _coerce_float(
                _primeiro_preenchido(
                    totais.get("valorDesconto"), item.get("valorDesconto")
                ),
                0.0,
            ),
            "valor_total": _extrair_valor_nota(item),
        },
        "transporte": {
            "tipo": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(transporte.get("tipo")),
                    _texto_relacionado(transporte.get("modalidade")),
                )
            ),
            "frete_por_conta": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(transporte.get("fretePorConta")),
                    _texto_relacionado(item.get("fretePorConta")),
                )
            ),
        },
        "endereco_entrega": {
            "nome": _texto(
                _primeiro_preenchido(endereco_entrega.get("nome"), contato.get("nome"))
            ),
            "cep": _texto(endereco_entrega.get("cep")),
            "uf": _texto(
                _primeiro_preenchido(
                    endereco_entrega.get("uf"), endereco_entrega.get("estado")
                )
            ),
            "municipio": _texto(
                _primeiro_preenchido(
                    endereco_entrega.get("municipio"), endereco_entrega.get("cidade")
                )
            ),
            "bairro": _texto(endereco_entrega.get("bairro")),
            "endereco": _formatar_endereco(
                _primeiro_preenchido(
                    endereco_entrega.get("endereco"),
                    endereco_entrega.get("logradouro"),
                    endereco_entrega,
                )
            ),
            "numero": _texto(endereco_entrega.get("numero")),
            "complemento": _texto(endereco_entrega.get("complemento")),
        },
        "pagamento": {
            "condicao": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(pagamento.get("condicaoPagamento")),
                    _texto_relacionado(pagamento.get("descricaoCondicaoPagamento")),
                    item.get("condicaoPagamento"),
                )
            ),
            "categoria": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(pagamento.get("categoria")),
                    _texto_relacionado(item.get("categoria")),
                )
            ),
            "parcelas": parcelas,
        },
        "intermediador": {
            "ativo": _texto(
                _primeiro_preenchido(
                    _texto_relacionado(intermediador.get("tipo")),
                    _texto_relacionado(intermediador.get("ativo")),
                )
            ),
            "cnpj": _texto(
                _primeiro_preenchido(
                    intermediador.get("cnpj"),
                    resumo_canal.get("intermediador", {}).get("cnpj"),
                )
            ),
            "identificacao": _texto(
                _primeiro_preenchido(
                    intermediador.get("identificacao"),
                    intermediador.get("identificacaoIntermediador"),
                    resumo_canal.get("intermediador", {}).get("identificacao"),
                )
            ),
        },
        "informacoes_adicionais": {
            "numero_loja_virtual": resumo_canal.get("numero_loja_virtual"),
            "origem_loja_virtual": resumo_canal.get("origem_loja_virtual"),
            "origem_canal_venda": resumo_canal.get("origem_canal_venda"),
            "numero_pedido_loja": resumo_canal.get("numero_pedido_loja"),
            "informacoes_complementares": _texto(
                _primeiro_preenchido(
                    info_adicionais.get("informacoesComplementares"),
                    item.get("informacoesComplementares"),
                )
            ),
            "informacoes_fisco": _texto(
                _primeiro_preenchido(
                    info_adicionais.get("informacoesAdicionaisInteresseFisco"),
                    info_adicionais.get("informacoesInteresseFisco"),
                    item.get("informacoesAdicionaisInteresseFisco"),
                )
            ),
        },
        "pessoas_autorizadas_xml": pessoas_autorizadas,
        "canal": resumo_canal.get("canal"),
        "canal_label": resumo_canal.get("canal_label"),
        "loja": resumo_canal.get("loja"),
        "unidade_negocio": resumo_canal.get("unidade_negocio"),
        "origem": "bling",
    }


def _normalizar_nota_bling(item: dict, modelo: int) -> dict:
    contato = item.get("contato") or {}
    resumo_canal = _normalizar_resumo_canal(item)
    return {
        "id": str(item.get("id", "")),
        "venda_id": None,
        "numero": str(item.get("numero", "")),
        "serie": str(item.get("serie", "")),
        "tipo": "nfce" if modelo == 65 else "nfe",
        "tipo_codigo": 1 if modelo == 65 else 0,
        "modelo": modelo,
        "chave": item.get("chaveAcesso") or "",
        "status": _status_nota_bling(item),
        "data_emissao": item.get("dataEmissao") or item.get("data_emissao"),
        "valor": _extrair_valor_nota(item),
        "cliente": {
            "id": contato.get("id"),
            "nome": contato.get("nome") or contato.get("descricao"),
            "cpf_cnpj": contato.get("cpf")
            or contato.get("cnpj")
            or contato.get("cpfCnpj"),
        },
        "canal": resumo_canal.get("canal"),
        "canal_label": resumo_canal.get("canal_label"),
        "loja": resumo_canal.get("loja"),
        "unidade_negocio": resumo_canal.get("unidade_negocio"),
        "numero_loja_virtual": resumo_canal.get("numero_loja_virtual"),
        "origem_loja_virtual": resumo_canal.get("origem_loja_virtual"),
        "origem_canal_venda": resumo_canal.get("origem_canal_venda"),
        "numero_pedido_loja": resumo_canal.get("numero_pedido_loja"),
        "pedido_bling_id_ref": resumo_canal.get("pedido_bling_id_ref"),
        "origem": "bling",
    }


def _normalizar_nota_venda_local(venda: Venda) -> dict:
    canal_slug = _canal_slug(venda.canal)
    return {
        "id": str(venda.nfe_bling_id),
        "venda_id": venda.id,
        "numero": venda.nfe_numero,
        "serie": venda.nfe_serie,
        "tipo": "nfce" if _venda_usa_nfce(venda) else "nfe",
        "tipo_codigo": 1 if _venda_usa_nfce(venda) else 0,
        "modelo": _coerce_int(venda.nfe_modelo, 65 if _venda_usa_nfce(venda) else 55),
        "chave": venda.nfe_chave,
        "status": venda.nfe_status or "Pendente",
        "data_emissao": venda.nfe_data_emissao.isoformat()
        if venda.nfe_data_emissao
        else None,
        "valor": float(venda.total or 0),
        "cliente": {
            "id": venda.cliente.id if venda.cliente else None,
            "nome": venda.cliente.nome if venda.cliente else None,
            "cpf_cnpj": (venda.cliente.cpf or venda.cliente.cnpj)
            if venda.cliente
            else None,
        },
        "canal": _texto(venda.canal),
        "canal_label": _canal_label(canal_slug, venda.canal),
        "loja": {
            "id": None,
            "nome": _texto(venda.loja_origem),
        },
        "unidade_negocio": {
            "id": None,
            "nome": None,
        },
        "numero_loja_virtual": None,
        "origem_loja_virtual": None,
        "origem_canal_venda": _texto(venda.canal),
        "numero_pedido_loja": _texto(venda.numero_venda),
        "origem": "local",
    }
