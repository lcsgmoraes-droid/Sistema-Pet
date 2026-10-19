"""Salvar uma pessoa deve devolver os dados que o formulario exibe sem novo GET."""

from datetime import datetime
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.clientes.crud_routes import _montar_resposta_update


def _cliente(**changes):
    dados = {
        "id": 42,
        "codigo": "QA-PF-0042",
        "nome": "Pessoa de teste",
        "tipo_pessoa": "PF",
        "is_cliente": True,
        "is_fornecedor": False,
        "is_veterinario": False,
        "is_funcionario": False,
        "origem_tenant_id": uuid4(),
        "cpf": None,
        "cnpj": None,
        "email": "pessoa@example.com",
        "telefone": None,
        "celular": "11999991111",
        "contatos_adicionais": [],
        "parceiro_ativo": False,
        "data_fechamento_comissao": None,
        "alertas_pdv": [],
        "ativo": True,
        "created_at": datetime(2026, 10, 19, 10),
        "updated_at": datetime(2026, 10, 19, 11),
        "cep": "01001-000",
        "endereco": "Rua de teste",
        "numero": "S/N",
        "complemento": "Sala 2",
        "bairro": "Centro",
        "cidade": "Sao Paulo",
        "estado": "SP",
        "codigo_municipio": "3550308",
        "endereco_entrega": "Endereco de entrega legado",
        "endereco_entrega_2": "Outro endereco legado",
        "enderecos_adicionais": None,
    }
    dados.update(changes)
    return SimpleNamespace(**dados)


def test_resposta_update_mantem_endereco_principal_e_codigo_fiscal():
    resposta = _montar_resposta_update(_cliente())

    assert {
        campo: resposta.get(campo)
        for campo in (
            "cep",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "codigo_municipio",
            "endereco_entrega",
            "endereco_entrega_2",
        )
    } == {
        "cep": "01001-000",
        "endereco": "Rua de teste",
        "numero": "S/N",
        "complemento": "Sala 2",
        "bairro": "Centro",
        "cidade": "Sao Paulo",
        "estado": "SP",
        "codigo_municipio": "3550308",
        "endereco_entrega": "Endereco de entrega legado",
        "endereco_entrega_2": "Outro endereco legado",
    }
    assert resposta["tipos_cadastro"] == ["cliente"]


@pytest.mark.parametrize("serializado", [False, True])
def test_resposta_update_devolve_enderecos_adicionais_como_lista(serializado):
    enderecos = [
        {
            "tipo": "entrega",
            "apelido": "Loja",
            "endereco": "Avenida de teste",
            "numero": "123-A",
            "cidade": "Sao Paulo",
            "estado": "SP",
            "codigo_municipio": "3550308",
        }
    ]
    cliente = _cliente(
        enderecos_adicionais=json.dumps(enderecos) if serializado else enderecos,
    )

    resposta = _montar_resposta_update(cliente)

    assert resposta.get("enderecos_adicionais") == enderecos


def test_resposta_update_preserva_demais_abas_para_um_novo_salvamento():
    nascimento = datetime(2000, 1, 2)
    cliente = _cliente(
        data_nascimento=nascimento,
        inscricao_estadual="ISENTO",
        razao_social="Empresa de teste",
        nome_fantasia="Nome comercial",
        responsavel="Responsavel",
        crmv="SP-12345",
        celular_whatsapp=True,
        observacoes="Manter esta observacao",
        is_entregador=True,
        entregador_ativo=True,
        modelo_custo_entrega="por_km",
        tipo_acerto_entrega="semanal",
    )

    resposta = _montar_resposta_update(cliente)

    assert resposta.get("data_nascimento") == nascimento
    for campo in (
        "inscricao_estadual",
        "razao_social",
        "nome_fantasia",
        "responsavel",
        "crmv",
        "celular_whatsapp",
        "observacoes",
        "is_entregador",
        "entregador_ativo",
        "modelo_custo_entrega",
        "tipo_acerto_entrega",
    ):
        assert resposta.get(campo) == getattr(cliente, campo)


def test_resposta_update_representa_remocao_do_ultimo_endereco():
    resposta = _montar_resposta_update(_cliente(enderecos_adicionais="[]"))

    assert resposta.get("enderecos_adicionais") == []
