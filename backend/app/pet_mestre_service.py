"""Sugestão e vínculo de pet-mestre do grupo comercial. Mesmo princípio dos
checkpoints anteriores: nunca funde sozinho, só sugere (leitura) ou vincula
quando pedido explicitamente (escrita) — ver
Documentacao/Dominio/Plano-Camada-Geral.md.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models_cadastros import Pet
from app.pet_mestre_models import PetMestre
from app.veterinario_models import PerfilComportamental


def sugerir_pet_mestre(
    db: Session, grupo_id: int, *, microchip: str | None = None, nome: str | None = None
) -> PetMestre | None:
    """Prioriza microchip (identificador confiável) quando informado; nome
    sozinho é sugestão fraca — mesmo nome de pet é comum, então também
    exige espécie/raça parecida seria ideal, mas fica pro time avaliar
    junto da UI (aqui só nome, decisão final é sempre do usuário)."""
    microchip_limpo = (microchip or "").strip()
    if microchip_limpo:
        achado = (
            db.query(PetMestre)
            .filter(
                PetMestre.grupo_id == grupo_id,
                PetMestre.ativo.is_(True),
                PetMestre.microchip == microchip_limpo,
            )
            .first()
        )
        if achado:
            return achado

    nome_limpo = " ".join((nome or "").split())
    if not nome_limpo:
        return None
    return (
        db.query(PetMestre)
        .filter(
            PetMestre.grupo_id == grupo_id,
            PetMestre.ativo.is_(True),
            PetMestre.nome.ilike(nome_limpo),
        )
        .first()
    )


def vincular_pet_mestre(
    db: Session,
    *,
    pet: Pet,
    grupo_id: int,
    usuario_id: int,
    pet_mestre_id: int | None,
) -> PetMestre:
    if pet_mestre_id is not None:
        mestre = (
            db.query(PetMestre)
            .filter(
                PetMestre.id == pet_mestre_id,
                PetMestre.grupo_id == grupo_id,
                PetMestre.ativo.is_(True),
            )
            .first()
        )
        if mestre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pet-mestre não encontrado neste grupo.",
            )
    else:
        perfil = (
            db.query(PerfilComportamental)
            .filter(PerfilComportamental.pet_id == pet.id)
            .first()
        )
        mestre = PetMestre(
            grupo_id=grupo_id,
            nome=" ".join(pet.nome.split()),
            especie=pet.especie,
            raca=pet.raca,
            sexo=pet.sexo,
            porte=pet.porte,
            cor=pet.cor,
            cor_pelagem=pet.cor_pelagem,
            data_nascimento=pet.data_nascimento,
            castrado=pet.castrado,
            castrado_data=pet.castrado_data,
            foto_url=pet.foto_url,
            microchip=pet.microchip,
            tipo_sanguineo=pet.tipo_sanguineo,
            pedigree_registro=pet.pedigree_registro,
            alergias=pet.alergias,
            alergias_lista=pet.alergias_lista,
            doencas_cronicas=pet.doencas_cronicas,
            condicoes_cronicas_lista=pet.condicoes_cronicas_lista,
            medicamentos_continuos=pet.medicamentos_continuos,
            medicamentos_continuos_lista=pet.medicamentos_continuos_lista,
            restricoes_alimentares_lista=pet.restricoes_alimentares_lista,
            historico_clinico=pet.historico_clinico,
            criado_por_usuario_id=usuario_id,
        )
        if perfil is not None:
            mestre.temperamento = perfil.temperamento
            mestre.reacao_animais = perfil.reacao_animais
            mestre.reacao_pessoas = perfil.reacao_pessoas
            mestre.medo_secador = perfil.medo_secador
            mestre.medo_tesoura = perfil.medo_tesoura
            mestre.aceita_focinheira = perfil.aceita_focinheira
            mestre.comportamento_carro = perfil.comportamento_carro
        db.add(mestre)
        db.flush()

    pet.pet_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre


def desvincular_pet_mestre(db: Session, *, pet: Pet) -> None:
    pet.pet_mestre_id = None
    db.commit()
