"""Helpers de IA do modulo veterinario."""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .ia.aba6_models import Conversa, MensagemChat
from .models import Pet
from .veterinario_models import ConsultaVet, ExameVet, MedicamentoCatalogo

logger = logging.getLogger(__name__)


def _normalizar_texto(v: Optional[str]) -> str:
    return (v or "").strip().lower()


def _detectar_medicamentos_no_texto(
    texto: str, meds: list[MedicamentoCatalogo]
) -> list[MedicamentoCatalogo]:
    encontrados: list[MedicamentoCatalogo] = []
    for med in meds:
        nome = _normalizar_texto(med.nome)
        nome_comercial = _normalizar_texto(med.nome_comercial)
        principio = _normalizar_texto(med.principio_ativo)
        if (
            (nome and nome in texto)
            or (nome_comercial and nome_comercial in texto)
            or (principio and principio in texto)
        ):
            encontrados.append(med)
        if len(encontrados) >= 2:
            break
    return encontrados


def _normalizar_modo_ia(modo: Optional[str]) -> str:
    modo_limpo = (modo or "livre").strip().lower()
    return modo_limpo if modo_limpo in ["livre", "atendimento"] else "livre"


def _garantir_tabelas_memoria_ia(db: Session) -> dict:
    """
    Garante que as tabelas de memoria usadas pela IA existam.
    Evita falha silenciosa de historico em ambientes sem migracao aplicada.
    """
    bind = db.get_bind()
    insp = inspect(bind)
    criadas = []

    if not insp.has_table("conversas_ia"):
        Conversa.__table__.create(bind=bind, checkfirst=True)
        criadas.append("conversas_ia")

    if not insp.has_table("mensagens_chat"):
        MensagemChat.__table__.create(bind=bind, checkfirst=True)
        criadas.append("mensagens_chat")

    return {"ok": True, "criadas": criadas}


def _encerrar_transacao_antes_do_provedor(db: Session) -> bool:
    """
    Fecha a transacao de leitura/preparacao antes de chamar um provedor externo.

    A chamada ao LLM pode levar dezenas de segundos. Manter a conexao PostgreSQL
    ociosa dentro de uma transacao nesse intervalo faz o servidor encerrar a
    sessao por ``idle_in_transaction_session_timeout`` e impede que o historico
    seja salvo quando a resposta chega.
    """
    try:
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.warning(
            "Nao foi possivel finalizar a preparacao da IA veterinaria: %s",
            exc.__class__.__name__,
        )
        return False


def _carregar_memoria_conversa(
    db: Session, tenant_id, conversa_id: int, limite: int = 8
) -> list[MensagemChat]:
    return (
        db.query(MensagemChat)
        .filter(
            MensagemChat.tenant_id == str(tenant_id),
            MensagemChat.conversa_id == conversa_id,
        )
        .order_by(MensagemChat.id.desc())
        .limit(limite)
        .all()[::-1]
    )


def _resumir_feedbacks_memoria(
    mensagens: list[MensagemChat],
    limite_comentarios: int = 8,
) -> dict[str, Any]:
    """Turn explicit user feedback into scoped preferences, not clinical truth."""
    comments = []
    useful = 0
    not_useful = 0
    debate_notes = 0
    preference_markers = (
        "prefiro ",
        "na nossa clínica",
        "na minha clínica",
        "sempre responda",
        "quero que você ",
        "corrigindo sua resposta",
        "minha conduta ",
    )
    for message in mensagens:
        if getattr(message, "tipo", "assistente") == "usuario":
            user_text = str(getattr(message, "conteudo", "") or "").strip()
            normalized_user_text = user_text.casefold()
            if (
                user_text
                and any(marker in normalized_user_text for marker in preference_markers)
                and len(comments) < limite_comentarios
            ):
                comments.append(
                    {
                        "resposta_util": None,
                        "comentario_do_veterinario": user_text[:800],
                        "origem": "debate_na_conversa",
                    }
                )
                debate_notes += 1
            continue
        context = (
            message.contexto_usado if isinstance(message.contexto_usado, dict) else {}
        )
        feedback = context.get("feedback")
        if not isinstance(feedback, dict):
            continue
        if feedback.get("util") is True:
            useful += 1
        elif feedback.get("util") is False:
            not_useful += 1
        comment = str(feedback.get("comentario") or "").strip()
        if comment and len(comments) < limite_comentarios:
            comments.append(
                {
                    "resposta_util": bool(feedback.get("util")),
                    "comentario_do_veterinario": comment[:800],
                    "origem": "feedback_explicito",
                }
            )
    return {
        "feedbacks_considerados": useful + not_useful,
        "debates_considerados": debate_notes,
        "memorias_consideradas": useful + not_useful + debate_notes,
        "respostas_uteis": useful,
        "respostas_nao_uteis": not_useful,
        "preferencias_e_correcoes_explicitas": comments,
        "escopo": "usuario_atual_no_tenant_atual",
    }


def _carregar_memoria_feedback_usuario(
    db: Session,
    tenant_id,
    user_id: int,
) -> dict[str, Any]:
    mensagens = (
        db.query(MensagemChat)
        .join(Conversa, Conversa.id == MensagemChat.conversa_id)
        .filter(
            MensagemChat.tenant_id == str(tenant_id),
            Conversa.usuario_id == user_id,
        )
        .order_by(MensagemChat.id.desc())
        .limit(250)
        .all()
    )
    return _resumir_feedbacks_memoria(mensagens)


def _safety_identifier_vet(tenant_id, user_id: int) -> str:
    raw = f"corepet-vet:{tenant_id}:{user_id}".encode()
    return f"vet_{hashlib.sha256(raw).hexdigest()[:32]}"


def _obter_ou_criar_conversa_vet(
    db: Session,
    tenant_id,
    user_id: int,
    payload,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> Conversa:
    if payload.conversa_id:
        conversa = (
            db.query(Conversa)
            .filter(
                Conversa.id == payload.conversa_id,
                Conversa.tenant_id == str(tenant_id),
                Conversa.usuario_id == user_id,
            )
            .first()
        )
        if conversa:
            return conversa

    modo = _normalizar_modo_ia(payload.modo)
    if pet:
        titulo = f"Vet {modo} - {pet.nome}"
    elif consulta:
        titulo = f"Vet {modo} - Consulta {consulta.id}"
    elif exame:
        titulo = f"Vet {modo} - Exame {exame.id}"
    else:
        titulo = f"Vet {modo} - {datetime.now().strftime('%d/%m %H:%M')}"

    conversa = Conversa(
        tenant_id=str(tenant_id),
        usuario_id=user_id,
        titulo=titulo,
        finalizada=False,
    )
    db.add(conversa)
    db.flush()
    return conversa


def _resumo_contexto_clinico(
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> str:
    blocos = []
    if pet:
        blocos.append(
            f"Paciente: {pet.nome} | espécie: {pet.especie or 'não informada'} | raça: {pet.raca or 'n/i'}"
        )
        alergias = getattr(pet, "alergias_lista", None) or getattr(
            pet, "alergias", None
        )
        condicoes = getattr(pet, "condicoes_cronicas_lista", None) or getattr(
            pet, "doencas_cronicas", None
        )
        medicamentos = getattr(pet, "medicamentos_continuos_lista", None) or getattr(
            pet, "medicamentos_continuos", None
        )
        blocos.append(
            "Segurança do paciente: "
            f"alergias={alergias or 'não revisadas'}; "
            f"condições crônicas={condicoes or 'não informadas'}; "
            f"medicamentos contínuos={medicamentos or 'não informados'}"
        )
    if consulta:
        blocos.append(
            "Consulta atual: "
            f"queixa={consulta.queixa_principal or 'n/i'}; "
            f"história={consulta.historia_clinica or 'n/i'}; "
            f"exame físico={consulta.exame_fisico or 'n/i'}; "
            f"diagnóstico={consulta.diagnostico or consulta.hipotese_diagnostica or 'n/i'}"
        )
    if exame:
        data_ref = exame.data_resultado.isoformat() if exame.data_resultado else "n/i"
        blocos.append(
            "Exame selecionado: "
            f"{exame.nome or exame.tipo} | data={data_ref} | "
            f"resumo ia={exame.interpretacao_ia_resumo or 'n/i'}"
        )
    return "\n".join(blocos).strip()


def _montar_resposta_dose(
    mensagem: str,
    meds: list[MedicamentoCatalogo],
    peso_kg: Optional[float],
    especie: Optional[str],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    if not any(k in texto for k in ["dose", "dosagem", "mg/kg", "posologia"]):
        return None

    if not peso_kg or peso_kg <= 0:
        return "Para calcular dose com segurança, informe o peso atual do pet em kg."

    if not especie:
        return "Para cálculo de dose com segurança, informe também a espécie do pet (cão, gato, etc.)."

    med_match = None
    for med in meds:
        nome = _normalizar_texto(med.nome)
        nome_comercial = _normalizar_texto(med.nome_comercial)
        principio = _normalizar_texto(med.principio_ativo)
        if (
            (nome and nome in texto)
            or (nome_comercial and nome_comercial in texto)
            or (principio and principio in texto)
        ):
            med_match = med
            break

    if not med_match:
        return "Não identifiquei o medicamento na pergunta. Informe o nome (ou princípio ativo) para calcular a dose."

    dose_min = med_match.dose_min_mgkg
    dose_max = med_match.dose_max_mgkg
    if dose_min is None and dose_max is None:
        return (
            f"Encontrei {med_match.nome}, mas ele não tem dose mg/kg cadastrada no catálogo. "
            "Verifique a bula/protocolo antes de prescrever."
        )

    dose_ref = dose_min if dose_min is not None else dose_max
    dose_max_ref = dose_max if dose_max is not None else dose_min

    total_min = float(dose_ref) * float(peso_kg)
    total_max = float(dose_max_ref) * float(peso_kg)
    total_media = (total_min + total_max) / 2

    if abs(total_min - total_max) < 1e-9:
        faixa = f"{total_min:.2f} mg"
        faixa_mgkg = f"{dose_ref:.2f} mg/kg"
    else:
        faixa = f"{total_min:.2f} mg a {total_max:.2f} mg"
        faixa_mgkg = f"{dose_ref:.2f} a {dose_max_ref:.2f} mg/kg"

    return (
        f"Dose de referência para {med_match.nome} (peso {peso_kg:.2f} kg): {faixa_mgkg}. "
        f"Total estimado: {faixa} (média {total_media:.2f} mg). "
        "Confirme frequência, via e duração conforme bula e condição clínica. "
        "Se houver comorbidade renal/hepática, considere ajuste de dose."
    )


def _montar_resposta_interacao(
    mensagem: str,
    meds: list[MedicamentoCatalogo],
    medicamento_1: Optional[str],
    medicamento_2: Optional[str],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    if not any(
        k in texto for k in ["associar", "junto", "intera", "combinar", "pode usar com"]
    ):
        return None

    med_a = None
    med_b = None
    m1 = _normalizar_texto(medicamento_1)
    m2 = _normalizar_texto(medicamento_2)

    if m1 and m2:
        for med in meds:
            nome = _normalizar_texto(med.nome)
            nome_comercial = _normalizar_texto(med.nome_comercial)
            principio = _normalizar_texto(med.principio_ativo)
            if not med_a and (
                m1 == nome or m1 == nome_comercial or m1 == principio or m1 in nome
            ):
                med_a = med
            if not med_b and (
                m2 == nome or m2 == nome_comercial or m2 == principio or m2 in nome
            ):
                med_b = med
    else:
        encontrados = _detectar_medicamentos_no_texto(texto, meds)
        if len(encontrados) >= 2:
            med_a, med_b = encontrados[0], encontrados[1]

    if not med_a or not med_b:
        return "Para avaliar associação medicamentosa, informe dois medicamentos (nome ou princípio ativo)."

    principio_a = _normalizar_texto(med_a.principio_ativo)
    principio_b = _normalizar_texto(med_b.principio_ativo)

    if principio_a and principio_b and principio_a == principio_b:
        return (
            f"Atenção: {med_a.nome} e {med_b.nome} parecem ter o mesmo princípio ativo ({med_a.principio_ativo}). "
            "Há risco de duplicidade terapêutica e aumento de efeitos adversos."
        )

    riscos = []
    texto_interacoes = (
        f"{_normalizar_texto(med_a.interacoes)} {_normalizar_texto(med_b.interacoes)}"
    )
    if principio_a and principio_a in texto_interacoes:
        riscos.append(
            f"{med_b.nome} cita interação relevante com o princípio {med_a.principio_ativo}."
        )
    if principio_b and principio_b in texto_interacoes:
        riscos.append(
            f"{med_a.nome} cita interação relevante com o princípio {med_b.principio_ativo}."
        )

    if riscos:
        return (
            f"Associação {med_a.nome} + {med_b.nome}: encontrada possível interação em catálogo. "
            + " ".join(riscos)
            + " Avalie ajuste de dose, intervalo e monitoramento clínico."
        )

    return (
        f"Não encontrei alerta explícito de interação entre {med_a.nome} e {med_b.nome} no catálogo local. "
        "Mesmo assim, confirme em bula e considere função renal/hepática, idade e comorbidades antes de associar."
    )


def _montar_resposta_sintomas(mensagem: str, especie: Optional[str]) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    gatilhos = [
        "sintoma",
        "possibilidade",
        "diagnóstico",
        "hipótese",
        "o que olhar",
        "investigar",
    ]
    if not any(k in texto for k in gatilhos):
        return None

    mapa = {
        "vomit": [
            "gastroenterite",
            "ingestão alimentar inadequada",
            "pancreatite",
            "corpo estranho",
        ],
        "diarre": [
            "parasitoses",
            "gastroenterite",
            "disbiose",
            "doença inflamatória intestinal",
        ],
        "tosse": [
            "traqueobronquite",
            "colapso de traqueia",
            "cardiopatia",
            "pneumonia",
        ],
        "febre": [
            "processo infeccioso",
            "inflamação sistêmica",
            "doença transmitida por vetor",
        ],
        "apat": ["dor", "infecção", "anemia", "distúrbio metabólico"],
        "prur": ["dermatite alérgica", "ectoparasitas", "infecção cutânea secundária"],
        "poliuria": ["doença renal", "diabetes mellitus", "hiperadrenocorticismo"],
        "convuls": [
            "epilepsia",
            "distúrbio metabólico",
            "intoxicação",
            "doença intracraniana",
        ],
    }

    hipoteses = []
    for chave, possibilidades in mapa.items():
        if chave in texto:
            hipoteses.extend(possibilidades)

    if not hipoteses:
        hipoteses = [
            "processo infeccioso",
            "dor/condição inflamatória",
            "distúrbio metabólico/endócrino",
            "causa gastrointestinal",
        ]

    especie_txt = (especie or "não informada").strip()
    hipoteses_unicas = []
    for h in hipoteses:
        if h not in hipoteses_unicas:
            hipoteses_unicas.append(h)

    principais = ", ".join(hipoteses_unicas[:5])
    return (
        f"Pelas informações citadas ({especie_txt}), as principais hipóteses iniciais incluem: {principais}. "
        "Para fechar diagnóstico, recomendo revisar sinais vitais completos, dor, hidratação, evolução temporal, "
        "histórico medicamentoso e exames complementares dirigidos (hemograma, bioquímica e imagem conforme achados)."
    )


def _montar_resposta_plano_estruturado(
    mensagem: str,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
) -> Optional[str]:
    texto = _normalizar_texto(mensagem)
    gatilhos = [
        "plano",
        "conduta",
        "fechar diagnóstico",
        "fechar diagnostico",
        "o que fazer agora",
    ]
    if not any(k in texto for k in gatilhos):
        return None

    contexto = _resumo_contexto_clinico(pet, consulta, exame)
    if not contexto:
        return (
            "Plano sugerido (estrutura mínima):\n"
            "1) Estabilização e dor: confirmar sinais vitais e escala de dor.\n"
            "2) Diagnóstico direcionado: hemograma + bioquímica + exame complementar conforme sistema acometido.\n"
            "3) Terapêutica inicial: suporte e monitorização de resposta em 24-48h.\n"
            "4) Reavaliação: definir critério de melhora/piora e retorno programado."
        )

    return (
        "Plano clínico estruturado com base no contexto atual:\n"
        "1) Hipóteses priorizadas: usar queixa + exame físico + exame complementar para ranquear hipóteses.\n"
        "2) Exames de confirmação: escolher exames com maior impacto para diferenciar as principais hipóteses.\n"
        "3) Conduta imediata: suporte, analgesia e hidratação conforme estado clínico.\n"
        "4) Segurança medicamentosa: revisar dose por espécie/peso e risco de interação.\n"
        "5) Follow-up: registrar sinais de alarme e prazo de reavaliação.\n"
        f"Resumo de contexto utilizado:\n{contexto}"
    )


def _montar_prompt_vet_llm(
    mensagem: str,
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
    especie: Optional[str],
    peso_kg: Optional[float],
    meds: list[MedicamentoCatalogo],
    modo: Optional[str],
    contexto_estruturado: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    especie_txt = (especie or "não informada").strip()
    peso_txt = (
        f"{float(peso_kg):.2f} kg" if peso_kg and peso_kg > 0 else "não informado"
    )

    meds_preview = []
    for med in meds[:20]:
        partes = [med.nome]
        if med.principio_ativo:
            partes.append(f"princípio: {med.principio_ativo}")
        if med.dose_min_mgkg is not None or med.dose_max_mgkg is not None:
            dmin = (
                med.dose_min_mgkg
                if med.dose_min_mgkg is not None
                else med.dose_max_mgkg
            )
            dmax = (
                med.dose_max_mgkg
                if med.dose_max_mgkg is not None
                else med.dose_min_mgkg
            )
            partes.append(f"dose mg/kg: {dmin} a {dmax}")
        meds_preview.append(" | ".join(partes))

    if contexto_estruturado:
        contexto_clinico = json.dumps(
            contexto_estruturado,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )[:18000]
    else:
        contexto_clinico = (
            _resumo_contexto_clinico(pet, consulta, exame)
            or "Sem contexto clínico detalhado."
        )

    prompt_system = (
        "Você é o copiloto clínico veterinário do CorePet, para apoio à decisão de médicos-veterinários. "
        "Responda em português do Brasil, direto e claro. "
        "Não invente dados, referências, doses nem interações. "
        "Diferencie claramente fato do prontuário, hipótese clínica e recomendação. "
        "Não repita avisos genéricos se já houver um aviso clínico na interface.\n\n"
        "REGRAS:\n"
        "1) Se faltar dado crítico (peso, espécie, medicamento), peça esse dado antes de concluir.\n"
        "2) Nunca converta mg em comprimidos ou mL sem concentração e apresentação compatíveis.\n"
        "3) Em dose, use somente dados do catálogo/contexto e mande confirmar a fonte oficial.\n"
        "4) Em interação, diga 'não há dado suficiente' quando a fonte explícita não estiver no contexto.\n"
        "5) Em urgência, priorize estabilização e sinais de alarme; evite diagnóstico definitivo.\n"
        "6) Considere alergias, medicamentos em uso, condições crônicas, exames e prescrições já registradas.\n"
        "7) Seja objetivo, mas mostre o raciocínio clínico em tópicos quando pedirem discussão de caso.\n\n"
        "8) Use somente as evidências clínicas disponíveis presentes no contexto. "
        "Ao usá-las, cite a referência [E1], [E2] correspondente; não invente estudos.\n"
        "9) Informe limitações do desenho do estudo. Triagem automática de fonte não "
        "equivale a consenso nem substitui a leitura do artigo completo.\n"
        "10) Memórias de feedback representam preferências ou correções do usuário. "
        "Use-as para adaptar comunicação e fluxo, mas nunca como evidência científica "
        "universal ou substituto de fonte clínica.\n\n"
        f"MODO: {_normalizar_modo_ia(modo)}\n"
        f"ESPÉCIE: {especie_txt}\n"
        f"PESO: {peso_txt}\n"
        f"CONTEXTO CLÍNICO ESTRUTURADO:\n{contexto_clinico}\n\n"
        "CATÁLOGO LOCAL DE MEDICAMENTOS (pode estar incompleto; não trate ausência como prova de segurança):\n"
        f"{chr(10).join(meds_preview) if meds_preview else 'Sem medicamentos ativos no catálogo.'}"
    )

    prompt_user = f"Pergunta do veterinário: {mensagem}"
    return prompt_system, prompt_user


def _tentar_resposta_llm_veterinaria(
    mensagem: str,
    memoria: list[MensagemChat],
    pet: Optional[Pet],
    consulta: Optional[ConsultaVet],
    exame: Optional[ExameVet],
    especie: Optional[str],
    peso_kg: Optional[float],
    meds: list[MedicamentoCatalogo],
    modo: Optional[str],
    contexto_estruturado: Optional[dict[str, Any]] = None,
    safety_identifier: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], str]:
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not (groq_key or openai_key or gemini_key):
        return None, None, "sem_provedor_configurado"

    prompt_system, prompt_user = _montar_prompt_vet_llm(
        mensagem=mensagem,
        pet=pet,
        consulta=consulta,
        exame=exame,
        especie=especie,
        peso_kg=peso_kg,
        meds=meds,
        modo=modo,
        contexto_estruturado=contexto_estruturado,
    )

    mensagens = [{"role": "system", "content": prompt_system}]
    for m in memoria[-6:]:
        conteudo = (m.conteudo or "").strip()
        if not conteudo:
            continue
        role = "assistant" if m.tipo == "assistente" else "user"
        mensagens.append({"role": role, "content": conteudo[:3000]})
    mensagens.append({"role": "user", "content": prompt_user})

    falha_provedor = False

    if openai_key:
        from openai import AuthenticationError, OpenAI, RateLimitError

        client_ia = OpenAI(api_key=openai_key, timeout=45.0)
        modelo_principal = (
            os.getenv("VET_OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5.6"
        ).strip()
        modelo_fallback = (
            os.getenv("VET_OPENAI_FALLBACK_MODEL") or "gpt-4o-mini"
        ).strip()
        modelos = [modelo_principal]
        if modelo_fallback and modelo_fallback != modelo_principal:
            modelos.append(modelo_fallback)

        for indice, modelo in enumerate(modelos):
            try:
                kwargs = {
                    "model": modelo,
                    "input": mensagens,
                    "max_output_tokens": 1200,
                    "store": False,
                }
                if safety_identifier:
                    kwargs["safety_identifier"] = safety_identifier
                if modelo.startswith("gpt-5"):
                    kwargs["reasoning"] = {
                        "effort": (
                            os.getenv("VET_OPENAI_REASONING_EFFORT") or "medium"
                        ).strip()
                    }
                response = client_ia.responses.create(**kwargs)
                resposta = (response.output_text or "").strip()
                if resposta:
                    status = "llm" if indice == 0 else "llm_fallback_modelo"
                    return resposta, f"openai:{modelo}", status
            except (AuthenticationError, RateLimitError):
                logger.warning(
                    "OpenAI veterinaria indisponivel por autenticacao ou limite."
                )
                falha_provedor = True
                break
            except Exception as exc:
                logger.warning(
                    "Falha no modelo veterinario OpenAI %s: %s",
                    modelo,
                    exc.__class__.__name__,
                )
                falha_provedor = True

    try:
        if groq_key:
            from groq import Groq

            client_ia = Groq(api_key=groq_key)
            completion = client_ia.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=mensagens,
                temperature=0.2,
                max_tokens=600,
            )
            resposta = (completion.choices[0].message.content or "").strip()
            return (resposta or None), "groq:llama-3.3-70b-versatile", "llm"

        if gemini_key:
            import google.generativeai as genai

            genai.configure(api_key=gemini_key)
            model_ia = genai.GenerativeModel("gemini-1.5-flash")
            historico_txt = "\n".join(
                [
                    f"{msg['role']}: {msg['content']}"
                    for msg in mensagens
                    if msg["role"] != "system"
                ]
            )
            prompt_completo = f"{prompt_system}\n\n{historico_txt}"
            response = model_ia.generate_content(prompt_completo)
            resposta = (getattr(response, "text", "") or "").strip()
            return (resposta or None), "gemini:gemini-1.5-flash", "llm"

    except Exception as exc:
        logger.warning(
            "Provedor alternativo da IA veterinaria falhou: %s",
            exc.__class__.__name__,
        )
        falha_provedor = True

    return None, None, "erro_provedor" if falha_provedor else "sem_resposta"


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
    achados_imagem = (
        payload_ia.get("achados_imagem") if isinstance(payload_ia, dict) else []
    )
    limitacoes = payload_ia.get("limitacoes") if isinstance(payload_ia, dict) else []
    conduta_sugerida = (
        payload_ia.get("conduta_sugerida") if isinstance(payload_ia, dict) else []
    )

    if any(
        k in pergunta
        for k in [
            "resumo",
            "resumir",
            "explicar",
            "o que diz",
            "o que significa",
            "resultado",
        ]
    ):
        if not texto_resultado and not dados_json:
            return f"O exame '{exame_nome}' ainda não tem resultado registrado. Adicione o resultado antes de solicitar a interpretação."
        partes = []
        if conclusao_ia:
            partes.append(f"**Conclusão da triagem automática:** {conclusao_ia}")
        if resumo_ia and resumo_ia != conclusao_ia:
            partes.append(f"**Detalhes:** {resumo_ia}")
        if alertas_mensagens:
            partes.append("**Alertas encontrados:** " + "; ".join(alertas_mensagens))
        return (
            "\n\n".join(partes) if partes else "Nenhuma interpretação disponível ainda."
        )

    if any(
        k in pergunta
        for k in ["alerta", "preocupante", "crítico", "grave", "urgente", "emergência"]
    ):
        if not alertas:
            return f"A triagem automática do exame '{exame_nome}' não encontrou alertas críticos. Isso não substitui a avaliação clínica — verifique os valores numericamente se disponíveis."
        msgs = (
            "\n- ".join(alertas_mensagens)
            if alertas_mensagens
            else "Alertas detectados, mas sem detalhes textuais."
        )
        return f"**Pontos de atenção encontrados no exame {exame_nome}:**\n\n- {msgs}\n\nRecomendo revisão clínica presencial."

    if any(
        k in pergunta
        for k in ["normal", "status", "tudo certo", "está bem", "dentro do normal"]
    ):
        if not alertas:
            return f"A triagem automática não encontrou valores fora do padrão em '{exame_nome}'. O exame parece dentro da normalidade pelos critérios automatizados — confirme com avaliação clínica."
        return f"Foram encontrados {len(alertas)} ponto(s) de atenção: {resumo_ia}. Revise os valores clínicamente."

    if any(
        k in pergunta
        for k in [
            "próximo passo",
            "conduta",
            "tratamento",
            "o que fazer",
            "recomendação",
        ]
    ):
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

    if any(
        k in pergunta
        for k in ["alergia", "medicamento", "contraindicado", "intolerância"]
    ):
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
            if any(
                t in k.lower() for t in ["leuco", "eritro", "hemo", "plaqueta", "glob"]
            )
        }
        if dados_hemo:
            linhas = "\n".join(f"- {k}: {v}" for k, v in dados_hemo.items())
            return f"Valores hematológicos registrados no resultado:\n{linhas}\n\nInterpretação geral: {resumo_ia or 'sem interpretação automática disponível'}"
        return f"Não há valores hematológicos estruturados no resultado do exame '{exame_nome}'. Verifique o texto do laudo ou reenvie como JSON estruturado."

    if any(k in pergunta for k in ["rim", "renal", "creatinina", "ureia", "uréia"]):
        dados_renal = {
            k: v
            for k, v in dados_json.items()
            if any(
                t in k.lower()
                for t in ["creat", "ureia", "uria", "rim", "renal", "tgo", "tgp"]
            )
        }
        if dados_renal:
            linhas = "\n".join(f"- {k}: {v}" for k, v in dados_renal.items())
            return f"Valores relacionados à função renal/hepática:\n{linhas}\n\n{resumo_ia or 'Consulte a interpretação automática.'}"
        return "Não há parâmetros renais estruturados no resultado. Verifique o laudo original."

    if any(
        k in pergunta
        for k in ["imagem", "raio", "ultrassom", "eco", "rx", "radiografia"]
    ):
        if tipo_exame in {"radiografia", "ultrassom", "ecocardiograma", "imagem"}:
            if achados_imagem:
                partes = [
                    f"**Achados sugeridos pela análise do arquivo em '{exame_nome}':**",
                    "\n- "
                    + "\n- ".join(
                        str(item) for item in achados_imagem if str(item).strip()
                    ),
                ]
                if limitacoes:
                    partes.append(
                        "\n**Limitações:** "
                        + "; ".join(
                            str(item) for item in limitacoes if str(item).strip()
                        )
                    )
                partes.append(
                    "\nConfirme sempre com o laudo do especialista e a correlação clínica."
                )
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
        partes_resposta.append(
            f"\n**Pontos de atenção:** {'; '.join(alertas_mensagens)}"
        )
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
