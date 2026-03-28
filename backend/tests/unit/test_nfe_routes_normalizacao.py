from types import SimpleNamespace

from app.nfe_routes import (
    _extrair_valor_nota,
    _normalizar_detalhe_nota_bling,
    _normalizar_nota_bling,
    _normalizar_resumo_canal,
    _situacao_num,
    _status_nota_bling,
)


def test_situacao_num_prioriza_valor_quando_bling_retorna_objeto():
    assert _situacao_num({"id": 5, "valor": 9}) == 9


def test_normalizar_nota_bling_mapeia_autorizada_sem_confundir_com_inutilizada():
    nota = _normalizar_nota_bling(
        {
            "id": 123,
            "numero": "10971",
            "serie": "1",
            "situacao": {"id": 5, "valor": 9},
            "totais": {"valorTotal": 439.30},
            "contato": {"nome": "Livia"},
        },
        modelo=55,
    )

    assert nota["status"] == "Autorizada"
    assert nota["valor"] == 439.30
    assert nota["cliente"]["nome"] == "Livia"


def test_extrair_valor_nota_aceita_totais_aninhados():
    assert _extrair_valor_nota({"totais": {"valorTotal": "42.90"}}) == 42.90


def test_extrair_valor_nota_aceita_valor_nota_do_detalhe():
    assert _extrair_valor_nota({"valorNota": 439}) == 439


def test_extrair_valor_nota_calcula_total_a_partir_dos_componentes():
    assert _extrair_valor_nota(
        {
            "totais": {
                "valorProdutos": 199,
                "valorFrete": 0,
                "valorSeguro": 0,
                "outrasDespesas": 0,
                "valorDesconto": 64.03,
            }
        }
    ) == 134.97


def test_status_nota_bling_trata_situacao_5_como_autorizada_no_payload_real():
    assert _status_nota_bling({"situacao": 5, "chaveAcesso": "123"}) == "Autorizada"


def test_normalizar_nota_bling_trata_payload_real_do_bling_com_valor_nota():
    nota = _normalizar_nota_bling(
        {
            "id": 25426416457,
            "numero": "010971",
            "serie": 2,
            "situacao": 5,
            "chaveAcesso": "35260333590794000140550020000109711254264166",
            "valorNota": 439,
            "contato": {"nome": "Livia"},
        },
        modelo=55,
    )

    assert nota["status"] == "Autorizada"
    assert nota["valor"] == 439
    assert nota["tipo"] == "nfe"


def test_normalizar_resumo_canal_expoe_loja_e_marketplace():
    resumo = _normalizar_resumo_canal(
        {
            "loja": {"id": 1, "nome": "Shopee Atacado"},
            "origemLojaVirtual": "Shopee",
            "origemCanalVenda": "Outros",
            "numeroPedidoLoja": "260329CDGSH41N",
            "intermediador": {"cnpj": "35.635.824/0001-12", "identificacao": "1189728757"},
        }
    )

    assert resumo["canal"] == "shopee"
    assert resumo["canal_label"] == "Shopee"
    assert resumo["loja"]["nome"] == "Shopee Atacado"
    assert resumo["numero_pedido_loja"] == "260329CDGSH41N"
    assert resumo["intermediador"]["identificacao"] == "1189728757"


def test_normalizar_resumo_canal_infere_marketplace_pelo_numero_loja_virtual():
    resumo = _normalizar_resumo_canal(
        {
            "numeroLojaVirtual": "702-4379429-6925030",
            "intermediador": {"identificacao": "Atacadopetpp"},
        }
    )

    assert resumo["canal"] == "amazon"
    assert resumo["canal_label"] == "Amazon"
    assert resumo["origem_loja_virtual"] == "Amazon"


def test_normalizar_detalhe_nota_bling_expoe_campos_ricos():
    venda = SimpleNamespace(
        id=123,
        canal="shopee",
        numero_venda="202603280001",
        loja_origem="Shopee Atacado",
        cliente=SimpleNamespace(nome="Adna Alves Da Silva Santos", cpf="10842775650", cnpj=None),
        vendedor=SimpleNamespace(nome=""),
    )
    detalhe = _normalizar_detalhe_nota_bling(
        {
            "id": 25427303470,
            "numero": "010972",
            "serie": 2,
            "chaveAcesso": "35260333590794000140550020000109721254273030",
            "situacao": 5,
            "dataEmissao": "2026-03-28",
            "horaEmissao": "16:54:38",
            "dataSaida": "2026-03-28",
            "horaSaida": "16:54:38",
            "loja": {"nome": "Shopee Atacado"},
            "unidadeNegocio": {"nome": "Matriz"},
            "naturezaOperacao": {"descricao": "Venda de mercadoria com ST"},
            "codigoRegimeTributario": "Simples nacional",
            "finalidade": "NF-e normal",
            "indicadorPresenca": "9 - Operacao nao presencial, outros",
            "contato": {
                "nome": "Adna Alves Da Silva Santos",
                "tipoPessoa": "F",
                "cpf": "108.427.756-50",
                "cep": "35622000",
                "uf": "MG",
                "municipio": "Paineiras",
                "bairro": "Centro",
                "endereco": "Job Feliciano Alves",
                "numero": "645",
                "complemento": "Casa de esquina",
            },
            "itens": [
                {
                    "descricao": "MGZ EXT CALOPSITAS E PERIQUIT PM13 900G Quantidade:1",
                    "codigo": "018631.1",
                    "unidade": "UN",
                    "quantidade": 1,
                    "valor": 159,
                    "total": 159,
                    "ncm": "2309.90.10",
                }
            ],
            "totais": {
                "valorProdutos": 159,
                "valorFrete": 0,
                "valorSeguro": 0,
                "outrasDespesas": 0,
                "valorDesconto": 90.07,
                "valorTotal": 68.93,
            },
            "transporte": {
                "tipo": "Nao havera transporte",
                "fretePorConta": "9 - Sem Ocorrencia de Transporte",
            },
            "enderecoEntrega": {
                "nome": "Adna Alves Da Silva Santos",
                "cep": "35622000",
                "uf": "MG",
                "municipio": "Paineiras",
                "bairro": "Centro",
                "endereco": "Job Feliciano Alves",
                "numero": "645",
                "complemento": "Casa de esquina",
            },
            "pagamento": {
                "condicaoPagamento": "30",
                "categoria": "Sem categoria",
                "parcelas": [
                    {
                        "dias": 30,
                        "data": "2026-04-27",
                        "valor": 68.93,
                        "forma": "Dinheiro",
                    }
                ],
            },
            "intermediador": {
                "tipo": "Sim",
                "cnpj": "35.635.824/0001-12",
                "identificacao": "1189728757",
            },
            "numeroPedidoLoja": "260329CDGSH41N",
            "origemLojaVirtual": "Shopee",
            "origemCanalVenda": "Outros",
            "informacoesAdicionais": {
                "informacoesComplementares": "N° Pedido Loja: 260329CDGSH41N",
                "informacoesAdicionaisInteresseFisco": "Total aproximado de tributos: R$ 21,68 (31,45%). Fonte IBPT.",
            },
        },
        55,
        venda=venda,
    )

    assert detalhe["status"] == "Autorizada"
    assert detalhe["tipo_label"] == "NF-e"
    assert detalhe["loja"]["nome"] == "Shopee Atacado"
    assert detalhe["unidade_negocio"]["nome"] == "Matriz"
    assert detalhe["cliente"]["tipo_pessoa"] == "Fisica"
    assert detalhe["itens"][0]["codigo"] == "018631.1"
    assert detalhe["totais"]["valor_total"] == 68.93
    assert detalhe["pagamento"]["parcelas"][0]["forma"] == "Dinheiro"
    assert detalhe["intermediador"]["cnpj"] == "35.635.824/0001-12"
    assert detalhe["informacoes_adicionais"]["numero_pedido_loja"] == "260329CDGSH41N"
    assert detalhe["canal_label"] == "Shopee"


def test_normalizar_detalhe_nota_bling_formata_objetos_aninhados_sem_exibir_dict_cru():
    detalhe = _normalizar_detalhe_nota_bling(
        {
            "id": 25426248868,
            "numero": "010969",
            "situacao": 5,
            "naturezaOperacao": {"id": 15103736276},
            "contato": {
                "nome": "Jeciane",
                "cpf": "44101288844",
                "endereco": {
                    "endereco": "Avenida Bandeirantes",
                    "numero": "308",
                    "bairro": "Alianca",
                    "municipio": "Osasco",
                    "uf": "SP",
                },
                "vendedor": {"id": 0},
            },
            "totais": {
                "valorProdutos": 199,
                "valorDesconto": 64.03,
            },
            "numeroLojaVirtual": "260328C036BAQ6",
        },
        55,
    )

    assert detalhe["natureza_operacao"] == "ID 15103736276"
    assert detalhe["cliente"]["endereco"] == "Avenida Bandeirantes, 308 - Alianca, Osasco, SP"
    assert detalhe["cliente"]["vendedor"] is None
    assert detalhe["totais"]["valor_total"] == 134.97
    assert detalhe["canal_label"] == "Shopee"
