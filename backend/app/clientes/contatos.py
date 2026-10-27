"""Validação e persistência dos celulares vinculados a uma pessoa."""

from collections import Counter

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.clientes.common import _somente_digitos
from app.models import Cliente, ClienteContato
from app.services.pessoa_telefone import (
    bloquear_escopo_telefone_pessoa,
    normalizar_telefone_pessoa,
    validar_telefones_pessoa,
)


def validar_contatos_adicionais(
    db: Session, tenant_id, cliente_id, contatos, celular, telefone, pessoa_atual=None
):
    if pessoa_atual is None and cliente_id is not None:
        pessoa_atual = (
            db.query(Cliente)
            .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
            .first()
        )
    validar_telefones_pessoa(
        db,
        tenant_id,
        pessoa_atual=pessoa_atual,
        telefone=telefone,
        celular=celular,
        contatos_adicionais=contatos,
    )
    anteriores = Counter()
    if pessoa_atual is not None:
        anteriores.update(
            normalizar_telefone_pessoa(valor)
            for valor in (
                pessoa_atual.telefone,
                pessoa_atual.celular,
                *(c.numero for c in pessoa_atual.contatos_adicionais),
            )
        )
    novos = Counter()
    numeros_principais = Counter(
        chave
        for valor in (celular, telefone)
        if (chave := normalizar_telefone_pessoa(valor))
    )
    for contato in contatos:
        numero = normalizar_telefone_pessoa(contato.numero)
        novos[numero] += 1
        repeticoes = novos[numero] + numeros_principais[numero]
        if repeticoes > max(1, anteriores[numero]):
            raise HTTPException(409, "Celular adicional repetido neste cadastro.")


def salvar_contatos_adicionais(db: Session, cliente: Cliente, contatos):
    """Mantém IDs/chaves existentes; só inclui ou remove o que a lista alterou."""
    bloquear_escopo_telefone_pessoa(db, cliente.tenant_id)
    existentes = (
        db.query(ClienteContato)
        .filter(
            ClienteContato.tenant_id == cliente.tenant_id,
            ClienteContato.cliente_id == cliente.id,
        )
        .order_by(ClienteContato.id)
        .all()
    )
    por_numero = {}
    for existente in existentes:
        por_numero.setdefault(normalizar_telefone_pessoa(existente.numero), []).append(
            existente
        )
    mantidos = set()
    for contato in contatos:
        candidatos = por_numero.get(normalizar_telefone_pessoa(contato.numero), [])
        existente = candidatos.pop(0) if candidatos else None
        if existente:
            mantidos.add(existente.id)
            existente.numero = contato.numero
            existente.numero_digitos = _somente_digitos(contato.numero)
            existente.vinculo = contato.vinculo
        else:
            db.add(
                ClienteContato(
                    tenant_id=cliente.tenant_id,
                    cliente_id=cliente.id,
                    numero=contato.numero,
                    numero_digitos=_somente_digitos(contato.numero),
                    vinculo=contato.vinculo,
                )
            )
    for existente in existentes:
        if existente.id not in mantidos:
            db.delete(existente)
    db.flush()
    db.expire(cliente, ["contatos_adicionais"])
