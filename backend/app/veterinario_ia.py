"""Helpers de IA do modulo veterinario."""


def _responder_chat_exame(
    *,
    pergunta: str,
    exame_nome: str,
    tipo_exame: str,
    especie: str,
    nome_pet: str,
    alergias: list,
    alertas: list,
    resumo_ia: str,
    conclusao_ia: str,
    dados_json: dict,
    texto_resultado: str,
    payload_ia: dict,
    tem_arquivo: bool,
) -> str:
    """Responde perguntas clinicas usando regras contextuais e os dados do exame."""

    if not conclusao_ia and not resumo_ia:
        if tem_arquivo:
            resumo_ia = "Ainda sem interpretação automática concluída. Use 'Processar arquivo + IA' para extrair o arquivo anexado."
        else:
            resumo_ia = "Ainda sem interpretação automática. Use 'Interpretar com IA' antes de perguntar."
        conclusao_ia = resumo_ia

    alertas_mensagens = [a.get("mensagem", "") for a in alertas if isinstance(a, dict)]
    achados_imagem = payload_ia.get("achados_imagem") if isinstance(payload_ia, dict) else []
    limitacoes = payload_ia.get("limitacoes") if isinstance(payload_ia, dict) else []
    conduta_sugerida = payload_ia.get("conduta_sugerida") if isinstance(payload_ia, dict) else []

    if any(k in pergunta for k in ["resumo", "resumir", "explicar", "o que diz", "o que significa", "resultado"]):
        if not texto_resultado and not dados_json:
            return f"O exame '{exame_nome}' ainda não tem resultado registrado. Adicione o resultado antes de solicitar a interpretação."
        partes = []
        if conclusao_ia:
            partes.append(f"**Conclusão da triagem automática:** {conclusao_ia}")
        if resumo_ia and resumo_ia != conclusao_ia:
            partes.append(f"**Detalhes:** {resumo_ia}")
        if alertas_mensagens:
            partes.append("**Alertas encontrados:** " + "; ".join(alertas_mensagens))
        return "\n\n".join(partes) if partes else "Nenhuma interpretação disponível ainda."

    if any(k in pergunta for k in ["alerta", "preocupante", "crítico", "grave", "urgente", "emergência"]):
        if not alertas:
            return f"A triagem automática do exame '{exame_nome}' não encontrou alertas críticos. Isso não substitui a avaliação clínica — verifique os valores numericamente se disponíveis."
        msgs = "\n- ".join(alertas_mensagens) if alertas_mensagens else "Alertas detectados, mas sem detalhes textuais."
        return f"**Pontos de atenção encontrados no exame {exame_nome}:**\n\n- {msgs}\n\nRecomendo revisão clínica presencial."

    if any(k in pergunta for k in ["normal", "status", "tudo certo", "está bem", "dentro do normal"]):
        if not alertas:
            return f"A triagem automática não encontrou valores fora do padrão em '{exame_nome}'. O exame parece dentro da normalidade pelos critérios automatizados — confirme com avaliação clínica."
        return f"Foram encontrados {len(alertas)} ponto(s) de atenção: {resumo_ia}. Revise os valores clínicamente."

    if any(k in pergunta for k in ["próximo passo", "conduta", "tratamento", "o que fazer", "recomendação"]):
        if alertas:
            return (
                f"Com base nos alertas encontrados em '{exame_nome}' ({especie}), a conduta sugerida é:\n\n"
                f"1. Avaliar os itens fora do normal diretamente nos valores do resultado\n"
                f"2. Correlacionar com sinais clínicos de {nome_pet}\n"
                f"3. Considerar exames complementares se necessário\n"
                f"4. Registrar diagnóstico e tratamento na consulta\n\n"
                f"_Alertas identificados: {resumo_ia}_"
            )
        return (
            f"A triagem automática de '{exame_nome}' não indicou alterações críticas.\n"
            f"Sugestões gerais de conduta:\n\n"
            f"1. Confirmar valores com referências da espécie ({especie})\n"
            f"2. Correlacionar com os sinais clínicos de {nome_pet}\n"
            f"3. Repetir o exame conforme evolução clínica\n"
        )

    if any(k in pergunta for k in ["alergia", "medicamento", "contraindicado", "intolerância"]):
        if alergias:
            lista_al = ", ".join(alergias)
            return (
                f"{nome_pet} tem alergias registradas: **{lista_al}**.\n\n"
                f"Ao definir o tratamento com base no exame '{exame_nome}', evite medicamentos ou substâncias relacionadas."
            )
        return f"Não há alergias registradas para {nome_pet}. Verifique a ficha clínica para mais segurança."

    if any(k in pergunta for k in ["leucocit", "hemograma", "glóbulo", "eritrocit"]):
        dados_hemo = {
            k: v
            for k, v in dados_json.items()
            if any(t in k.lower() for t in ["leuco", "eritro", "hemo", "plaqueta", "glob"])
        }
        if dados_hemo:
            linhas = "\n".join(f"- {k}: {v}" for k, v in dados_hemo.items())
            return f"Valores hematológicos registrados no resultado:\n{linhas}\n\nInterpretação geral: {resumo_ia or 'sem interpretação automática disponível'}"
        return f"Não há valores hematológicos estruturados no resultado do exame '{exame_nome}'. Verifique o texto do laudo ou reenvie como JSON estruturado."

    if any(k in pergunta for k in ["rim", "renal", "creatinina", "ureia", "uréia"]):
        dados_renal = {
            k: v
            for k, v in dados_json.items()
            if any(t in k.lower() for t in ["creat", "ureia", "uria", "rim", "renal", "tgo", "tgp"])
        }
        if dados_renal:
            linhas = "\n".join(f"- {k}: {v}" for k, v in dados_renal.items())
            return f"Valores relacionados à função renal/hepática:\n{linhas}\n\n{resumo_ia or 'Consulte a interpretação automática.'}"
        return "Não há parâmetros renais estruturados no resultado. Verifique o laudo original."

    if any(k in pergunta for k in ["imagem", "raio", "ultrassom", "eco", "rx", "radiografia"]):
        if tipo_exame in {"radiografia", "ultrassom", "ecocardiograma", "imagem"}:
            if achados_imagem:
                partes = [
                    f"**Achados sugeridos pela análise do arquivo em '{exame_nome}':**",
                    "\n- " + "\n- ".join(str(item) for item in achados_imagem if str(item).strip()),
                ]
                if limitacoes:
                    partes.append("\n**Limitações:** " + "; ".join(str(item) for item in limitacoes if str(item).strip()))
                partes.append("\nConfirme sempre com o laudo do especialista e a correlação clínica.")
                return "".join(partes)
            return (
                f"O exame '{exame_nome}' é do tipo imagem. "
                f"A interpretação de imagens requer avaliação por médico veterinário especialista. "
                f"Use os campos de resultado para registrar o laudo textual do radiologista/ultrassonografista, "
                f"que será incluído automaticamente na triagem."
            )
        return "Este exame não é do tipo imagem. Verifique o tipo de exame cadastrado."

    partes_resposta = [f"Sobre o exame **{exame_nome}** de {nome_pet} ({especie}):"]
    if conclusao_ia:
        partes_resposta.append(f"\n**Interpretação automática:** {conclusao_ia}")
    if alertas_mensagens:
        partes_resposta.append(f"\n**Pontos de atenção:** {'; '.join(alertas_mensagens)}")
    if not conclusao_ia and not alertas:
        if tem_arquivo:
            partes_resposta.append(
                "\nAinda sem interpretação final. O arquivo já foi anexado, então você pode usar 'Processar arquivo + IA' para extrair e resumir o exame."
            )
        else:
            partes_resposta.append(
                "\nAinda sem interpretação. Registre o resultado e use 'Interpretar com IA' para uma análise automática."
            )
    if conduta_sugerida:
        partes_resposta.append(
            f"\n**Sugestões de conduta:** {'; '.join(str(item) for item in conduta_sugerida if str(item).strip())}"
        )
    partes_resposta.append(
        "\n\n_Dica: tente perguntas como 'O que diz o resultado?', 'Há alertas?', 'Qual a conduta recomendada?' ou 'Tem risco de alergia?'_"
    )
    return "".join(partes_resposta)
