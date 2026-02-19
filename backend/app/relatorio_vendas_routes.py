"""
Endpoint de Relatório de Vendas
Similar ao SimplesVet com abas: Resumo, Totais por produto, Lista de Vendas
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_
from datetime import datetime, date
from typing import Optional
from io import BytesIO
import json
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .vendas_models import Venda, VendaItem, VendaPagamento
from .produtos_models import Produto
from .models import User, Cliente
from .comissoes_models import ComissaoItem
from .empresa_config_fiscal_models import EmpresaConfigFiscal
from .financeiro_models import FormaPagamento

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/relatorios")


@router.get("/vendas/relatorio")
async def obter_relatorio_vendas(
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Relatório completo de vendas com:
    - Resumo (cards)
    - Vendas por data
    - Formas de recebimento
    - Vendas por funcionário
    - Vendas por tipo (produto/serviço)
    - Vendas por grupo de produto
    - Produtos detalhados
    - Lista de vendas
    """
    current_user, tenant_id = user_and_tenant
    
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
    
    # OTIMIZAÇÃO: Buscar vendas com EAGER LOADING para evitar N+1 queries
    # Isso carrega todos os relacionamentos de uma vez, reduzindo drasticamente queries ao BD
    vendas = db.query(Venda).options(
        selectinload(Venda.cliente),
        selectinload(Venda.usuario),
        selectinload(Venda.itens).selectinload(VendaItem.produto).selectinload(Produto.categoria),
        selectinload(Venda.itens).selectinload(VendaItem.produto).selectinload(Produto.marca),
        selectinload(Venda.pagamentos)
    ).filter(
        and_(
            Venda.tenant_id == tenant_id,
            Venda.data_venda >= data_inicio_dt,
            Venda.data_venda <= data_fim_dt
        )
    ).all()
    
    # OTIMIZAÇÃO: Buscar config fiscal UMA VEZ (não para cada venda)
    # Tratamento de erro caso a tabela não exista
    try:
        config_fiscal = db.query(EmpresaConfigFiscal).filter(
            EmpresaConfigFiscal.tenant_id == tenant_id
        ).first()
        impostos_percentual_global = float(config_fiscal.aliquota_simples_vigente) if config_fiscal and config_fiscal.aliquota_simples_vigente else 0.0
    except Exception as e:
        logger.warning(f"Erro ao buscar config fiscal (tabela pode não existir): {e}")
        impostos_percentual_global = 0.0
    
    # OTIMIZAÇÃO: Carregar todas as comissões de uma vez
    venda_ids = [v.id for v in vendas]
    comissoes_map = {}
    if venda_ids:
        try:
            comissoes_itens = db.query(ComissaoItem).filter(
                and_(ComissaoItem.venda_id.in_(venda_ids), ComissaoItem.tenant_id == tenant_id)
            ).all()
            for com_item in comissoes_itens:
                if com_item.venda_id not in comissoes_map:
                    comissoes_map[com_item.venda_id] = []
                comissoes_map[com_item.venda_id].append(com_item)
        except Exception as e:
            logger.warning(f"Erro ao buscar comissões (tabela pode não existir): {e}")
    
    # OTIMIZAÇÃO: Carregar todas as formas de pagamento ativas de uma vez
    formas_pagamento_map = {}
    try:
        formas_pag_list = db.query(FormaPagamento).filter(
            and_(FormaPagamento.ativo == True, FormaPagamento.tenant_id == tenant_id)
        ).all()
        for fp in formas_pag_list:
            formas_pagamento_map[fp.nome.lower().strip()] = fp
    except Exception as e:
        logger.warning(f"Erro ao buscar formas de pagamento (tabela pode não existir): {e}")
    
    # ==============================================
    # RESUMO (Cards no topo)
    # ==============================================
    venda_bruta = sum(float(v.subtotal) for v in vendas)
    taxa_entrega = sum(float(v.taxa_entrega or 0) for v in vendas)
    desconto = sum(float(v.desconto_valor or 0) for v in vendas)
    venda_liquida = sum(float(v.total) for v in vendas)
    
    # Calcular em_aberto (vendas com status != finalizada)
    em_aberto = 0
    for v in vendas:
        if v.status != 'finalizada':
            # OTIMIZAÇÃO: usar pagamentos já carregados em vez de query ao BD
            total_pago = sum(float(p.valor) for p in v.pagamentos) if v.pagamentos else 0
            em_aberto += (float(v.total) - total_pago)
    
    percentual_desconto = round((desconto / venda_bruta * 100) if venda_bruta > 0 else 0, 1)
    
    resumo = {
        "venda_bruta": round(venda_bruta, 2),
        "taxa_entrega": round(taxa_entrega, 2),
        "desconto": round(desconto, 2),
        "percentual_desconto": percentual_desconto,
        "venda_liquida": round(venda_liquida, 2),
        "em_aberto": round(em_aberto, 2),
        "quantidade_vendas": len(vendas)
    }
    
    # ==============================================
    # VENDAS POR DATA
    # ==============================================
    vendas_por_data = {}
    for venda in vendas:
        data_str = venda.data_venda.date().isoformat()
        if data_str not in vendas_por_data:
            vendas_por_data[data_str] = {
                "data": data_str,
                "quantidade": 0,
                "valor_bruto": 0,
                "taxa_entrega": 0,
                "desconto": 0,
                "valor_liquido": 0,
                "valor_recebido": 0,
                "saldo_aberto": 0
            }
        
        vendas_por_data[data_str]["quantidade"] += 1
        vendas_por_data[data_str]["valor_bruto"] += venda.subtotal
        vendas_por_data[data_str]["taxa_entrega"] += venda.taxa_entrega or 0
        vendas_por_data[data_str]["desconto"] += venda.desconto_valor or 0
        vendas_por_data[data_str]["valor_liquido"] += venda.total
        
        # OTIMIZAÇÃO: usar pagamentos já carregados
        total_pago = sum(p.valor for p in venda.pagamentos) if venda.pagamentos else 0
        vendas_por_data[data_str]["valor_recebido"] += total_pago
        vendas_por_data[data_str]["saldo_aberto"] += (venda.total - total_pago) if venda.status != 'finalizada' else 0
    
    # Calcular ticket médio
    for data_str in vendas_por_data:
        qtd = vendas_por_data[data_str]["quantidade"]
        vendas_por_data[data_str]["ticket_medio"] = round(vendas_por_data[data_str]["valor_bruto"] / qtd if qtd > 0 else 0, 2)
        vendas_por_data[data_str]["percentual_desconto"] = round(
            (vendas_por_data[data_str]["desconto"] / vendas_por_data[data_str]["valor_bruto"] * 100) if vendas_por_data[data_str]["valor_bruto"] > 0 else 0, 1
        )
    
    vendas_por_data_lista = sorted(vendas_por_data.values(), key=lambda x: x["data"])
    
    # ==============================================
    # FORMAS DE RECEBIMENTO
    # ==============================================
    # Mapeamento de códigos para descrições legíveis
    FORMAS_PAGAMENTO_MAP = {
        '1': 'Dinheiro',
        '2': 'PIX',
        '3': 'Cartão Débito',
        '4': 'Cartão Crédito',
        '5': 'Cartão Crédito',
        'dinheiro': 'Dinheiro',
        'pix': 'PIX',
        'debito': 'Cartão Débito',
        'cartao_debito': 'Cartão Débito',
        'credito': 'Cartão Crédito',
        'cartao_credito': 'Cartão Crédito',
        'credito_parcelado': 'Cartão Crédito',
        'credito_cliente': 'Crédito do Cliente'
    }
    
    formas_recebimento = {}
    for venda in vendas:
        # OTIMIZAÇÃO: usar pagamentos já carregados
        for pag in venda.pagamentos:
            forma_codigo = str(pag.forma_pagamento) if pag.forma_pagamento else "Não informado"
            forma_base = FORMAS_PAGAMENTO_MAP.get(forma_codigo, forma_codigo)
            
            # Criar chave única com forma + parcelas
            if pag.numero_parcelas and pag.numero_parcelas > 1:
                forma_completa = f"{forma_base} {pag.numero_parcelas}x"
                parcelas = pag.numero_parcelas
            else:
                forma_completa = forma_base
                parcelas = 1
            
            if forma_completa not in formas_recebimento:
                formas_recebimento[forma_completa] = {
                    "forma_pagamento": forma_completa,
                    "valor_total": 0,
                    "ordem_forma": forma_base,  # Para ordenar por tipo de pagamento
                    "ordem_parcelas": parcelas  # Para ordenar por número de parcelas
                }
            formas_recebimento[forma_completa]["valor_total"] += pag.valor
    
    # Ordenar por tipo de pagamento e depois por número de parcelas (crescente)
    formas_recebimento_lista = sorted(
        formas_recebimento.values(), 
        key=lambda x: (x["ordem_forma"], x["ordem_parcelas"])
    )
    
    # Remover campos auxiliares de ordenação
    for item in formas_recebimento_lista:
        item.pop("ordem_forma", None)
        item.pop("ordem_parcelas", None)
    
    # ==============================================
    # VENDAS POR FUNCIONÁRIO
    # ==============================================
    vendas_por_funcionario = {}
    for venda in vendas:
        funcionario_id = venda.user_id
        # OTIMIZAÇÃO: usar relacionamento usuario já carregado
        if funcionario_id:
            nome_func = venda.usuario.nome if venda.usuario else f"ID {funcionario_id}"
        else:
            nome_func = "Sem funcionário"
        
        if nome_func not in vendas_por_funcionario:
            vendas_por_funcionario[nome_func] = {
                "funcionario": nome_func,
                "quantidade": 0,
                "valor_bruto": 0,
                "desconto": 0,
                "valor_liquido": 0
            }
        
        vendas_por_funcionario[nome_func]["quantidade"] += 1
        vendas_por_funcionario[nome_func]["valor_bruto"] += venda.subtotal
        vendas_por_funcionario[nome_func]["desconto"] += venda.desconto_valor or 0
        vendas_por_funcionario[nome_func]["valor_liquido"] += venda.total
    
    vendas_por_funcionario_lista = sorted(vendas_por_funcionario.values(), key=lambda x: x["valor_liquido"], reverse=True)
    
    # ==============================================
    # VENDAS POR TIPO (Produto/Serviço)
    # ==============================================
    vendas_por_tipo = {
        "Produto": {"tipo": "Produto", "quantidade": 0, "valor_bruto": 0, "desconto": 0, "valor_liquido": 0}
    }
    
    for venda in vendas:
        vendas_por_tipo["Produto"]["quantidade"] += 1
        vendas_por_tipo["Produto"]["valor_bruto"] += venda.subtotal
        vendas_por_tipo["Produto"]["desconto"] += venda.desconto_valor or 0
        vendas_por_tipo["Produto"]["valor_liquido"] += venda.total
    
    vendas_por_tipo_lista = list(vendas_por_tipo.values())
    
    # ==============================================
    # VENDAS POR GRUPO DE PRODUTO
    # ==============================================
    vendas_por_grupo = {}
    total_geral = sum(v.total for v in vendas)
    
    for venda in vendas:
        # OTIMIZAÇÃO: usar itens já carregados
        for item in venda.itens:
            # OTIMIZAÇÃO: usar relacionamento produto já carregado
            produto = item.produto
            if produto and produto.categoria:
                grupo = produto.categoria.nome if hasattr(produto.categoria, 'nome') else str(produto.categoria)
            else:
                grupo = "Sem categoria"
            
            if grupo not in vendas_por_grupo:
                vendas_por_grupo[grupo] = {
                    "grupo": grupo,
                    "valor_bruto": 0,
                    "desconto": 0,
                    "valor_liquido": 0,
                    "percentual": 0
                }
            
            valor_item = item.quantidade * item.preco_unitario
            desconto_item = (item.quantidade * item.preco_unitario * (venda.desconto_valor or 0) / venda.subtotal) if venda.subtotal > 0 else 0
            
            vendas_por_grupo[grupo]["valor_bruto"] += valor_item
            vendas_por_grupo[grupo]["desconto"] += desconto_item
            vendas_por_grupo[grupo]["valor_liquido"] += (valor_item - desconto_item)
    
    # Calcular percentuais
    for grupo in vendas_por_grupo:
        vendas_por_grupo[grupo]["percentual"] = round(
            (vendas_por_grupo[grupo]["valor_liquido"] / total_geral * 100) if total_geral > 0 else 0, 1
        )
    
    vendas_por_grupo_lista = sorted(vendas_por_grupo.values(), key=lambda x: x["valor_liquido"], reverse=True)
    
    # ==============================================
    # PRODUTOS DETALHADOS AGRUPADOS POR CATEGORIA/SUBCATEGORIA
    # ==============================================
    produtos_por_categoria = {}
    
    for venda in vendas:
        # OTIMIZAÇÃO: usar itens já carregados
        for item in venda.itens:
            produto_id = item.produto_id
            # OTIMIZAÇÃO: usar relacionamento produto já carregado
            produto = item.produto
            
            # Determinar categoria e subcategoria
            if produto and produto.categoria:
                categoria_nome = produto.categoria.nome if hasattr(produto.categoria, 'nome') else str(produto.categoria)
            else:
                categoria_nome = "Sem categoria"
            
            subcategoria_nome = produto.subcategoria if produto and hasattr(produto, 'subcategoria') and produto.subcategoria else None
            produto_nome = f"{produto.nome} ({produto.id})" if produto else f"Produto ID {produto_id}"
            
            # Criar estrutura hierárquica
            if categoria_nome not in produtos_por_categoria:
                produtos_por_categoria[categoria_nome] = {
                    "categoria": categoria_nome,
                    "subcategorias": {},
                    "produtos": {},
                    "total_quantidade": 0,
                    "total_bruto": 0,
                    "total_desconto": 0,
                    "total_liquido": 0
                }
            
            # Se tem subcategoria, organizar em subcategoria
            if subcategoria_nome:
                if subcategoria_nome not in produtos_por_categoria[categoria_nome]["subcategorias"]:
                    produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome] = {
                        "subcategoria": subcategoria_nome,
                        "produtos": {},
                        "total_quantidade": 0,
                        "total_bruto": 0,
                        "total_desconto": 0,
                        "total_liquido": 0
                    }
                
                if produto_nome not in produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["produtos"]:
                    produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["produtos"][produto_nome] = {
                        "produto": produto_nome,
                        "quantidade": 0,
                        "valor_bruto": 0,
                        "desconto": 0,
                        "valor_liquido": 0
                    }
                
                valor_item = item.quantidade * item.preco_unitario
                desconto_item = (item.quantidade * item.preco_unitario * (venda.desconto_valor or 0) / venda.subtotal) if venda.subtotal > 0 else 0
                
                # Atualizar produto
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["produtos"][produto_nome]["quantidade"] += item.quantidade
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["produtos"][produto_nome]["valor_bruto"] += valor_item
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["produtos"][produto_nome]["desconto"] += desconto_item
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["produtos"][produto_nome]["valor_liquido"] += (valor_item - desconto_item)
                
                # Atualizar subcategoria
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["total_quantidade"] += item.quantidade
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["total_bruto"] += valor_item
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["total_desconto"] += desconto_item
                produtos_por_categoria[categoria_nome]["subcategorias"][subcategoria_nome]["total_liquido"] += (valor_item - desconto_item)
            else:
                # Produto direto na categoria (sem subcategoria)
                if produto_nome not in produtos_por_categoria[categoria_nome]["produtos"]:
                    produtos_por_categoria[categoria_nome]["produtos"][produto_nome] = {
                        "produto": produto_nome,
                        "quantidade": 0,
                        "valor_bruto": 0,
                        "desconto": 0,
                        "valor_liquido": 0
                    }
                
                valor_item = item.quantidade * item.preco_unitario
                desconto_item = (item.quantidade * item.preco_unitario * (venda.desconto_valor or 0) / venda.subtotal) if venda.subtotal > 0 else 0
                
                produtos_por_categoria[categoria_nome]["produtos"][produto_nome]["quantidade"] += item.quantidade
                produtos_por_categoria[categoria_nome]["produtos"][produto_nome]["valor_bruto"] += valor_item
                produtos_por_categoria[categoria_nome]["produtos"][produto_nome]["desconto"] += desconto_item
                produtos_por_categoria[categoria_nome]["produtos"][produto_nome]["valor_liquido"] += (valor_item - desconto_item)
            
            # Atualizar totais da categoria
            valor_item = item.quantidade * item.preco_unitario
            desconto_item = (item.quantidade * item.preco_unitario * (venda.desconto_valor or 0) / venda.subtotal) if venda.subtotal > 0 else 0
            produtos_por_categoria[categoria_nome]["total_quantidade"] += item.quantidade
            produtos_por_categoria[categoria_nome]["total_bruto"] += valor_item
            produtos_por_categoria[categoria_nome]["total_desconto"] += desconto_item
            produtos_por_categoria[categoria_nome]["total_liquido"] += (valor_item - desconto_item)
    
    # Converter para lista e ordenar
    produtos_detalhados_lista = []
    for cat_nome, cat_data in sorted(produtos_por_categoria.items(), key=lambda x: x[1]["total_liquido"], reverse=True):
        categoria_obj = {
            "categoria": cat_nome,
            "total_quantidade": cat_data["total_quantidade"],
            "total_bruto": round(cat_data["total_bruto"], 2),
            "total_desconto": round(cat_data["total_desconto"], 2),
            "total_liquido": round(cat_data["total_liquido"], 2),
            "subcategorias": [],
            "produtos": []
        }
        
        # Adicionar subcategorias
        for subcat_nome, subcat_data in sorted(cat_data["subcategorias"].items(), key=lambda x: x[1]["total_liquido"], reverse=True):
            subcat_obj = {
                "subcategoria": subcat_nome,
                "total_quantidade": subcat_data["total_quantidade"],
                "total_bruto": round(subcat_data["total_bruto"], 2),
                "total_desconto": round(subcat_data["total_desconto"], 2),
                "total_liquido": round(subcat_data["total_liquido"], 2),
                "produtos": []
            }
            
            # Produtos da subcategoria
            for prod in sorted(subcat_data["produtos"].values(), key=lambda x: x["valor_liquido"], reverse=True):
                subcat_obj["produtos"].append({
                    "produto": prod["produto"],
                    "quantidade": prod["quantidade"],
                    "valor_bruto": round(prod["valor_bruto"], 2),
                    "desconto": round(prod["desconto"], 2),
                    "valor_liquido": round(prod["valor_liquido"], 2)
                })
            
            categoria_obj["subcategorias"].append(subcat_obj)
        
        # Produtos diretos da categoria (sem subcategoria)
        for prod in sorted(cat_data["produtos"].values(), key=lambda x: x["valor_liquido"], reverse=True):
            categoria_obj["produtos"].append({
                "produto": prod["produto"],
                "quantidade": prod["quantidade"],
                "valor_bruto": round(prod["valor_bruto"], 2),
                "desconto": round(prod["desconto"], 2),
                "valor_liquido": round(prod["valor_liquido"], 2)
            })
        
        produtos_detalhados_lista.append(categoria_obj)
    
    # ==============================================
    # LISTA DE VENDAS COM ANÁLISE DE RENTABILIDADE
    # ==============================================
    lista_vendas = []
    custo_total_geral = 0
    taxa_total_geral = 0
    comissao_total_geral = 0
    lucro_total_geral = 0
    
    # Taxas de cartão (parametrizável futuramente)
    TAXAS_CARTAO = {
        'Dinheiro': 0,
        'dinheiro': 0,
        '1': 0,  # Dinheiro (código do PDV)
        'PIX': 0,
        'pix': 0,
        '2': 0,  # PIX (código do PDV)
        'Débito': 1.5,
        'debito': 1.5,
        'cartao_debito': 1.5,
        '3': 1.5,  # Débito (código do PDV)
        'Crédito à Vista': 2.5,
        'credito': 2.5,
        'cartao_credito': 2.5,
        '4': 2.5,  # Crédito à Vista (código do PDV)
        'Crédito Parcelado': 3.5,
        '5': 3.5,  # Crédito Parcelado (código do PDV)
        'credito_cliente': 0  # Crédito do cliente (sem taxa)
    }
    
    # Comissão padrão (será parametrizado por funcionário futuramente)
    COMISSAO_PADRAO = 5.0  # 5%
    
    for venda in vendas:
        # OTIMIZAÇÃO: usar itens já carregados em vez de query ao BD
        itens = venda.itens

        # ==============================
        # CALCULO DE RENTABILIDADE (safe)
        # ==============================
        taxa_total = 0.0
        comissao = 0.0
        impostos_percentual = impostos_percentual_global  # OTIMIZAÇÃO: usar valor já carregado
        taxa_operacional_entrega = 0.0

        # Taxa de cartao por FormaPagamento (JSON taxas_por_parcela)
        # OTIMIZAÇÃO: usar pagamentos já carregados
        for pag in venda.pagamentos:
            taxa_percentual = 0.0
            if pag.forma_pagamento:
                # OTIMIZAÇÃO: usar map pré-carregado em vez de query ao BD
                forma_pag = formas_pagamento_map.get(pag.forma_pagamento.lower().strip())
                if not forma_pag:
                    logger.warning(
                        "FormaPagamento nao encontrada: %s (venda_id=%s)",
                        pag.forma_pagamento,
                        venda.id
                    )
                else:
                    taxas_por_parcela = forma_pag.taxas_por_parcela
                    if isinstance(taxas_por_parcela, str):
                        try:
                            taxas_por_parcela = json.loads(taxas_por_parcela)
                        except Exception:
                            logger.warning(
                                "taxas_por_parcela invalido para FormaPagamento %s",
                                forma_pag.nome
                            )
                            taxas_por_parcela = None

                    if isinstance(taxas_por_parcela, dict) and pag.numero_parcelas:
                        taxa_percentual = float(
                            taxas_por_parcela.get(str(pag.numero_parcelas), 0) or 0
                        )
                    elif forma_pag.taxa_percentual:
                        taxa_percentual = float(forma_pag.taxa_percentual)
            else:
                logger.warning("Pagamento sem forma_pagamento (venda_id=%s)", venda.id)

            taxa_total += (float(pag.valor or 0) * taxa_percentual / 100.0)

        # OTIMIZAÇÃO: Comissao real da tabela comissoes_itens (usar map pré-carregado)
        comissoes_itens = comissoes_map.get(venda.id, [])
        if not comissoes_itens:
            logger.warning("Sem comissao para venda_id=%s", venda.id)
        for com_item in comissoes_itens:
            comissao += float(com_item.valor_comissao or 0)

        # OTIMIZAÇÃO: Imposto já foi carregado globalmente (impostos_percentual_global)

        # Taxa operacional de entrega
        if venda.tem_entrega and venda.entregador_id:
            # OTIMIZAÇÃO: Carregar entregador apenas se necessário
            # Idealmente, isso deveria ser eager-loaded também, mas é menos comum
            try:
                entregador = db.query(Cliente).filter(
                    and_(Cliente.id == venda.entregador_id, Cliente.tenant_id == tenant_id)
                ).first()
                if not entregador:
                    logger.warning("Entregador nao encontrado (id=%s)", venda.entregador_id)
                elif entregador.taxa_fixa_entrega:
                    taxa_operacional_entrega = float(entregador.taxa_fixa_entrega)
            except Exception as e:
                logger.warning(f"Erro ao buscar entregador: {e}")
        else:
            pass  # Sem warning se não tem entrega
        
        # Calcular CUSTO TOTAL e SUBTOTAL dos produtos para rateio
        custo_total = 0
        subtotal_itens = 0
        itens_detalhados = []
        
        # Primeiro loop: calcular totais
        for item in itens:
            # OTIMIZAÇÃO: usar relacionamento produto já carregado
            produto = item.produto
            custo_unitario = float(produto.preco_custo) if produto and produto.preco_custo else 0
            custo_item = custo_unitario * float(item.quantidade)
            subtotal_item = float(item.quantidade) * float(item.preco_unitario)
            
            custo_total += custo_item
            subtotal_itens += subtotal_item
        
        # Segundo loop: calcular rateio para cada item
        for item in itens:
            # OTIMIZAÇÃO: usar relacionamento produto já carregado
            produto = item.produto
            custo_unitario = float(produto.preco_custo) if produto and produto.preco_custo else 0
            quantidade = float(item.quantidade)
            preco_unit = float(item.preco_unitario)
            
            # Valores do item
            subtotal_item = quantidade * preco_unit
            custo_item = custo_unitario * quantidade
            
            # Calcular percentual do item no total da venda (para rateio)
            percentual_item = (subtotal_item / subtotal_itens) if subtotal_itens > 0 else 0
            
            # RATEIO PROPORCIONAL de despesas
            desconto_rateado = float(venda.desconto_valor or 0) * percentual_item
            taxa_entrega_rateada = float(venda.taxa_entrega or 0) * percentual_item
            taxa_cartao_rateada = taxa_total * percentual_item
            comissao_rateada = comissao * percentual_item
            imposto_rateado = (subtotal_item * impostos_percentual / 100.0) * percentual_item
            taxa_operacional_rateada = taxa_operacional_entrega * percentual_item
            
            # Valor líquido do item
            valor_liquido_item = subtotal_item - desconto_rateado
            
            # Lucro do item
            lucro_item = (
                valor_liquido_item
                - custo_item
                - taxa_entrega_rateada
                - taxa_cartao_rateada
                - comissao_rateada
                - imposto_rateado
                - taxa_operacional_rateada
            )
            
            # Margens do item
            margem_sobre_venda_item = (lucro_item / valor_liquido_item * 100) if valor_liquido_item > 0 else 0
            margem_sobre_custo_item = (lucro_item / custo_item * 100) if custo_item > 0 else 0
            
            # Valores unitários (para tooltip)
            lucro_unitario = lucro_item / quantidade if quantidade > 0 else 0
            margem_sobre_venda_unit = margem_sobre_venda_item  # Margem % é a mesma
            margem_sobre_custo_unit = margem_sobre_custo_item
            
            itens_detalhados.append({
                "produto_nome": produto.nome if produto else "Produto removido",
                "quantidade": quantidade,
                "preco_unitario": round(preco_unit, 2),
                "venda_bruta": round(subtotal_item, 2),
                "desconto": round(desconto_rateado, 2),
                "taxa_entrega": round(taxa_entrega_rateada, 2),
                "taxa_cartao": round(taxa_cartao_rateada, 2),
                "comissao": round(comissao_rateada, 2),
                "imposto": round(imposto_rateado, 2),
                "taxa_operacional": round(taxa_operacional_rateada, 2),
                "custo_unitario": round(custo_unitario, 2),
                "custo_total": round(custo_item, 2),
                "valor_liquido": round(valor_liquido_item, 2),
                "lucro": round(lucro_item, 2),
                "lucro_unitario": round(lucro_unitario, 2),
                "margem_sobre_venda": round(margem_sobre_venda_item, 1),
                "margem_sobre_custo": round(margem_sobre_custo_item, 1)
            })
        
        # Calcular LUCRO
        imposto_total = float(venda.total) * (impostos_percentual / 100.0)
        lucro = (
            float(venda.total)
            - custo_total
            - taxa_total
            - comissao
            - imposto_total
            - float(venda.taxa_entrega or 0)
            - taxa_operacional_entrega
        )
        
        # Calcular MARGENS
        margem_sobre_venda = (lucro / float(venda.total) * 100) if venda.total > 0 else 0
        margem_sobre_custo = (lucro / custo_total * 100) if custo_total > 0 else 0
        
        # Acumular totais gerais
        custo_total_geral += custo_total
        taxa_total_geral += taxa_total
        comissao_total_geral += comissao
        lucro_total_geral += lucro
        
        lista_vendas.append({
            "id": venda.id,
            "numero_venda": venda.numero_venda,
            "data_venda": venda.data_venda.isoformat(),
            "cliente_nome": venda.cliente.nome if venda.cliente else "Sem cliente",
            "venda_bruta": round(float(venda.subtotal), 2),
            "desconto": round(float(venda.desconto_valor or 0), 2),
            "taxa_entrega": round(float(venda.taxa_entrega or 0), 2),
            "taxa_cartao": round(taxa_total, 2),
            "comissao": round(comissao, 2),
            "imposto": round(imposto_total, 2),
            "taxa_operacional": round(taxa_operacional_entrega, 2),
            "custo_produtos": round(custo_total, 2),
            "venda_liquida": round(float(venda.total), 2),
            "lucro": round(lucro, 2),
            "margem_sobre_venda": round(margem_sobre_venda, 1),
            "margem_sobre_custo": round(margem_sobre_custo, 1),
            "status": venda.status,
            "itens": itens_detalhados
        })
    
    lista_vendas = sorted(lista_vendas, key=lambda x: x["data_venda"], reverse=True)
    
    # Adicionar análise de rentabilidade ao resumo
    resumo["custo_total"] = round(custo_total_geral, 2)
    resumo["taxa_cartao_total"] = round(taxa_total_geral, 2)
    resumo["comissao_total"] = round(comissao_total_geral, 2)
    resumo["lucro_total"] = round(lucro_total_geral, 2)
    resumo["margem_media"] = round((lucro_total_geral / venda_liquida * 100) if venda_liquida > 0 else 0, 1)
    
    # ==============================================
    # PRODUTOS PARA ANÁLISE INTELIGENTE (flat list)
    # ==============================================
    produtos_analise = {}
    for venda in vendas:
        # OTIMIZAÇÃO: usar itens já carregados
        for item in venda.itens:
            # OTIMIZAÇÃO: usar relacionamento produto já carregado
            produto = item.produto
            if not produto:
                continue
                
            prod_nome = produto.nome
            if prod_nome not in produtos_analise:
                produtos_analise[prod_nome] = {
                    'nome': prod_nome,
                    'produto': prod_nome,
                    'marca': produto.marca.nome if produto.marca else None,
                    'categoria': produto.categoria.nome if produto.categoria else None,
                    'quantidade': 0,
                    'valor_total': 0,
                    'custo_total': 0
                }
            
            produtos_analise[prod_nome]['quantidade'] += float(item.quantidade or 0)
            produtos_analise[prod_nome]['valor_total'] += float(item.subtotal or 0)
            
            # Calcular custo
            if produto.preco_custo:
                produtos_analise[prod_nome]['custo_total'] += float(produto.preco_custo) * float(item.quantidade or 0)
    
    # Converter para lista e ordenar por valor
    produtos_analise_lista = sorted(
        list(produtos_analise.values()), 
        key=lambda x: x['valor_total'], 
        reverse=True
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
        "lista_vendas": lista_vendas
    }


@router.get("/vendas/export/pdf")
async def exportar_vendas_pdf(
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
    funcionario: Optional[str] = Query(None),
    forma_pagamento: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Exporta relatório de vendas para PDF"""
    from fastapi import HTTPException
    import logging
    import traceback
    
    logger = logging.getLogger(__name__)
    current_user, tenant_id = user_and_tenant
    
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    except ImportError as e:
        logger.error(f"Erro ao importar reportlab: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab não instalada. Execute: pip install reportlab"
        )
    
    # Buscar dados do relatório - obter_relatorio_vendas retorna um dict diretamente
    try:
        logger.info(f"Gerando PDF de vendas para período: {data_inicio} até {data_fim}")
        # Construir filtros de data
        if not data_inicio:
            data_inicio = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        if not data_fim:
            data_fim = datetime.now().strftime('%Y-%m-%d')
        
        # Buscar todas as vendas do período com filtro de tenant
        vendas_query = db.query(Venda).filter(
            and_(
                Venda.tenant_id == tenant_id,
                func.date(Venda.data_venda) >= data_inicio,
                func.date(Venda.data_venda) <= data_fim,
                Venda.status != 'cancelada'
            )
        )
        
        vendas = vendas_query.all()
        
        # Calcular resumo
        venda_bruta = sum(float(v.subtotal or 0) for v in vendas)
        taxa_entrega = sum(float(v.taxa_entrega or 0) for v in vendas)
        desconto = sum(float(v.desconto_valor or 0) for v in vendas)
        venda_liquida = sum(float(v.total or 0) for v in vendas)
        em_aberto = sum(float(v.total or 0) for v in vendas if v.status == 'aberta')
        quantidade_vendas = len(vendas)
        
        resumo = {
            'venda_bruta': venda_bruta,
            'taxa_entrega': taxa_entrega,
            'desconto': desconto,
            'venda_liquida': venda_liquida,
            'em_aberto': em_aberto,
            'quantidade_vendas': quantidade_vendas
        }
        
        # Agrupar vendas por data
        vendas_por_data_dict = {}
        for v in vendas:
            data_str = v.data_venda.strftime('%Y-%m-%d') if isinstance(v.data_venda, datetime) else str(v.data_venda)
            if data_str not in vendas_por_data_dict:
                vendas_por_data_dict[data_str] = {
                    'data': data_str,
                    'quantidade': 0,
                    'valor_bruto': 0,
                    'taxa_entrega': 0,
                    'desconto': 0,
                    'valor_liquido': 0,
                    'valor_recebido': 0,
                    'saldo_aberto': 0
                }
            vendas_por_data_dict[data_str]['quantidade'] += 1
            vendas_por_data_dict[data_str]['valor_bruto'] += float(v.subtotal or 0)
            vendas_por_data_dict[data_str]['taxa_entrega'] += float(v.taxa_entrega or 0)
            vendas_por_data_dict[data_str]['desconto'] += float(v.desconto_valor or 0)
            vendas_por_data_dict[data_str]['valor_liquido'] += float(v.total or 0)
            if v.status != 'aberta':
                vendas_por_data_dict[data_str]['valor_recebido'] += float(v.total or 0)
            else:
                vendas_por_data_dict[data_str]['saldo_aberto'] += float(v.total or 0)
        
        vendas_por_data = list(vendas_por_data_dict.values())
        for v in vendas_por_data:
            v['ticket_medio'] = v['valor_liquido'] / v['quantidade'] if v['quantidade'] > 0 else 0
        
        # Formas de recebimento
        formas_dict = {}
        for v in vendas:
            pagamentos = db.query(VendaPagamento).filter(
                and_(VendaPagamento.venda_id == v.id, VendaPagamento.tenant_id == tenant_id)
            ).all()
            for p in pagamentos:
                forma = p.forma_pagamento or 'Não informado'
                if forma not in formas_dict:
                    formas_dict[forma] = 0
                formas_dict[forma] += p.valor or 0
        
        formas_recebimento = [{'forma_pagamento': k, 'valor_total': v} for k, v in formas_dict.items()]
        
        # Vendas por funcionário
        func_dict = {}
        for v in vendas:
            func_nome = v.vendedor.nome if v.vendedor else 'Sem registro'
            if func_nome not in func_dict:
                func_dict[func_nome] = {'funcionario': func_nome, 'quantidade': 0, 'valor_total': 0}
            func_dict[func_nome]['quantidade'] += 1
            func_dict[func_nome]['valor_total'] += float(v.total or 0)
        
        vendas_por_funcionario = list(func_dict.values())
        for f in vendas_por_funcionario:
            f['ticket_medio'] = f['valor_total'] / f['quantidade'] if f['quantidade'] > 0 else 0
        
        # Produtos detalhados
        prod_dict = {}
        for v in vendas:
            itens = db.query(VendaItem).filter(
                and_(VendaItem.venda_id == v.id, VendaItem.tenant_id == tenant_id)
            ).all()
            for item in itens:
                prod_nome = item.produto.nome if item.produto else 'Produto sem nome'
                if prod_nome not in prod_dict:
                    prod_dict[prod_nome] = {
                        'produto': prod_nome,
                        'nome': prod_nome,
                        'quantidade': 0,
                        'valor_total': 0,
                        'custo_total': 0,
                        'marca': item.produto.marca.nome if (item.produto and item.produto.marca) else None,
                        'categoria': item.produto.categoria.nome if (item.produto and item.produto.categoria) else None
                    }
                prod_dict[prod_nome]['quantidade'] += float(item.quantidade or 0)
                prod_dict[prod_nome]['valor_total'] += float(item.subtotal or 0)
                # Adicionar custo do produto
                if item.produto and item.produto.preco_custo:
                    prod_dict[prod_nome]['custo_total'] += float(item.produto.preco_custo) * float(item.quantidade or 0)
        
        produtos_detalhados = sorted(list(prod_dict.values()), key=lambda x: x['valor_total'], reverse=True)
        
        logger.info(f"Dados carregados: {len(vendas)} vendas, {len(produtos_detalhados)} produtos")
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dados: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dados: {str(e)}")
    
    # Aplicar filtros se fornecidos
    if funcionario:
        vendas_por_funcionario = [v for v in vendas_por_funcionario if v.get('funcionario') == funcionario]
    if forma_pagamento:
        formas_recebimento = [f for f in formas_recebimento if f.get('forma_pagamento') == forma_pagamento]
    
    # Gerar PDF
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15*mm, bottomMargin=15*mm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a56db'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        elements.append(Paragraph("RELATÓRIO DE VENDAS", title_style))
        elements.append(Spacer(1, 5*mm))
        
        # Período
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER
        )
        periodo_text = f"Período: {data_inicio} até {data_fim}"
        elements.append(Paragraph(periodo_text, subtitle_style))
        elements.append(Spacer(1, 8*mm))
    
        # Resumo Financeiro
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a56db'),
            spaceAfter=6
        )
        elements.append(Paragraph("Resumo Financeiro", header_style))
    
        resumo_data = [
            ['Métrica', 'Valor'],
            ['Venda Bruta', f"R$ {resumo['venda_bruta']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Taxa de Entrega', f"R$ {resumo['taxa_entrega']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Desconto', f"R$ {resumo['desconto']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Venda Líquida', f"R$ {resumo['venda_liquida']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Valor Recebido', f"R$ {resumo['venda_liquida'] - resumo['em_aberto']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Em Aberto', f"R$ {resumo['em_aberto']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
            ['Quantidade de Vendas', str(resumo['quantidade_vendas'])],
        ]
    
        resumo_table = Table(resumo_data, colWidths=[60*mm, 40*mm])
        resumo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(resumo_table)
        elements.append(Spacer(1, 10*mm))
    
        # Vendas por Data (se houver)
        if vendas_por_data:
            elements.append(Paragraph("Vendas por Data", header_style))
            
            vendas_data_list = [['Data', 'Qtd', 'Tkt Médio', 'Vl Bruto', 'Taxa', 'Desc.', 'Vl Líq.', 'Recebido', 'Aberto']]
            for v in vendas_por_data[:10]:  # Limitar a 10 linhas para caber na página
                vendas_data_list.append([
                    v['data'],
                    str(v['quantidade']),
                    f"R$ {v['ticket_medio']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {v['valor_bruto']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {v['taxa_entrega']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {v['desconto']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {v['valor_liquido']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {v['valor_recebido']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {v['saldo_aberto']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ])
            
            vendas_table = Table(vendas_data_list, colWidths=[22*mm, 12*mm, 22*mm, 22*mm, 18*mm, 18*mm, 22*mm, 22*mm, 22*mm])
            vendas_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(vendas_table)
            elements.append(Spacer(1, 10*mm))
    
        # Formas de Pagamento
        if formas_recebimento:
            elements.append(Paragraph("Formas de Pagamento", header_style))
            
            formas_data_list = [['Forma de Pagamento', 'Valor Total']]
            for f in formas_recebimento:
                formas_data_list.append([
                    f['forma_pagamento'],
                    f"R$ {f['valor_total']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ])
            
            formas_table = Table(formas_data_list, colWidths=[80*mm, 40*mm])
            formas_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(formas_table)
            elements.append(Spacer(1, 10*mm))
    
        # Vendas por Funcionário
        if vendas_por_funcionario:
            elements.append(Paragraph("Vendas por Funcionário", header_style))
            
            func_data_list = [['Funcionário', 'Qtd Vendas', 'Valor Total', 'Ticket Médio']]
            for f in vendas_por_funcionario[:10]:
                func_data_list.append([
                    f.get('funcionario', 'Sem registro'),
                    str(f['quantidade']),
                    f"R$ {f['valor_total']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"R$ {f['ticket_medio']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ])
            
            func_table = Table(func_data_list, colWidths=[80*mm, 25*mm, 35*mm, 35*mm])
            func_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(func_table)
            elements.append(Spacer(1, 10*mm))
    
        # Produtos Mais Vendidos (Top 20)
        if produtos_detalhados:
            elements.append(Paragraph("Produtos Mais Vendidos (Top 20)", header_style))
            
            prod_data_list = [['Produto', 'Qtd', 'Valor Total']]
            for p in produtos_detalhados[:20]:
                prod_data_list.append([
                    p.get('produto', 'Produto sem nome'),
                    str(p['quantidade']),
                    f"R$ {p['valor_total']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ])
            
            prod_table = Table(prod_data_list, colWidths=[120*mm, 20*mm, 35*mm])
            prod_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ec4899')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(prod_table)
    
        # Rodapé
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        )
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", footer_style))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        logger.info("PDF gerado com sucesso")
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=relatorio_vendas_{data_inicio}_{data_fim}.pdf"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
