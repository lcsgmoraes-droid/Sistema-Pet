"""Base de calendario preventivo veterinario."""


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
