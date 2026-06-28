"""Rotas de deteccao e tratamento de duplicatas de racoes."""

from datetime import datetime
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.duplicatas_ignoradas_models import DuplicataIgnorada
from app.opcoes_racao_models import PorteAnimal
from app.produtos_models import Marca, Produto
from app.racoes_sugestoes_common import _validar_tenant_e_obter_usuario
from app.racoes_sugestoes_schemas import DuplicataDetectada


router = APIRouter()


@router.get("/duplicatas", response_model=list[DuplicataDetectada])
async def detectar_duplicatas(
    threshold_similaridade: float = Query(
        0.80, ge=0.5, le=1.0, description="Limiar de similaridade (0-1)"
    ),
    apenas_ativas: bool = Query(True, description="Apenas produtos ativos"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    pares_ignorados = (
        db.query(DuplicataIgnorada)
        .filter(DuplicataIgnorada.tenant_id == tenant_id)
        .all()
    )
    pares_ignorados_set = {
        (
            min(par.produto_id_1, par.produto_id_2),
            max(par.produto_id_1, par.produto_id_2),
        )
        for par in pares_ignorados
    }

    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id, Produto.tipo == "ração"
    )
    if apenas_ativas:
        query = query.filter(Produto.ativo.is_(True))

    duplicatas = []
    produtos = query.all()
    for i, prod1 in enumerate(produtos):
        for prod2 in produtos[i + 1 :]:
            id_menor = min(prod1.id, prod2.id)
            id_maior = max(prod1.id, prod2.id)
            if (id_menor, id_maior) in pares_ignorados_set:
                continue

            if not _par_produtos_pode_ser_duplicata(db, prod1, prod2):
                continue

            score, razoes = _score_duplicata(
                prod1, prod2, threshold_similaridade=threshold_similaridade
            )
            if score < 70:
                continue

            marca1 = db.query(Marca).filter(Marca.id == prod1.marca_id).first()
            marca2 = db.query(Marca).filter(Marca.id == prod2.marca_id).first()
            duplicatas.append(
                DuplicataDetectada(
                    produto_1=_produto_resumo_duplicata(prod1, marca1),
                    produto_2=_produto_resumo_duplicata(prod2, marca2),
                    score_similaridade=round(score / 100, 2),
                    razoes=razoes,
                    sugestao_acao=_sugestao_por_score(score),
                )
            )

    duplicatas.sort(key=lambda x: x.score_similaridade, reverse=True)
    return duplicatas


@router.post("/duplicatas/ignorar")
async def ignorar_duplicata(
    produto_id_1: int,
    produto_id_2: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    prod1 = _obter_produto_tenant(db, produto_id_1, tenant_id)
    prod2 = _obter_produto_tenant(db, produto_id_2, tenant_id)

    if not prod1 or not prod2:
        raise HTTPException(
            status_code=404, detail="Um ou ambos produtos não encontrados"
        )

    id_menor = min(produto_id_1, produto_id_2)
    id_maior = max(produto_id_1, produto_id_2)
    existente = (
        db.query(DuplicataIgnorada)
        .filter(
            DuplicataIgnorada.tenant_id == tenant_id,
            DuplicataIgnorada.produto_id_1 == id_menor,
            DuplicataIgnorada.produto_id_2 == id_maior,
        )
        .first()
    )

    if existente:
        return {
            "success": True,
            "mensagem": "Este par já estava marcado como não-duplicata",
        }

    nova_ignorada = DuplicataIgnorada(
        tenant_id=tenant_id,
        produto_id_1=id_menor,
        produto_id_2=id_maior,
        usuario_id=current_user.id,
    )
    db.add(nova_ignorada)
    db.commit()

    return {
        "success": True,
        "mensagem": f"Par {prod1.nome} x {prod2.nome} marcado como não-duplicata e não será mais sugerido",
    }


@router.post("/duplicatas/mesclar")
async def mesclar_produtos(
    produto_id_manter: int,
    produto_id_remover: int,
    transferir_estoque: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    prod_manter = _obter_produto_tenant(db, produto_id_manter, tenant_id)
    prod_remover = _obter_produto_tenant(db, produto_id_remover, tenant_id)

    if not prod_manter or not prod_remover:
        raise HTTPException(
            status_code=404, detail="Um ou ambos produtos não encontrados"
        )

    estoque_transferido = prod_remover.estoque_atual or 0
    if transferir_estoque and estoque_transferido:
        if not prod_manter.estoque_atual:
            prod_manter.estoque_atual = 0
        prod_manter.estoque_atual += estoque_transferido
        prod_remover.estoque_atual = 0

    prod_remover.ativo = False
    prod_remover.produto_predecessor_id = produto_id_manter
    prod_remover.data_descontinuacao = datetime.utcnow()
    prod_remover.motivo_descontinuacao = "Mesclado - Duplicata"

    db.commit()

    if transferir_estoque and prod_remover.estoque_atual is not None:
        _sincronizar_estoque_mesclagem(prod_manter)

    return {
        "success": True,
        "mensagem": f"Produto {produto_id_remover} mesclado com {produto_id_manter}",
        "produto_mantido": {
            "id": prod_manter.id,
            "nome": prod_manter.nome,
            "estoque": float(prod_manter.estoque_atual)
            if prod_manter.estoque_atual
            else 0,
        },
    }


def _obter_produto_tenant(
    db: Session, produto_id: int, tenant_id: str
) -> Produto | None:
    return (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )


def _par_produtos_pode_ser_duplicata(
    db: Session, prod1: Produto, prod2: Produto
) -> bool:
    if prod1.peso_embalagem and prod2.peso_embalagem:
        if abs(prod1.peso_embalagem - prod2.peso_embalagem) > 0.5:
            return False

    if prod1.fase_publico_id and prod2.fase_publico_id:
        if prod1.fase_publico_id != prod2.fase_publico_id:
            return False

    if prod1.porte_animal_id and prod2.porte_animal_id:
        return _portes_compativeis(db, prod1.porte_animal_id, prod2.porte_animal_id)

    return True


def _portes_compativeis(db: Session, porte_id_1: int, porte_id_2: int) -> bool:
    if porte_id_1 == porte_id_2:
        return True

    porte1 = db.query(PorteAnimal).filter(PorteAnimal.id == porte_id_1).first()
    porte2 = db.query(PorteAnimal).filter(PorteAnimal.id == porte_id_2).first()
    if not porte1 or not porte2:
        return True
    if porte1.nome == "Todos" or porte2.nome == "Todos":
        return True

    portes_ordem = {"Pequeno": 1, "Médio": 2, "Grande": 3, "Gigante": 4}
    if porte1.nome in portes_ordem and porte2.nome in portes_ordem:
        return abs(portes_ordem[porte1.nome] - portes_ordem[porte2.nome]) <= 1

    return True


def _score_duplicata(
    prod1: Produto, prod2: Produto, *, threshold_similaridade: float
) -> tuple[int, list[str]]:
    nome_similarity = SequenceMatcher(
        None, prod1.nome.lower(), prod2.nome.lower()
    ).ratio()
    if nome_similarity < threshold_similaridade:
        return 0, []

    score = 60
    razoes = [f"Nomes {int(nome_similarity * 100)}% similares"]

    if prod1.marca_id and prod2.marca_id:
        if prod1.marca_id != prod2.marca_id:
            return 0, []
        score += 15
        razoes.append("Mesma marca")

    if prod1.peso_embalagem and prod2.peso_embalagem:
        if abs(prod1.peso_embalagem - prod2.peso_embalagem) < 0.1:
            score += 10
            razoes.append("Mesmo peso")

    for attr, pontos, razao in (
        ("porte_animal_id", 5, "Mesmo porte"),
        ("fase_publico_id", 5, "Mesma fase"),
        ("sabor_proteina_id", 5, "Mesmo sabor"),
    ):
        if getattr(prod1, attr) and getattr(prod2, attr):
            if getattr(prod1, attr) == getattr(prod2, attr):
                score += pontos
                razoes.append(razao)

    return score, razoes


def _produto_resumo_duplicata(produto: Produto, marca: Marca | None) -> dict:
    return {
        "id": produto.id,
        "nome": produto.nome,
        "marca": marca.nome if marca else "Sem Marca",
        "preco": float(produto.preco_venda),
        "estoque": float(produto.estoque_atual) if produto.estoque_atual else 0,
    }


def _sugestao_por_score(score: int) -> str:
    if score >= 90:
        return "Alta probabilidade de duplicata - Considerar mesclar"
    if score >= 80:
        return "Possível duplicata - Revisar características"
    return "Verificar manualmente"


def _sincronizar_estoque_mesclagem(prod_manter: Produto) -> None:
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            prod_manter.id, prod_manter.estoque_atual or 0, "mesclagem_produto"
        )
    except Exception:
        pass


__all__ = [
    "detectar_duplicatas",
    "ignorar_duplicata",
    "mesclar_produtos",
    "router",
]
