"""Montagem do payload JSON do relatorio de vendas."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from .relatorio_vendas_common import (
    _as_float,
    _enriquecer_itens_promocionais,
    _normalizar_canal_venda_relatorio,
    _precisa_reclassificar_campanha,
    _total_recebido_venda,
    _valor_cupom_venda,
    _valores_operacionais_venda,
    _venda_tem_documento_fiscal,
)
from .relatorio_vendas_preloads import (
    carregar_contexto_relatorio_vendas,
    carregar_vendas_relatorio,
    montar_agregados_operacionais_relatorio,
)
from .services.venda_rentabilidade_snapshot_service import (
    get_or_build_venda_rentabilidade_snapshot,
)


def montar_relatorio_vendas(
    *,
    data_inicio: Optional[str],
    data_fim: Optional[str],
    canal_venda: Optional[str],
    db: Session,
    tenant_id,
) -> dict:
    # Definir datas padrão (hoje)
    if not data_inicio:
        data_inicio = date.today().isoformat()
    if not data_fim:
        data_fim = date.today().isoformat()

    # Converter strings para datetime naive (datas no banco são naive em horário de Brasília)
    data_inicio_dt = datetime.fromisoformat(data_inicio)
    data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0)
    data_fim_dt = datetime.fromisoformat(data_fim)
    data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
    canal_normalizado = _normalizar_canal_venda_relatorio(canal_venda)

    vendas = carregar_vendas_relatorio(
        db=db,
        tenant_id=tenant_id,
        data_inicio_dt=data_inicio_dt,
        data_fim_dt=data_fim_dt,
        canal_normalizado=canal_normalizado,
    )
    contexto_relatorio = carregar_contexto_relatorio_vendas(
        db=db,
        tenant_id=tenant_id,
        vendas=vendas,
    )
    impostos_percentual_global = contexto_relatorio["impostos_percentual_global"]
    comissoes_map = contexto_relatorio["comissoes_map"]
    comissao_total_por_venda = contexto_relatorio["comissao_total_por_venda"]
    formas_pagamento_map = contexto_relatorio["formas_pagamento_map"]
    cashback_por_venda = contexto_relatorio["cashback_por_venda"]
    cupons_por_venda = contexto_relatorio["cupons_por_venda"]
    entregadores_map = contexto_relatorio["entregadores_map"]
    estoque_custos_por_venda = contexto_relatorio["estoque_custos_por_venda"]

    agregados_operacionais = montar_agregados_operacionais_relatorio(vendas)
    valores_operacionais_por_venda = agregados_operacionais["valores_operacionais_por_venda"]
    resumo = agregados_operacionais["resumo"]
    vendas_por_data_lista = agregados_operacionais["vendas_por_data_lista"]
    formas_recebimento_lista = agregados_operacionais["formas_recebimento_lista"]
    vendas_por_funcionario_lista = agregados_operacionais["vendas_por_funcionario_lista"]
    vendas_por_tipo_lista = agregados_operacionais["vendas_por_tipo_lista"]

    # ==============================================
    # VENDAS POR GRUPO DE PRODUTO
    # ==============================================
    vendas_por_grupo = {}
    total_geral = sum(
        v["valor_liquido"] for v in valores_operacionais_por_venda.values()
    )

    for venda in vendas:
        valores_venda = valores_operacionais_por_venda.get(
            venda.id
        ) or _valores_operacionais_venda(venda)
        bruto_venda = valores_venda["valor_bruto"]
        desconto_venda = valores_venda["desconto"]
        # OTIMIZAÇÃO: usar itens já carregados
        for item in venda.itens:
            # OTIMIZAÇÃO: usar relacionamento produto já carregado
            produto = item.produto
            if produto and produto.categoria:
                grupo = (
                    produto.categoria.nome
                    if hasattr(produto.categoria, "nome")
                    else str(produto.categoria)
                )
            else:
                grupo = "Sem categoria"

            if grupo not in vendas_por_grupo:
                vendas_por_grupo[grupo] = {
                    "grupo": grupo,
                    "valor_bruto": 0,
                    "desconto": 0,
                    "valor_liquido": 0,
                    "percentual": 0,
                }

            valor_item = _as_float(getattr(item, "quantidade", 0)) * _as_float(
                getattr(item, "preco_unitario", 0)
            )
            desconto_item = (
                (valor_item * desconto_venda / bruto_venda) if bruto_venda > 0 else 0
            )

            vendas_por_grupo[grupo]["valor_bruto"] += valor_item
            vendas_por_grupo[grupo]["desconto"] += desconto_item
            vendas_por_grupo[grupo]["valor_liquido"] += valor_item - desconto_item

    # Calcular percentuais
    for grupo in vendas_por_grupo:
        vendas_por_grupo[grupo]["percentual"] = round(
            (vendas_por_grupo[grupo]["valor_liquido"] / total_geral * 100)
            if total_geral > 0
            else 0,
            1,
        )

    vendas_por_grupo_lista = sorted(
        vendas_por_grupo.values(), key=lambda x: x["valor_liquido"], reverse=True
    )

    # ==============================================
    # PRODUTOS DETALHADOS AGRUPADOS POR CATEGORIA/SUBCATEGORIA
    # ==============================================
    produtos_por_categoria = {}

    for venda in vendas:
        valores_venda = valores_operacionais_por_venda.get(
            venda.id
        ) or _valores_operacionais_venda(venda)
        bruto_venda = valores_venda["valor_bruto"]
        desconto_venda = valores_venda["desconto"]
        # OTIMIZAÇÃO: usar itens já carregados
        for item in venda.itens:
            produto_id = item.produto_id
            # OTIMIZAÇÃO: usar relacionamento produto já carregado
            produto = item.produto

            # Determinar categoria e subcategoria
            if produto and produto.categoria:
                categoria_nome = (
                    produto.categoria.nome
                    if hasattr(produto.categoria, "nome")
                    else str(produto.categoria)
                )
            else:
                categoria_nome = "Sem categoria"

            subcategoria_nome = (
                produto.subcategoria
                if produto and hasattr(produto, "subcategoria") and produto.subcategoria
                else None
            )
            produto_nome = (
                f"{produto.nome} ({produto.id})"
                if produto
                else f"Produto ID {produto_id}"
            )

            # Criar estrutura hierárquica
            if categoria_nome not in produtos_por_categoria:
                produtos_por_categoria[categoria_nome] = {
                    "categoria": categoria_nome,
                    "subcategorias": {},
                    "produtos": {},
                    "total_quantidade": 0,
                    "total_bruto": 0,
                    "total_desconto": 0,
                    "total_liquido": 0,
                }

            # Se tem subcategoria, organizar em subcategoria
            if subcategoria_nome:
                if (
                    subcategoria_nome
                    not in produtos_por_categoria[categoria_nome]["subcategorias"]
                ):
                    produtos_por_categoria[categoria_nome]["subcategorias"][
                        subcategoria_nome
                    ] = {
                        "subcategoria": subcategoria_nome,
                        "produtos": {},
                        "total_quantidade": 0,
                        "total_bruto": 0,
                        "total_desconto": 0,
                        "total_liquido": 0,
                    }

                if (
                    produto_nome
                    not in produtos_por_categoria[categoria_nome]["subcategorias"][
                        subcategoria_nome
                    ]["produtos"]
                ):
                    produtos_por_categoria[categoria_nome]["subcategorias"][
                        subcategoria_nome
                    ]["produtos"][produto_nome] = {
                        "produto": produto_nome,
                        "quantidade": 0,
                        "valor_bruto": 0,
                        "desconto": 0,
                        "valor_liquido": 0,
                    }

                valor_item = _as_float(getattr(item, "quantidade", 0)) * _as_float(
                    getattr(item, "preco_unitario", 0)
                )
                desconto_item = (
                    (valor_item * desconto_venda / bruto_venda)
                    if bruto_venda > 0
                    else 0
                )

                # Atualizar produto
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["produtos"][produto_nome]["quantidade"] += item.quantidade
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["produtos"][produto_nome]["valor_bruto"] += valor_item
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["produtos"][produto_nome]["desconto"] += desconto_item
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["produtos"][produto_nome]["valor_liquido"] += (
                    valor_item - desconto_item
                )

                # Atualizar subcategoria
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["total_quantidade"] += item.quantidade
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["total_bruto"] += valor_item
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["total_desconto"] += desconto_item
                produtos_por_categoria[categoria_nome]["subcategorias"][
                    subcategoria_nome
                ]["total_liquido"] += valor_item - desconto_item
            else:
                # Produto direto na categoria (sem subcategoria)
                if (
                    produto_nome
                    not in produtos_por_categoria[categoria_nome]["produtos"]
                ):
                    produtos_por_categoria[categoria_nome]["produtos"][produto_nome] = {
                        "produto": produto_nome,
                        "quantidade": 0,
                        "valor_bruto": 0,
                        "desconto": 0,
                        "valor_liquido": 0,
                    }

                valor_item = _as_float(getattr(item, "quantidade", 0)) * _as_float(
                    getattr(item, "preco_unitario", 0)
                )
                desconto_item = (
                    (valor_item * desconto_venda / bruto_venda)
                    if bruto_venda > 0
                    else 0
                )

                produtos_por_categoria[categoria_nome]["produtos"][produto_nome][
                    "quantidade"
                ] += item.quantidade
                produtos_por_categoria[categoria_nome]["produtos"][produto_nome][
                    "valor_bruto"
                ] += valor_item
                produtos_por_categoria[categoria_nome]["produtos"][produto_nome][
                    "desconto"
                ] += desconto_item
                produtos_por_categoria[categoria_nome]["produtos"][produto_nome][
                    "valor_liquido"
                ] += valor_item - desconto_item

            # Atualizar totais da categoria
            valor_item = _as_float(getattr(item, "quantidade", 0)) * _as_float(
                getattr(item, "preco_unitario", 0)
            )
            desconto_item = (
                (valor_item * desconto_venda / bruto_venda) if bruto_venda > 0 else 0
            )
            produtos_por_categoria[categoria_nome]["total_quantidade"] += (
                item.quantidade
            )
            produtos_por_categoria[categoria_nome]["total_bruto"] += valor_item
            produtos_por_categoria[categoria_nome]["total_desconto"] += desconto_item
            produtos_por_categoria[categoria_nome]["total_liquido"] += (
                valor_item - desconto_item
            )

    # Converter para lista e ordenar
    produtos_detalhados_lista = []
    for cat_nome, cat_data in sorted(
        produtos_por_categoria.items(),
        key=lambda x: x[1]["total_liquido"],
        reverse=True,
    ):
        categoria_obj = {
            "categoria": cat_nome,
            "total_quantidade": cat_data["total_quantidade"],
            "total_bruto": round(cat_data["total_bruto"], 2),
            "total_desconto": round(cat_data["total_desconto"], 2),
            "total_liquido": round(cat_data["total_liquido"], 2),
            "subcategorias": [],
            "produtos": [],
        }

        # Adicionar subcategorias
        for subcat_nome, subcat_data in sorted(
            cat_data["subcategorias"].items(),
            key=lambda x: x[1]["total_liquido"],
            reverse=True,
        ):
            subcat_obj = {
                "subcategoria": subcat_nome,
                "total_quantidade": subcat_data["total_quantidade"],
                "total_bruto": round(subcat_data["total_bruto"], 2),
                "total_desconto": round(subcat_data["total_desconto"], 2),
                "total_liquido": round(subcat_data["total_liquido"], 2),
                "produtos": [],
            }

            # Produtos da subcategoria
            for prod in sorted(
                subcat_data["produtos"].values(),
                key=lambda x: x["valor_liquido"],
                reverse=True,
            ):
                subcat_obj["produtos"].append(
                    {
                        "produto": prod["produto"],
                        "quantidade": prod["quantidade"],
                        "valor_bruto": round(prod["valor_bruto"], 2),
                        "desconto": round(prod["desconto"], 2),
                        "valor_liquido": round(prod["valor_liquido"], 2),
                    }
                )

            categoria_obj["subcategorias"].append(subcat_obj)

        # Produtos diretos da categoria (sem subcategoria)
        for prod in sorted(
            cat_data["produtos"].values(),
            key=lambda x: x["valor_liquido"],
            reverse=True,
        ):
            categoria_obj["produtos"].append(
                {
                    "produto": prod["produto"],
                    "quantidade": prod["quantidade"],
                    "valor_bruto": round(prod["valor_bruto"], 2),
                    "desconto": round(prod["desconto"], 2),
                    "valor_liquido": round(prod["valor_liquido"], 2),
                }
            )

        produtos_detalhados_lista.append(categoria_obj)

    # ==============================================
    # LISTA DE VENDAS COM ANÁLISE DE RENTABILIDADE
    # ==============================================
    lista_vendas = []
    custo_total_geral = 0
    taxa_total_geral = 0
    taxa_loja_total_geral = 0
    taxa_entrega_repasse_total_geral = 0
    taxa_operacional_total_geral = 0
    comissao_total_geral = 0
    imposto_total_geral = 0
    custo_campanha_total_geral = 0
    lucro_total_geral = 0
    venda_liquida_geral = 0
    venda_bruta_snapshot_geral = 0
    desconto_snapshot_geral = 0
    valor_recebido_geral = 0

    for venda in vendas:
        valor_recebido_venda = _total_recebido_venda(venda)
        valor_recebido_geral += valor_recebido_venda
        cupom_desconto = _valor_cupom_venda(venda, cupons_por_venda)
        custo_campanha_venda = round(
            float(cashback_por_venda.get(venda.id, 0.0) or 0.0) + cupom_desconto,
            2,
        )
        snapshot = get_or_build_venda_rentabilidade_snapshot(
            venda,
            db,
            tenant_id,
            persist_if_missing=True,
            force_refresh=_precisa_reclassificar_campanha(
                venda,
                custo_campanha_venda,
                cupom_desconto,
            ),
            impostos_percentual=impostos_percentual_global,
            formas_pagamento_map=formas_pagamento_map,
            custo_campanha=custo_campanha_venda,
            cupom_desconto=cupom_desconto,
            comissao_total=comissao_total_por_venda.get(venda.id, 0.0),
            taxa_operacional_entrega=(
                entregadores_map.get(venda.entregador_id, 0.0)
                if venda.tem_entrega
                else None
            ),
            estoque_custos_por_produto=estoque_custos_por_venda.get(venda.id, {}),
        )

        venda_bruta_snapshot_geral += float(snapshot.get("venda_bruta", 0) or 0)
        desconto_snapshot_geral += float(snapshot.get("desconto", 0) or 0)
        custo_total_geral += float(snapshot.get("custo_produtos", 0) or 0)
        taxa_total_geral += float(snapshot.get("taxa_cartao", 0) or 0)
        taxa_loja_total_geral += float(snapshot.get("taxa_loja", 0) or 0)
        taxa_entrega_repasse_total_geral += float(snapshot.get("taxa_entrega", 0) or 0)
        taxa_operacional_total_geral += float(snapshot.get("taxa_operacional", 0) or 0)
        comissao_total_geral += float(snapshot.get("comissao", 0) or 0)
        imposto_total_geral += float(snapshot.get("imposto", 0) or 0)
        custo_campanha_total_geral += float(snapshot.get("custo_campanha", 0) or 0)
        lucro_total_geral += float(snapshot.get("lucro", 0) or 0)
        venda_liquida_geral += float(snapshot.get("venda_liquida", 0) or 0)
        itens_enriquecidos = _enriquecer_itens_promocionais(
            venda,
            list(snapshot.get("itens", []) or []),
        )
        itens_promocionais = [
            item for item in itens_enriquecidos if item.get("em_promocao")
        ]
        origens_promocao = sorted(
            {
                origem.strip()
                for item in itens_promocionais
                for origem in str(item.get("promocao_origem") or "").split(",")
                if origem.strip()
            }
        )

        lista_vendas.append(
            {
                "id": venda.id,
                "numero_venda": venda.numero_venda,
                "data_venda": venda.data_venda.isoformat(),
                "cliente_nome": venda.cliente.nome if venda.cliente else "Sem cliente",
                "nf_emitida": _venda_tem_documento_fiscal(venda),
                "nfe_tipo": venda.nfe_tipo,
                "nfe_status": venda.nfe_status,
                "nfe_numero": venda.nfe_numero,
                "nfe_chave": venda.nfe_chave,
                "nfe_bling_id": str(venda.nfe_bling_id) if venda.nfe_bling_id else None,
                "cupom_code": snapshot.get("cupom_code") or venda.cupom_code,
                "cupom_discount_applied": round(
                    float(snapshot.get("cupom_desconto", cupom_desconto) or 0),
                    2,
                ),
                "venda_bruta": round(float(snapshot.get("venda_bruta", 0) or 0), 2),
                "taxa_loja": round(float(snapshot.get("taxa_loja", 0) or 0), 2),
                "desconto": round(float(snapshot.get("desconto", 0) or 0), 2),
                "taxa_entrega": round(float(snapshot.get("taxa_entrega", 0) or 0), 2),
                "taxa_cartao": round(float(snapshot.get("taxa_cartao", 0) or 0), 2),
                "comissao": round(float(snapshot.get("comissao", 0) or 0), 2),
                "imposto": round(float(snapshot.get("imposto", 0) or 0), 2),
                "taxa_operacional": round(
                    float(snapshot.get("taxa_operacional", 0) or 0), 2
                ),
                "custo_produtos": round(
                    float(snapshot.get("custo_produtos", 0) or 0), 2
                ),
                "custo_campanha": round(
                    float(snapshot.get("custo_campanha", 0) or 0), 2
                ),
                "venda_liquida": round(float(snapshot.get("venda_liquida", 0) or 0), 2),
                "valor_recebido": round(valor_recebido_venda, 2),
                "lucro": round(float(snapshot.get("lucro", 0) or 0), 2),
                "margem_sobre_venda": round(
                    float(snapshot.get("margem_sobre_venda", 0) or 0), 1
                ),
                "margem_sobre_custo": round(
                    float(snapshot.get("margem_sobre_custo", 0) or 0), 1
                ),
                "canal": getattr(venda, "canal", None),
                "loja_origem": getattr(venda, "loja_origem", None),
                "gateway_provider": snapshot.get("gateway_provider"),
                "gateway_payment_ids": snapshot.get("gateway_payment_ids") or [],
                "taxa_gateway": (
                    round(float(snapshot.get("taxa_gateway") or 0), 2)
                    if snapshot.get("taxa_gateway") is not None
                    else None
                ),
                "valor_liquido_gateway": (
                    round(float(snapshot.get("valor_liquido_gateway") or 0), 2)
                    if snapshot.get("valor_liquido_gateway") is not None
                    else None
                ),
                "valor_bruto_gateway": (
                    round(float(snapshot.get("valor_bruto_gateway") or 0), 2)
                    if snapshot.get("valor_bruto_gateway") is not None
                    else None
                ),
                "status": venda.status,
                "tem_promocao": bool(itens_promocionais),
                "itens_promocionais": len(itens_promocionais),
                "valor_promocional": round(
                    sum(
                        float(item.get("valor_promocional", 0) or 0)
                        for item in itens_promocionais
                    ),
                    2,
                ),
                "origens_promocao": origens_promocao,
                "itens": itens_enriquecidos,
            }
        )

    lista_vendas = sorted(lista_vendas, key=lambda x: x["data_venda"], reverse=True)

    # Adicionar análise de rentabilidade ao resumo
    resumo["venda_bruta"] = round(venda_bruta_snapshot_geral, 2)
    resumo["desconto"] = round(desconto_snapshot_geral, 2)
    resumo["percentual_desconto"] = round(
        (desconto_snapshot_geral / venda_bruta_snapshot_geral * 100)
        if venda_bruta_snapshot_geral > 0
        else 0,
        1,
    )
    resumo["custo_total"] = round(custo_total_geral, 2)
    resumo["taxa_loja_total"] = round(taxa_loja_total_geral, 2)
    resumo["taxa_entrega_repasse_total"] = round(taxa_entrega_repasse_total_geral, 2)
    resumo["taxa_operacional_total"] = round(taxa_operacional_total_geral, 2)
    resumo["taxa_cartao_total"] = round(taxa_total_geral, 2)
    resumo["comissao_total"] = round(comissao_total_geral, 2)
    resumo["imposto_total"] = round(imposto_total_geral, 2)
    resumo["custo_campanha_total"] = round(custo_campanha_total_geral, 2)
    resumo["lucro_total"] = round(lucro_total_geral, 2)
    resumo["venda_liquida"] = round(venda_liquida_geral, 2)
    resumo["valor_recebido"] = round(valor_recebido_geral, 2)
    resumo["margem_media"] = round(
        (lucro_total_geral / venda_liquida_geral * 100)
        if venda_liquida_geral > 0
        else 0,
        1,
    )

    # ==============================================
    # PRODUTOS PARA ANÁLISE INTELIGENTE (flat list)
    # ==============================================
    produtos_analise = {}
    vendas_por_id = {venda.id: venda for venda in vendas}
    for venda_snapshot in lista_vendas:
        venda_obj = vendas_por_id.get(venda_snapshot["id"])
        produtos_relacao = {
            item.produto_id: item.produto
            for item in list(getattr(venda_obj, "itens", []) or [])
            if getattr(item, "produto", None)
        }

        for item_snapshot in venda_snapshot["itens"]:
            produto_rel = produtos_relacao.get(item_snapshot.get("produto_id"))
            prod_nome = item_snapshot.get("produto_nome") or "Produto removido"
            if prod_nome not in produtos_analise:
                produtos_analise[prod_nome] = {
                    "nome": prod_nome,
                    "produto": prod_nome,
                    "marca": produto_rel.marca.nome
                    if produto_rel and produto_rel.marca
                    else None,
                    "categoria": produto_rel.categoria.nome
                    if produto_rel and produto_rel.categoria
                    else None,
                    "quantidade": 0,
                    "valor_total": 0,
                    "custo_total": 0,
                }

            produtos_analise[prod_nome]["quantidade"] += float(
                item_snapshot.get("quantidade", 0) or 0
            )
            produtos_analise[prod_nome]["valor_total"] += float(
                item_snapshot.get("venda_bruta", 0) or 0
            )
            produtos_analise[prod_nome]["custo_total"] += float(
                item_snapshot.get("custo_total", 0) or 0
            )
    # Converter para lista e ordenar por valor
    produtos_analise_lista = sorted(
        list(produtos_analise.values()), key=lambda x: x["valor_total"], reverse=True
    )

    # ==============================================
    # RETORNO COMPLETO
    # ==============================================
    return {
        "resumo": resumo,
        "vendas_por_data": vendas_por_data_lista,
        "formas_recebimento": formas_recebimento_lista,
        "vendas_por_funcionario": vendas_por_funcionario_lista,
        "vendas_por_tipo": vendas_por_tipo_lista,
        "vendas_por_grupo": vendas_por_grupo_lista,
        "produtos_detalhados": produtos_detalhados_lista,
        "produtos_analise": produtos_analise_lista,
        "lista_vendas": lista_vendas,
    }
