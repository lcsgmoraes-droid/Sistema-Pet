"""
Endpoint especializado para informações do cliente no PDV
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import Counter, defaultdict
from pydantic import BaseModel
import os

from app.db import get_session
from app.models import User, Cliente, Pet
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto
from app.auth import get_current_user, get_current_user_and_tenant

router = APIRouter(prefix="/clientes", tags=["clientes"])

# Schema para chat IA
class ChatPDVRequest(BaseModel):
    mensagem: str


@router.get("/{cliente_id}/info-pdv")
def get_cliente_info_pdv(
    cliente_id: int,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Retorna informações completas do cliente para exibir no PDV:
    - Resumo financeiro (total gasto, ticket médio, etc)
    - Pets registrados
    - Últimas compras (histórico)
    - Oportunidades (produtos que deve reabastecer)
    - Sugestões de produtos baseadas no histórico
    """
    current_user, tenant_id = user_and_tenant
    
    # Buscar cliente
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id,
        Cliente.ativo == True
    ).first()
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # ========== 1. RESUMO FINANCEIRO ==========
    vendas = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status != 'cancelada'
    ).all()
    
    total_gasto = sum(float(v.total) for v in vendas)
    numero_compras = len(vendas)
    ticket_medio = total_gasto / numero_compras if numero_compras > 0 else 0
    maior_compra = max((float(v.total) for v in vendas), default=0)
    maior_compra_venda = max(vendas, key=lambda v: float(v.total), default=None) if vendas else None
    
    # Última compra
    ultima_venda = sorted(vendas, key=lambda v: v.data_venda, reverse=True)[0] if vendas else None
    
    resumo_financeiro = {
        "total_gasto": round(total_gasto, 2),
        "numero_compras": numero_compras,
        "ticket_medio": round(ticket_medio, 2),
        "maior_compra": {
            "valor": round(maior_compra, 2),
            "data": maior_compra_venda.data_venda.strftime("%d/%m/%Y") if maior_compra_venda else None,
            "numero_venda": maior_compra_venda.numero_venda if maior_compra_venda else None
        },
        "ultima_compra": {
            "numero_venda": ultima_venda.numero_venda if ultima_venda else None,
            "data": ultima_venda.data_venda.strftime("%d/%m/%Y") if ultima_venda else None,
            "valor": float(ultima_venda.total) if ultima_venda else 0
        }
    }
    
    # ========== 2. PETS REGISTRADOS ==========
    pets = db.query(Pet).filter(
        Pet.cliente_id == cliente_id,
        Pet.ativo == True
    ).all()
    
    pets_info = []
    for pet in pets:
        idade_anos = None
        if pet.data_nascimento:
            # Garantir que data_nascimento seja date (não datetime)
            data_nasc = pet.data_nascimento.date() if isinstance(pet.data_nascimento, datetime) else pet.data_nascimento
            idade = datetime.now().date() - data_nasc
            idade_anos = idade.days // 365
        
        pets_info.append({
            "id": pet.id,
            "nome": pet.nome,
            "especie": pet.especie,
            "raca": pet.raca,
            "peso": float(pet.peso) if pet.peso else None,
            "idade_anos": idade_anos,
            "sexo": pet.sexo
        })
    
    # ========== 3. ÚLTIMAS COMPRAS (5 mais recentes) ==========
    ultimas_vendas = sorted(vendas, key=lambda v: v.data_venda, reverse=True)[:5]
    
    ultimas_compras = []
    for venda in ultimas_vendas:
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        
        produtos = []
        for item in itens:
            if item.produto_id:
                produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
                produtos.append({
                    "nome": produto.nome if produto else "Produto deletado",
                    "quantidade": float(item.quantidade),
                    "valor": float(item.subtotal)
                })
        
        ultimas_compras.append({
            "data": venda.data_venda.strftime("%d/%m/%Y"),
            "numero_venda": venda.numero_venda,
            "valor_total": float(venda.total),
            "produtos": produtos[:3]  # Limitar a 3 produtos por venda
        })
    
    # ========== 4. ANÁLISE DE PADRÕES (Oportunidades) ==========
    # Pegar produtos mais comprados
    produtos_comprados = {}
    for venda in vendas:
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        for item in itens:
            if item.produto_id:
                if item.produto_id not in produtos_comprados:
                    produtos_comprados[item.produto_id] = {
                        "quantidade_vezes": 0,
                        "ultima_compra": None,
                        "quantidade_total": 0
                    }
                produtos_comprados[item.produto_id]["quantidade_vezes"] += 1
                produtos_comprados[item.produto_id]["quantidade_total"] += float(item.quantidade)
                if not produtos_comprados[item.produto_id]["ultima_compra"] or venda.data_venda > produtos_comprados[item.produto_id]["ultima_compra"]:
                    produtos_comprados[item.produto_id]["ultima_compra"] = venda.data_venda
    
    # Calcular intervalo médio de compra para produtos recorrentes
    oportunidades = []
    for produto_id, info in produtos_comprados.items():
        if info["quantidade_vezes"] >= 2:  # Produto comprado pelo menos 2x
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if not produto:
                continue
            
            # Pegar todas as datas de compra desse produto
            vendas_produto = db.query(Venda).join(VendaItem).filter(
                VendaItem.produto_id == produto_id,
                Venda.cliente_id == cliente_id,
                Venda.status != 'cancelada'
            ).order_by(Venda.data_venda).all()
            
            if len(vendas_produto) >= 2:
                # Calcular intervalo médio entre compras
                intervalos = []
                for i in range(1, len(vendas_produto)):
                    delta = (vendas_produto[i].data_venda - vendas_produto[i-1].data_venda).days
                    intervalos.append(delta)
                
                intervalo_medio = sum(intervalos) / len(intervalos) if intervalos else 0
                
                # Verificar se está atrasado
                if info["ultima_compra"]:
                    dias_desde_ultima = (datetime.now() - info["ultima_compra"]).days
                    
                    # Se passou do intervalo médio + margem de 7 dias
                    if dias_desde_ultima > (intervalo_medio + 7):
                        oportunidades.append({
                            "tipo": "reabastecimento",
                            "produto_nome": produto.nome,
                            "produto_id": produto.id,
                            "mensagem": f"{produto.nome} normalmente a cada {int(intervalo_medio)} dias (última: {info['ultima_compra'].strftime('%d/%m/%Y')} - {dias_desde_ultima} dias atrás)",
                            "urgencia": "alta" if dias_desde_ultima > (intervalo_medio + 14) else "media",
                            "dias_atraso": dias_desde_ultima - int(intervalo_medio)
                        })
    
    # ========== 5. SUGESTÕES (produtos mais comprados) ==========
    produtos_mais_comprados = sorted(
        produtos_comprados.items(),
        key=lambda x: x[1]["quantidade_vezes"],
        reverse=True
    )[:5]
    
    sugestoes = []
    for produto_id, info in produtos_mais_comprados:
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if produto:
            sugestoes.append({
                "produto_id": produto.id,
                "nome": produto.nome,
                "preco": float(produto.preco_venda),
                "vezes_comprado": info["quantidade_vezes"],
                "ultima_compra": info["ultima_compra"].strftime("%d/%m/%Y") if info["ultima_compra"] else None
            })
    
    # ========== 6. ANÁLISE DE PRODUTOS COMPRADOS JUNTOS ==========
    # Análise de co-ocorrência (produtos comprados na mesma venda)
    combinacoes = defaultdict(int)
    produtos_por_venda = defaultdict(set)
    
    for venda in vendas:
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        produtos_venda = [item.produto_id for item in itens if item.produto_id]
        
        # Registrar produtos desta venda
        for p_id in produtos_venda:
            produtos_por_venda[venda.id].add(p_id)
        
        # Contar combinações (produtos que aparecem juntos)
        for i, p1 in enumerate(produtos_venda):
            for p2 in produtos_venda[i+1:]:
                if p1 != p2:
                    par = tuple(sorted([p1, p2]))
                    combinacoes[par] += 1
    
    # Top 5 combinações mais frequentes
    produtos_relacionados = []
    for (p1_id, p2_id), frequencia in sorted(combinacoes.items(), key=lambda x: x[1], reverse=True)[:5]:
        p1 = db.query(Produto).filter(Produto.id == p1_id).first()
        p2 = db.query(Produto).filter(Produto.id == p2_id).first()
        if p1 and p2:
            produtos_relacionados.append({
                "produto1": {"id": p1.id, "nome": p1.nome, "preco": float(p1.preco_venda)},
                "produto2": {"id": p2.id, "nome": p2.nome, "preco": float(p2.preco_venda)},
                "vezes_juntos": frequencia
            })
    
    # ========== 7. ANÁLISE SAZONAL ==========
    # Agrupar vendas por mês
    vendas_por_mes = defaultdict(lambda: {"total": 0, "quantidade": 0})
    for venda in vendas:
        mes_ano = venda.data_venda.strftime("%m/%Y")
        vendas_por_mes[mes_ano]["total"] += float(venda.total)
        vendas_por_mes[mes_ano]["quantidade"] += 1
    
    # Últimos 6 meses
    padroes_sazonais = []
    for mes_ano, dados in sorted(vendas_por_mes.items(), reverse=True)[:6]:
        padroes_sazonais.append({
            "mes_ano": mes_ano,
            "total_gasto": round(dados["total"], 2),
            "numero_compras": dados["quantidade"],
            "ticket_medio": round(dados["total"] / dados["quantidade"], 2) if dados["quantidade"] > 0 else 0
        })
    
    # ========== RESPOSTA COMPLETA ==========
    return {
        "cliente": {
            "id": cliente.id,
            "codigo": cliente.codigo,
            "nome": cliente.nome,
            "cpf_cnpj": cliente.cpf or cliente.cnpj,
            "telefone": cliente.telefone or cliente.celular,
            "email": cliente.email,
            "endereco": cliente.endereco,
            "numero": cliente.numero,
            "bairro": cliente.bairro,
            "cidade": cliente.cidade,
            "estado": cliente.estado
        },
        "resumo_financeiro": resumo_financeiro,
        "pets": pets_info,
        "ultimas_compras": ultimas_compras,
        "oportunidades": oportunidades,
        "sugestoes": sugestoes,
        "produtos_relacionados": produtos_relacionados,
        "padroes_sazonais": padroes_sazonais
    }


@router.post("/{cliente_id}/chat-pdv")
async def chat_pdv_cliente(
    cliente_id: int,
    request: ChatPDVRequest,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Chat IA contextual sobre o cliente no PDV.
    Envia contexto completo do cliente para um LLM real (Groq/OpenAI/Gemini).
    """
    current_user, tenant_id = user_and_tenant

    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.tenant_id == tenant_id,
        Cliente.ativo == True
    ).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # ── 1. VENDAS: últimas 30, ordenadas ──────────────────────────────────
    vendas = db.query(Venda).filter(
        Venda.cliente_id == cliente_id,
        Venda.tenant_id == tenant_id,
        Venda.status != 'cancelada'
    ).order_by(desc(Venda.data_venda)).limit(30).all()

    total_gasto = sum(float(v.total) for v in vendas)
    ticket_medio = total_gasto / len(vendas) if vendas else 0

    # ── 2. ITENS de todas as vendas (1 query por venda, máx 30) ──────────
    historico_detalhado = []
    produtos_counter = Counter()
    produtos_ultima_compra = {}   # produto_id → última data de compra
    produtos_primeira_compra = {} # produto_id → primeira data de compra

    for idx, venda in enumerate(vendas):
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        for item in itens:
            if item.produto_id:
                produtos_counter[item.produto_id] += 1
                if item.produto_id not in produtos_ultima_compra or venda.data_venda > produtos_ultima_compra[item.produto_id]:
                    produtos_ultima_compra[item.produto_id] = venda.data_venda
                if item.produto_id not in produtos_primeira_compra or venda.data_venda < produtos_primeira_compra[item.produto_id]:
                    produtos_primeira_compra[item.produto_id] = venda.data_venda
        if idx < 10:
            nomes_itens = []
            for item in itens:
                nome = item.produto_nome or f"Produto #{item.produto_id}"
                qtd = float(item.quantidade)
                nomes_itens.append(f"{nome} x{qtd:.0f}")
            historico_detalhado.append(
                f"  • {venda.data_venda.strftime('%d/%m/%Y')} — R$ {float(venda.total):.2f}: {', '.join(nomes_itens)}"
            )

    # ── 3. TOP PRODUTOS (com frequência + dias desde última compra) ───────
    top_produtos_lines = []
    for produto_id, qtd in produtos_counter.most_common(10):
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if produto:
            ultima = produtos_ultima_compra.get(produto_id)
            dias = (datetime.now() - ultima).days if ultima else None
            dias_str = f", {dias}d atrás" if dias is not None else ""
            top_produtos_lines.append(f"    - {produto.nome} ({qtd}x{dias_str})")

    # ── 4. POTENCIAIS REABASTECIMENTOS (sem queries extras) ───────────────
    alertas_reabastecimento = []
    for produto_id, qtd in produtos_counter.most_common():
        if qtd < 2:
            break
        primeira = produtos_primeira_compra.get(produto_id)
        ultima = produtos_ultima_compra.get(produto_id)
        if not primeira or not ultima or primeira == ultima:
            continue
        dias_desde = (datetime.now() - ultima).days
        # Intervalo médio: spread total / (nº compras - 1)
        intervalo_medio = (ultima - primeira).days / (qtd - 1)
        if intervalo_medio < 5:  # ignora produtos de intervalo irrealista
            continue
        atraso = dias_desde - intervalo_medio
        if atraso > 7:
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if produto:
                alertas_reabastecimento.append(
                    f"    ⚠️ {produto.nome}: compra a cada ~{int(intervalo_medio)}d, última há {dias_desde}d ({int(atraso)}d atrasado)"
                )

    # ── 5. PETS (detalhes completos) ──────────────────────────────────────
    pets = db.query(Pet).filter(Pet.cliente_id == cliente_id, Pet.ativo == True).all()
    pets_lines = []
    for pet in pets:
        idade_str = ""
        if pet.data_nascimento:
            data_nasc = pet.data_nascimento.date() if isinstance(pet.data_nascimento, datetime) else pet.data_nascimento
            idade_anos = (datetime.now().date() - data_nasc).days // 365
            idade_str = f", {idade_anos} anos"
        peso_str = f", {float(pet.peso):.1f}kg" if pet.peso else ""
        raca_str = f" ({pet.raca})" if pet.raca else ""
        pets_lines.append(f"    - {pet.nome}: {pet.especie}{raca_str}{idade_str}{peso_str}")

    # ── 6. CONTEXTO COMPLETO PARA A IA ───────────────────────────────────
    dias_desde_ultima = (datetime.now() - vendas[0].data_venda).days if vendas else None
    contexto = f"""
=== CLIENTE ===
Nome: {cliente.nome}
CPF/CNPJ: {cliente.cpf or cliente.cnpj or 'não informado'}
Telefone: {cliente.telefone or cliente.celular or 'não informado'}
Cidade: {f"{cliente.cidade}/{cliente.estado}" if cliente.cidade else 'não informada'}

=== HISTÓRICO DE COMPRAS ===
Total de compras: {len(vendas)}
Total gasto: R$ {total_gasto:.2f}
Ticket médio: R$ {ticket_medio:.2f}
Última compra: {vendas[0].data_venda.strftime('%d/%m/%Y') + f' (há {dias_desde_ultima} dias)' if vendas else 'nunca'}

Detalhes das últimas {min(10, len(vendas))} compras:
{chr(10).join(historico_detalhado) if historico_detalhado else '  (nenhuma)'}

=== PRODUTOS MAIS COMPRADOS ===
{chr(10).join(top_produtos_lines) if top_produtos_lines else '  (nenhum)'}

=== ALERTAS DE REABASTECIMENTO ===
{chr(10).join(alertas_reabastecimento) if alertas_reabastecimento else '  Nenhum atrasado no momento.'}

=== PETS ===
{chr(10).join(pets_lines) if pets_lines else '  Nenhum pet cadastrado.'}
""".strip()

    SYSTEM_PROMPT = """Você é um assistente especializado em atendimento de Pet Shop, rodando direto no caixa (PDV).

Seu papel é ajudar o OPERADOR DE CAIXA a atender melhor o cliente que está na frente dele AGORA.

Você tem acesso ao histórico completo de compras, produtos favoritos, pets, padrões de reabastecimento e alertas.

Regras:
- Responda SEMPRE em português do Brasil
- Seja BREVE e DIRETO (máximo 4-5 linhas normalmente)
- Foque no que é útil AGORA para o atendimento
- Se perceber que um produto favorito está atrasado, mencione proativamente
- Se os pets do cliente tiverem características relevantes (raça, peso, idade), considere isso nas sugestões
- Responda perguntas específicas com dados exatos do histórico
- Não invente informações — use apenas o que está no contexto

Exemplos de perguntas que você responde bem:
- "O que ele comprou na última vez?"
- "Quantas vezes ele comprou ração X?"
- "Qual o pet dele?"
- "Tem algum produto que ele compra regularmente que pode estar acabando?"
- "Qual o ticket médio dele?"
"""

    try:
        groq_key = os.getenv('GROQ_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        gemini_key = os.getenv('GEMINI_API_KEY')

        resposta_ia = None

        if groq_key:
            from groq import Groq
            client_ia = Groq(api_key=groq_key)
            completion = client_ia.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + contexto},
                    {"role": "user", "content": request.mensagem}
                ],
                temperature=0.4,
                max_tokens=400
            )
            resposta_ia = completion.choices[0].message.content

        elif openai_key:
            from openai import OpenAI
            client_ia = OpenAI(api_key=openai_key)
            completion = client_ia.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + contexto},
                    {"role": "user", "content": request.mensagem}
                ],
                temperature=0.4,
                max_tokens=400
            )
            resposta_ia = completion.choices[0].message.content

        elif gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model_ia = genai.GenerativeModel('gemini-1.5-flash')
            prompt_completo = SYSTEM_PROMPT + "\n\n" + contexto + f"\n\nPergunta do operador: {request.mensagem}"
            response = model_ia.generate_content(prompt_completo)
            resposta_ia = response.text

        else:
            resposta_ia = gerar_resposta_sem_ia(request.mensagem, cliente, vendas,
                                                [l.strip('- ') for l in top_produtos_lines[:5]], pets_lines)

        return {
            "resposta": resposta_ia,
            "ia_disponivel": bool(groq_key or openai_key or gemini_key)
        }

    except Exception as e:
        return {
            "resposta": gerar_resposta_sem_ia(request.mensagem, cliente, vendas,
                                              [l.strip('- ') for l in top_produtos_lines[:5]], pets_lines),
            "ia_disponivel": False,
            "erro": str(e)
        }


def gerar_resposta_sem_ia(mensagem: str, cliente, vendas, top_produtos, pets_info):
    """Gera respostas básicas sem IA quando API não está disponível"""
    
    msg_lower = mensagem.lower()
    
    if any(palavra in msg_lower for palavra in ['compra', 'comprou', 'produto', 'favorito']):
        if top_produtos:
            return f"Os produtos favoritos de {cliente.nome} são: {', '.join(top_produtos)}. Já comprou {len(vendas)} vezes conosco."
        else:
            return f"{cliente.nome} ainda não tem histórico de compras."
    
    elif any(palavra in msg_lower for palavra in ['pet', 'animal', 'cachorro', 'gato']):
        if pets_info:
            return f"{cliente.nome} tem {len(pets_info)} pet(s): {', '.join(pets_info)}."
        else:
            return f"{cliente.nome} não tem pets cadastrados."
    
    elif any(palavra in msg_lower for palavra in ['última', 'ultimo', 'recente']):
        if vendas:
            ultima = vendas[0]
            return f"Última compra: {ultima.data_venda.strftime('%d/%m/%Y')}, no valor de R$ {float(ultima.total):.2f}."
        else:
            return "Cliente ainda não fez compras."
    
    elif any(palavra in msg_lower for palavra in ['total', 'quanto', 'gastou', 'valor']):
        total = sum(float(v.total) for v in vendas)
        return f"{cliente.nome} já gastou R$ {total:.2f} em {len(vendas)} compras."
    
    else:
        return f"📊 Informações de {cliente.nome}: {len(vendas)} compras, {len(pets_info)} pet(s) cadastrado(s). Pergunte sobre produtos favoritos, última compra ou pets!"

