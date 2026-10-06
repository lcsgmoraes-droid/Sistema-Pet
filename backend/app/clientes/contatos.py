"""Validação e persistência dos celulares vinculados a uma pessoa."""

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.clientes.common import _somente_digitos, _somente_digitos_coluna
from app.models import Cliente, ClienteContato


def validar_contatos_adicionais(db: Session, tenant_id, cliente_id, contatos, celular, telefone):
    numeros = set()
    numeros_principais = {_somente_digitos(celular), _somente_digitos(telefone)} - {""}
    for contato in contatos:
        numero = _somente_digitos(contato.numero)
        if numero in numeros or numero in numeros_principais:
            raise HTTPException(409, "Celular adicional repetido neste cadastro.")
        numeros.add(numero)

    if not numeros:
        return

    contatos_outros = db.query(ClienteContato).filter(
        ClienteContato.tenant_id == tenant_id,
        ClienteContato.numero_digitos.in_(numeros),
    )
    pessoas_outras = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.ativo.is_not(False),
        or_(
            _somente_digitos_coluna(Cliente.celular).in_(numeros),
            _somente_digitos_coluna(Cliente.telefone).in_(numeros),
        ),
    )
    if cliente_id is not None:
        contatos_outros = contatos_outros.filter(ClienteContato.cliente_id != cliente_id)
        pessoas_outras = pessoas_outras.filter(Cliente.id != cliente_id)
    if contatos_outros.first() or pessoas_outras.first():
        raise HTTPException(409, "Um celular adicional ja pertence a outro cadastro.")


def salvar_contatos_adicionais(db: Session, cliente: Cliente, contatos):
    """Substitui a lista apenas quando o campo foi enviado na requisição."""
    db.query(ClienteContato).filter(
        ClienteContato.tenant_id == cliente.tenant_id,
        ClienteContato.cliente_id == cliente.id,
    ).delete(synchronize_session=False)
    db.flush()
    for contato in contatos:
        db.add(
            ClienteContato(
                tenant_id=cliente.tenant_id,
                cliente_id=cliente.id,
                numero=contato.numero,
                numero_digitos=_somente_digitos(contato.numero),
                vinculo=contato.vinculo,
            )
        )
    db.flush()
    db.expire(cliente, ["contatos_adicionais"])
