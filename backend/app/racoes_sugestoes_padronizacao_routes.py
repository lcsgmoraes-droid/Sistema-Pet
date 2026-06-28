"""Rotas de padronizacao de nomes de racoes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.opcoes_racao_models import (
    FasePublico,
    PorteAnimal,
    SaborProteina,
    TipoTratamento,
)
from app.produtos_models import Marca, Produto
from app.racoes_sugestoes_common import (
    _produto_eh_racao_expr,
    _validar_tenant_e_obter_usuario,
)
from app.racoes_sugestoes_schemas import PadronizacaoNome


router = APIRouter()


@router.get("/padronizar-nomes", response_model=list[PadronizacaoNome])
async def sugerir_padronizacao_nomes(
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            _produto_eh_racao_expr(),
            Produto.ativo.is_(True),
        )
        .limit(limite)
        .all()
    )

    sugestoes = []
    for produto in produtos:
        sugestao = _sugerir_nome_produto(db, produto)
        if sugestao:
            sugestoes.append(sugestao)

    sugestoes.sort(key=lambda x: x.confianca, reverse=True)
    return sugestoes


def _sugerir_nome_produto(db: Session, produto: Produto) -> PadronizacaoNome | None:
    nome_atual = produto.nome.strip()
    partes_nome = ["Ração"]
    campos_usados = []
    confianca = 1.0

    confianca = _adicionar_marca(db, produto, partes_nome, campos_usados, confianca)
    confianca = _adicionar_especie(produto, partes_nome, campos_usados, confianca)
    confianca = _adicionar_fase(db, produto, partes_nome, campos_usados, confianca)
    _adicionar_porte(db, produto, partes_nome, campos_usados)
    confianca = _adicionar_sabor(db, produto, partes_nome, campos_usados, confianca)
    _adicionar_tratamento(db, produto, partes_nome, campos_usados)
    confianca = _adicionar_peso(produto, partes_nome, campos_usados, confianca)

    nome_sugerido = " ".join(partes_nome)
    if (
        len(partes_nome) < 3
        or nome_sugerido.lower() == nome_atual.lower()
        or confianca < 0.5
    ):
        return None

    return PadronizacaoNome(
        produto_id=produto.id,
        nome_atual=nome_atual,
        nome_sugerido=nome_sugerido,
        razao=f"Padronização estruturada usando: {', '.join(campos_usados)}",
        confianca=confianca,
    )


def _adicionar_marca(
    db: Session,
    produto: Produto,
    partes_nome: list[str],
    campos_usados: list[str],
    confianca: float,
) -> float:
    if not produto.marca_id:
        return confianca - 0.2

    marca = db.query(Marca).filter(Marca.id == produto.marca_id).first()
    if not marca:
        return confianca - 0.1

    partes_nome.append(marca.nome)
    campos_usados.append("marca")
    return confianca


def _adicionar_especie(
    produto: Produto, partes_nome: list[str], campos_usados: list[str], confianca: float
) -> float:
    if not produto.especies_indicadas:
        return confianca - 0.15

    especie_str = produto.especies_indicadas.lower()
    if especie_str == "dog":
        partes_nome.append("Cães")
        campos_usados.append("especie")
    elif especie_str == "cat":
        partes_nome.append("Gatos")
        campos_usados.append("especie")
    elif especie_str == "both":
        campos_usados.append("especie")
    return confianca


def _adicionar_fase(
    db: Session,
    produto: Produto,
    partes_nome: list[str],
    campos_usados: list[str],
    confianca: float,
) -> float:
    if not produto.fase_publico_id:
        return confianca - 0.15

    fase = (
        db.query(FasePublico).filter(FasePublico.id == produto.fase_publico_id).first()
    )
    if fase and fase.nome != "Todos":
        partes_nome.append(fase.nome)
        campos_usados.append("fase")
        return confianca

    return confianca - 0.1


def _adicionar_porte(
    db: Session, produto: Produto, partes_nome: list[str], campos_usados: list[str]
) -> None:
    if not produto.porte_animal_id:
        return

    porte = (
        db.query(PorteAnimal).filter(PorteAnimal.id == produto.porte_animal_id).first()
    )
    if porte and porte.nome != "Todos":
        porte_formatado = (
            f"Raças {porte.nome}s"
            if not porte.nome.endswith("s")
            else f"Raças {porte.nome}"
        )
        partes_nome.append(porte_formatado)
        campos_usados.append("porte")


def _adicionar_sabor(
    db: Session,
    produto: Produto,
    partes_nome: list[str],
    campos_usados: list[str],
    confianca: float,
) -> float:
    if not produto.sabor_proteina_id:
        return confianca - 0.15

    sabor = (
        db.query(SaborProteina)
        .filter(SaborProteina.id == produto.sabor_proteina_id)
        .first()
    )
    if sabor:
        partes_nome.append(sabor.nome)
        campos_usados.append("sabor")
        return confianca

    return confianca - 0.1


def _adicionar_tratamento(
    db: Session, produto: Produto, partes_nome: list[str], campos_usados: list[str]
) -> None:
    if not produto.tipo_tratamento_id:
        return

    tratamento = (
        db.query(TipoTratamento)
        .filter(TipoTratamento.id == produto.tipo_tratamento_id)
        .first()
    )
    if tratamento:
        partes_nome.append(tratamento.nome)
        campos_usados.append("tratamento")


def _adicionar_peso(
    produto: Produto, partes_nome: list[str], campos_usados: list[str], confianca: float
) -> float:
    if not produto.peso_embalagem:
        return confianca - 0.2

    peso_str = (
        f"{int(produto.peso_embalagem)}kg"
        if produto.peso_embalagem == int(produto.peso_embalagem)
        else f"{produto.peso_embalagem}kg"
    )
    partes_nome.append(peso_str)
    campos_usados.append("peso")
    return confianca


__all__ = ["router", "sugerir_padronizacao_nomes"]
