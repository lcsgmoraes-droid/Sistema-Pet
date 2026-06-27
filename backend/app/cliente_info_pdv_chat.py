"""Chat contextual de cliente no PDV."""

import json
import os
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import get_current_user_and_tenant
from app.cliente_info_pdv_schemas import ChatPDVRequest
from app.db import get_session
from app.models import Cliente, Pet
from app.produtos_models import Produto
from app.vendas_models import Venda, VendaItem

router = APIRouter()


@router.post("/{cliente_id}/chat-pdv")
async def chat_pdv_cliente(
    cliente_id: int,
    request: ChatPDVRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Chat IA contextual sobre o cliente no PDV.
    Envia contexto completo do cliente para um LLM real (Groq/OpenAI/Gemini).
    """
    _current_user, tenant_id = user_and_tenant

    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id, Cliente.ativo)
        .first()
    )

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nÃ£o encontrado")

    # â”€â”€ 1. VENDAS: Ãºltimas 30, ordenadas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    vendas = (
        db.query(Venda)
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status != "cancelada",
        )
        .order_by(desc(Venda.data_venda))
        .limit(30)
        .all()
    )

    total_gasto = sum(float(v.total) for v in vendas)
    ticket_medio = total_gasto / len(vendas) if vendas else 0

    # â”€â”€ 2. ITENS de todas as vendas (1 query por venda, mÃ¡x 30) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    historico_detalhado = []
    produtos_counter = Counter()
    produtos_ultima_compra = {}  # produto_id â†’ Ãºltima data de compra
    produtos_primeira_compra = {}  # produto_id â†’ primeira data de compra

    for idx, venda in enumerate(vendas):
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        for item in itens:
            if item.produto_id:
                produtos_counter[item.produto_id] += 1
                if (
                    item.produto_id not in produtos_ultima_compra
                    or venda.data_venda > produtos_ultima_compra[item.produto_id]
                ):
                    produtos_ultima_compra[item.produto_id] = venda.data_venda
                if (
                    item.produto_id not in produtos_primeira_compra
                    or venda.data_venda < produtos_primeira_compra[item.produto_id]
                ):
                    produtos_primeira_compra[item.produto_id] = venda.data_venda
        if idx < 10:
            nomes_itens = []
            for item in itens:
                if item.produto:
                    nome = item.produto.nome
                elif item.servico_descricao:
                    nome = item.servico_descricao
                else:
                    nome = f"Produto #{item.produto_id}"
                qtd = float(item.quantidade)
                nomes_itens.append(f"{nome} x{qtd:.0f}")
            historico_detalhado.append(
                f"  â€¢ {venda.data_venda.strftime('%d/%m/%Y')} â€” R$ {float(venda.total):.2f}: {', '.join(nomes_itens)}"
            )

    # â”€â”€ 3. TOP PRODUTOS (com frequÃªncia + dias desde Ãºltima compra) â”€â”€â”€â”€â”€â”€â”€
    top_produtos_lines = []
    for produto_id, qtd in produtos_counter.most_common(10):
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if produto:
            ultima = produtos_ultima_compra.get(produto_id)
            dias = (datetime.now() - ultima).days if ultima else None
            dias_str = f", {dias}d atrÃ¡s" if dias is not None else ""
            top_produtos_lines.append(f"    - {produto.nome} ({qtd}x{dias_str})")

    # â”€â”€ 4. POTENCIAIS REABASTECIMENTOS (sem queries extras) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    alertas_reabastecimento = []
    for produto_id, qtd in produtos_counter.most_common():
        if qtd < 2:
            break
        primeira = produtos_primeira_compra.get(produto_id)
        ultima = produtos_ultima_compra.get(produto_id)
        if not primeira or not ultima or primeira == ultima:
            continue
        dias_desde = (datetime.now() - ultima).days
        # Intervalo mÃ©dio: spread total / (nÂº compras - 1)
        intervalo_medio = (ultima - primeira).days / (qtd - 1)
        if intervalo_medio < 5:  # ignora produtos de intervalo irrealista
            continue
        atraso = dias_desde - intervalo_medio
        if atraso > 7:
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if produto:
                alertas_reabastecimento.append(
                    f"    âš ï¸ {produto.nome}: compra a cada ~{int(intervalo_medio)}d, Ãºltima hÃ¡ {dias_desde}d ({int(atraso)}d atrasado)"
                )

    # â”€â”€ 5. PETS (detalhes completos com saÃºde) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    pets = db.query(Pet).filter(Pet.cliente_id == cliente_id, Pet.ativo).all()
    pets_lines = []
    pets_data = []  # usado nas anÃ¡lises do carrinho
    for pet in pets:
        idade_anos = None
        if pet.data_nascimento:
            data_nasc = (
                pet.data_nascimento.date()
                if isinstance(pet.data_nascimento, datetime)
                else pet.data_nascimento
            )
            idade_anos = (datetime.now().date() - data_nasc).days // 365
        peso_val = float(pet.peso) if pet.peso else None
        raca_str = f" ({pet.raca})" if pet.raca else ""
        fase = (
            "filhote"
            if (idade_anos is not None and idade_anos < 1)
            else "idoso"
            if (idade_anos is not None and idade_anos >= 7)
            else "adulto"
        )
        linha = f"    - {pet.nome}: {pet.especie}{raca_str}"
        if idade_anos is not None:
            linha += f", {idade_anos} anos ({fase})"
        if peso_val:
            linha += f", {peso_val:.1f}kg"
        if pet.alergias:
            linha += f"\n      âš ï¸ ALERGIAS: {pet.alergias}"
        if pet.doencas_cronicas:
            linha += f"\n      ðŸ¥ DoenÃ§as crÃ´nicas: {pet.doencas_cronicas}"
        if pet.medicamentos_continuos:
            linha += f"\n      ðŸ’Š Medicamentos: {pet.medicamentos_continuos}"
        if pet.historico_clinico:
            linha += f"\n      ðŸ“‹ HistÃ³rico: {pet.historico_clinico}"
        pets_lines.append(linha)
        pets_data.append(
            {
                "nome": pet.nome,
                "especie": pet.especie,
                "raca": pet.raca,
                "idade_anos": idade_anos,
                "peso_kg": peso_val,
                "fase": fase,
                "alergias": pet.alergias or "",
                "doencas": pet.doencas_cronicas or "",
            }
        )

    # â”€â”€ 6. CARRINHO ATUAL + ANÃLISE DE RAÃ‡Ã•ES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    carrinho_lines = []
    alertas_carrinho = []

    if request.carrinho:
        for item_c in request.carrinho:
            linha_c = f"    - {item_c.produto_nome} x{item_c.quantidade:.0f} (R$ {item_c.preco_unitario:.2f}/un)"
            produto_db = None
            if item_c.produto_id:
                produto_db = (
                    db.query(Produto).filter(Produto.id == item_c.produto_id).first()
                )

            if produto_db and produto_db.peso_embalagem:
                # Ã‰ raÃ§Ã£o â€” enriquecer com dados nutricionais
                nutri = {}
                if produto_db.tabela_nutricional:
                    try:
                        nutri = json.loads(produto_db.tabela_nutricional)
                    except Exception:
                        pass

                nutri_str = ""
                if nutri:
                    partes = []
                    for k, v in nutri.items():
                        partes.append(f"{k}: {v}%")
                    nutri_str = f" | Nutri: {', '.join(partes)}"

                linha_c += f"\n      ðŸ¾ RaÃ§Ã£o {produto_db.classificacao_racao or ''} | {produto_db.peso_embalagem}kg"
                if produto_db.categoria_racao:
                    linha_c += f" | Fase: {produto_db.categoria_racao}"
                if produto_db.sabor_proteina:
                    linha_c += f" | ProteÃ­na: {produto_db.sabor_proteina}"
                linha_c += nutri_str

                # Calcular duraÃ§Ã£o por pet
                for pet in pets_data:
                    if pet["peso_kg"] and pet["peso_kg"] > 0:
                        from app.calculadora_racao import calcular_quantidade_diaria

                        qtd_diaria_g = calcular_quantidade_diaria(
                            peso_pet_kg=pet["peso_kg"],
                            idade_meses=int(pet["idade_anos"] * 12)
                            if pet["idade_anos"] is not None
                            else None,
                            nivel_atividade="normal",
                            tabela_consumo_json=None,
                        )
                        total_g = produto_db.peso_embalagem * 1000 * item_c.quantidade
                        duracao_dias = (
                            int(total_g / qtd_diaria_g) if qtd_diaria_g > 0 else None
                        )
                        custo_dia = (
                            (item_c.preco_unitario * item_c.quantidade) / duracao_dias
                            if duracao_dias
                            else None
                        )
                        if duracao_dias:
                            linha_c += f"\n      ðŸ“… Para {pet['nome']} ({pet['peso_kg']}kg): ~{qtd_diaria_g:.0f}g/dia â†’ dura {duracao_dias} dias (R$ {custo_dia:.2f}/dia)"

                # Alertas automÃ¡ticos: fase de vida
                if produto_db.categoria_racao:
                    for pet in pets_data:
                        fase_racao = produto_db.categoria_racao.lower()
                        fase_pet = pet["fase"]
                        if (
                            fase_pet == "idoso"
                            and "senior" not in fase_racao
                            and "idoso" not in fase_racao
                            and "sÃªnior" not in fase_racao
                        ):
                            alertas_carrinho.append(
                                f"    âš ï¸ {pet['nome']} Ã© IDOSO ({pet['idade_anos']} anos) mas a raÃ§Ã£o '{produto_db.nome}' Ã© para '{produto_db.categoria_racao}' â€” considere recomendar raÃ§Ã£o sÃªnior"
                            )
                        elif fase_pet == "filhote" and "filhote" not in fase_racao:
                            alertas_carrinho.append(
                                f"    âš ï¸ {pet['nome']} Ã© FILHOTE mas a raÃ§Ã£o '{produto_db.nome}' Ã© para '{produto_db.categoria_racao}'"
                            )

                # Alertas: proteÃ­na x alergia do pet
                if produto_db.sabor_proteina:
                    for pet in pets_data:
                        if (
                            pet["alergias"]
                            and produto_db.sabor_proteina.lower()
                            in pet["alergias"].lower()
                        ):
                            alertas_carrinho.append(
                                f"    ðŸš¨ {pet['nome']} tem ALERGIA registrada a '{produto_db.sabor_proteina}' e a raÃ§Ã£o '{produto_db.nome}' contÃ©m essa proteÃ­na!"
                            )

            carrinho_lines.append(linha_c)

    # â”€â”€ 7. CONTEXTO COMPLETO PARA A IA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    dias_desde_ultima = (datetime.now() - vendas[0].data_venda).days if vendas else None
    contexto = f"""
=== CLIENTE ===
Nome: {cliente.nome}
CPF/CNPJ: {cliente.cpf or cliente.cnpj or "nÃ£o informado"}
Telefone: {cliente.telefone or cliente.celular or "nÃ£o informado"}
Cidade: {f"{cliente.cidade}/{cliente.estado}" if cliente.cidade else "nÃ£o informada"}

=== CARRINHO ATUAL ===
{chr(10).join(carrinho_lines) if carrinho_lines else "  (carrinho vazio)"}

=== ALERTAS DO CARRINHO ===
{chr(10).join(alertas_carrinho) if alertas_carrinho else "  Nenhum alerta detectado."}

=== HISTÃ“RICO DE COMPRAS ===
Total de compras: {len(vendas)}
Total gasto: R$ {total_gasto:.2f}
Ticket mÃ©dio: R$ {ticket_medio:.2f}
Ãšltima compra: {vendas[0].data_venda.strftime("%d/%m/%Y") + f" (hÃ¡ {dias_desde_ultima} dias)" if vendas else "nunca"}

Detalhes das Ãºltimas {min(10, len(vendas))} compras:
{chr(10).join(historico_detalhado) if historico_detalhado else "  (nenhuma)"}

=== PRODUTOS MAIS COMPRADOS ===
{chr(10).join(top_produtos_lines) if top_produtos_lines else "  (nenhum)"}

=== ALERTAS DE REABASTECIMENTO ===
{chr(10).join(alertas_reabastecimento) if alertas_reabastecimento else "  Nenhum atrasado no momento."}

=== PETS (perfil completo) ===
{chr(10).join(pets_lines) if pets_lines else "  Nenhum pet cadastrado."}
""".strip()

    SYSTEM_PROMPT = """VocÃª Ã© um assistente especializado em atendimento de Pet Shop, rodando direto no caixa (PDV).

Seu papel Ã© ajudar o OPERADOR DE CAIXA a atender melhor o cliente que estÃ¡ na frente dele AGORA.

VocÃª tem acesso ao:
- CARRINHO ATUAL: o que o cliente estÃ¡ comprando neste momento, com tabela nutricional das raÃ§Ãµes, duraÃ§Ã£o estimada por pet, e alertas jÃ¡ detectados automaticamente
- HISTÃ“RICO COMPLETO de compras do cliente
- PERFIL COMPLETO dos pets: espÃ©cie, raÃ§a, idade, peso, fase de vida (filhote/adulto/idoso), alergias, doenÃ§as crÃ´nicas, medicamentos
- ALERTAS jÃ¡ calculados (ex: raÃ§Ã£o errada para a fase de vida, alergia detectada)

Regras:
- Responda SEMPRE em portuguÃªs do Brasil
- Seja BREVE e DIRETO (mÃ¡ximo 4-5 linhas normalmente, a nÃ£o ser que pedirem detalhes)
- Foque no que Ã© Ãºtil AGORA para o atendimento
- Se hÃ¡ ALERTAS DO CARRINHO, priorize mencionÃ¡-los quando relevante
- Para perguntas de duraÃ§Ã£o de raÃ§Ã£o: use os dados jÃ¡ calculados no contexto (duraÃ§Ã£o em dias por pet)
- Para perguntas sobre alergia ou saÃºde: seja cuidadoso e sugira consulta veterinÃ¡ria quando necessÃ¡rio
- NÃ£o invente informaÃ§Ãµes â€” use apenas o que estÃ¡ no contexto
- Quando sugerir produtos alternativos, seja especÃ­fico (ex: "raÃ§Ã£o sÃªnior para cÃ£es de porte mÃ©dio")
"""

    try:
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")

        resposta_ia = None

        if groq_key:
            from groq import Groq

            client_ia = Groq(api_key=groq_key)
            completion = client_ia.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + contexto},
                    {"role": "user", "content": request.mensagem},
                ],
                temperature=0.4,
                max_tokens=400,
            )
            resposta_ia = completion.choices[0].message.content

        elif openai_key:
            from openai import OpenAI

            client_ia = OpenAI(api_key=openai_key)
            completion = client_ia.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + contexto},
                    {"role": "user", "content": request.mensagem},
                ],
                temperature=0.4,
                max_tokens=400,
            )
            resposta_ia = completion.choices[0].message.content

        elif gemini_key:
            import google.generativeai as genai

            genai.configure(api_key=gemini_key)
            model_ia = genai.GenerativeModel("gemini-1.5-flash")
            prompt_completo = (
                SYSTEM_PROMPT
                + "\n\n"
                + contexto
                + f"\n\nPergunta do operador: {request.mensagem}"
            )
            response = model_ia.generate_content(prompt_completo)
            resposta_ia = response.text

        else:
            resposta_ia = gerar_resposta_sem_ia(
                request.mensagem,
                cliente,
                vendas,
                [linha.strip("- ") for linha in top_produtos_lines[:5]],
                pets_lines,
            )

        return {
            "resposta": resposta_ia,
            "ia_disponivel": bool(groq_key or openai_key or gemini_key),
        }

    except Exception as e:
        return {
            "resposta": gerar_resposta_sem_ia(
                request.mensagem,
                cliente,
                vendas,
                [linha.strip("- ") for linha in top_produtos_lines[:5]],
                pets_lines,
            ),
            "ia_disponivel": False,
            "erro": str(e),
        }


def gerar_resposta_sem_ia(mensagem: str, cliente, vendas, top_produtos, pets_info):
    """Gera respostas bÃ¡sicas sem IA quando API nÃ£o estÃ¡ disponÃ­vel"""

    msg_lower = mensagem.lower()

    if any(
        palavra in msg_lower for palavra in ["compra", "comprou", "produto", "favorito"]
    ):
        if top_produtos:
            return f"Os produtos favoritos de {cliente.nome} sÃ£o: {', '.join(top_produtos)}. JÃ¡ comprou {len(vendas)} vezes conosco."
        else:
            return f"{cliente.nome} ainda nÃ£o tem histÃ³rico de compras."

    elif any(palavra in msg_lower for palavra in ["pet", "animal", "cachorro", "gato"]):
        if pets_info:
            return (
                f"{cliente.nome} tem {len(pets_info)} pet(s): {', '.join(pets_info)}."
            )
        else:
            return f"{cliente.nome} nÃ£o tem pets cadastrados."

    elif any(palavra in msg_lower for palavra in ["Ãºltima", "ultimo", "recente"]):
        if vendas:
            ultima = vendas[0]
            return f"Ãšltima compra: {ultima.data_venda.strftime('%d/%m/%Y')}, no valor de R$ {float(ultima.total):.2f}."
        else:
            return "Cliente ainda nÃ£o fez compras."

    elif any(
        palavra in msg_lower for palavra in ["total", "quanto", "gastou", "valor"]
    ):
        total = sum(float(v.total) for v in vendas)
        return f"{cliente.nome} jÃ¡ gastou R$ {total:.2f} em {len(vendas)} compras."

    else:
        return f"ðŸ“Š InformaÃ§Ãµes de {cliente.nome}: {len(vendas)} compras, {len(pets_info)} pet(s) cadastrado(s). Pergunte sobre produtos favoritos, Ãºltima compra ou pets!"
