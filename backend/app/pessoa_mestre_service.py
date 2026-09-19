"""Sugestão e vínculo de pessoa-mestre do grupo comercial.

Mais cauteloso que os checkpoints anteriores, de propósito: só sugere por
CPF/CNPJ (identificador forte) — nunca por nome sozinho, que é comum
demais pra ser confiável em dado pessoal. E, como em todo domínio mestre,
o vínculo em si é sempre uma confirmação explícita do usuário, nunca uma
fusão automática — ver Documentacao/Dominio/Plano-Camada-Geral.md,
Checkpoint 4, e a ressalva de LGPD lá descrita.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models_cadastros import Cliente
from app.pessoa_mestre_models import PessoaMestre


def _limpar_documento(valor: str | None) -> str:
    return "".join(ch for ch in (valor or "") if ch.isalnum())


def sugerir_pessoa_mestre(
    db: Session, grupo_id: int, *, cpf: str | None = None, cnpj: str | None = None
) -> PessoaMestre | None:
    cpf_limpo = _limpar_documento(cpf)
    if cpf_limpo:
        achado = (
            db.query(PessoaMestre)
            .filter(
                PessoaMestre.grupo_id == grupo_id,
                PessoaMestre.ativo.is_(True),
                PessoaMestre.cpf == cpf_limpo,
            )
            .first()
        )
        if achado:
            return achado

    cnpj_limpo = _limpar_documento(cnpj)
    if cnpj_limpo:
        achado = (
            db.query(PessoaMestre)
            .filter(
                PessoaMestre.grupo_id == grupo_id,
                PessoaMestre.ativo.is_(True),
                PessoaMestre.cnpj == cnpj_limpo,
            )
            .first()
        )
        if achado:
            return achado

    return None


def vincular_pessoa_mestre(
    db: Session,
    *,
    cliente: Cliente,
    grupo_id: int,
    usuario_id: int,
    pessoa_mestre_id: int | None,
) -> PessoaMestre:
    if pessoa_mestre_id is not None:
        mestre = (
            db.query(PessoaMestre)
            .filter(
                PessoaMestre.id == pessoa_mestre_id,
                PessoaMestre.grupo_id == grupo_id,
                PessoaMestre.ativo.is_(True),
            )
            .first()
        )
        if mestre is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pessoa-mestre não encontrada neste grupo.",
            )
    else:
        mestre = PessoaMestre(
            grupo_id=grupo_id,
            nome=" ".join(cliente.nome.split()),
            tipo_pessoa=cliente.tipo_pessoa,
            tipo_cadastro=cliente.tipo_cadastro,
            cpf=_limpar_documento(cliente.cpf) or None,
            cnpj=_limpar_documento(cliente.cnpj) or None,
            inscricao_estadual=cliente.inscricao_estadual,
            razao_social=cliente.razao_social,
            nome_fantasia=cliente.nome_fantasia,
            crmv=cliente.crmv,
            data_nascimento=cliente.data_nascimento,
            telefone=cliente.telefone,
            celular=cliente.celular,
            email=cliente.email,
            cep=cliente.cep,
            endereco=cliente.endereco,
            numero=cliente.numero,
            complemento=cliente.complemento,
            bairro=cliente.bairro,
            cidade=cliente.cidade,
            estado=cliente.estado,
            codigo_municipio=cliente.codigo_municipio,
            criado_por_usuario_id=usuario_id,
        )
        db.add(mestre)
        db.flush()

    cliente.pessoa_mestre_id = mestre.id
    db.commit()
    db.refresh(mestre)
    return mestre


def desvincular_pessoa_mestre(db: Session, *, cliente: Cliente) -> None:
    cliente.pessoa_mestre_id = None
    db.commit()
