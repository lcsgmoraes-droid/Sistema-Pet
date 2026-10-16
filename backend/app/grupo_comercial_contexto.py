"""Resolve o grupo comercial ativo de um tenant.

Helper leve e reaproveitável por qualquer domínio "mestre" (espécie/raça,
produto, pet, pessoa — ver Documentacao/Dominio/Plano-Camada-Geral.md).
Não depende de GrupoComercialService (que carrega bastante lógica de
autorização de HTTPException) — só precisa da leitura mais simples possível.
"""

from sqlalchemy.orm import Session

from app.grupo_comercial_models import GrupoComercialMembro


def obter_grupo_id_ativo(db: Session, empresa_id) -> int | None:
    """Grupo comercial ativo da empresa, priorizando aquele em que ela é
    responsável (normalmente o dela mesma, desde a fundação automática no
    cadastro). Uma empresa tecnicamente pode ter mais de uma participação
    ativa — sem constraint que impeça — então o fallback é a mais antiga.
    Retorna None só se a empresa não tiver nenhum grupo (não deveria
    acontecer para tenants criados depois da fundação automática).
    """
    empresa_id = str(empresa_id)

    responsavel = (
        db.query(GrupoComercialMembro.grupo_id)
        .filter(
            GrupoComercialMembro.empresa_id == empresa_id,
            GrupoComercialMembro.status == "ativo",
            GrupoComercialMembro.papel == "responsavel",
        )
        .order_by(GrupoComercialMembro.id)
        .first()
    )
    if responsavel:
        return responsavel[0]

    qualquer = (
        db.query(GrupoComercialMembro.grupo_id)
        .filter(
            GrupoComercialMembro.empresa_id == empresa_id,
            GrupoComercialMembro.status == "ativo",
        )
        .order_by(GrupoComercialMembro.id)
        .first()
    )
    return qualquer[0] if qualquer else None


def listar_empresas_do_grupo(db: Session, empresa_id) -> list[str]:
    """IDs de todas as empresas ativas no grupo comercial de `empresa_id`
    (inclusive ela mesma). Sem grupo ativo, devolve só a própria empresa -
    nunca uma lista vazia, pra quem usa isso como escopo de `tenant_id IN (...)`
    não acabar filtrando tudo fora.
    """
    empresa_id = str(empresa_id)
    grupo_id = obter_grupo_id_ativo(db, empresa_id)
    if grupo_id is None:
        return [empresa_id]

    membros = (
        db.query(GrupoComercialMembro.empresa_id)
        .filter(
            GrupoComercialMembro.grupo_id == grupo_id,
            GrupoComercialMembro.status == "ativo",
        )
        .all()
    )
    return [str(membro[0]) for membro in membros]
