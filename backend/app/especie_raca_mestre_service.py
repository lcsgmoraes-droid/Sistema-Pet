"""Sugestão e vínculo de espécie/raça mestre do grupo comercial.

Nunca funde/vincula sozinho — toda ligação passa por uma ação explícita do
usuário (ver Documentacao/Dominio/Plano-Camada-Geral.md, princípio do
padrão mestre: "override explícito, nunca silencioso"). As funções daqui só
sugerem (leitura) ou executam o vínculo quando pedidas (escrita explícita).
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.especie_raca_mestre_models import EspecieMestre, RacaMestre
from app.models import Especie, Raca


def sugerir_especie_mestre(
    db: Session, grupo_id: int, nome: str
) -> EspecieMestre | None:
    nome_limpo = " ".join((nome or "").split())
    if not nome_limpo:
        return None
    return (
        db.query(EspecieMestre)
        .filter(
            EspecieMestre.grupo_id == grupo_id,
            EspecieMestre.ativo.is_(True),
            EspecieMestre.nome.ilike(nome_limpo),
        )
        .first()
    )


def sugerir_raca_mestre(
    db: Session, grupo_id: int, especie_mestre_id: int, nome: str
) -> RacaMestre | None:
    nome_limpo = " ".join((nome or "").split())
    if not nome_limpo:
        return None
    return (
        db.query(RacaMestre)
        .filter(
            RacaMestre.grupo_id == grupo_id,
            RacaMestre.especie_mestre_id == especie_mestre_id,
            RacaMestre.ativo.is_(True),
            RacaMestre.nome.ilike(nome_limpo),
        )
        .first()
    )


def vincular_especie_mestre(
    db: Session,
    *,
    especie: Especie,
    grupo_id: int,
    usuario_id: int,
    especie_mestre_id: int | None,
) -> EspecieMestre:
    """Vincula a espécie local a um mestre existente do grupo, ou — se
    `especie_mestre_id` vier vazio — promove a própria espécie local a um
    mestre novo (única forma de um mestre nascer: ação explícita do
    responsável, nunca automática)."""
    if especie_mestre_id is not None:
        mestre = (
            db.query(EspecieMestre)
            .filter(
                EspecieMestre.id == especie_mestre_id,
                EspecieMestre.grupo_id == grupo_id,
                EspecieMestre.ativo.is_(True),
            )
            .first()
        )
        if mestre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espécie-mestre não encontrada neste grupo.",
            )
    else:
        mestre = EspecieMestre(
            grupo_id=grupo_id,
            nome=" ".join(especie.nome.split()),
            criado_por_usuario_id=usuario_id,
        )
        db.add(mestre)
        db.flush()

    especie.especie_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre


def vincular_raca_mestre(
    db: Session,
    *,
    raca: Raca,
    grupo_id: int,
    especie_mestre_id: int,
    usuario_id: int,
    raca_mestre_id: int | None,
) -> RacaMestre:
    if raca_mestre_id is not None:
        mestre = (
            db.query(RacaMestre)
            .filter(
                RacaMestre.id == raca_mestre_id,
                RacaMestre.grupo_id == grupo_id,
                RacaMestre.ativo.is_(True),
            )
            .first()
        )
        if mestre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Raça-mestre não encontrada neste grupo.",
            )
    else:
        mestre = RacaMestre(
            grupo_id=grupo_id,
            especie_mestre_id=especie_mestre_id,
            nome=" ".join(raca.nome.split()),
            criado_por_usuario_id=usuario_id,
        )
        db.add(mestre)
        db.flush()

    raca.raca_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre


def desvincular_especie_mestre(db: Session, *, especie: Especie) -> None:
    """Remove o vínculo (a espécie local continua existindo, só deixa de
    herdar do mestre); o mestre em si não é apagado."""
    especie.especie_mestre_id = None
    db.commit()


def desvincular_raca_mestre(db: Session, *, raca: Raca) -> None:
    raca.raca_mestre_id = None
    db.commit()
