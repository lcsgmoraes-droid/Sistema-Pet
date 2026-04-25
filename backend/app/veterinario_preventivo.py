"""Base e montagem de calendario preventivo veterinario."""

from sqlalchemy import or_

from .veterinario_models import ProtocoloVacina


_CALENDARIO_PADRAO = {
    "cão": [
        {"vacina": "V8 / V10 (1ª dose)", "fase": "filhote", "idade_semanas_min": 6, "idade_semanas_max": 8, "dose": "1ª dose", "reforco_anual": False, "observacoes": "Iniciar série em filhotes a partir de 6 semanas"},
        {"vacina": "V8 / V10 (2ª dose)", "fase": "filhote", "idade_semanas_min": 9, "idade_semanas_max": 11, "dose": "2ª dose", "reforco_anual": False, "observacoes": "21-28 dias após a 1ª dose"},
        {"vacina": "V8 / V10 (3ª dose)", "fase": "filhote", "idade_semanas_min": 12, "idade_semanas_max": 16, "dose": "3ª dose", "reforco_anual": False, "observacoes": "21-28 dias após a 2ª dose — completar série"},
        {"vacina": "V8 / V10 (reforço adulto)", "fase": "adulto", "idade_semanas_min": 52, "idade_semanas_max": None, "dose": "Reforço anual", "reforco_anual": True, "observacoes": "Reforço anual após completar a série filhote"},
        {"vacina": "Antirrábica", "fase": "filhote", "idade_semanas_min": 12, "idade_semanas_max": 16, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Obrigatória por lei. Reforço anual"},
        {"vacina": "Bordetella (tosse dos canis)", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 12, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Especialmente para cães em contato com outros cães"},
        {"vacina": "Leishmaniose", "fase": "adulto", "idade_semanas_min": 24, "idade_semanas_max": None, "dose": "3 doses (0, 21, 42 dias)", "reforco_anual": True, "observacoes": "Recomendada em áreas endêmicas. Requer teste negativo antes"},
        {"vacina": "Giárdia", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": None, "dose": "2 doses (21 dias)", "reforco_anual": True, "observacoes": "Para cães com risco de exposição"},
        {"vacina": "Leptospirose", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 12, "dose": "2 doses (21 dias)", "reforco_anual": True, "observacoes": "Geralmente inclusa na V8/V10. Reforço semestral em áreas de risco"},
    ],
    "gato": [
        {"vacina": "Tríplice Felina V3 (1ª dose)", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 10, "dose": "1ª dose", "reforco_anual": False, "observacoes": "Cobre herpevírus, calicivírus e panleucopenia"},
        {"vacina": "Tríplice Felina V3 (2ª dose)", "fase": "filhote", "idade_semanas_min": 11, "idade_semanas_max": 13, "dose": "2ª dose", "reforco_anual": False, "observacoes": "21 dias após a 1ª dose"},
        {"vacina": "Tríplice Felina V3 (3ª dose)", "fase": "filhote", "idade_semanas_min": 14, "idade_semanas_max": 16, "dose": "3ª dose + início anual", "reforco_anual": True, "observacoes": "Completar série. Após: reforço anual"},
        {"vacina": "Antirrábica", "fase": "filhote", "idade_semanas_min": 12, "idade_semanas_max": 16, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Recomendada. Reforço anual"},
        {"vacina": "FeLV (Leucemia Felina)", "fase": "filhote", "idade_semanas_min": 8, "idade_semanas_max": 12, "dose": "2 doses (28 dias)", "reforco_anual": True, "observacoes": "Para gatos com acesso à rua ou contato com outros felinos. Requer teste FeLV negativo antes"},
        {"vacina": "FIV/FeLV combo", "fase": "adulto", "idade_semanas_min": 26, "idade_semanas_max": None, "dose": "3 doses (21 dias)", "reforco_anual": True, "observacoes": "Para gatos de exterior. Teste negativo obrigatório antes"},
        {"vacina": "Clamidofilose (V4)", "fase": "filhote", "idade_semanas_min": 9, "idade_semanas_max": None, "dose": "2 doses (21 dias)", "reforco_anual": True, "observacoes": "Para gatos em criações ou com outros felinos"},
    ],
    "coelho": [
        {"vacina": "Calicivírus Hemorrágico (VHD)", "fase": "adulto", "idade_semanas_min": 12, "idade_semanas_max": None, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Alta mortalidade. Disponibilidade varia por região"},
        {"vacina": "Mixomatose", "fase": "adulto", "idade_semanas_min": 6, "idade_semanas_max": None, "dose": "1ª dose", "reforco_anual": True, "observacoes": "Principalmente para coelhos com acesso a áreas externas"},
    ],
    "todos": [
        {"vacina": "Antiparasitário (vermífugo)", "fase": "filhote", "idade_semanas_min": 2, "idade_semanas_max": None, "dose": "Preventivo", "reforco_anual": False, "observacoes": "A cada 15 dias até 3 meses, depois trimestral"},
        {"vacina": "Antipulgas / Carrapatos", "fase": "todos", "idade_semanas_min": 8, "idade_semanas_max": None, "dose": "Mensal ou conforme produto", "reforco_anual": False, "observacoes": "Ectoparasitas — manter regularmente durante toda a vida"},
    ],
}


def _aliases_especie_calendario(especie: str) -> set[str]:
    especie_norm = (especie or "").strip().lower()
    if not especie_norm:
        return set()
    aliases = {especie_norm}
    if especie_norm in {"canino", "cao", "cão", "cachorro", "dog"}:
        aliases.update({"canino", "cao", "cão", "cachorro", "dog"})
    if especie_norm in {"felino", "gato", "cat"}:
        aliases.update({"felino", "gato", "cat"})
    return aliases


def _normalizar_especie_calendario(especie: str) -> str:
    aliases = _aliases_especie_calendario(especie)
    if {"canino", "cao", "cão", "cachorro", "dog"} & aliases:
        return "cão"
    if {"felino", "gato", "cat"} & aliases:
        return "gato"
    return (especie or "").strip().lower()


def montar_calendario_preventivo(db, tenant_id, especie: str | None = None) -> dict:
    especie_norm = _normalizar_especie_calendario(especie or "")
    aliases = _aliases_especie_calendario(especie_norm)

    calendario_base = []
    for esp, protocolos in _CALENDARIO_PADRAO.items():
        if not especie_norm or especie_norm in esp or esp in especie_norm or esp == "todos":
            for protocolo in protocolos:
                calendario_base.append({**protocolo, "especie": esp, "fonte": "padrao"})

    query_protocolos = db.query(ProtocoloVacina).filter(
        ProtocoloVacina.tenant_id == tenant_id,
        ProtocoloVacina.ativo == True,  # noqa
    )
    if aliases:
        query_protocolos = query_protocolos.filter(
            (ProtocoloVacina.especie == None) |
            (ProtocoloVacina.especie == "") |
            or_(*[ProtocoloVacina.especie.ilike(f"%{alias}%") for alias in aliases])
        )

    for protocolo in query_protocolos.all():
        idade_min = protocolo.dose_inicial_semanas
        calendario_base.append({
            "vacina": protocolo.nome,
            "fase": "filhote" if (idade_min or 0) < 26 else "adulto",
            "idade_semanas_min": idade_min,
            "idade_semanas_max": None,
            "dose": f"{protocolo.numero_doses_serie} dose(s)" if protocolo.numero_doses_serie > 1 else "dose única",
            "reforco_anual": protocolo.reforco_anual,
            "intervalo_doses_dias": protocolo.intervalo_doses_dias,
            "observacoes": protocolo.observacoes or "",
            "especie": protocolo.especie or "todos",
            "fonte": "personalizado",
            "protocolo_id": protocolo.id,
        })

    calendario_base.sort(key=lambda item: (item.get("especie", ""), item.get("idade_semanas_min") or 0))

    return {
        "especie_filtro": especie_norm or "todas",
        "total": len(calendario_base),
        "items": calendario_base,
    }
