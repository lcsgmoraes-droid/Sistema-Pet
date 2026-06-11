from types import SimpleNamespace

from app.services.cliente_alertas_pdv import (
    alertas_pdv_ativos,
    normalizar_alertas_pdv,
)


def test_normalizar_alertas_pdv_remove_vazios_e_padroniza_campos():
    alertas = normalizar_alertas_pdv(
        [
            {
                "tag": " Preco especial ",
                "observacao": " Fazer racao X por R$ 120 ",
                "prioridade": "IMPORTANTE",
            },
            {"titulo": "", "mensagem": "   "},
            {"titulo": "Inativo", "mensagem": "Nao mostrar", "ativo": False},
            "valor invalido",
        ]
    )

    assert alertas == [
        {
            "titulo": "Preco especial",
            "mensagem": "Fazer racao X por R$ 120",
            "prioridade": "importante",
            "ativo": True,
        },
        {
            "titulo": "Inativo",
            "mensagem": "Nao mostrar",
            "prioridade": "aviso",
            "ativo": False,
        },
    ]


def test_alertas_pdv_ativos_filtra_inativos():
    assert alertas_pdv_ativos(
        [
            {"titulo": "VIP", "mensagem": "Dar brinde", "ativo": True},
            {"titulo": "Antigo", "mensagem": "Nao vale mais", "ativo": False},
        ]
    ) == [
        {
            "titulo": "VIP",
            "mensagem": "Dar brinde",
            "prioridade": "aviso",
            "ativo": True,
        }
    ]


def test_cliente_create_update_accept_alertas_pdv_payloads():
    from app.clientes_routes import ClienteCreate, ClienteUpdate

    create_payload = ClienteCreate(
        nome="Cliente Teste",
        telefone="11999999999",
        alertas_pdv=[{"tag": "VIP", "observacao": "Atendimento especial"}],
    )
    update_payload = ClienteUpdate(
        alertas_pdv=[{"titulo": "Preco", "mensagem": "Racao X por R$ 120"}],
    )

    assert create_payload.alertas_pdv == [
        {
            "titulo": "VIP",
            "mensagem": "Atendimento especial",
            "prioridade": "aviso",
            "ativo": True,
        }
    ]
    assert update_payload.alertas_pdv == [
        {
            "titulo": "Preco",
            "mensagem": "Racao X por R$ 120",
            "prioridade": "aviso",
            "ativo": True,
        }
    ]


def test_cliente_response_expoe_alertas_pdv_normalizados():
    from app.clientes_routes import ClienteResponse

    cliente = SimpleNamespace(
        id=1,
        codigo="10001",
        tipo_cadastro="cliente",
        tipo_pessoa="PF",
        fornecedor_grupo_id=None,
        fornecedor_grupo_nome=None,
        nome="Cliente Teste",
        data_nascimento=None,
        cpf=None,
        email=None,
        telefone="11999999999",
        celular=None,
        cnpj=None,
        inscricao_estadual=None,
        razao_social=None,
        nome_fantasia=None,
        responsavel=None,
        crmv=None,
        parceiro_ativo=False,
        parceiro_desde=None,
        parceiro_observacoes=None,
        data_fechamento_comissao=None,
        cep=None,
        endereco=None,
        numero=None,
        complemento=None,
        bairro=None,
        cidade=None,
        estado=None,
        endereco_entrega=None,
        endereco_entrega_2=None,
        enderecos_adicionais=None,
        is_entregador=False,
        is_terceirizado=False,
        recebe_repasse=False,
        gera_conta_pagar=False,
        tipo_vinculo_entrega=None,
        valor_padrao_entrega=None,
        valor_por_km=None,
        recebe_comissao_entrega=False,
        entregador_ativo=True,
        entregador_padrao=False,
        controla_rh=False,
        gera_conta_pagar_custo_entrega=False,
        media_entregas_configurada=None,
        media_entregas_real=None,
        custo_rh_ajustado=None,
        modelo_custo_entrega=None,
        taxa_fixa_entrega=None,
        valor_por_km_entrega=None,
        moto_propria=True,
        tipo_acerto_entrega=None,
        dia_semana_acerto=None,
        dia_mes_acerto=None,
        data_ultimo_acerto=None,
        controla_dre=True,
        observacoes=None,
        alertas_pdv=[{"tag": "Especial", "observacao": "Preco combinado"}],
        ativo=True,
        credito=0,
        created_at="2026-06-11T10:00:00",
        updated_at="2026-06-11T10:00:00",
        criado_por_id=None,
        criado_por_nome=None,
        criado_por_email=None,
        pets=[],
        de_parceiro=False,
    )

    response = ClienteResponse.model_validate(cliente)

    assert response.alertas_pdv == [
        {
            "titulo": "Especial",
            "mensagem": "Preco combinado",
            "prioridade": "aviso",
            "ativo": True,
        }
    ]
