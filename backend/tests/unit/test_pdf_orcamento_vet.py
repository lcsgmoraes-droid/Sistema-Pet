from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pdfplumber

from app.pdf_orcamento_vet import gerar_pdf_orcamento_vet


def _clinica():
    return SimpleNamespace(
        name="Clínica Bichos & Cia",
        razao_social="Bichos e Cia Ltda",
        cnpj="12.345.678/0001-90",
        endereco="Rua das Flores",
        numero="123",
        complemento=None,
        bairro="Centro",
        cidade="Cuiabá",
        uf="MT",
        cep="78000-000",
        telefone="(65) 3333-0000",
        email="contato@bichos.example",
    )


def _orcamento(itens=2):
    return SimpleNamespace(
        id=42,
        created_at=datetime(2026, 10, 2, 12, 0),
        consulta_id=7,
        internacao_id=None,
        titulo="Orçamento da consulta",
        pet=SimpleNamespace(nome="Luna", especie="Canina"),
        cliente=SimpleNamespace(nome="Ana Souza"),
        veterinario=SimpleNamespace(nome="Dra. Beatriz Silva", crmv="MT-12345"),
        preco_total=Decimal("309.90"),
        custo_total_estimado=Decimal("117.74"),
        margem_valor=Decimal("192.16"),
        itens=[
            SimpleNamespace(
                id=indice,
                ordem=indice,
                nome=f"Consulta <avaliação> {indice}",
                quantidade=1,
                unidade="un",
                preco_unitario=Decimal("154.95"),
                preco_total=Decimal("154.95"),
                custo_total_estimado=Decimal("58.87"),
                margem_valor=Decimal("96.08"),
            )
            for indice in range(1, itens + 1)
        ],
    )


def test_pdf_orcamento_para_tutor_mostra_identificacao_e_precos_sem_dados_internos():
    buffer = gerar_pdf_orcamento_vet(_orcamento(), _clinica())

    with pdfplumber.open(buffer) as reader:
        texto = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert len(reader.pages) == 1

    for trecho in (
        "Clínica Bichos & Cia",
        "Dra. Beatriz Silva",
        "CRMV MT-12345",
        "Ana Souza",
        "Luna",
        "R$ 309,90",
        "Consulta <avaliação> 1",
    ):
        assert trecho in texto
    for trecho in ("Custo", "Margem", "117,74", "192,16"):
        assert trecho not in texto


def test_pdf_orcamento_com_muitos_itens_quebra_paginas_e_repete_cabecalho():
    buffer = gerar_pdf_orcamento_vet(_orcamento(itens=55), _clinica())
    with pdfplumber.open(buffer) as reader:
        assert len(reader.pages) > 1
        assert all("Descrição" in (page.extract_text() or "") for page in reader.pages)
