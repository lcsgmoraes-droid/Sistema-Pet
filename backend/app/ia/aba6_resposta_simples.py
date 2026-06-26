"""Resposta simples baseada em regras para o chat IA da aba 6."""

from typing import Dict, Optional


def gerar_resposta_simples(
    service, mensagem: str, contexto: Dict, tenant_id: Optional[str] = None
) -> str:
    """Gera resposta simples usando os metodos de contexto do ChatIAService."""
    """Gera resposta simples baseada em regras (temporário antes de OpenAI)"""

    msg_lower = mensagem.lower()
    msg_normalizada = service._normalizar_texto(mensagem)

    indices = contexto.get("indices_saude", {})
    alertas = contexto.get("alertas", [])
    projecoes = contexto.get("projecoes", [])
    vendas_hoje = contexto.get("vendas_hoje", {})

    saldo = indices.get("saldo_atual", 0)
    dias_caixa = indices.get("dias_de_caixa", 0)
    status = indices.get("status", "").lower()

    periodo_detectado = service._detectar_periodo(mensagem)
    resumo_periodo = service._montar_resumo_executivo_periodo(
        tenant_id, periodo_detectado
    )
    resumo_vendas_periodo = resumo_periodo["resumo_vendas"]
    produtos_periodo = resumo_periodo["produtos"]
    dre_periodo = resumo_periodo["dre"]
    rankings_periodo = resumo_periodo["rankings"]
    label_periodo = periodo_detectado["label"]
    comparacao_periodos = service._detectar_comparacao_periodos(mensagem)

    def moeda(valor: float) -> str:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if comparacao_periodos:
        resumo_a = service._montar_resumo_executivo_periodo(
            tenant_id, comparacao_periodos["periodo_a"]
        )
        resumo_b = service._montar_resumo_executivo_periodo(
            tenant_id, comparacao_periodos["periodo_b"]
        )

        faturamento_a = float(resumo_a["resumo_vendas"].get("faturamento_liquido", 0))
        faturamento_b = float(resumo_b["resumo_vendas"].get("faturamento_liquido", 0))
        lucro_a = float(resumo_a["dre"].get("lucro_liquido_estimado", 0))
        lucro_b = float(resumo_b["dre"].get("lucro_liquido_estimado", 0))

        if any(palavra in msg_normalizada for palavra in ["canal", "canais"]):
            canais_a = {
                item["canal"]: item
                for item in resumo_a["rankings"].get("top_canais", [])
            }
            canais_b = {
                item["canal"]: item
                for item in resumo_b["rankings"].get("top_canais", [])
            }
            canais_ordenados = sorted(
                set(canais_a.keys()) | set(canais_b.keys()),
                key=lambda canal: max(
                    float(canais_a.get(canal, {}).get("receita", 0)),
                    float(canais_b.get(canal, {}).get("receita", 0)),
                ),
                reverse=True,
            )[:5]

            if not canais_ordenados:
                return "Ainda não encontrei canais com vendas suficientes para comparar esses períodos."

            linhas = [
                f"🛒 **Comparação por canal: {comparacao_periodos['periodo_a']['label']} x {comparacao_periodos['periodo_b']['label']}**\n"
            ]
            for canal in canais_ordenados:
                receita_a = float(canais_a.get(canal, {}).get("receita", 0))
                receita_b = float(canais_b.get(canal, {}).get("receita", 0))
                linhas.append(
                    f"- {canal}: {moeda(receita_a)} vs {moeda(receita_b)} | diferença **{moeda(receita_a - receita_b)}**"
                )
            return "\n".join(linhas)

        return (
            f"📊 **Comparação: {comparacao_periodos['periodo_a']['label']} x {comparacao_periodos['periodo_b']['label']}**\n\n"
            f"- Faturamento {comparacao_periodos['periodo_a']['label']}: **{moeda(faturamento_a)}**\n"
            f"- Faturamento {comparacao_periodos['periodo_b']['label']}: **{moeda(faturamento_b)}**\n"
            f"- Diferença de faturamento: **{moeda(faturamento_a - faturamento_b)}**\n"
            f"- Lucro líquido {comparacao_periodos['periodo_a']['label']}: **{moeda(lucro_a)}**\n"
            f"- Lucro líquido {comparacao_periodos['periodo_b']['label']}: **{moeda(lucro_b)}**\n"
            f"- Diferença de lucro: **{moeda(lucro_a - lucro_b)}**\n"
            f"- Margem {comparacao_periodos['periodo_a']['label']}: **{float(resumo_a['dre'].get('margem_liquida_estimada', 0)):.2f}%**\n"
            f"- Margem {comparacao_periodos['periodo_b']['label']}: **{float(resumo_b['dre'].get('margem_liquida_estimada', 0)):.2f}%**"
        )

    if any(
        palavra in msg_lower
        for palavra in ["vendas do dia", "vendas hoje", "quanto vendi hoje"]
    ):
        return (
            "📊 **Vendas de Hoje**\n\n"
            f"- Quantidade: **{int(vendas_hoje.get('quantidade', 0))}** vendas\n"
            f"- Faturamento bruto: **{moeda(float(vendas_hoje.get('faturamento_bruto', 0)))}**\n"
            f"- Descontos: **{moeda(float(vendas_hoje.get('descontos', 0)))}**\n"
            f"- Faturamento líquido: **{moeda(float(vendas_hoje.get('faturamento_liquido', 0)))}**"
        )

    if any(
        palavra in msg_normalizada
        for palavra in [
            "raio x",
            "raio-x",
            "resumo geral",
            "resumo gerencial",
            "panorama",
        ]
    ):
        top_produto = (produtos_periodo.get("top_vendidos") or [None])[0]
        top_categoria = (rankings_periodo.get("top_categorias_margem") or [None])[0]
        top_canal = (rankings_periodo.get("top_canais") or [None])[0]

        linhas = [
            f"📌 **Raio-x do periodo: {label_periodo}**\n",
            f"- Vendas: **{int(resumo_vendas_periodo.get('quantidade', 0))}**",
            f"- Faturamento liquido: **{moeda(float(resumo_vendas_periodo.get('faturamento_liquido', 0)))}**",
            f"- Lucro liquido estimado: **{moeda(float(dre_periodo.get('lucro_liquido_estimado', 0)))}**",
            f"- Margem liquida estimada: **{float(dre_periodo.get('margem_liquida_estimada', 0)):.2f}%**",
        ]
        if top_produto:
            linhas.append(
                f"- Produto lider: **{top_produto['produto']}** com {top_produto['quantidade']:.0f} unid"
            )
        if top_categoria:
            linhas.append(
                f"- Melhor categoria por margem: **{top_categoria['categoria']}** com **{top_categoria['margem_percentual']:.2f}%**"
            )
        if top_canal:
            linhas.append(
                f"- Canal mais forte: **{top_canal['canal']}** com **{moeda(float(top_canal['receita']))}**"
            )
        if alertas:
            linhas.append(f"- Alertas ativos: **{len(alertas)}**")
        return "\n".join(linhas)

    if any(palavra in msg_lower for palavra in ["vendas do mês", "vendas do mes"]) or (
        "vendas" in msg_normalizada
        and any(
            chave in msg_normalizada
            for chave in [
                "ultimo",
                "ultimos",
                "marco",
                "abril",
                "maio",
                "junho",
                "julho",
                "agosto",
                "setembro",
                "outubro",
                "novembro",
                "dezembro",
                "janeiro",
                "fevereiro",
                "mes",
            ]
        )
    ):
        return (
            f"📅 **Vendas de {label_periodo}**\n\n"
            f"- Quantidade: **{int(resumo_vendas_periodo.get('quantidade', 0))}** vendas\n"
            f"- Faturamento bruto: **{moeda(float(resumo_vendas_periodo.get('faturamento_bruto', 0)))}**\n"
            f"- Descontos: **{moeda(float(resumo_vendas_periodo.get('descontos', 0)))}**\n"
            f"- Faturamento líquido: **{moeda(float(resumo_vendas_periodo.get('faturamento_liquido', 0)))}**"
        )

    if any(
        palavra in msg_lower
        for palavra in ["mais vendido", "top produtos", "produto mais vendido"]
    ):
        top_vendidos = produtos_periodo.get("top_vendidos", [])
        if not top_vendidos:
            return f"Ainda não encontrei produtos vendidos em {label_periodo} para montar o ranking."

        linhas = [f"🏆 **Top Produtos Mais Vendidos ({label_periodo})**\n"]
        for idx, item in enumerate(top_vendidos, 1):
            linhas.append(
                f"{idx}. {item['produto']} — {item['quantidade']:.0f} unid — {moeda(float(item['receita']))}"
            )
        return "\n".join(linhas)

    if any(
        palavra in msg_lower for palavra in ["margem", "melhor margem", "maior margem"]
    ):
        if "categoria" in msg_normalizada:
            top_categorias = rankings_periodo.get("top_categorias_margem", [])
            if not top_categorias:
                return f"Ainda não encontrei categorias com margem calculável em {label_periodo}."

            linhas = [f"📦 **Categorias com Melhor Margem ({label_periodo})**\n"]
            for idx, item in enumerate(top_categorias, 1):
                linhas.append(
                    f"{idx}. {item['categoria']} — margem {item['margem_percentual']:.2f}% — lucro {moeda(float(item['lucro']))}"
                )
            return "\n".join(linhas)

        top_margem = produtos_periodo.get("top_margem", [])
        if not top_margem:
            return f"Ainda não encontrei produtos com margem calculável em {label_periodo}."

        linhas = [f"💎 **Produtos com Melhor Margem ({label_periodo})**\n"]
        for idx, item in enumerate(top_margem, 1):
            linhas.append(
                f"{idx}. {item['produto']} — margem {item['margem_percentual']:.2f}% — lucro {moeda(float(item['lucro']))}"
            )
        return "\n".join(linhas)

    if any(
        palavra in msg_normalizada
        for palavra in ["canal", "canais", "desempenho por canal"]
    ):
        top_canais = rankings_periodo.get("top_canais", [])
        if not top_canais:
            return f"Ainda não encontrei vendas por canal em {label_periodo}."

        linhas = [f"🛒 **Desempenho por Canal ({label_periodo})**\n"]
        for idx, item in enumerate(top_canais, 1):
            linhas.append(
                f"{idx}. {item['canal']} — {item['quantidade']} vendas — {moeda(float(item['receita']))}"
            )
        return "\n".join(linhas)

    if "dre" in msg_lower:
        return (
            f"📈 **DRE Simplificada ({label_periodo})**\n\n"
            f"- Receita bruta: **{moeda(float(dre_periodo.get('receita_bruta', 0)))}**\n"
            f"- Descontos: **{moeda(float(dre_periodo.get('descontos', 0)))}**\n"
            f"- Receita líquida: **{moeda(float(dre_periodo.get('receita_liquida', 0)))}**\n"
            f"- CMV estimado: **{moeda(float(dre_periodo.get('cmv_estimado', 0)))}**\n"
            f"- Lucro bruto: **{moeda(float(dre_periodo.get('lucro_bruto', 0)))}**\n"
            f"- Despesas operacionais: **{moeda(float(dre_periodo.get('despesas_operacionais', 0)))}**\n"
            f"- Lucro líquido estimado: **{moeda(float(dre_periodo.get('lucro_liquido_estimado', 0)))}**\n"
            f"- Margem líquida estimada: **{float(dre_periodo.get('margem_liquida_estimada', 0)):.2f}%**"
        )

    if any(palavra in msg_lower for palavra in ["saldo", "quanto tenho", "dinheiro"]):
        return f"📊 Seu saldo atual é de **R$ {saldo:,.2f}**.\n\nVocê tem **{dias_caixa:.1f} dias de caixa**, o que significa que consegue cobrir suas despesas por esse período sem novas receitas.\n\n{'⚠️ Status: ' + status.upper() if status in ['critico', 'alerta'] else '✅ Status: OK'}"

    if any(
        palavra in msg_lower
        for palavra in ["dias de caixa", "quanto tempo", "quantos dias"]
    ):
        interpretacao = ""
        if dias_caixa < 7:
            interpretacao = (
                "🔴 **CRÍTICO**: Menos de uma semana! Ação urgente necessária."
            )
        elif dias_caixa < 15:
            interpretacao = (
                "🟡 **ALERTA**: Menos de duas semanas. Monitore com atenção."
            )
        else:
            interpretacao = "🟢 **OK**: Situação confortável."

        return f"Você tem **{dias_caixa:.1f} dias de caixa**.\n\n{interpretacao}\n\nIsso é calculado dividindo seu saldo atual (R$ {saldo:,.2f}) pela despesa média diária."

    if any(
        palavra in msg_lower for palavra in ["como está", "situação", "saúde", "status"]
    ):
        if status == "critico":
            return f"🔴 **Situação CRÍTICA!**\n\nSeu caixa está com apenas {dias_caixa:.1f} dias.\n\n**Ações recomendadas:**\n- Cortar despesas não essenciais\n- Acelerar cobranças\n- Buscar empréstimo/capital\n- Revisar planejamento urgentemente"
        if status == "alerta":
            return f"🟡 **Situação de ALERTA**\n\nVocê tem {dias_caixa:.1f} dias de caixa.\n\n**Recomendações:**\n- Monitorar diariamente\n- Evitar grandes gastos\n- Planejar com cuidado\n- Cobrar clientes em atraso"
        return f"🟢 **Situação OK!**\n\nVocê tem {dias_caixa:.1f} dias de caixa.\n\nSeu negócio está saudável financeiramente. Continue monitorando e aproveite para investir em crescimento."

    if any(
        palavra in msg_lower for palavra in ["alerta", "aviso", "problema", "risco"]
    ):
        if alertas:
            resposta = f"⚠️ **Você tem {len(alertas)} alerta(s):**\n\n"
            for i, alerta in enumerate(alertas[:3], 1):
                resposta += f"{i}. **{alerta.get('titulo', 'Alerta')}**\n   {alerta.get('mensagem', '')}\n\n"
            return resposta
        return "✅ **Nenhum alerta no momento!**\n\nSeu caixa está saudável e não há riscos iminentes."

    if any(
        palavra in msg_lower
        for palavra in ["projeção", "previsão", "futuro", "próximos dias"]
    ):
        if projecoes:
            resposta = "📈 **Projeção dos próximos 7 dias:**\n\n"
            for proj in projecoes[:7]:
                data = proj.get("data", "").split("T")[0]
                saldo_est = proj.get("saldo_estimado", 0)
                resposta += f"- **{data}**: R$ {saldo_est:,.2f}\n"
            return resposta
        return "Não há projeções disponíveis no momento. Clique em 'Atualizar Projeção' no Dashboard."

    return f'Olá! 👋 Sou seu assistente financeiro com IA.\n\n**Perguntas que você pode fazer agora:**\n- "vendas de março"\n- "vendas dos últimos 15 dias"\n- "compare março com fevereiro"\n- "compare por canal este mês com o mês anterior"\n- "produto mais vendido no mês"\n- "melhor margem por categoria"\n- "desempenho por canal"\n- "DRE de março"\n- "qual é meu saldo atual?"\n- "há algum alerta?"\n- "me dá um raio-x do negócio"\n\n📊 **Resumo rápido:**\n- Saldo: {moeda(float(saldo))}\n- Dias de caixa: {dias_caixa:.1f}\n- Status: {status.upper()}'
