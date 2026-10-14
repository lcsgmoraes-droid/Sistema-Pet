from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.dre_canais.agregacao import (
    agregar_contas_receber_manuais_por_canal,
    agregar_devolucoes_por_canal,
    agregar_contas_pagar_por_canal,
    agregar_fretes_sobre_compras,
    obter_vendas_por_canal,
)
from app.dre_canais.base import (
    CANAIS_CONFIG,
    _decimal,
    _normalizar_canal,
    _novo_canal,
    _periodo_label_intervalo,
)
from app.dre_canais.detalhes import router as detalhes_router
from app.dre_canais.linhas import montar_linhas_dre_competencia
from app.dre_canais.schemas import DREPorCanalResponse

router = APIRouter(prefix="/financeiro/dre/canais", tags=["DRE por Canal"])
router.include_router(detalhes_router)


def _montar_alertas_cmv_estimado(dados_canais: dict) -> list[dict]:
    alertas = []
    for canal, dados in dados_canais.items():
        itens = list(dados.get("itens_cmv_estimado") or [])
        itens_ambiguos = [
            item
            for item in dados.get("itens_cmv_atribuido", []) or []
            if item.get("rateio_ambiguo")
        ]
        custos_sem_rateio = [
            item
            for item in dados.get("itens_cmv_atribuido", []) or []
            if item.get("conciliacao_pendente")
        ]
        if itens_ambiguos:
            config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])
            alertas.append(
                {
                    "codigo": "cmv_rateio_ambiguo",
                    "nivel": "atencao",
                    "canal": canal,
                    "titulo": f"Rateio provisório de CMV a conferir — {config['nome']}",
                    "mensagem": (
                        "O snapshot legado nao identifica o custo individual das linhas. "
                        "O CMV agregado foi rateado apenas "
                        "para a DRE; nao comprova o custo original de cada item "
                        "nem altera o estoque. Confira antes de conciliar devolucoes."
                    ),
                    "quantidade_itens": len(itens_ambiguos),
                    "valor_estimado": float(
                        sum(
                            (
                                _decimal(item.get("valor_cmv_atribuido", 0))
                                for item in itens_ambiguos
                            ),
                            _decimal(0),
                        )
                    ),
                }
            )
        if custos_sem_rateio:
            config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])
            alertas.append(
                {
                    "codigo": "cmv_agregado_sem_rateio",
                    "nivel": "critico",
                    "canal": canal,
                    "titulo": f"CMV agregado a conciliar — {config['nome']}",
                    "mensagem": (
                        "O snapshot legado tem CMV total sem vinculo seguro aos "
                        "itens da venda. A DRE preserva esse total e nao soma nova "
                        "estimativa; uma devolucao pode deixar custo residual ate "
                        "conciliacao manual."
                    ),
                    "quantidade_vendas": len(
                        {item.get("venda_id") for item in custos_sem_rateio}
                    ),
                    "valor_sem_rateio": float(
                        sum(
                            (
                                _decimal(item.get("custo_total_sem_rateio", 0))
                                for item in custos_sem_rateio
                            ),
                            _decimal(0),
                        )
                    ),
                }
            )
        if not itens:
            continue

        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])
        produtos = {
            str(
                item.get("produto_id")
                or item.get("produto_codigo")
                or item.get("produto_nome")
            )
            for item in itens
        }
        valor_vendas = sum(
            (_decimal(item.get("valor_venda", 0)) for item in itens),
            _decimal(0),
        )
        valor_estimado = _decimal(dados.get("cmv_estimado", 0))
        percentual = _decimal(dados.get("percentual_cmv_estimado", 0))
        origem = dados.get("origem_percentual_cmv_estimado")
        tem_item_sem_valor = any(
            _decimal(item.get("valor_venda", 0)) <= 0 for item in itens
        )
        sem_base = origem == "sem_base" or tem_item_sem_valor

        if origem == "todos_canais_periodo":
            base_mensagem = "a média ponderada de todos os canais deste período"
        else:
            base_mensagem = f"a média ponderada da {config['nome']} neste período"

        if sem_base:
            mensagem = (
                f"{len(produtos)} produto(s), em {len(itens)} item(ns) vendido(s), "
                "continuam sem custo confiável e ao menos um deles não possui base "
                "suficiente para estimativa. Cadastre o custo ou confira a movimentação "
                "de estoque; o cadastro não foi alterado."
            )
        else:
            mensagem = (
                f"{len(produtos)} produto(s), em {len(itens)} item(ns) vendido(s) que "
                "ainda não possuem custo confiável receberam CMV provisório. Foi aplicada "
                f"a proporção de custo de {float(percentual):.2f}% com base em "
                f"{base_mensagem}. "
                "A estimativa não altera o cadastro e será substituída quando houver custo real."
            )

        alertas.append(
            {
                "codigo": "cmv_produtos_sem_custo",
                "nivel": "critico" if sem_base else "atencao",
                "canal": canal,
                "titulo": f"CMV provisório — {config['nome']}",
                "mensagem": mensagem,
                "quantidade_produtos": len(produtos),
                "quantidade_itens": len(itens),
                "valor_vendas": float(valor_vendas),
                "valor_estimado": float(valor_estimado),
                "percentual_custo_aplicado": float(percentual),
                "sem_base_estimativa": sem_base,
            }
        )
    return alertas


def _montar_alertas_devolucoes(dados_canais: dict) -> list[dict]:
    alertas = []
    for canal, dados in dados_canais.items():
        pendentes = dados.get("devolucoes_custo_pendente") or []
        if not pendentes and _decimal(dados.get("devolucoes", 0)) <= 0:
            continue
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG["loja_fisica"])
        if pendentes:
            alertas.append(
                {
                    "codigo": "devolucao_custo_original_pendente",
                    "nivel": "atencao",
                    "canal": canal,
                    "titulo": f"Custo de devolução a conferir — {config['nome']}",
                    "mensagem": (
                        f"{len(pendentes)} devolucao(oes) tiveram a receita deduzida, "
                        "mas ao menos um item nao possui custo original comprovado. "
                        "A DRE pode reverter provisoriamente o CMV que havia atribuido "
                        "a esses itens, sem tratar esse valor como custo historico. "
                        "Se o vinculo com a linha da venda for ambiguo, o CMV anterior "
                        "permanece ate a conciliacao. "
                        "Se houve retorno de produto ao estoque, a entrada recebeu valor "
                        "provisorio zero. Confira o detalhe e ajuste manualmente "
                        "o custo quando aplicavel."
                    ),
                    "quantidade_itens": sum(
                        sum(
                            bool(item.get("custo_pendente"))
                            for item in (evento.itens or [])
                        )
                        for evento in pendentes
                    ),
                    "valor_vendas": float(
                        sum(
                            (_decimal(evento.valor_devolvido) for evento in pendentes),
                            _decimal(0),
                        )
                    ),
                }
            )
        if _decimal(dados.get("devolucoes", 0)) > 0:
            alertas.append(
                {
                    "codigo": "devolucao_imposto_a_conciliar",
                    "nivel": "atencao",
                    "canal": canal,
                    "titulo": f"Imposto de devolução a conferir — {config['nome']}",
                    "mensagem": (
                        "A devolucao nao estorna automaticamente os impostos "
                        "estimados sobre a venda. Confirme o documento fiscal e "
                        "o direito ao credito tributario antes de ajustar a DRE."
                    ),
                    "valor_vendas": float(_decimal(dados.get("devolucoes", 0))),
                }
            )
    return alertas


@router.get("", response_model=DREPorCanalResponse)
def gerar_dre_por_canais(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="Mês do DRE (1-12)"),
    mes_inicial: Optional[int] = Query(
        None, description="Mês inicial para período acumulado (1-12)"
    ),
    data_final: Optional[date] = Query(
        None, description="Último dia incluído no período acumulado"
    ),
    canais: str = Query(
        "",
        description="Canais selecionados separados por vírgula (ex: loja_fisica,mercado_livre)",
    ),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera DRE com cada canal em linhas separadas

    Cada linha terá:
    - Nome do canal na descrição (ex: "Descontos Concedidos Loja Física")
    - Cor específica do canal
    - Valores individuais
    """

    mes_inicial = mes if mes_inicial is None else mes_inicial
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")
    if mes_inicial < 1 or mes_inicial > mes:
        raise HTTPException(
            status_code=400,
            detail="Mês inicial deve estar entre 1 e o mês final",
        )
    if data_final is not None and (
        data_final.year != ano
        or data_final.month < mes_inicial
        or data_final.month > mes
    ):
        raise HTTPException(
            status_code=400,
            detail="Data final deve pertencer ao período informado",
        )

    # Processar canais selecionados
    canais_selecionados = [
        _normalizar_canal(c.strip()) for c in canais.split(",") if c.strip()
    ]
    if not canais_selecionados:
        canais_selecionados = ["loja_fisica"]

    periodo = _periodo_label_intervalo(mes_inicial, mes, ano, data_final)

    # Extrair user e tenant
    _, tenant_id = user_and_tenant

    dados_canais_calculados = obter_vendas_por_canal(
        db,
        mes,
        ano,
        tenant_id,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )
    agregar_devolucoes_por_canal(
        db,
        mes,
        ano,
        tenant_id,
        dados_canais_calculados,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )
    agregar_contas_receber_manuais_por_canal(
        db,
        mes,
        ano,
        tenant_id,
        dados_canais_calculados,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )
    agregar_contas_pagar_por_canal(
        db,
        mes,
        ano,
        tenant_id,
        dados_canais_calculados,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )
    agregar_fretes_sobre_compras(
        db,
        mes,
        ano,
        tenant_id,
        dados_canais_calculados,
        mes_inicial=mes_inicial,
        data_final=data_final,
    )

    dados_canais_resultado = {
        canal_id: dados_canais_calculados.get(canal_id, _novo_canal())
        for canal_id in canais_selecionados
    }

    linhas, totais = montar_linhas_dre_competencia(dados_canais_resultado)

    return DREPorCanalResponse(
        periodo=periodo,
        mes_inicial=mes_inicial,
        mes=mes,
        ano=ano,
        data_final=data_final,
        linhas=linhas,
        totais=totais,
        canais_encontrados=list(dados_canais_resultado.keys()),
        alertas=(
            _montar_alertas_cmv_estimado(dados_canais_resultado)
            + _montar_alertas_devolucoes(dados_canais_resultado)
        ),
    )
