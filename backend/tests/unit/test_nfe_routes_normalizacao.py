from types import SimpleNamespace
from unittest.mock import Mock
from datetime import datetime

from app.nfe_routes import (
    _normalizar_nota_pedido_integrado,
    _enriquecer_notas_com_pedidos_integrados,
    _enriquecer_notas_com_detalhes_bling,
    _extrair_campos_fiscais_do_xml,
    _extrair_valor_nota,
    _normalizar_detalhe_nota_bling,
    _normalizar_nota_bling,
    _normalizar_resumo_canal,
    _planejar_sincronizacao_bling_nfes,
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


def test_normalizar_resumo_canal_nao_promove_id_da_loja_a_canal():
    resumo = _normalizar_resumo_canal(
        {
            "loja": {"id": 205367939},
            "numeroLojaVirtual": "260329CJYQJRA2",
        }
    )

    assert resumo["canal"] == "shopee"
    assert resumo["canal_label"] == "Shopee"
    assert resumo["origem_loja_virtual"] == "Shopee"
    assert resumo["origem_canal_venda"] == "Shopee"
    assert resumo["loja"]["nome"] is None


def test_normalizar_resumo_canal_mapeia_loja_id_conhecida_para_mercado_livre():
    resumo = _normalizar_resumo_canal(
        {
            "loja": {"id": 204647675},
            "numeroLojaVirtual": "2000015737461914",
        }
    )

    assert resumo["canal"] == "mercado_livre"
    assert resumo["canal_label"] == "Mercado Livre"
    assert resumo["origem_loja_virtual"] == "Mercado Livre"


def test_normalizar_nota_pedido_integrado_usa_ultima_nf_salva_no_payload():
    pedido = SimpleNamespace(
        id=123,
        tenant_id="tenant-1",
        pedido_bling_id="25432947365",
        pedido_bling_numero="11609",
        canal="mercado_livre",
        created_at=None,
        updated_at=None,
        payload={
            "pedido": {
                "numeroPedidoLoja": "2000015755197092",
                "origemLojaVirtual": "Mercado Livre",
                "contato": {
                    "nome": "Leonardo Marcal Valles",
                    "cpfCnpj": "12345678900",
                },
            },
            "ultima_nf": {
                "id": "25432772133",
                "numero": "011008",
                "serie": "2",
                "situacao_codigo": 9,
                "valor_total": 440.13,
                "chave": "35123456789012345678901234567890123456789012",
                "data_emissao": "2026-03-30",
            },
        },
    )

    nota = _normalizar_nota_pedido_integrado(pedido)

    assert nota is not None
    assert nota["id"] == "25432772133"
    assert nota["numero"] == "011008"
    assert nota["status"] == "Autorizada"
    assert nota["valor"] == 440.13
    assert nota["numero_pedido_loja"] == "2000015755197092"
    assert nota["cliente"]["nome"] == "Leonardo Marcal Valles"


def test_normalizar_nota_pedido_integrado_descarta_id_zero_da_nf():
    pedido = SimpleNamespace(
        id=124,
        tenant_id="tenant-1",
        pedido_bling_id="25432947366",
        pedido_bling_numero="11610",
        canal="shopee",
        created_at=None,
        updated_at=None,
        payload={
            "pedido": {
                "numeroPedidoLoja": "260329CBKA46J1",
                "contato": {"nome": "Cliente Teste"},
            },
            "ultima_nf": {
                "id": "0",
                "numero": "011009",
                "situacao_codigo": 9,
                "valor_total": 36.10,
            },
        },
    )

    nota = _normalizar_nota_pedido_integrado(pedido)

    assert nota is not None
    assert nota["id"] == ""
    assert nota["numero"] == "011009"


def test_enriquecer_notas_com_detalhes_bling_preenche_numero_quando_cache_veio_incompleto(monkeypatch):
    class FakeBling:
        pass

    notas = [
        {
            "id": "25432772133",
            "numero": "",
            "serie": "",
            "modelo": 55,
            "status": "Pendente",
            "valor": 0,
            "canal_label": None,
            "loja": {"id": None, "nome": None},
            "origem_loja_virtual": None,
            "numero_pedido_loja": None,
            "chave": "",
            "cliente": {},
        }
    ]
    detalhe = {
        "id": 25432772133,
        "numero": "011008",
        "serie": 2,
        "situacao": 5,
        "valorNota": 440.13,
        "chaveAcesso": "CHAVE-123",
        "contato": {"nome": "Leonardo"},
        "numeroPedidoLoja": "2000015755197092",
    }
    upserts = []

    monkeypatch.setattr("app.nfe_routes._obter_detalhe_nfe_cache", lambda tenant_id, nfe_id, modelo=None: detalhe)
    monkeypatch.setattr("app.nfe_routes.obter_detalhe_nota_cache", lambda **kwargs: detalhe)
    monkeypatch.setattr("app.nfe_routes.upsert_nota_cache", lambda *args, **kwargs: upserts.append(kwargs))

    _enriquecer_notas_com_detalhes_bling(
        FakeBling(),
        db=Mock(),
        tenant_id="tenant-1",
        notas=notas,
        limite_consultas=10,
    )

    assert notas[0]["numero"] == "011008"
    assert notas[0]["serie"] == "2"
    assert notas[0]["status"] == "Autorizada"
    assert notas[0]["chave"] == "CHAVE-123"
    assert upserts


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


def test_extrair_campos_fiscais_do_xml_preenche_horas_e_rotulos():
    campos = _extrair_campos_fiscais_do_xml(
        """<?xml version="1.0" encoding="UTF-8"?>
        <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
          <NFe>
            <infNFe>
              <ide>
                <natOp>Venda de mercadoria com ST</natOp>
                <dhEmi>2026-03-28T22:03:22-03:00</dhEmi>
                <dhSaiEnt>2026-03-28T22:03:22-03:00</dhSaiEnt>
                <finNFe>1</finNFe>
                <indPres>9</indPres>
              </ide>
              <emit>
                <CRT>1</CRT>
              </emit>
            </infNFe>
          </NFe>
        </nfeProc>"""
    )

    assert campos["data_emissao"] == "2026-03-28"
    assert campos["hora_emissao"] == "22:03:22"
    assert campos["data_saida"] == "2026-03-28"
    assert campos["hora_saida"] == "22:03:22"
    assert campos["natureza_operacao"] == "Venda de mercadoria com ST"
    assert campos["codigo_regime_tributario"] == "Simples Nacional"
    assert campos["finalidade"] == "NF-e normal"
    assert campos["indicador_presenca"] == "9 - Operacao nao presencial, outros"


def test_normalizar_detalhe_nota_bling_extrai_hora_de_timestamp_compacto():
    detalhe = _normalizar_detalhe_nota_bling(
        {
            "id": 25428294101,
            "numero": "010980",
            "situacao": 5,
            "dataEmissao": "2026-03-28 22:03:22",
            "dataOperacao": "2026-03-28 22:03:22",
            "contato": {"nome": "Maria Carolina Silveira Silva"},
        },
        55,
    )

    assert detalhe["data_emissao"] == "2026-03-28"
    assert detalhe["hora_emissao"] == "22:03:22"
    assert detalhe["data_saida"] == "2026-03-28"
    assert detalhe["hora_saida"] == "22:03:22"


def test_enriquecer_notas_com_pedidos_integrados_preenche_valor_total_do_pedido():
    db = Mock()
    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        pedido_bling_id="25428293804",
        pedido_bling_numero="11595",
        canal="shopee",
        payload={
            "pedido": {
                "numeroLoja": "260329CXSEF6VM",
                "origemLojaVirtual": "Shopee",
                "total": 158.74,
            },
            "ultima_nf": {
                "id": "25428294101",
                "numero": "010980",
            },
        },
        created_at="2026-03-28T22:03:22",
    )
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [pedido]
    notas = [
        {
            "id": "25428294101",
            "numero": "010980",
            "valor": 0.0,
            "canal": None,
            "canal_label": None,
            "numero_pedido_loja": "260329CXSEF6VM",
            "loja": {"id": None, "nome": None},
        }
    ]

    _enriquecer_notas_com_pedidos_integrados(db, "tenant-1", notas)

    assert notas[0]["valor"] == 158.74
    assert notas[0]["canal_label"] == "Shopee"
    assert notas[0]["origem_loja_virtual"] == "Shopee"


def test_enriquecer_notas_com_pedidos_integrados_relaciona_por_id_da_nf_quando_resumo_nao_tem_pedido():
    db = Mock()
    pedido = SimpleNamespace(
        tenant_id="tenant-1",
        pedido_bling_id="2539990001",
        pedido_bling_numero="11601",
        canal="mercado_livre",
        payload={
            "pedido": {
                "origemLojaVirtual": "Mercado Livre",
                "total": 490.99,
            },
            "ultima_nf": {
                "id": "25428517969",
                "numero": "010977",
            },
        },
        created_at="2026-03-28T22:12:52",
    )
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [pedido]
    notas = [
        {
            "id": "25428517969",
            "numero": "010977",
            "valor": 0.0,
            "canal": None,
            "canal_label": None,
            "numero_pedido_loja": None,
            "numero_loja_virtual": None,
            "loja": {"id": None, "nome": None},
        }
    ]

    _enriquecer_notas_com_pedidos_integrados(db, "tenant-1", notas)

    assert notas[0]["valor"] == 490.99
    assert notas[0]["canal_label"] == "Mercado Livre"
    assert notas[0]["origem_loja_virtual"] == "Mercado Livre"


def test_planejar_sincronizacao_bling_nfes_faz_bootstrap_quando_cache_esta_vazio():
    deve_sincronizar, data_inicial, data_final, estrategia = _planejar_sincronizacao_bling_nfes(
        force_refresh=False,
        data_inicial=None,
        data_final=None,
        cache_total=0,
        cache_intervalo_tem_dados=False,
        ultimo_sync=None,
        ultima_data_emissao=None,
        agora=datetime(2026, 3, 30, 9, 0, 0),
    )

    assert deve_sincronizar is True
    assert data_inicial == "2026-03-23"
    assert data_final == "2026-03-30"
    assert estrategia == "bootstrap_cache_vazio"


def test_planejar_sincronizacao_bling_nfes_reduz_para_janela_incremental_quando_cache_existe():
    deve_sincronizar, data_inicial, data_final, estrategia = _planejar_sincronizacao_bling_nfes(
        force_refresh=False,
        data_inicial=None,
        data_final=None,
        cache_total=18,
        cache_intervalo_tem_dados=True,
        ultimo_sync=datetime(2026, 3, 30, 8, 45, 0),
        ultima_data_emissao=datetime(2026, 3, 29, 17, 30, 0),
        agora=datetime(2026, 3, 30, 9, 0, 0),
    )

    assert deve_sincronizar is True
    assert data_inicial == "2026-03-27"
    assert data_final == "2026-03-30"
    assert estrategia == "janela_incremental_recente"


def test_planejar_sincronizacao_bling_nfes_nao_reconsulta_intervalo_quando_cache_esta_recente():
    deve_sincronizar, data_inicial, data_final, estrategia = _planejar_sincronizacao_bling_nfes(
        force_refresh=False,
        data_inicial="2026-03-28",
        data_final="2026-03-30",
        cache_total=18,
        cache_intervalo_tem_dados=True,
        ultimo_sync=datetime(2026, 3, 30, 8, 58, 0),
        ultima_data_emissao=datetime(2026, 3, 29, 17, 30, 0),
        agora=datetime(2026, 3, 30, 9, 0, 0),
    )

    assert deve_sincronizar is False
    assert data_inicial is None
    assert data_final is None
    assert estrategia == "cache_intervalo_recente"
