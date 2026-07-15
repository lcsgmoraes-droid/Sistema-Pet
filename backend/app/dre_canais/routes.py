from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.dre_canais.agregacao import (
    agregar_contas_pagar_por_canal,
    agregar_fretes_sobre_compras,
    obter_vendas_por_canal,
)
from app.dre_canais.base import (
    CANAIS_CONFIG,
    _decimal,
    _normalizar_canal,
    _novo_canal,
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


@router.get("", response_model=DREPorCanalResponse)
def gerar_dre_por_canais(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="Mês do DRE (1-12)"),
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

    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")

    # Processar canais selecionados
    canais_selecionados = [
        _normalizar_canal(c.strip()) for c in canais.split(",") if c.strip()
    ]
    if not canais_selecionados:
        canais_selecionados = ["loja_fisica"]

    meses = [
        "",
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    periodo = f"{meses[mes]}/{ano}"

    # Extrair user e tenant
    _, tenant_id = user_and_tenant

    dados_canais_calculados = obter_vendas_por_canal(db, mes, ano, tenant_id)
    agregar_contas_pagar_por_canal(db, mes, ano, tenant_id, dados_canais_calculados)
    agregar_fretes_sobre_compras(db, mes, ano, tenant_id, dados_canais_calculados)

    dados_canais_resultado = {
        canal_id: dados_canais_calculados.get(canal_id, _novo_canal())
        for canal_id in canais_selecionados
    }

    linhas, totais = montar_linhas_dre_competencia(dados_canais_resultado)

    return DREPorCanalResponse(
        periodo=periodo,
        mes=mes,
        ano=ano,
        linhas=linhas,
        totais=totais,
        canais_encontrados=list(dados_canais_resultado.keys()),
        alertas=_montar_alertas_cmv_estimado(dados_canais_resultado),
    )
