"""
Endpoint especializado para informaÃ§Ãµes do cliente no PDV
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from collections import defaultdict

from app.db import get_session
from app.models import Cliente, Pet
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto
from app.auth import get_current_user_and_tenant
from app.veterinario_models import ExameVet
from app.services.cliente_alertas_pdv import alertas_pdv_ativos
from app.cliente_info_pdv_chat import router as chat_router
from app.cliente_info_pdv_schemas import AlertasCarrinhoRequest

router = APIRouter(prefix="/clientes", tags=["clientes"])
router.include_router(chat_router)


@router.post("/{cliente_id}/alertas-carrinho")
def alertas_carrinho_pdv(
    cliente_id: int,
    request: AlertasCarrinhoRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Analisa o carrinho atual em tempo real e retorna alertas proativos:
    - RaÃ§Ã£o errada para a fase de vida do pet
    - ProteÃ­na com alergia registrada
    - DuraÃ§Ã£o estimada por pet
    """
    _, tenant_id = user_and_tenant

    pets = db.query(Pet).filter(Pet.cliente_id == cliente_id, Pet.ativo).all()
    alertas = []
    infos = []

    for item in request.itens:
        if not item.produto_id:
            continue
        produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
        if not produto or not produto.peso_embalagem:
            continue  # sÃ³ analisa raÃ§Ãµes

        for pet in pets:
            pet_nome = pet.nome
            idade_anos = None
            if pet.data_nascimento:
                data_nasc = (
                    pet.data_nascimento.date()
                    if isinstance(pet.data_nascimento, datetime)
                    else pet.data_nascimento
                )
                idade_anos = (datetime.now().date() - data_nasc).days // 365
            fase_pet = (
                "filhote"
                if (idade_anos is not None and idade_anos < 1)
                else "idoso"
                if (idade_anos is not None and idade_anos >= 7)
                else "adulto"
            )

            # Alerta: fase de vida errada
            if produto.categoria_racao:
                fase_racao = produto.categoria_racao.lower()
                if (
                    fase_pet == "idoso"
                    and "senior" not in fase_racao
                    and "idoso" not in fase_racao
                    and "sÃªnior" not in fase_racao
                ):
                    alertas.append(
                        {
                            "tipo": "fase_vida",
                            "nivel": "aviso",
                            "mensagem": f"{pet_nome} Ã© idoso ({idade_anos} anos) â€” raÃ§Ã£o '{produto.nome}' Ã© para '{produto.categoria_racao}'. Recomendar versÃ£o sÃªnior.",
                        }
                    )
                elif fase_pet == "filhote" and "filhote" not in fase_racao:
                    alertas.append(
                        {
                            "tipo": "fase_vida",
                            "nivel": "aviso",
                            "mensagem": f"{pet_nome} Ã© filhote â€” raÃ§Ã£o '{produto.nome}' Ã© para '{produto.categoria_racao}'.",
                        }
                    )

            # Alerta: alergia
            if produto.sabor_proteina and pet.alergias:
                if produto.sabor_proteina.lower() in pet.alergias.lower():
                    alertas.append(
                        {
                            "tipo": "alergia",
                            "nivel": "critico",
                            "mensagem": f"ðŸš¨ {pet_nome} tem alergia a '{produto.sabor_proteina}' registrada! A raÃ§Ã£o '{produto.nome}' contÃ©m essa proteÃ­na.",
                        }
                    )

            # Info: duraÃ§Ã£o estimada
            if pet.peso and float(pet.peso) > 0:
                try:
                    from app.calculadora_racao import calcular_quantidade_diaria

                    peso_pet = float(pet.peso)
                    qtd_diaria_g = calcular_quantidade_diaria(
                        peso_pet_kg=peso_pet,
                        idade_meses=int(idade_anos * 12)
                        if idade_anos is not None
                        else None,
                        nivel_atividade="normal",
                        tabela_consumo_json=None,
                    )
                    total_g = produto.peso_embalagem * 1000 * item.quantidade
                    duracao_dias = (
                        int(total_g / qtd_diaria_g) if qtd_diaria_g > 0 else None
                    )
                    if duracao_dias:
                        custo_total = item.preco_unitario * item.quantidade
                        infos.append(
                            {
                                "tipo": "duracao",
                                "mensagem": f"'{produto.nome}' para {pet_nome} ({peso_pet}kg): ~{qtd_diaria_g:.0f}g/dia â†’ dura {duracao_dias} dias (R$ {custo_total / duracao_dias:.2f}/dia)",
                            }
                        )
                except Exception:
                    pass

    return {"alertas": alertas, "infos": infos}


@router.get("/{cliente_id}/info-pdv")
def get_cliente_info_pdv(
    cliente_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Retorna informaÃ§Ãµes completas do cliente para exibir no PDV:
    - Resumo financeiro (total gasto, ticket mÃ©dio, etc)
    - Pets registrados
    - Ãšltimas compras (histÃ³rico)
    - Oportunidades (produtos que deve reabastecer)
    - SugestÃµes de produtos baseadas no histÃ³rico
    """
    current_user, tenant_id = user_and_tenant

    # Buscar cliente
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id, Cliente.ativo)
        .first()
    )

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nÃ£o encontrado")

    # ========== 1. RESUMO FINANCEIRO ==========
    vendas = (
        db.query(Venda)
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status != "cancelada",
        )
        .all()
    )

    total_gasto = sum(float(v.total) for v in vendas)
    numero_compras = len(vendas)
    ticket_medio = total_gasto / numero_compras if numero_compras > 0 else 0
    maior_compra = max((float(v.total) for v in vendas), default=0)
    maior_compra_venda = (
        max(vendas, key=lambda v: float(v.total), default=None) if vendas else None
    )

    # Ãšltima compra
    ultima_venda = (
        sorted(vendas, key=lambda v: v.data_venda, reverse=True)[0] if vendas else None
    )

    resumo_financeiro = {
        "total_gasto": round(total_gasto, 2),
        "numero_compras": numero_compras,
        "ticket_medio": round(ticket_medio, 2),
        "maior_compra": {
            "valor": round(maior_compra, 2),
            "data": maior_compra_venda.data_venda.strftime("%d/%m/%Y")
            if maior_compra_venda
            else None,
            "numero_venda": maior_compra_venda.numero_venda
            if maior_compra_venda
            else None,
        },
        "ultima_compra": {
            "numero_venda": ultima_venda.numero_venda if ultima_venda else None,
            "data": ultima_venda.data_venda.strftime("%d/%m/%Y")
            if ultima_venda
            else None,
            "valor": float(ultima_venda.total) if ultima_venda else 0,
        },
    }

    # ========== 2. PETS REGISTRADOS ==========
    pets = db.query(Pet).filter(Pet.cliente_id == cliente_id, Pet.ativo).all()

    pets_info = []
    alertas_veterinarios = []
    for pet in pets:
        idade_anos = None
        if pet.data_nascimento:
            # Garantir que data_nascimento seja date (nÃ£o datetime)
            data_nasc = (
                pet.data_nascimento.date()
                if isinstance(pet.data_nascimento, datetime)
                else pet.data_nascimento
            )
            idade = datetime.now().date() - data_nasc
            idade_anos = idade.days // 365

        alergias_lista = getattr(pet, "alergias_lista", None) or (
            [pet.alergias] if pet.alergias else []
        )
        restricoes_lista = getattr(pet, "restricoes_alimentares_lista", None) or []
        vacinas_vencidas = []
        try:
            from app.veterinario_clinico import _status_vacinal_pet

            status_vacinal = _status_vacinal_pet(db, pet, tenant_id)
            vacinas_vencidas = status_vacinal.get("vencidas", [])
        except Exception:
            status_vacinal = {"resumo": {"total_vencidas": 0, "total_pendentes": 0}}

        exames_pendentes = (
            db.query(ExameVet)
            .filter(
                ExameVet.pet_id == pet.id,
                ExameVet.tenant_id == tenant_id,
                ExameVet.status.in_(["solicitado", "aguardando", "disponivel"]),
            )
            .count()
        )

        pets_info.append(
            {
                "id": pet.id,
                "nome": pet.nome,
                "especie": pet.especie,
                "raca": pet.raca,
                "peso": float(pet.peso) if pet.peso else None,
                "idade_anos": idade_anos,
                "sexo": pet.sexo,
                "alergias_lista": alergias_lista,
                "restricoes_alimentares_lista": restricoes_lista,
                "vacinas_vencidas": vacinas_vencidas,
                "exames_pendentes": exames_pendentes,
            }
        )

        for alergia in alergias_lista:
            alertas_veterinarios.append(
                {
                    "pet_id": pet.id,
                    "pet_nome": pet.nome,
                    "tipo": "alergia",
                    "nivel": "critico",
                    "mensagem": f"{pet.nome}: alergia registrada em {alergia}.",
                }
            )
        for restricao in restricoes_lista:
            alertas_veterinarios.append(
                {
                    "pet_id": pet.id,
                    "pet_nome": pet.nome,
                    "tipo": "restricao",
                    "nivel": "aviso",
                    "mensagem": f"{pet.nome}: restriÃ§Ã£o alimentar em {restricao}.",
                }
            )
        for vacina in vacinas_vencidas:
            alertas_veterinarios.append(
                {
                    "pet_id": pet.id,
                    "pet_nome": pet.nome,
                    "tipo": "vacina_atrasada",
                    "nivel": "aviso",
                    "mensagem": f"{pet.nome}: vacina {vacina['nome']} atrasada hÃ¡ {vacina['dias_atraso']} dia(s).",
                }
            )
        if exames_pendentes:
            alertas_veterinarios.append(
                {
                    "pet_id": pet.id,
                    "pet_nome": pet.nome,
                    "tipo": "exame_pendente",
                    "nivel": "info",
                    "mensagem": f"{pet.nome}: {exames_pendentes} exame(s) pendente(s) de revisÃ£o.",
                }
            )

    # ========== 3. ÃšLTIMAS COMPRAS (5 mais recentes) ==========
    ultimas_vendas = sorted(vendas, key=lambda v: v.data_venda, reverse=True)[:5]

    ultimas_compras = []
    for venda in ultimas_vendas:
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()

        produtos = []
        for item in itens:
            if item.produto_id:
                produto = (
                    db.query(Produto).filter(Produto.id == item.produto_id).first()
                )
                produtos.append(
                    {
                        "nome": produto.nome if produto else "Produto deletado",
                        "quantidade": float(item.quantidade),
                        "valor": float(item.subtotal),
                    }
                )

        ultimas_compras.append(
            {
                "data": venda.data_venda.strftime("%d/%m/%Y"),
                "numero_venda": venda.numero_venda,
                "valor_total": float(venda.total),
                "produtos": produtos[:3],  # Limitar a 3 produtos por venda
            }
        )

    # ========== 4. ANÃLISE DE PADRÃ•ES (Oportunidades) ==========
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
                        "quantidade_total": 0,
                    }
                produtos_comprados[item.produto_id]["quantidade_vezes"] += 1
                produtos_comprados[item.produto_id]["quantidade_total"] += float(
                    item.quantidade
                )
                if (
                    not produtos_comprados[item.produto_id]["ultima_compra"]
                    or venda.data_venda
                    > produtos_comprados[item.produto_id]["ultima_compra"]
                ):
                    produtos_comprados[item.produto_id]["ultima_compra"] = (
                        venda.data_venda
                    )

    # Calcular intervalo mÃ©dio de compra para produtos recorrentes
    oportunidades = []
    for produto_id, info in produtos_comprados.items():
        if info["quantidade_vezes"] >= 2:  # Produto comprado pelo menos 2x
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if not produto:
                continue

            # Pegar todas as datas de compra desse produto
            vendas_produto = (
                db.query(Venda)
                .join(VendaItem)
                .filter(
                    VendaItem.produto_id == produto_id,
                    Venda.cliente_id == cliente_id,
                    Venda.status != "cancelada",
                )
                .order_by(Venda.data_venda)
                .all()
            )

            if len(vendas_produto) >= 2:
                # Calcular intervalo mÃ©dio entre compras
                intervalos = []
                for i in range(1, len(vendas_produto)):
                    delta = (
                        vendas_produto[i].data_venda - vendas_produto[i - 1].data_venda
                    ).days
                    intervalos.append(delta)

                intervalo_medio = sum(intervalos) / len(intervalos) if intervalos else 0

                # Verificar se estÃ¡ atrasado
                if info["ultima_compra"]:
                    dias_desde_ultima = (datetime.now() - info["ultima_compra"]).days

                    # Se passou do intervalo mÃ©dio + margem de 7 dias
                    if dias_desde_ultima > (intervalo_medio + 7):
                        oportunidades.append(
                            {
                                "tipo": "reabastecimento",
                                "produto_nome": produto.nome,
                                "produto_id": produto.id,
                                "mensagem": f"{produto.nome} normalmente a cada {int(intervalo_medio)} dias (Ãºltima: {info['ultima_compra'].strftime('%d/%m/%Y')} - {dias_desde_ultima} dias atrÃ¡s)",
                                "urgencia": "alta"
                                if dias_desde_ultima > (intervalo_medio + 14)
                                else "media",
                                "dias_atraso": dias_desde_ultima - int(intervalo_medio),
                            }
                        )

    # ========== 5. SUGESTÃ•ES (produtos mais comprados) ==========
    produtos_mais_comprados = sorted(
        produtos_comprados.items(), key=lambda x: x[1]["quantidade_vezes"], reverse=True
    )[:5]

    sugestoes = []
    for produto_id, info in produtos_mais_comprados:
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if produto:
            sugestoes.append(
                {
                    "produto_id": produto.id,
                    "nome": produto.nome,
                    "preco": float(produto.preco_venda),
                    "vezes_comprado": info["quantidade_vezes"],
                    "ultima_compra": info["ultima_compra"].strftime("%d/%m/%Y")
                    if info["ultima_compra"]
                    else None,
                }
            )

    # ========== 6. ANÃLISE DE PRODUTOS COMPRADOS JUNTOS ==========
    # AnÃ¡lise de co-ocorrÃªncia (produtos comprados na mesma venda)
    combinacoes = defaultdict(int)
    produtos_por_venda = defaultdict(set)

    for venda in vendas:
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        produtos_venda = [item.produto_id for item in itens if item.produto_id]

        # Registrar produtos desta venda
        for p_id in produtos_venda:
            produtos_por_venda[venda.id].add(p_id)

        # Contar combinaÃ§Ãµes (produtos que aparecem juntos)
        for i, p1 in enumerate(produtos_venda):
            for p2 in produtos_venda[i + 1 :]:
                if p1 != p2:
                    par = tuple(sorted([p1, p2]))
                    combinacoes[par] += 1

    # Top 5 combinaÃ§Ãµes mais frequentes
    produtos_relacionados = []
    for (p1_id, p2_id), frequencia in sorted(
        combinacoes.items(), key=lambda x: x[1], reverse=True
    )[:5]:
        p1 = db.query(Produto).filter(Produto.id == p1_id).first()
        p2 = db.query(Produto).filter(Produto.id == p2_id).first()
        if p1 and p2:
            produtos_relacionados.append(
                {
                    "produto1": {
                        "id": p1.id,
                        "nome": p1.nome,
                        "preco": float(p1.preco_venda),
                    },
                    "produto2": {
                        "id": p2.id,
                        "nome": p2.nome,
                        "preco": float(p2.preco_venda),
                    },
                    "vezes_juntos": frequencia,
                }
            )

    # ========== 7. ANÃLISE SAZONAL ==========
    # Agrupar vendas por mÃªs
    vendas_por_mes = defaultdict(lambda: {"total": 0, "quantidade": 0})
    for venda in vendas:
        mes_ano = venda.data_venda.strftime("%m/%Y")
        vendas_por_mes[mes_ano]["total"] += float(venda.total)
        vendas_por_mes[mes_ano]["quantidade"] += 1

    # Ãšltimos 6 meses
    padroes_sazonais = []
    for mes_ano, dados in sorted(vendas_por_mes.items(), reverse=True)[:6]:
        padroes_sazonais.append(
            {
                "mes_ano": mes_ano,
                "total_gasto": round(dados["total"], 2),
                "numero_compras": dados["quantidade"],
                "ticket_medio": round(dados["total"] / dados["quantidade"], 2)
                if dados["quantidade"] > 0
                else 0,
            }
        )

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
            "estado": cliente.estado,
            "alertas_pdv": alertas_pdv_ativos(getattr(cliente, "alertas_pdv", None)),
        },
        "resumo_financeiro": resumo_financeiro,
        "pets": pets_info,
        "alertas_veterinarios": alertas_veterinarios[:12],
        "ultimas_compras": ultimas_compras,
        "oportunidades": oportunidades,
        "sugestoes": sugestoes,
        "produtos_relacionados": produtos_relacionados,
        "padroes_sazonais": padroes_sazonais,
    }
