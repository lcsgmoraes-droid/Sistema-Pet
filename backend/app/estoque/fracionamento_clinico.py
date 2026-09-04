"""Regras de abertura de embalagens para consumo clinico fracionado."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.produtos_models import (
    EstoqueFracionamentoConversao,
    EstoqueFracionamentoVinculo,
    EstoqueMovimentacao,
    Produto,
    ProdutoLote,
)


_EPSILON = 1e-9


def _numero_positivo(valor: Any, campo: str) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{campo} invalido") from exc
    if not math.isfinite(numero) or numero <= 0:
        raise HTTPException(status_code=422, detail=f"{campo} deve ser maior que zero")
    return numero


def _produto_operacional(produto: Produto | None, *, papel: str) -> Produto:
    if not produto:
        raise HTTPException(
            status_code=404, detail=f"Produto de {papel} nao encontrado"
        )
    if (
        getattr(produto, "ativo", True) is False
        or getattr(produto, "situacao", True) is False
    ):
        raise HTTPException(status_code=400, detail=f"Produto de {papel} esta inativo")
    if not getattr(produto, "controlar_estoque", True):
        raise HTTPException(
            status_code=400,
            detail=f"Produto de {papel} precisa controlar estoque",
        )
    if getattr(produto, "e_granel", False):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Produto de {papel} esta configurado como granel; "
                "use o fluxo especifico de granel"
            ),
        )
    if getattr(produto, "tipo_produto", None) == "PAI" or getattr(
        produto, "is_parent", False
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Produto de {papel} nao pode ser um agrupador de variacoes",
        )
    if (
        getattr(produto, "tipo_produto", None) == "KIT"
        and getattr(produto, "tipo_kit", None) == "VIRTUAL"
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Produto de {papel} nao pode ser um kit virtual",
        )
    return produto


def _sem_timezone(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)
    return valor


def _menor_validade(*valores: datetime | None) -> datetime | None:
    datas = [_sem_timezone(valor) for valor in valores if valor is not None]
    return min(datas) if datas else None


def _serializar_lotes_json(lotes: list[dict]) -> list[dict]:
    return [
        {
            chave: valor.isoformat() if isinstance(valor, datetime) else valor
            for chave, valor in lote.items()
        }
        for lote in lotes
    ]


def _serializar_produto(produto: Produto) -> dict:
    return {
        "id": produto.id,
        "codigo": getattr(produto, "codigo", None),
        "nome": produto.nome,
        "unidade": (getattr(produto, "unidade", None) or "UN").upper(),
        "estoque_atual": float(getattr(produto, "estoque_atual", 0) or 0),
        "preco_custo": float(getattr(produto, "preco_custo", 0) or 0),
    }


def serializar_vinculo_fracionamento(vinculo: EstoqueFracionamentoVinculo) -> dict:
    origem = vinculo.produto_origem
    destino = vinculo.produto_destino
    return {
        "id": vinculo.id,
        "produto_origem_id": vinculo.produto_origem_id,
        "produto_destino_id": vinculo.produto_destino_id,
        "produto_origem": _serializar_produto(origem) if origem else None,
        "produto_destino": _serializar_produto(destino) if destino else None,
        "fator_conversao": float(vinculo.fator_conversao or 0),
        "validade_apos_abertura_dias": vinculo.validade_apos_abertura_dias,
        "observacao": vinculo.observacao,
        "ativo": bool(vinculo.ativo),
    }


def listar_lotes_disponiveis_fracionamento(
    db: Session, *, tenant_id, produto_id: int
) -> list[dict]:
    lotes = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.tenant_id == tenant_id,
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.status == "ativo",
            ProdutoLote.quantidade_disponivel > 0,
            or_(
                ProdutoLote.data_validade.is_(None),
                ProdutoLote.data_validade > datetime.utcnow(),
            ),
        )
        .order_by(
            ProdutoLote.data_validade.asc().nullslast(),
            ProdutoLote.ordem_entrada.asc(),
            ProdutoLote.id.asc(),
        )
        .all()
    )
    return [
        {
            "id": lote.id,
            "nome_lote": lote.nome_lote,
            "quantidade_disponivel": float(lote.quantidade_disponivel or 0),
            "data_fabricacao": lote.data_fabricacao,
            "data_validade": lote.data_validade,
            "custo_unitario": float(lote.custo_unitario or 0),
        }
        for lote in lotes
    ]


def _obter_ou_atualizar_vinculo(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    produto_origem: Produto,
    produto_destino: Produto,
    fator_conversao: float,
    validade_apos_abertura_dias: int | None,
    observacao: str | None,
) -> EstoqueFracionamentoVinculo:
    vinculo = (
        db.query(EstoqueFracionamentoVinculo)
        .filter(
            EstoqueFracionamentoVinculo.tenant_id == tenant_id,
            EstoqueFracionamentoVinculo.produto_origem_id == produto_origem.id,
            EstoqueFracionamentoVinculo.produto_destino_id == produto_destino.id,
        )
        .first()
    )
    if vinculo:
        vinculo.fator_conversao = fator_conversao
        vinculo.validade_apos_abertura_dias = validade_apos_abertura_dias
        vinculo.observacao = observacao
        vinculo.ativo = True
        vinculo.user_id = user_id
        return vinculo

    vinculo = EstoqueFracionamentoVinculo(
        tenant_id=tenant_id,
        produto_origem_id=produto_origem.id,
        produto_destino_id=produto_destino.id,
        fator_conversao=fator_conversao,
        validade_apos_abertura_dias=validade_apos_abertura_dias,
        observacao=observacao,
        ativo=True,
        user_id=user_id,
    )
    db.add(vinculo)
    db.flush()
    return vinculo


def _lotes_origem_para_consumo(
    db: Session,
    *,
    tenant_id,
    produto: Produto,
    quantidade: float,
    lote_origem_id: int | None,
) -> tuple[list[dict], float]:
    query = db.query(ProdutoLote).filter(
        ProdutoLote.tenant_id == tenant_id,
        ProdutoLote.produto_id == produto.id,
        ProdutoLote.status == "ativo",
        ProdutoLote.quantidade_disponivel > 0,
        or_(
            ProdutoLote.data_validade.is_(None),
            ProdutoLote.data_validade > datetime.utcnow(),
        ),
    )
    if lote_origem_id:
        query = query.filter(ProdutoLote.id == lote_origem_id)
    lotes = (
        query.order_by(
            ProdutoLote.data_validade.asc().nullslast(),
            ProdutoLote.ordem_entrada.asc(),
            ProdutoLote.id.asc(),
        )
        .with_for_update()
        .all()
    )
    lotes = [
        lote
        for lote in lotes
        if lote.produto_id == produto.id
        and lote.status == "ativo"
        and float(lote.quantidade_disponivel or 0) > 0
        and (not lote_origem_id or lote.id == lote_origem_id)
    ]

    total_lotes = sum(float(lote.quantidade_disponivel or 0) for lote in lotes)
    exige_lote = bool(lote_origem_id or getattr(produto, "controle_lote", False))
    if exige_lote and total_lotes + _EPSILON < quantidade:
        detalhe = "Lote selecionado" if lote_origem_id else "Lotes disponiveis"
        raise HTTPException(
            status_code=400,
            detail=(
                f"{detalhe} sem saldo suficiente para abrir {quantidade:g} "
                f"{getattr(produto, 'unidade', None) or 'UN'} de {produto.nome}"
            ),
        )

    restante = quantidade
    consumidos: list[dict] = []
    custo_total = 0.0
    for lote in lotes:
        if restante <= _EPSILON:
            break
        disponivel = float(lote.quantidade_disponivel or 0)
        retirar = min(disponivel, restante)
        custo_lote = float(lote.custo_unitario or produto.preco_custo or 0)
        lote.quantidade_disponivel = max(0.0, disponivel - retirar)
        if lote.quantidade_disponivel <= _EPSILON:
            lote.quantidade_disponivel = 0.0
            lote.status = "esgotado"
        restante -= retirar
        custo_total += retirar * custo_lote
        consumidos.append(
            {
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "quantidade": retirar,
                "custo_unitario": custo_lote,
                "data_fabricacao": lote.data_fabricacao,
                "data_validade": lote.data_validade,
            }
        )

    if restante > _EPSILON:
        custo_total += restante * float(produto.preco_custo or 0)
    return consumidos, custo_total


def _criar_lotes_destino(
    db: Session,
    *,
    tenant_id,
    conversao: EstoqueFracionamentoConversao,
    produto_destino: Produto,
    lotes_origem: list[dict],
    quantidade_destino: float,
    fator_conversao: float,
    custo_destino: float,
    validade_abertura: datetime | None,
) -> list[dict]:
    bases = lotes_origem or [
        {
            "lote_id": None,
            "nome_lote": "SEM-LOTE",
            "quantidade": conversao.quantidade_origem,
            "data_fabricacao": None,
            "data_validade": None,
        }
    ]
    criados: list[dict] = []
    total_criado = 0.0
    for indice, origem in enumerate(bases):
        quantidade = float(origem["quantidade"] or 0) * fator_conversao
        if indice == len(bases) - 1:
            quantidade = quantidade_destino - total_criado
        total_criado += quantidade
        sufixo = str(origem.get("nome_lote") or "SEM-LOTE")
        nome_lote = f"CL-{conversao.id}-{sufixo}"[:50]
        data_validade = _menor_validade(origem.get("data_validade"), validade_abertura)
        lote = ProdutoLote(
            tenant_id=tenant_id,
            produto_id=produto_destino.id,
            nome_lote=nome_lote,
            data_fabricacao=_sem_timezone(origem.get("data_fabricacao")),
            data_validade=data_validade,
            deposito="clinica",
            quantidade_inicial=quantidade,
            quantidade_disponivel=quantidade,
            quantidade_reservada=0,
            limite_dias=30,
            codigo_agregacao=f"FRAC-{conversao.id}",
            status="ativo",
            ordem_entrada=int(conversao.aberto_em.timestamp()) + indice,
            custo_unitario=custo_destino,
        )
        db.add(lote)
        db.flush()
        criados.append(
            {
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "lote_origem_id": origem.get("lote_id"),
                "quantidade": quantidade,
                "data_validade": lote.data_validade,
            }
        )
    produto_destino.controle_lote = True
    return criados


def executar_fracionamento_clinico(
    db: Session,
    *,
    tenant_id,
    current_user,
    payload: Any,
) -> dict:
    """Baixa a embalagem fechada e abastece o item clinico na mesma transacao."""

    produto_origem_id = int(payload.produto_origem_id)
    produto_destino_id = int(payload.produto_destino_id)
    if produto_origem_id == produto_destino_id:
        raise HTTPException(
            status_code=400,
            detail="Produto fechado e produto clinico precisam ser diferentes",
        )

    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id.in_(sorted([produto_origem_id, produto_destino_id])),
        )
        .order_by(Produto.id.asc())
        .with_for_update()
        .all()
    )
    produtos_por_id = {produto.id: produto for produto in produtos}
    produto_origem = _produto_operacional(
        produtos_por_id.get(produto_origem_id), papel="origem"
    )
    produto_destino = _produto_operacional(
        produtos_por_id.get(produto_destino_id), papel="destino"
    )

    quantidade_origem = _numero_positivo(
        payload.quantidade_origem, "Quantidade de embalagens"
    )
    unidade_origem = (produto_origem.unidade or "UN").upper()
    if not math.isclose(quantidade_origem, round(quantidade_origem), abs_tol=_EPSILON):
        raise HTTPException(
            status_code=422,
            detail="Produto em unidade deve ser aberto em quantidade inteira",
        )
    fator_conversao = _numero_positivo(
        payload.fator_conversao, "Conteudo por embalagem"
    )
    quantidade_destino = quantidade_origem * fator_conversao
    estoque_origem_anterior = float(produto_origem.estoque_atual or 0)
    estoque_destino_anterior = float(produto_destino.estoque_atual or 0)
    if estoque_origem_anterior + _EPSILON < quantidade_origem:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente de {produto_origem.nome}. Disponivel: "
                f"{estoque_origem_anterior:g}, necessario: {quantidade_origem:g}"
            ),
        )
    if estoque_destino_anterior > _EPSILON:
        saldo_lotes_destino = sum(
            item["quantidade_disponivel"]
            for item in listar_lotes_disponiveis_fracionamento(
                db,
                tenant_id=tenant_id,
                produto_id=produto_destino.id,
            )
        )
        if saldo_lotes_destino + _EPSILON < estoque_destino_anterior:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"O produto clinico {produto_destino.nome} possui saldo sem lote "
                    "valido. Regularize esse saldo antes de abrir uma nova embalagem."
                ),
            )

    user_id = getattr(current_user, "id", None)
    if not user_id and isinstance(current_user, dict):
        user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="Usuario invalido para fracionamento"
        )

    validade_dias = getattr(payload, "validade_apos_abertura_dias", None)
    observacao = (getattr(payload, "observacao", None) or "").strip() or None
    vinculo = _obter_ou_atualizar_vinculo(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        produto_origem=produto_origem,
        produto_destino=produto_destino,
        fator_conversao=fator_conversao,
        validade_apos_abertura_dias=validade_dias,
        observacao=observacao,
    )

    lotes_origem, custo_total = _lotes_origem_para_consumo(
        db,
        tenant_id=tenant_id,
        produto=produto_origem,
        quantidade=quantidade_origem,
        lote_origem_id=getattr(payload, "lote_origem_id", None),
    )
    custo_origem_unitario = custo_total / quantidade_origem
    custo_destino_unitario = custo_total / quantidade_destino
    estoque_origem_novo = estoque_origem_anterior - quantidade_origem
    estoque_destino_novo = estoque_destino_anterior + quantidade_destino

    produto_origem.estoque_atual = estoque_origem_novo
    produto_destino.estoque_atual = estoque_destino_novo
    if estoque_destino_novo > 0:
        custo_destino_anterior = float(produto_destino.preco_custo or 0)
        valor_anterior = max(estoque_destino_anterior, 0) * custo_destino_anterior
        produto_destino.preco_custo = (
            valor_anterior + custo_total
        ) / estoque_destino_novo

    aberto_em = datetime.now(timezone.utc)
    validade_abertura = (
        aberto_em + timedelta(days=int(validade_dias)) if validade_dias else None
    )
    conversao = EstoqueFracionamentoConversao(
        tenant_id=tenant_id,
        vinculo_id=vinculo.id,
        produto_origem_id=produto_origem.id,
        produto_destino_id=produto_destino.id,
        quantidade_origem=quantidade_origem,
        fator_conversao=fator_conversao,
        quantidade_destino=quantidade_destino,
        unidade_origem=unidade_origem,
        unidade_destino=(produto_destino.unidade or "UN").upper(),
        estoque_origem_anterior=estoque_origem_anterior,
        estoque_origem_novo=estoque_origem_novo,
        estoque_destino_anterior=estoque_destino_anterior,
        estoque_destino_novo=estoque_destino_novo,
        custo_origem_unitario=custo_origem_unitario,
        custo_destino_unitario=custo_destino_unitario,
        lotes_origem_consumidos=(
            _serializar_lotes_json(lotes_origem) if lotes_origem else None
        ),
        aberto_em=aberto_em,
        validade_apos_abertura_em=validade_abertura,
        documento=(getattr(payload, "documento", None) or "").strip() or None,
        observacao=observacao,
        status="confirmado",
        user_id=user_id,
    )
    db.add(conversao)
    db.flush()

    lotes_destino = _criar_lotes_destino(
        db,
        tenant_id=tenant_id,
        conversao=conversao,
        produto_destino=produto_destino,
        lotes_origem=lotes_origem,
        quantidade_destino=quantidade_destino,
        fator_conversao=fator_conversao,
        custo_destino=custo_destino_unitario,
        validade_abertura=validade_abertura,
    )
    conversao.lotes_destino_criados = _serializar_lotes_json(lotes_destino)

    documento = conversao.documento or f"FRAC-{conversao.id}"
    mov_saida = EstoqueMovimentacao(
        tenant_id=tenant_id,
        produto_id=produto_origem.id,
        tipo="saida",
        motivo="fracionamento_clinico",
        quantidade=quantidade_origem,
        quantidade_anterior=estoque_origem_anterior,
        quantidade_nova=estoque_origem_novo,
        custo_unitario=custo_origem_unitario,
        valor_total=custo_total,
        lotes_consumidos=json.dumps(lotes_origem, default=str)
        if lotes_origem
        else None,
        estoque_origem="loja",
        estoque_destino="clinica",
        documento=documento,
        referencia_id=conversao.id,
        referencia_tipo="fracionamento_clinico",
        observacao=(
            f"Abertura para uso clinico: {quantidade_destino:g} "
            f"{produto_destino.unidade or 'UN'} em {produto_destino.nome}"
        ),
        user_id=user_id,
    )
    mov_entrada = EstoqueMovimentacao(
        tenant_id=tenant_id,
        produto_id=produto_destino.id,
        tipo="entrada",
        motivo="fracionamento_clinico",
        quantidade=quantidade_destino,
        quantidade_anterior=estoque_destino_anterior,
        quantidade_nova=estoque_destino_novo,
        custo_unitario=custo_destino_unitario,
        valor_total=custo_total,
        lote_id=lotes_destino[0]["lote_id"] if len(lotes_destino) == 1 else None,
        estoque_origem="loja",
        estoque_destino="clinica",
        documento=documento,
        referencia_id=conversao.id,
        referencia_tipo="fracionamento_clinico",
        observacao=(
            f"Entrada clinica a partir de {quantidade_origem:g} "
            f"{produto_origem.unidade or 'UN'} de {produto_origem.nome}"
        ),
        user_id=user_id,
    )
    db.add(mov_saida)
    db.add(mov_entrada)
    db.commit()
    db.refresh(conversao)

    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto_origem.id,
            produto_origem.estoque_atual,
            "fracionamento_clinico_saida",
        )
        sincronizar_bling_background(
            produto_destino.id,
            produto_destino.estoque_atual,
            "fracionamento_clinico_entrada",
        )
    except Exception:
        pass

    return {
        "id": conversao.id,
        "vinculo_id": vinculo.id,
        "produto_origem": _serializar_produto(produto_origem),
        "produto_destino": _serializar_produto(produto_destino),
        "quantidade_origem": quantidade_origem,
        "fator_conversao": fator_conversao,
        "quantidade_destino": quantidade_destino,
        "custo_destino_unitario": custo_destino_unitario,
        "validade_apos_abertura_em": validade_abertura,
        "lotes_origem_consumidos": lotes_origem,
        "lotes_destino_criados": lotes_destino,
        "movimentacoes": {
            "saida_origem_id": mov_saida.id,
            "entrada_destino_id": mov_entrada.id,
        },
    }


def sugerir_fracionamento_clinico(
    db: Session,
    *,
    tenant_id,
    produto_destino_id: int,
    quantidade_necessaria: float,
) -> dict:
    quantidade_necessaria = _numero_positivo(
        quantidade_necessaria, "Quantidade necessaria"
    )
    destino = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.id == produto_destino_id,
        )
        .first()
    )
    destino = _produto_operacional(destino, papel="destino")
    estoque_destino = float(destino.estoque_atual or 0)
    deficit = max(0.0, quantidade_necessaria - estoque_destino)
    if deficit <= _EPSILON:
        return {
            "necessita_fracionamento": False,
            "estoque_atual": estoque_destino,
            "quantidade_necessaria": quantidade_necessaria,
            "sugestao": None,
        }

    vinculos = (
        db.query(EstoqueFracionamentoVinculo)
        .filter(
            EstoqueFracionamentoVinculo.tenant_id == tenant_id,
            EstoqueFracionamentoVinculo.produto_destino_id == produto_destino_id,
            EstoqueFracionamentoVinculo.ativo.is_(True),
        )
        .all()
    )
    sugestoes = []
    for vinculo in vinculos:
        origem = vinculo.produto_origem
        if (
            not origem
            or getattr(origem, "ativo", True) is False
            or getattr(origem, "situacao", True) is False
            or not getattr(origem, "controlar_estoque", True)
            or getattr(origem, "e_granel", False)
            or getattr(origem, "tipo_produto", None) == "PAI"
            or getattr(origem, "is_parent", False)
            or (
                getattr(origem, "tipo_produto", None) == "KIT"
                and getattr(origem, "tipo_kit", None) == "VIRTUAL"
            )
        ):
            continue
        fator = float(vinculo.fator_conversao or 0)
        if fator <= 0:
            continue
        quantidade_origem = int(math.ceil(deficit / fator))
        estoque_origem = float(origem.estoque_atual or 0)
        if quantidade_origem <= 0 or estoque_origem + _EPSILON < quantidade_origem:
            continue
        if getattr(origem, "controle_lote", False):
            saldo_lotes = sum(
                item["quantidade_disponivel"]
                for item in listar_lotes_disponiveis_fracionamento(
                    db,
                    tenant_id=tenant_id,
                    produto_id=origem.id,
                )
            )
            if saldo_lotes + _EPSILON < quantidade_origem:
                continue
        sugestoes.append(
            {
                "vinculo_id": vinculo.id,
                "produto_origem": _serializar_produto(origem),
                "produto_destino": _serializar_produto(destino),
                "quantidade_origem": quantidade_origem,
                "fator_conversao": fator,
                "quantidade_destino": quantidade_origem * fator,
                "validade_apos_abertura_dias": vinculo.validade_apos_abertura_dias,
                "sobra_estimada_apos_consumo": (
                    estoque_destino + quantidade_origem * fator - quantidade_necessaria
                ),
            }
        )
    sugestoes.sort(
        key=lambda item: (
            item["sobra_estimada_apos_consumo"],
            item["quantidade_origem"],
        )
    )
    return {
        "necessita_fracionamento": True,
        "estoque_atual": estoque_destino,
        "quantidade_necessaria": quantidade_necessaria,
        "deficit": deficit,
        "sugestao": sugestoes[0] if sugestoes else None,
    }
