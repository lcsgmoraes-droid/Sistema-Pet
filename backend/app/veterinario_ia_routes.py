"""Rotas do assistente IA veterinario."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .ia.aba6_models import Conversa, MensagemChat
from .models import Pet
from .veterinario_core import _get_tenant
from .veterinario_exames_arquivos import _process_exam_file_with_ai
from .veterinario_ia import (
    _carregar_memoria_conversa,
    _garantir_tabelas_memoria_ia,
    _montar_resposta_dose,
    _montar_resposta_interacao,
    _montar_resposta_plano_estruturado,
    _montar_resposta_sintomas,
    _normalizar_modo_ia,
    _obter_ou_criar_conversa_vet,
    _responder_chat_exame,
    _tentar_resposta_llm_veterinaria,
)
from .veterinario_models import ConsultaVet, ExameVet, MedicamentoCatalogo
from .veterinario_schemas import ExameChatPayload, VetAssistenteIAPayload, VetMensagemFeedbackPayload

router = APIRouter()

# ═══════════════════════════════════════════════════════════════
# CHAT IA — interpretação clínica conversacional de exames
# ═══════════════════════════════════════════════════════════════

@router.post("/ia/assistente", summary="Assistente IA veterinário (livre ou vinculado ao atendimento)")
def assistente_ia_veterinario(
    payload: VetAssistenteIAPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)

    mensagem = (payload.mensagem or "").strip()
    if not mensagem:
        raise HTTPException(422, "Informe uma mensagem para o assistente.")

    pet = None
    consulta = None
    exame = None

    if payload.pet_id:
        pet = db.query(Pet).filter(Pet.id == payload.pet_id, Pet.tenant_id == tenant_id).first()

    if payload.consulta_id:
        consulta = db.query(ConsultaVet).filter(
            ConsultaVet.id == payload.consulta_id,
            ConsultaVet.tenant_id == tenant_id,
        ).first()
        if consulta and not pet:
            pet = db.query(Pet).filter(Pet.id == consulta.pet_id, Pet.tenant_id == tenant_id).first()

    if payload.exame_id:
        exame = db.query(ExameVet).filter(
            ExameVet.id == payload.exame_id,
            ExameVet.tenant_id == tenant_id,
        ).first()
        if exame and not pet:
            pet = db.query(Pet).filter(Pet.id == exame.pet_id, Pet.tenant_id == tenant_id).first()

    especie = payload.especie or (pet.especie if pet else None)
    peso_kg = payload.peso_kg
    if (not peso_kg or peso_kg <= 0) and pet and getattr(pet, "peso", None):
        try:
            peso_kg = float(pet.peso)
        except Exception:
            peso_kg = None
    if (not peso_kg or peso_kg <= 0) and consulta and getattr(consulta, "peso_consulta", None):
        try:
            peso_kg = float(consulta.peso_consulta)
        except Exception:
            peso_kg = None

    meds = db.query(MedicamentoCatalogo).filter(
        MedicamentoCatalogo.tenant_id == tenant_id,
        MedicamentoCatalogo.ativo == True,  # noqa
    ).order_by(MedicamentoCatalogo.nome).limit(200).all()

    conversa = None
    memoria = []
    contexto_memoria = ""
    historico_salvo = False
    modelo_usado = "vet-regra"
    if payload.salvar_historico:
        try:
            _garantir_tabelas_memoria_ia(db)
            conversa = _obter_ou_criar_conversa_vet(
                db=db,
                tenant_id=tenant_id,
                user_id=user.id,
                payload=payload,
                pet=pet,
                consulta=consulta,
                exame=exame,
            )
            memoria = _carregar_memoria_conversa(db, tenant_id, conversa.id, limite=8)
            memoria_usuario = [m.conteudo for m in memoria if m.tipo == "usuario"]
            contexto_memoria = " | ".join(memoria_usuario[-2:]).strip()
        except Exception:
            db.rollback()
            conversa = None
            memoria = []
            contexto_memoria = ""

    mensagem_analise = mensagem
    if contexto_memoria:
        mensagem_analise = f"{mensagem} {contexto_memoria}"

    resposta_llm, modelo_llm = _tentar_resposta_llm_veterinaria(
        mensagem=mensagem,
        memoria=memoria,
        pet=pet,
        consulta=consulta,
        exame=exame,
        especie=especie,
        peso_kg=peso_kg,
        meds=meds,
        modo=payload.modo,
    )

    if resposta_llm:
        resposta_final = resposta_llm
        modelo_usado = modelo_llm or "vet-llm"
    else:
        respostas = []

        if exame:
            respostas.append(
                _responder_chat_exame(
                    pergunta=mensagem_analise.lower(),
                    exame_nome=exame.nome,
                    tipo_exame=exame.tipo,
                    especie=(pet.especie if pet else "não informada"),
                    nome_pet=(pet.nome if pet else "paciente"),
                    alergias=(getattr(pet, "alergias_lista", None) or []),
                    alertas=(exame.interpretacao_ia_alertas or []),
                    resumo_ia=(exame.interpretacao_ia_resumo or ""),
                    conclusao_ia=(exame.interpretacao_ia or ""),
                    dados_json=(exame.resultado_json or {}),
                    texto_resultado=(exame.resultado_texto or ""),
                    payload_ia=(exame.interpretacao_ia_payload or {}),
                    tem_arquivo=bool(exame.arquivo_url),
                )
            )

        resp_dose = _montar_resposta_dose(mensagem_analise, meds, peso_kg, especie)
        if resp_dose:
            respostas.append(resp_dose)

        resp_interacao = _montar_resposta_interacao(
            mensagem_analise,
            meds,
            payload.medicamento_1,
            payload.medicamento_2,
        )
        if resp_interacao:
            respostas.append(resp_interacao)

        resp_sintomas = _montar_resposta_sintomas(mensagem_analise, especie)
        if resp_sintomas:
            respostas.append(resp_sintomas)

        resp_plano = _montar_resposta_plano_estruturado(mensagem_analise, pet, consulta, exame)
        if resp_plano:
            respostas.append(resp_plano)

        if not respostas:
            contexto = []
            if pet:
                contexto.append(f"pet: {pet.nome}")
            if especie:
                contexto.append(f"espécie: {especie}")
            if peso_kg:
                contexto.append(f"peso: {peso_kg:.2f} kg")
            contexto_txt = " | ".join(contexto) if contexto else "sem contexto clínico selecionado"

            respostas.append(
                "Posso te ajudar com: cálculo de dose por mg/kg, avaliação de associação medicamentosa, "
                "hipóteses por sintomas e checklist para fechamento diagnóstico. "
                f"Contexto atual: {contexto_txt}."
            )

        resposta_final = "\n\n".join(respostas)

    resposta_final += (
        "\n\nAviso clínico: resposta de apoio à decisão. "
        "Sempre confirmar conduta final com exame físico, histórico completo e protocolos da clínica."
    )

    contexto_msg = {
        "modulo": "vet",
        "modo": _normalizar_modo_ia(payload.modo),
        "pet_id": pet.id if pet else None,
        "consulta_id": consulta.id if consulta else None,
        "exame_id": exame.id if exame else None,
        "peso_kg": peso_kg,
        "especie": especie,
    }

    if payload.salvar_historico and conversa:
        try:
            db.add(MensagemChat(
                tenant_id=str(tenant_id),
                conversa_id=conversa.id,
                tipo="usuario",
                conteudo=mensagem,
                modelo_usado=modelo_usado,
                contexto_usado=contexto_msg,
            ))
            db.add(MensagemChat(
                tenant_id=str(tenant_id),
                conversa_id=conversa.id,
                tipo="assistente",
                conteudo=resposta_final,
                modelo_usado=modelo_usado,
                contexto_usado={**contexto_msg, "feedback": None},
            ))
            conversa.atualizado_em = datetime.utcnow()
            db.commit()
            historico_salvo = True
        except Exception:
            db.rollback()
            historico_salvo = False

    return {
        "resposta": resposta_final,
        "conversa_id": conversa.id if conversa else payload.conversa_id,
        "historico_salvo": historico_salvo,
        "contexto": {
            "modo": payload.modo,
            "pet_id": pet.id if pet else None,
            "pet_nome": pet.nome if pet else None,
            "consulta_id": consulta.id if consulta else None,
            "exame_id": exame.id if exame else None,
            "peso_kg": peso_kg,
            "especie": especie,
        },
    }


@router.get("/ia/conversas", summary="Lista conversas do assistente IA veterinário")
def listar_conversas_assistente_vet(
    limit: int = Query(20, ge=1, le=100),
    pet_id: Optional[int] = Query(None),
    consulta_id: Optional[int] = Query(None),
    exame_id: Optional[int] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    conversas = db.query(Conversa).filter(
        Conversa.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).order_by(Conversa.atualizado_em.desc(), Conversa.id.desc()).limit(limit).all()

    itens = []
    for conversa in conversas:
        mensagens = db.query(MensagemChat).filter(
            MensagemChat.tenant_id == str(tenant_id),
            MensagemChat.conversa_id == conversa.id,
        ).order_by(MensagemChat.id.asc()).all()

        if not mensagens:
            continue

        mensagens_vet = [m for m in mensagens if isinstance(m.contexto_usado, dict) and m.contexto_usado.get("modulo") == "vet"]
        if not mensagens_vet:
            continue

        ultima = mensagens[-1]
        contexto_base = next((m.contexto_usado for m in mensagens_vet if isinstance(m.contexto_usado, dict)), {}) or {}

        if pet_id and int(contexto_base.get("pet_id") or 0) != int(pet_id):
            continue
        if consulta_id and int(contexto_base.get("consulta_id") or 0) != int(consulta_id):
            continue
        if exame_id and int(contexto_base.get("exame_id") or 0) != int(exame_id):
            continue

        itens.append({
            "id": conversa.id,
            "titulo": conversa.titulo,
            "atualizado_em": conversa.atualizado_em.isoformat() if conversa.atualizado_em else None,
            "ultima_mensagem": (ultima.conteudo or "")[:180],
            "contexto": {
                "modo": contexto_base.get("modo"),
                "pet_id": contexto_base.get("pet_id"),
                "consulta_id": contexto_base.get("consulta_id"),
                "exame_id": contexto_base.get("exame_id"),
            },
        })

    return {"items": itens}


@router.get("/ia/conversas/{conversa_id}/mensagens", summary="Lista mensagens de uma conversa IA veterinária")
def listar_mensagens_conversa_assistente_vet(
    conversa_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    conversa = db.query(Conversa).filter(
        Conversa.id == conversa_id,
        Conversa.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).first()
    if not conversa:
        raise HTTPException(404, "Conversa não encontrada.")

    mensagens = db.query(MensagemChat).filter(
        MensagemChat.tenant_id == str(tenant_id),
        MensagemChat.conversa_id == conversa_id,
    ).order_by(MensagemChat.id.asc()).all()

    itens = []
    for msg in mensagens:
        contexto = msg.contexto_usado if isinstance(msg.contexto_usado, dict) else {}
        if contexto.get("modulo") != "vet":
            continue
        itens.append({
            "id": msg.id,
            "tipo": msg.tipo,
            "conteudo": msg.conteudo,
            "criado_em": msg.criado_em.isoformat() if msg.criado_em else None,
            "feedback": contexto.get("feedback"),
        })

    return {
        "conversa": {
            "id": conversa.id,
            "titulo": conversa.titulo,
            "atualizado_em": conversa.atualizado_em.isoformat() if conversa.atualizado_em else None,
        },
        "items": itens,
    }


@router.post("/ia/mensagens/{mensagem_id}/feedback", summary="Registra feedback da resposta da IA veterinária")
def registrar_feedback_mensagem_assistente_vet(
    mensagem_id: int,
    payload: VetMensagemFeedbackPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    _garantir_tabelas_memoria_ia(db)

    mensagem = db.query(MensagemChat).join(
        Conversa, Conversa.id == MensagemChat.conversa_id
    ).filter(
        MensagemChat.id == mensagem_id,
        MensagemChat.tenant_id == str(tenant_id),
        Conversa.usuario_id == user.id,
    ).first()
    if not mensagem:
        raise HTTPException(404, "Mensagem não encontrada.")
    if mensagem.tipo != "assistente":
        raise HTTPException(400, "Feedback só pode ser registrado em respostas da IA.")

    contexto = mensagem.contexto_usado if isinstance(mensagem.contexto_usado, dict) else {}
    if contexto.get("modulo") != "vet":
        raise HTTPException(400, "Mensagem não pertence ao assistente veterinário.")

    contexto["feedback"] = {
        "util": bool(payload.util),
        "nota": payload.nota,
        "comentario": (payload.comentario or "").strip() or None,
        "avaliado_em": datetime.utcnow().isoformat(),
        "avaliado_por": user.id,
    }
    mensagem.contexto_usado = contexto
    db.commit()

    return {"ok": True, "mensagem_id": mensagem.id, "feedback": contexto["feedback"]}


@router.get("/ia/memoria-status", summary="Verifica e prepara tabelas de memória da IA veterinária")
def memoria_status_assistente_vet(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _user, _tenant_id = _get_tenant(current)
    status_memoria = _garantir_tabelas_memoria_ia(db)
    return status_memoria


@router.post("/exames/{exame_id}/chat", summary="Chat clínico conversacional sobre um exame")
def chat_exame_ia(
    exame_id: int,
    payload: ExameChatPayload,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Responde perguntas clínicas sobre um exame específico, usando o resultado,
    a interpretação existente e o histórico básico do paciente como contexto.
    """
    user, tenant_id = _get_tenant(current)

    exame = db.query(ExameVet).filter(
        ExameVet.id == exame_id,
        ExameVet.tenant_id == tenant_id,
    ).first()
    if not exame:
        raise HTTPException(404, "Exame não encontrado.")

    if exame.arquivo_url and not exame.resultado_texto and not exame.resultado_json:
        try:
            exame = _process_exam_file_with_ai(db, tenant_id=tenant_id, exame=exame)
            db.commit()
            db.refresh(exame)
        except HTTPException:
            pass

    pet = db.query(Pet).filter(Pet.id == exame.pet_id).first()
    pergunta = (payload.pergunta or "").strip().lower()

    # Monta contexto clínico do paciente
    especie = (pet.especie or "não informada") if pet else "não informada"
    nome_pet = pet.nome if pet else "paciente"
    alergias = []
    if pet:
        al = pet.alergias_lista or pet.alergias
        if isinstance(al, list):
            alergias = al
        elif isinstance(al, str) and al.strip():
            alergias = [al]

    alertas_exame = exame.interpretacao_ia_alertas or []
    resumo_ia = exame.interpretacao_ia_resumo or ""
    conclusao_ia = exame.interpretacao_ia or ""
    dados_json = exame.resultado_json or {}
    texto_resultado = exame.resultado_texto or ""
    payload_ia = exame.interpretacao_ia_payload or {}

    # Base de conhecimento para Q&A clínica
    resposta = _responder_chat_exame(
        pergunta=pergunta,
        exame_nome=exame.nome,
        tipo_exame=exame.tipo,
        especie=especie,
        nome_pet=nome_pet,
        alergias=alergias,
        alertas=alertas_exame,
        resumo_ia=resumo_ia,
        conclusao_ia=conclusao_ia,
        dados_json=dados_json,
        texto_resultado=texto_resultado,
        payload_ia=payload_ia,
        tem_arquivo=bool(exame.arquivo_url),
    )

    return {
        "exame_id": exame_id,
        "pergunta": payload.pergunta,
        "resposta": resposta,
        "contexto": {
            "pet_nome": nome_pet,
            "especie": especie,
            "exame_nome": exame.nome,
            "tem_interpretacao": bool(conclusao_ia),
        },
    }
