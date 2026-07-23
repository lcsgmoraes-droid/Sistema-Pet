from types import SimpleNamespace

import pdfplumber

from app.pdf_veterinario import gerar_pdf_prontuario, gerar_pdf_receita


def _consulta():
    veterinario = SimpleNamespace(nome="Dra. Beatriz Silva", crmv="SP-12345")
    return SimpleNamespace(
        id=42,
        pet=SimpleNamespace(nome="Luna"),
        cliente=SimpleNamespace(nome="Ana Souza"),
        veterinario=veterinario,
        status="finalizada",
        inicio_atendimento=None,
        fim_atendimento=None,
        finalizado_em=None,
        queixa_principal="Apatia",
        diagnostico="Gastroenterite em investigação",
        conduta="Tratamento de suporte e retorno em 48 horas.",
        retorno_em_dias=2,
        peso_consulta=12.5,
        temperatura=38.4,
        frequencia_cardiaca=90,
        frequencia_respiratoria=24,
    )


def test_prontuario_compacto_mantem_qr_e_crmv_na_primeira_pagina():
    consulta = _consulta()
    buffer = gerar_pdf_prontuario(
        consulta,
        {
            "assinada": True,
            "hash_valido": True,
            "hash_prontuario": "abc123",
        },
        [],
        "https://corepet.example/validar/abc123",
    )

    with pdfplumber.open(buffer) as reader:
        texto = "\n".join(page.extract_text() or "" for page in reader.pages)

        assert len(reader.pages) == 1
    assert "CRMV SP-12345" in texto
    assert "Validar prontuário" in texto


def test_receita_inclui_tutor_crmv_e_area_de_assinatura():
    consulta = _consulta()
    prescricao = SimpleNamespace(
        numero="RX-2026-42",
        data_emissao="23/07/2026",
        pet=consulta.pet,
        consulta=consulta,
        consulta_id=consulta.id,
        tipo_receituario="simples",
        hash_receita="receita123",
        itens=[
            SimpleNamespace(
                nome_medicamento="Medicamento exemplo",
                posologia="Conforme orientação do médico-veterinário",
                via_administracao="oral",
                duracao_dias=5,
            )
        ],
    )

    buffer = gerar_pdf_receita(
        prescricao,
        "https://corepet.example/validar/receita123",
    )

    with pdfplumber.open(buffer) as reader:
        texto = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Ana Souza" in texto
    assert "CRMV SP-12345" in texto
    assert "Assinatura do médico-veterinário" in texto
