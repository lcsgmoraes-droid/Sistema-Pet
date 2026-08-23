"""Catalogo unico de novidades e projetos exibidos no ERP e no app."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import logging
from typing import Any, Mapping, TYPE_CHECKING

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from app.evolucao_models import EvolucaoFuncionalidadeUso

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


STATUS_EVOLUCAO = {
    "em_estudo",
    "planejado",
    "em_desenvolvimento",
    "em_testes",
    "disponivel",
    "disponivel_teste",
    "implantado",
}

STATUS_DISPONIVEIS = {"disponivel", "disponivel_teste", "implantado"}

CICLO_PADRAO = {
    "dias_minimos_teste": 14,
    "usos_minimos_teste": 10,
    "promover_quando": "todos",
    "dias_visivel_apos_implantado": 30,
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
        "status": "implantado",
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
        "implantado_em": "2026-08-22",
        "dias_visivel_apos_implantado": 30,
        "atualizado_em": "2026-08-22",
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=acompanhar-novidades-projetos",
    },
    {
        "id": "expansao-central-ajuda",
        "titulo": "Central de Ajuda cada vez mais guiada",
        "resumo": (
            "A Central reúne artigos pesquisáveis por módulo e links diretos das novidades, "
            "com caminho da tela, passos, alertas e checklist de conferência."
        ),
        "status": "disponivel_teste",
        "tipo": "melhoria",
        "modulo": "Ajuda",
        "plataformas": ["ERP"],
        "canais": [
            "erp",
            "app_cliente",
            "app_funcionario",
            "app_entregador",
            "app_veterinario",
        ],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": {
            **deepcopy(CICLO_PADRAO),
            # A leitura dos artigos não identifica usuário ou empresa; a promoção
            # desta melhoria depende apenas do período mínimo de acompanhamento.
            "usos_minimos_teste": 0,
        },
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=usar-central-ajuda-guiada",
    },
    {
        "id": "cadastro-rapido-cliente-app-funcionario",
        "titulo": "Cadastro rápido de cliente durante a venda",
        "resumo": (
            "O botão + permite localizar ou cadastrar uma pessoa sem sair da venda. "
            "Nome, telefone e endereço são opcionais."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Vendas",
        "plataformas": ["App do funcionário"],
        "canais": ["erp", "app_funcionario"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=cadastro-rapido-cliente-app-funcionario",
    },
    {
        "id": "granel-bipagem-vinculada",
        "titulo": "Lançamento de granel com conferência por bipagem",
        "resumo": (
            "O produto a granel pode ser ligado a mais de um produto pai. A bipagem "
            "confere a combinação e pode ser obrigatória ou opcional por configuração."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Produtos e estoque",
        "plataformas": ["ERP", "App do funcionário"],
        "canais": ["erp", "app_funcionario"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=lancar-granel-bipagem",
    },
    {
        "id": "grupos-empresas-convites",
        "titulo": "Grupos de empresas por convite",
        "resumo": (
            "Cada empresa recebe um código mensal e pode criar ou aceitar grupos com "
            "outras empresas, mantendo o aceite e os membros sob controle."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Empresas",
        "plataformas": ["ERP"],
        "canais": ["erp"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=grupos-empresas-convites",
    },
    {
        "id": "grupos-empresas-visao-consolidada",
        "titulo": "Visão consolidada do grupo de empresas",
        "resumo": (
            "Compare vendas, estoque e saldos financeiros das empresas do grupo "
            "em uma única tela, sem misturar cadastros ou lançamentos individuais."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Empresas e relatórios",
        "plataformas": ["ERP"],
        "canais": ["erp"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=visao-consolidada-grupo-empresas",
    },
    {
        "id": "grupos-empresas-transferencia-integrada",
        "titulo": "Transferência integrada entre empresas do grupo",
        "resumo": (
            "A transferência registra a saída na empresa de origem e a entrada na "
            "empresa de destino em uma única operação, com conferência por código de barras "
            "e cancelamento seguro dos dois lados."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Empresas e estoque",
        "plataformas": ["ERP"],
        "canais": ["erp"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=transferencia-integrada-grupo",
    },
    {
        "id": "grupos-empresas-analises-detalhadas",
        "titulo": "Pedidos, produtos e contas consolidados por grupo",
        "resumo": (
            "Consulte vendas e pedidos de compra das empresas juntas, pesquise produtos por SKU "
            "ou EAN, confirme equivalências e acompanhe o contas a pagar mesclado."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Empresas e relatórios",
        "plataformas": ["ERP"],
        "canais": ["erp"],
        "publicado_em": "2026-08-23",
        "atualizado_em": "2026-08-23",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=visao-consolidada-grupo-empresas",
    },
    {
        "id": "grupos-empresas-planejamento-inteligente",
        "titulo": "Reposição e financeiro inteligentes para o grupo",
        "resumo": (
            "Planeje compras usando o estoque de todas as empresas, transfira sobras antes "
            "de comprar e acompanhe entradas e saídas por vencimento."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Empresas, compras e financeiro",
        "plataformas": ["ERP"],
        "canais": ["erp"],
        "publicado_em": "2026-08-23",
        "atualizado_em": "2026-08-23",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=visao-consolidada-grupo-empresas",
    },
    {
        "id": "crediario-vencimento-alertas",
        "titulo": "Crediário com vencimento e alertas",
        "resumo": (
            "A venda fica em aberto com data combinada para pagamento, alerta no ERP "
            "e aviso para o cliente no aplicativo."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Financeiro e vendas",
        "plataformas": ["ERP", "App do funcionário", "App do cliente"],
        "canais": ["erp", "app_funcionario", "app_cliente"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": True,
        "caminho_ajuda": "/ajuda?aba=central&artigo=venda-crediario-app-funcionario",
    },
    {
        "id": "avaliacao-entrega-app",
        "titulo": "Avaliação da entrega pelo aplicativo",
        "resumo": (
            "Depois da entrega, o cliente pode avaliar a experiência para que a empresa "
            "acompanhe a qualidade de cada atendimento."
        ),
        "status": "disponivel_teste",
        "tipo": "projeto",
        "modulo": "Entregas",
        "plataformas": ["ERP", "App do cliente"],
        "canais": ["erp", "app_cliente", "app_entregador"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": deepcopy(CICLO_PADRAO),
        "destaque": False,
        "caminho_ajuda": "/ajuda?aba=central&artigo=avaliar-entrega-app-cliente",
    },
    {
        "id": "foto-pet-carteira-vacina",
        "titulo": "Foto do pet na carteira de vacinação",
        "resumo": (
            "A carteira digital de vacinas exibe a foto cadastrada do pet, facilitando "
            "a identificação pelo tutor."
        ),
        "status": "disponivel_teste",
        "tipo": "novidade",
        "modulo": "Pets e vacinas",
        "plataformas": ["App do cliente"],
        "canais": ["erp", "app_cliente"],
        "publicado_em": "2026-08-22",
        "atualizado_em": "2026-08-22",
        "ciclo_novidade": {
            **deepcopy(CICLO_PADRAO),
            "usos_minimos_teste": 0,
        },
        "destaque": False,
        "caminho_ajuda": "/ajuda?aba=central&artigo=foto-pet-carteira-vacina",
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
            raise ValueError(
                f"Canais de evolucao invalidos em {item_id}: {sorted(canais)}"
            )

        if not item.get("atualizado_em"):
            raise ValueError(f"Item de evolucao sem data de atualizacao: {item_id}")

        if status in STATUS_DISPONIVEIS:
            if not item.get("publicado_em"):
                raise ValueError(
                    f"Novidade disponivel sem data de publicacao: {item_id}"
                )
            if not item.get("caminho_ajuda"):
                raise ValueError(f"Novidade disponivel sem caminho de ajuda: {item_id}")

        if status == "disponivel_teste":
            ciclo = item.get("ciclo_novidade") or {}
            if ciclo.get("promover_quando") not in {"todos", "qualquer"}:
                raise ValueError(f"Criterio de promocao invalido em {item_id}")
            for campo in (
                "dias_minimos_teste",
                "usos_minimos_teste",
                "dias_visivel_apos_implantado",
            ):
                valor = ciclo.get(campo)
                if not isinstance(valor, int) or valor < 0:
                    raise ValueError(f"{campo} invalido em {item_id}: {valor!r}")

        if status == "implantado" and not item.get("implantado_em"):
            raise ValueError(f"Novidade implantada sem data: {item_id}")


def _data(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None


def _agora_utc(agora: datetime | None = None) -> datetime:
    valor = agora or datetime.now(timezone.utc)
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _em_utc(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _item_por_id(item_id: str) -> dict[str, Any] | None:
    return next((item for item in ITENS_EVOLUCAO if item["id"] == item_id), None)


def registrar_uso_funcionalidade(
    db: "Session",
    item_id: str,
    *,
    quantidade: int = 1,
    agora: datetime | None = None,
) -> bool:
    """Incrementa uma metrica anonima depois de um uso concluido com sucesso."""

    item = _item_por_id(item_id)
    if not item or item.get("status") != "disponivel_teste" or quantidade <= 0:
        return False

    ciclo = item.get("ciclo_novidade") or CICLO_PADRAO
    usos_minimos = int(ciclo.get("usos_minimos_teste") or 0)
    momento = _agora_utc(agora)
    tabela = EvolucaoFuncionalidadeUso.__table__

    def incrementar_existente() -> bool:
        existente = (
            db.execute(
                select(tabela).where(tabela.c.item_id == item_id).with_for_update()
            )
            .mappings()
            .first()
        )
        if existente is None:
            return False
        novo_total = int(existente["usos_total"] or 0) + quantidade
        valores: dict[str, Any] = {
            "usos_total": novo_total,
            "primeiro_uso_em": existente["primeiro_uso_em"] or momento,
            "ultimo_uso_em": momento,
        }
        if (
            usos_minimos > 0
            and novo_total >= usos_minimos
            and existente["limiar_teste_atingido_em"] is None
        ):
            valores["limiar_teste_atingido_em"] = momento
        db.execute(update(tabela).where(tabela.c.item_id == item_id).values(**valores))
        db.commit()
        return True

    try:
        if incrementar_existente():
            return True
        db.execute(
            insert(tabela).values(
                item_id=item_id,
                usos_total=quantidade,
                primeiro_uso_em=momento,
                ultimo_uso_em=momento,
                limiar_teste_atingido_em=(
                    momento if usos_minimos > 0 and quantidade >= usos_minimos else None
                ),
            )
        )
        try:
            db.commit()
            return True
        except IntegrityError:
            # Outra requisicao pode ter criado o contador no mesmo instante.
            db.rollback()
            return incrementar_existente()
    except Exception:
        db.rollback()
        logger.warning(
            "Nao foi possivel registrar uso da funcionalidade %s",
            item_id,
            exc_info=True,
        )
        return False


def _resolver_fase_disponivel(
    item: dict[str, Any],
    metrica: Mapping[str, Any] | None,
    agora: datetime,
) -> tuple[str, datetime | None, date | None]:
    status = item["status"]
    dias_visivel = int(
        (item.get("ciclo_novidade") or {}).get(
            "dias_visivel_apos_implantado",
            item.get("dias_visivel_apos_implantado", 30),
        )
    )

    if status in {"implantado", "disponivel"}:
        implantado_data = _data(item.get("implantado_em") or item.get("publicado_em"))
        implantado_em = (
            datetime.combine(implantado_data, time.min, tzinfo=timezone.utc)
            if implantado_data
            else None
        )
    else:
        ciclo = item.get("ciclo_novidade") or CICLO_PADRAO
        publicado = _data(item.get("publicado_em")) or agora.date()
        marco_tempo = datetime.combine(
            publicado + timedelta(days=int(ciclo["dias_minimos_teste"])),
            time.min,
            tzinfo=timezone.utc,
        )
        usos_minimos = int(ciclo["usos_minimos_teste"])
        marco_uso = (
            marco_tempo
            if usos_minimos == 0
            else _em_utc(metrica.get("limiar_teste_atingido_em") if metrica else None)
        )
        criterio = ciclo.get("promover_quando", "todos")
        if criterio == "qualquer":
            candidatos = [valor for valor in (marco_tempo, marco_uso) if valor]
            implantado_em = (
                min(candidatos) if candidatos and agora >= min(candidatos) else None
            )
        else:
            implantado_em = (
                max(marco_tempo, marco_uso)
                if marco_uso is not None and agora >= max(marco_tempo, marco_uso)
                else None
            )

    if implantado_em is None:
        return "teste", None, None

    novidade_ate = implantado_em.date() + timedelta(days=dias_visivel)
    return "implantado", implantado_em, novidade_ate


def _serializar_item(
    item: dict[str, Any],
    metrica: Mapping[str, Any] | None,
    agora: datetime,
) -> dict[str, Any] | None:
    registro = deepcopy(item)
    if item["status"] not in STATUS_DISPONIVEIS:
        return registro

    fase, implantado_em, novidade_ate = _resolver_fase_disponivel(item, metrica, agora)
    if novidade_ate is not None and agora.date() > novidade_ate:
        return None

    # Compatibilidade: apps antigos continuam reconhecendo o item como disponivel.
    registro["status"] = "disponivel"
    registro["fase_disponibilidade"] = fase
    registro["status_label"] = (
        "Disponível — em fase de teste" if fase == "teste" else "Implantado"
    )
    registro["implantado_em"] = (
        implantado_em.date().isoformat() if implantado_em else None
    )
    registro["novidade_ate"] = novidade_ate.isoformat() if novidade_ate else None
    registro.pop("ciclo_novidade", None)
    registro.pop("dias_visivel_apos_implantado", None)
    return registro


def listar_evolucao_corepet(
    canal: str,
    db: "Session | None" = None,
    *,
    agora: datetime | None = None,
) -> dict[str, Any]:
    """Retorna apenas itens anunciados para o canal solicitado."""

    if canal not in CANAIS_EVOLUCAO:
        raise ValueError(f"Canal de evolucao invalido: {canal!r}")

    validar_catalogo_evolucao()
    catalogo_canal = [item for item in ITENS_EVOLUCAO if canal in item["canais"]]
    metricas: dict[str, Mapping[str, Any]] = {}
    if db is not None:
        ids = [
            item["id"]
            for item in catalogo_canal
            if item["status"] == "disponivel_teste"
        ]
        if ids:
            tabela = EvolucaoFuncionalidadeUso.__table__
            try:
                metricas = {
                    metrica["item_id"]: metrica
                    for metrica in db.execute(
                        select(tabela).where(tabela.c.item_id.in_(ids))
                    ).mappings()
                }
            except Exception:
                db.rollback()
                logger.warning(
                    "Metricas de implantacao indisponiveis; exibindo fase de teste",
                    exc_info=True,
                )

    momento = _agora_utc(agora)
    itens = [
        serializado
        for item in catalogo_canal
        if (serializado := _serializar_item(item, metricas.get(item["id"]), momento))
        is not None
    ]
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
        "atualizado_em": max(item["atualizado_em"] for item in itens)
        if itens
        else None,
        "total_disponivel": sum(item["status"] == "disponivel" for item in itens),
    }


validar_catalogo_evolucao()
