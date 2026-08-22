"""Catalogo unico de novidades e projetos exibidos no ERP e no app."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


STATUS_EVOLUCAO = {
    "em_estudo",
    "planejado",
    "em_desenvolvimento",
    "em_testes",
    "disponivel",
}

CANAIS_EVOLUCAO = {
    "erp",
    "app_cliente",
    "app_funcionario",
    "app_entregador",
    "app_veterinario",
}


ITENS_EVOLUCAO: tuple[dict[str, Any], ...] = (
    {
        "id": "evolucao-corepet",
        "titulo": "Acompanhe a evolução do CorePet",
        "resumo": (
            "Uma nova área reúne o que já foi liberado, o que está em andamento "
            "e os projetos que ainda estão em estudo."
        ),
        "status": "disponivel",
        "tipo": "novidade",
        "modulo": "CorePet",
        "plataformas": ["ERP", "App do cliente", "App do funcionário"],
        "canais": [
            "erp",
            "app_cliente",
            "app_funcionario",
            "app_entregador",
            "app_veterinario",
        ],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=acompanhar-novidades-projetos",
    },
    {
        "id": "expansao-central-ajuda",
        "titulo": "Central de Ajuda cada vez mais guiada",
        "resumo": (
            "Os artigos do sistema e os guias visuais em PDF serão ampliados por módulo, "
            "sempre com caminho da tela, exemplos, alertas e checklist final."
        ),
        "status": "em_desenvolvimento",
        "tipo": "melhoria",
        "modulo": "Ajuda",
        "plataformas": ["ERP", "App do cliente", "App do funcionário"],
        "canais": [
            "erp",
            "app_cliente",
            "app_funcionario",
            "app_entregador",
            "app_veterinario",
        ],
        "publicado_em": None,
        "atualizado_em": "2026-08-22",
        "destaque": True,
        "caminho_ajuda": None,
    },
    {
        "id": "cadastro-rapido-cliente-app-funcionario",
        "titulo": "Cadastro rápido de cliente durante a venda",
        "resumo": (
            "Um botão + permitirá localizar ou cadastrar uma pessoa sem sair da venda. "
            "Nome, telefone e endereço serão opcionais."
        ),
        "status": "planejado",
        "tipo": "projeto",
        "modulo": "Vendas",
        "plataformas": ["App do funcionário"],
        "canais": ["erp", "app_funcionario"],
        "publicado_em": None,
        "atualizado_em": "2026-08-22",
        "destaque": True,
        "caminho_ajuda": None,
    },
    {
        "id": "granel-bipagem-vinculada",
        "titulo": "Lançamento de granel com conferência por bipagem",
        "resumo": (
            "O produto a granel poderá ser ligado a mais de um produto pai. A bipagem "
            "confere a combinação e poderá ser obrigatória ou opcional por configuração."
        ),
        "status": "planejado",
        "tipo": "projeto",
        "modulo": "Produtos e estoque",
        "plataformas": ["ERP", "App do funcionário"],
        "canais": ["erp", "app_funcionario"],
        "publicado_em": None,
        "atualizado_em": "2026-08-22",
        "destaque": True,
        "caminho_ajuda": None,
    },
    {
        "id": "grupos-empresas-transferencia-integrada",
        "titulo": "Grupos de empresas e transferência integrada",
        "resumo": (
            "Empresas poderão formar grupos por convite, acompanhar resultados consolidados "
            "e transferir produtos com saída em uma empresa e entrada na outra."
        ),
        "status": "em_estudo",
        "tipo": "projeto",
        "modulo": "Empresas e estoque",
        "plataformas": ["ERP"],
        "canais": ["erp"],
        "publicado_em": None,
        "atualizado_em": "2026-08-22",
        "destaque": False,
        "caminho_ajuda": None,
    },
    {
        "id": "crediario-vencimento-alertas",
        "titulo": "Crediário com vencimento e alertas",
        "resumo": (
            "A venda ficará em aberto com data combinada para pagamento, alerta no ERP "
            "e aviso para o cliente no aplicativo."
        ),
        "status": "planejado",
        "tipo": "projeto",
        "modulo": "Financeiro e vendas",
        "plataformas": ["ERP", "App do cliente"],
        "canais": ["erp", "app_cliente"],
        "publicado_em": None,
        "atualizado_em": "2026-08-22",
        "destaque": True,
        "caminho_ajuda": None,
    },
    {
        "id": "avaliacao-entrega-app",
        "titulo": "Avaliação da entrega pelo aplicativo",
        "resumo": (
            "Depois da entrega, o cliente poderá avaliar a experiência para que a empresa "
            "acompanhe a qualidade de cada atendimento."
        ),
        "status": "planejado",
        "tipo": "projeto",
        "modulo": "Entregas",
        "plataformas": ["ERP", "App do cliente"],
        "canais": ["erp", "app_cliente", "app_entregador"],
        "publicado_em": None,
        "atualizado_em": "2026-08-22",
        "destaque": False,
        "caminho_ajuda": None,
    },
    {
        "id": "fracionamento-produtos-farmacia",
        "titulo": "Venda unitária de produtos de farmácia",
        "resumo": (
            "O fluxo correto para caixas com unidades será estudado usando fracionamento "
            "de embalagem ou produto com composição, sem misturar com ração a granel."
        ),
        "status": "em_estudo",
        "tipo": "projeto",
        "modulo": "Produtos e estoque",
        "plataformas": ["ERP"],
        "canais": ["erp"],
        "publicado_em": None,
        "atualizado_em": "2026-08-22",
        "destaque": False,
        "caminho_ajuda": None,
    },
)


def validar_catalogo_evolucao() -> None:
    """Falha cedo quando uma entrada quebra o combinado de publicacao."""

    ids: set[str] = set()
    for item in ITENS_EVOLUCAO:
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in ids:
            raise ValueError(f"ID de evolucao ausente ou duplicado: {item_id!r}")
        ids.add(item_id)

        status = item.get("status")
        if status not in STATUS_EVOLUCAO:
            raise ValueError(f"Status de evolucao invalido em {item_id}: {status!r}")

        canais = set(item.get("canais") or [])
        if not canais or not canais.issubset(CANAIS_EVOLUCAO):
            raise ValueError(f"Canais de evolucao invalidos em {item_id}: {sorted(canais)}")

        if not item.get("atualizado_em"):
            raise ValueError(f"Item de evolucao sem data de atualizacao: {item_id}")

        if status == "disponivel":
            if not item.get("publicado_em"):
                raise ValueError(f"Novidade disponivel sem data de publicacao: {item_id}")
            if not item.get("caminho_ajuda"):
                raise ValueError(f"Novidade disponivel sem caminho de ajuda: {item_id}")


def listar_evolucao_corepet(canal: str) -> dict[str, Any]:
    """Retorna apenas itens anunciados para o canal solicitado."""

    if canal not in CANAIS_EVOLUCAO:
        raise ValueError(f"Canal de evolucao invalido: {canal!r}")

    validar_catalogo_evolucao()
    itens = [deepcopy(item) for item in ITENS_EVOLUCAO if canal in item["canais"]]
    itens.sort(
        key=lambda item: (
            item.get("atualizado_em") or "",
            bool(item.get("destaque")),
            item["id"],
        ),
        reverse=True,
    )
    return {
        "itens": itens,
        "atualizado_em": max(item["atualizado_em"] for item in itens) if itens else None,
        "total_disponivel": sum(item["status"] == "disponivel" for item in itens),
    }


validar_catalogo_evolucao()
