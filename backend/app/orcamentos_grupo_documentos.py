"""Identidades visuais persistidas para os orcamentos do grupo."""

from __future__ import annotations

import secrets
from typing import Callable


def _modelo(modelo_id: str, **personalizacao) -> dict:
    base = {
        "id": modelo_id,
        "fonte": "vera",
        "cor_primaria": "#0f766e",
        "cor_texto": "#1e293b",
        "cor_detalhe": "#475569",
        "cor_borda": "#cbd5e1",
        "cor_linha": "#f8fafc",
        "cor_total_fundo": "#ecfdf5",
        "cor_total_texto": "#065f46",
        "titulo": "ORÇAMENTO COMERCIAL",
        "titulo_alinhamento": "center",
        "empresa_alinhamento": "left",
        "cabecalho_ordem": "empresa_primeiro",
        "meta_alinhamento": "right",
        "meta": ("Referência", "Data", "Validade"),
        "destinatario": "Destinatário",
        "colunas": ("Descrição", "Qtd.", "Un.", "Preço unit.", "Subtotal"),
        "total": "VALOR TOTAL",
        "observacoes": "Condições e observações",
        "assinaturas": ("Responsável", "Assinatura e data"),
        "ordem_itens": "original",
        "grade": True,
        "titulo_tamanho": 20,
    }
    base.update(personalizacao)
    return base


MODELOS_DOCUMENTO = (
    _modelo("moderno_verde"),
    _modelo(
        "classico_azul",
        fonte="times",
        cor_primaria="#1e3a5f",
        cor_texto="#172033",
        cor_detalhe="#526170",
        cor_borda="#9fb0c0",
        cor_linha="#f3f6f8",
        cor_total_fundo="#e8eef4",
        cor_total_texto="#162f49",
        titulo="PROPOSTA COMERCIAL",
        titulo_alinhamento="left",
        cabecalho_ordem="titulo_primeiro",
        meta_alinhamento="left",
        meta=("Proposta nº", "Emissão", "Válida até"),
        destinatario="Aos cuidados de",
        colunas=("Produto / serviço", "Quantidade", "Unidade", "Valor", "Total"),
        total="TOTAL DA PROPOSTA",
        observacoes="Termos da proposta",
        assinaturas=("Representante da empresa", "Aceite / data"),
        ordem_itens="inversa",
        titulo_tamanho=18,
    ),
    _modelo(
        "editorial_rubi",
        fonte="times",
        cor_primaria="#8b1e3f",
        cor_texto="#3f1725",
        cor_detalhe="#76515e",
        cor_borda="#d6a9b7",
        cor_linha="#fff6f8",
        cor_total_fundo="#fce7ef",
        cor_total_texto="#7f1738",
        titulo="COTAÇÃO DE PREÇOS",
        titulo_alinhamento="right",
        empresa_alinhamento="right",
        meta=("Cotação", "Preparada em", "Prazo"),
        destinatario="Solicitante",
        colunas=("Item cotado", "Qtde.", "Medida", "Preço", "Montante"),
        total="MONTANTE GERAL",
        observacoes="Notas desta cotação",
        assinaturas=("Emissor responsável", "Confirmação / data"),
        ordem_itens="alfabetica",
        grade=False,
        titulo_tamanho=22,
    ),
    _modelo(
        "tecnico_grafite",
        fonte="courier",
        cor_primaria="#334155",
        cor_texto="#111827",
        cor_detalhe="#64748b",
        cor_borda="#94a3b8",
        cor_linha="#f1f5f9",
        cor_total_fundo="#e2e8f0",
        cor_total_texto="#1e293b",
        titulo="MEMÓRIA DE PREÇOS",
        titulo_alinhamento="left",
        cabecalho_ordem="titulo_primeiro",
        meta_alinhamento="left",
        meta=("Documento", "Data-base", "Vencimento"),
        destinatario="Requisitante",
        colunas=("Especificação", "Qtde", "Medida", "Unitário", "Importe"),
        total="SOMA DO DOCUMENTO",
        observacoes="Informações complementares",
        assinaturas=("Responsável pela emissão", "Validação / data"),
        ordem_itens="alfabetica_desc",
        grade=True,
        titulo_tamanho=17,
    ),
    _modelo(
        "corporativo_azul",
        fonte="helvetica",
        cor_primaria="#1d4ed8",
        cor_texto="#172554",
        cor_detalhe="#475569",
        cor_borda="#93c5fd",
        cor_linha="#eff6ff",
        cor_total_fundo="#dbeafe",
        cor_total_texto="#1e40af",
        titulo="PROPOSTA DE FORNECIMENTO",
        titulo_alinhamento="center",
        empresa_alinhamento="center",
        meta=("Proposta", "Emitida em", "Validade até"),
        destinatario="Preparado para",
        colunas=("Descrição do fornecimento", "Qtd.", "Un.", "Preço", "Total"),
        total="INVESTIMENTO TOTAL",
        observacoes="Premissas comerciais",
        assinaturas=("Responsável comercial", "De acordo / data"),
        ordem_itens="rotacao",
        grade=False,
        titulo_tamanho=19,
    ),
    _modelo(
        "solar_ambar",
        fonte="vera",
        cor_primaria="#b45309",
        cor_texto="#422006",
        cor_detalhe="#786044",
        cor_borda="#f5c36b",
        cor_linha="#fffbeb",
        cor_total_fundo="#fef3c7",
        cor_total_texto="#92400e",
        titulo="RESUMO DE COTAÇÃO",
        titulo_alinhamento="right",
        empresa_alinhamento="left",
        meta_alinhamento="left",
        meta=("Controle", "Emissão", "Vigência"),
        destinatario="Interessado",
        colunas=("Referência", "Qtde.", "Med.", "Preço unitário", "Parcial"),
        total="TOTAL CONSOLIDADO",
        observacoes="Observações comerciais",
        assinaturas=("Responsável autorizado", "Assinatura / data"),
        ordem_itens="alternada",
        grade=True,
        titulo_tamanho=21,
    ),
)

MODELOS_POR_ID = {modelo["id"]: modelo for modelo in MODELOS_DOCUMENTO}


def sortear_modelos_documento(
    quantidade: int, *, randbelow: Callable[[int], int] = secrets.randbelow
) -> list[str]:
    disponiveis = [modelo["id"] for modelo in MODELOS_DOCUMENTO]
    for indice in range(len(disponiveis) - 1, 0, -1):
        destino = randbelow(indice + 1)
        disponiveis[indice], disponiveis[destino] = (
            disponiveis[destino],
            disponiveis[indice],
        )
    return [disponiveis[indice % len(disponiveis)] for indice in range(quantidade)]


def obter_modelo_documento(empresa_snapshot: dict | None, indice: int = 0) -> dict:
    modelo_id = (empresa_snapshot or {}).get("modelo_documento")
    return MODELOS_POR_ID.get(
        modelo_id, MODELOS_DOCUMENTO[indice % len(MODELOS_DOCUMENTO)]
    )


def ordenar_itens_documento(itens: list[dict], modelo_id: str) -> list[dict]:
    itens_ordenados = [dict(item) for item in itens]
    regra = MODELOS_POR_ID.get(modelo_id, MODELOS_DOCUMENTO[0])["ordem_itens"]
    if regra == "inversa":
        return list(reversed(itens_ordenados))
    if regra == "alfabetica":
        return sorted(
            itens_ordenados, key=lambda item: item.get("descricao", "").lower()
        )
    if regra == "alfabetica_desc":
        return sorted(
            itens_ordenados,
            key=lambda item: item.get("descricao", "").lower(),
            reverse=True,
        )
    if regra == "rotacao" and len(itens_ordenados) > 1:
        return itens_ordenados[1:] + itens_ordenados[:1]
    if regra == "alternada":
        return itens_ordenados[::2] + itens_ordenados[1::2]
    return itens_ordenados


def preparar_snapshot_documento(
    empresa_snapshot: dict, itens_snapshot: list[dict], modelo_id: str
) -> tuple[dict, list[dict]]:
    empresa = dict(empresa_snapshot)
    empresa["modelo_documento"] = modelo_id
    return empresa, ordenar_itens_documento(itens_snapshot, modelo_id)
