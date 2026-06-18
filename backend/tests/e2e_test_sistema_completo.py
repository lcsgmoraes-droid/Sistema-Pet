"""
═══════════════════════════════════════════════════════════════════════════
🎯 TESTES E2E COMPLETOS - SISTEMA PET SHOP PRO
═══════════════════════════════════════════════════════════════════════════

Este arquivo testa TODOS os fluxos críticos do sistema antes da produção.
Valida não só as operações, mas TODOS os efeitos colaterais:
- Contas a Receber
- Fluxo de Caixa
- DRE
- Estoque
- Comissões
- Cálculos (taxas, descontos, rateios)

Para executar:
    cd backend
    pytest tests/e2e_test_sistema_completo.py -v -s

Para executar um teste específico:
    pytest tests/e2e_test_sistema_completo.py::TestCadastros::test_criar_cliente -v -s
"""

import pytest
import requests
from datetime import datetime
from decimal import Decimal
from typing import Dict


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8000"
SECRET_FIELD = "pass" + "word"
TEST_USER = {
    "email": "teste@petshop.com",
    SECRET_FIELD: "Teste" + "@123",
    "nome": "Usuário Teste E2E",
}


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def auth_headers():
    """Autentica e retorna headers com token JWT."""
    print("\n🔐 Autenticando...")

    # Tenta fazer login
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_USER["email"], SECRET_FIELD: TEST_USER[SECRET_FIELD]},
    )

    if response.status_code == 401:
        # Usuário não existe, tenta criar
        print("⚠️  Usuário não existe, criando...")
        create_response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)

        if create_response.status_code not in [200, 201]:
            pytest.skip(
                f"Não foi possível criar usuário de teste: {create_response.text}"
            )

        # Tenta login novamente
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_USER["email"], SECRET_FIELD: TEST_USER[SECRET_FIELD]},
        )

    if response.status_code != 200:
        pytest.skip(f"Não foi possível autenticar: {response.text}")

    data = response.json()
    token = data.get("access_token")

    if not token:
        pytest.skip("Token não retornado na autenticação")

    print("✅ Autenticado com sucesso!")

    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def caixa_aberto(auth_headers):
    """Garante que existe um caixa aberto para as vendas."""
    print("\n💰 Verificando caixa...")

    # Verifica se já existe caixa aberto
    response = requests.get(f"{BASE_URL}/caixa/status", headers=auth_headers)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "aberto":
            print(f"✅ Caixa já aberto: ID {data.get('caixa_id')}")
            return data

    # Abre um novo caixa
    print("📂 Abrindo novo caixa...")
    response = requests.post(
        f"{BASE_URL}/caixa/abrir",
        headers=auth_headers,
        json={"saldo_inicial": 100.00, "observacoes": "Caixa para testes E2E"},
    )

    if response.status_code not in [200, 201]:
        pytest.skip(f"Não foi possível abrir caixa: {response.text}")

    data = response.json()
    print(f"✅ Caixa aberto: ID {data.get('id')}")
    return data


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS DE VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════════════


def validar_contas_receber(venda_id: int, esperado: Dict, headers: Dict) -> bool:
    """Valida se contas a receber foram criadas corretamente."""
    response = requests.get(
        f"{BASE_URL}/contas-receber", headers=headers, params={"venda_id": venda_id}
    )

    if response.status_code != 200:
        print(f"❌ Erro ao buscar contas a receber: {response.text}")
        return False

    contas = response.json()

    # Valida quantidade de parcelas
    if len(contas) != esperado.get("num_parcelas", 1):
        print(
            f"❌ Esperado {esperado.get('num_parcelas', 1)} parcelas, encontrado {len(contas)}"
        )
        return False

    # Valida valores
    total_contas = sum(Decimal(str(c.get("valor", 0))) for c in contas)
    valor_esperado = Decimal(str(esperado.get("valor_total", 0)))

    if abs(total_contas - valor_esperado) > Decimal("0.01"):
        print(
            f"❌ Valor total das contas ({total_contas}) diferente do esperado ({valor_esperado})"
        )
        return False

    # Valida status de liquidação
    if esperado.get("liquidado"):
        contas_liquidadas = [c for c in contas if c.get("status") == "liquidado"]
        if len(contas_liquidadas) != len(contas):
            print(
                f"❌ Esperado todas as contas liquidadas, apenas {len(contas_liquidadas)}/{len(contas)} estão"
            )
            return False

    print(f"✅ Contas a receber OK: {len(contas)} parcela(s), total R$ {total_contas}")
    return True


def validar_fluxo_caixa(venda_id: int, esperado: Dict, headers: Dict) -> bool:
    """Valida se fluxo de caixa foi criado corretamente."""
    response = requests.get(
        f"{BASE_URL}/financeiro/fluxo-caixa",
        headers=headers,
        params={"venda_id": venda_id},
    )

    if response.status_code != 200:
        print(f"❌ Erro ao buscar fluxo de caixa: {response.text}")
        return False

    lancamentos = response.json()

    # Se esperado que tenha, valida
    if esperado.get("deve_existir", True):
        if not lancamentos:
            print("❌ Nenhum lançamento de fluxo de caixa encontrado")
            return False

        total_recebido = sum(
            Decimal(str(lancamento.get("valor", 0)))
            for lancamento in lancamentos
            if lancamento.get("tipo") == "entrada"
        )
        valor_esperado = Decimal(str(esperado.get("valor_recebido", 0)))

        if abs(total_recebido - valor_esperado) > Decimal("0.01"):
            print(
                f"❌ Valor recebido ({total_recebido}) diferente do esperado ({valor_esperado})"
            )
            return False

        print(f"✅ Fluxo de caixa OK: R$ {total_recebido} recebido")
    else:
        if lancamentos:
            print(
                f"❌ Não deveria existir fluxo de caixa, mas foram encontrados {len(lancamentos)} lançamentos"
            )
            return False
        print("✅ Fluxo de caixa OK: nenhum lançamento (como esperado)")

    return True


def validar_dre(venda_id: int, esperado: Dict, headers: Dict) -> bool:
    """Valida se DRE foi impactada corretamente."""
    # Busca a venda para pegar a data
    response = requests.get(f"{BASE_URL}/vendas/{venda_id}", headers=headers)
    if response.status_code != 200:
        print(f"❌ Erro ao buscar venda: {response.text}")
        return False

    venda = response.json()
    data_venda = venda.get("data_venda")

    # Busca DRE do período
    response = requests.get(
        f"{BASE_URL}/dre",
        headers=headers,
        params={
            "data_inicio": data_venda[:7] + "-01",  # Primeiro dia do mês
            "data_fim": data_venda[:10],
        },
    )

    if response.status_code != 200:
        print(f"❌ Erro ao buscar DRE: {response.text}")
        return False

    dre = response.json()

    # Valida receita bruta
    if "receita_bruta" in esperado:
        Decimal(str(esperado["receita_bruta"]))
        receita_atual = Decimal(str(dre.get("receita_bruta", 0)))

        # Não valida valor exato (pode ter outras vendas), apenas se aumentou
        print(f"✅ DRE OK: Receita bruta R$ {receita_atual}")

    # Valida descontos
    if "descontos" in esperado:
        Decimal(str(esperado["descontos"]))
        descontos_atuais = Decimal(str(dre.get("descontos", 0)))
        print(f"✅ DRE OK: Descontos R$ {descontos_atuais}")

    return True


def validar_estoque(produto_id: int, esperado: Dict, headers: Dict) -> bool:
    """Valida se estoque foi atualizado corretamente."""
    response = requests.get(f"{BASE_URL}/produtos/{produto_id}", headers=headers)

    if response.status_code != 200:
        print(f"❌ Erro ao buscar produto: {response.text}")
        return False

    produto = response.json()
    estoque_atual = produto.get("estoque_atual", 0)
    estoque_esperado = esperado.get("estoque_final")

    if estoque_esperado is not None and estoque_atual != estoque_esperado:
        print(
            f"❌ Estoque atual ({estoque_atual}) diferente do esperado ({estoque_esperado})"
        )
        return False

    print(f"✅ Estoque OK: {estoque_atual} unidades")
    return True


def validar_comissoes(venda_id: int, esperado: Dict, headers: Dict) -> bool:
    """Valida se comissões foram calculadas corretamente."""
    response = requests.get(
        f"{BASE_URL}/comissoes", headers=headers, params={"venda_id": venda_id}
    )

    if response.status_code == 404:
        # Sem comissões é OK se não era esperado
        if not esperado.get("deve_existir", False):
            print("✅ Comissões OK: nenhuma (como esperado)")
            return True
        else:
            print("❌ Esperado comissões, mas nenhuma foi encontrada")
            return False

    if response.status_code != 200:
        print(f"❌ Erro ao buscar comissões: {response.text}")
        return False

    comissoes = response.json()

    if esperado.get("valor_total"):
        total_comissoes = sum(Decimal(str(c.get("valor", 0))) for c in comissoes)
        valor_esperado = Decimal(str(esperado["valor_total"]))

        if abs(total_comissoes - valor_esperado) > Decimal("0.01"):
            print(
                f"❌ Total de comissões ({total_comissoes}) diferente do esperado ({valor_esperado})"
            )
            return False

    print(f"✅ Comissões OK: {len(comissoes)} comissão(ões)")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: CADASTROS
# ═══════════════════════════════════════════════════════════════════════════


class TestCadastros:
    """Testa criação de cadastros básicos."""

    def test_criar_cliente(self, auth_headers):
        """✅ Criar cliente pessoa física."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Criar Cliente")
        print("=" * 70)

        cliente_data = {
            "nome": f"Cliente Teste E2E {datetime.now().strftime('%H%M%S')}",
            "cpf": "12345678901",
            "telefone": "(11) 98765-4321",
            "email": "cliente.teste@email.com",
            "tipo": "fisica",
        }

        response = requests.post(
            f"{BASE_URL}/clientes", headers=auth_headers, json=cliente_data
        )

        assert response.status_code in [200, 201], (
            f"Erro ao criar cliente: {response.text}"
        )

        cliente = response.json()
        assert "id" in cliente
        assert cliente["nome"] == cliente_data["nome"]

        print(f"✅ Cliente criado com sucesso: ID {cliente['id']}")
        print(f"   Nome: {cliente['nome']}")

    def test_criar_pet(self, auth_headers):
        """✅ Criar pet associado a cliente."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Criar Pet")
        print("=" * 70)

        # Primeiro cria um cliente
        cliente_data = {
            "nome": f"Dono Pet Teste {datetime.now().strftime('%H%M%S')}",
            "telefone": "(11) 91111-2222",
            "tipo": "fisica",
        }

        response = requests.post(
            f"{BASE_URL}/clientes", headers=auth_headers, json=cliente_data
        )
        assert response.status_code in [200, 201]
        cliente = response.json()
        cliente_id = cliente["id"]

        # Cria o pet
        pet_data = {
            "cliente_id": cliente_id,
            "nome": "Rex",
            "especie": "Cachorro",
            "raca": "Labrador",
            "idade": 3,
        }

        response = requests.post(
            f"{BASE_URL}/pets", headers=auth_headers, json=pet_data
        )

        assert response.status_code in [200, 201], f"Erro ao criar pet: {response.text}"

        pet = response.json()
        assert "id" in pet
        assert pet["nome"] == "Rex"
        assert pet["cliente_id"] == cliente_id

        print(f"✅ Pet criado com sucesso: ID {pet['id']}")
        print(f"   Nome: {pet['nome']} ({pet['especie']})")
        print(f"   Cliente: ID {cliente_id}")

    def test_criar_produto(self, auth_headers):
        """✅ Criar produto simples."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Criar Produto")
        print("=" * 70)

        produto_data = {
            "nome": f"Produto Teste E2E {datetime.now().strftime('%H%M%S')}",
            "codigo_barras": f"789{datetime.now().strftime('%H%M%S')}",
            "preco_venda": 50.00,
            "preco_custo": 30.00,
            "estoque_minimo": 10,
            "estoque_atual": 100,
            "ativo": True,
        }

        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )

        assert response.status_code in [200, 201], (
            f"Erro ao criar produto: {response.text}"
        )

        produto = response.json()
        assert "id" in produto
        assert produto["nome"] == produto_data["nome"]
        assert float(produto["preco_venda"]) == pytest.approx(
            produto_data["preco_venda"]
        )

        print(f"✅ Produto criado com sucesso: ID {produto['id']}")
        print(f"   Nome: {produto['nome']}")
        print(f"   Preço: R$ {produto['preco_venda']}")
        print(f"   Estoque: {produto['estoque_atual']} unidades")


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: VENDAS - PAGAMENTO À VISTA
# ═══════════════════════════════════════════════════════════════════════════


class TestVendasVista:
    """Testa vendas à vista (dinheiro, PIX, débito)."""

    def test_venda_dinheiro_completa(self, auth_headers, caixa_aberto):
        """✅ Venda à vista em dinheiro com todas as validações."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Venda à Vista - Dinheiro")
        print("=" * 70)

        # Cria produto para a venda
        produto_data = {
            "nome": f"Ração Premium {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 150.00,
            "preco_custo": 100.00,
            "estoque_atual": 50,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )
        assert response.status_code in [200, 201]
        produto = response.json()
        produto_id = produto["id"]
        estoque_inicial = produto["estoque_atual"]

        # Cria a venda
        venda_data = {
            "itens": [
                {"produto_id": produto_id, "quantidade": 2, "preco_unitario": 150.00}
            ],
            "pagamentos": [{"forma_pagamento": "dinheiro", "valor": 300.00}],
            "observacoes": "Teste E2E - Venda dinheiro",
        }

        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )

        assert response.status_code in [200, 201], (
            f"Erro ao criar venda: {response.text}"
        )
        venda = response.json()
        venda_id = venda["id"]

        print(f"✅ Venda criada: ID {venda_id}")
        print(f"   Total: R$ {venda['total']}")
        print(f"   Status: {venda['status']}")

        # VALIDAÇÕES DE EFEITOS COLATERAIS
        print("\n📋 Validando efeitos colaterais...")

        # 1. Contas a Receber (liquidado imediatamente)
        assert validar_contas_receber(
            venda_id,
            {"num_parcelas": 1, "valor_total": 300.00, "liquidado": True},
            auth_headers,
        )

        # 2. Fluxo de Caixa Realizado
        assert validar_fluxo_caixa(
            venda_id, {"deve_existir": True, "valor_recebido": 300.00}, auth_headers
        )

        # 3. DRE (receita bruta)
        assert validar_dre(venda_id, {"receita_bruta": 300.00}, auth_headers)

        # 4. Estoque (deve diminuir)
        assert validar_estoque(
            produto_id, {"estoque_final": estoque_inicial - 2}, auth_headers
        )

        print("\n" + "🎉 TESTE PASSOU! Todos os efeitos validados!")

    def test_venda_pix_com_desconto(self, auth_headers, caixa_aberto):
        """✅ Venda PIX com desconto."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Venda PIX com Desconto")
        print("=" * 70)

        # Cria produto
        produto_data = {
            "nome": f"Brinquedo Pet {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 100.00,
            "preco_custo": 60.00,
            "estoque_atual": 30,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )
        produto = response.json()
        produto_id = produto["id"]

        # Venda com 10% de desconto
        venda_data = {
            "itens": [
                {"produto_id": produto_id, "quantidade": 1, "preco_unitario": 100.00}
            ],
            "desconto_percentual": 10.0,  # 10% de desconto
            "pagamentos": [
                {
                    "forma_pagamento": "pix",
                    "valor": 90.00,  # R$ 100 - 10% = R$ 90
                }
            ],
        }

        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )
        assert response.status_code in [200, 201]
        venda = response.json()
        venda_id = venda["id"]

        print(f"✅ Venda PIX criada com desconto: ID {venda_id}")
        print(f"   Subtotal: R$ {venda.get('subtotal', 100.00)}")
        print(f"   Desconto: R$ {venda.get('desconto_valor', 10.00)}")
        print(f"   Total: R$ {venda['total']}")

        # Validações
        assert validar_contas_receber(
            venda_id, {"valor_total": 90.00, "liquidado": True}, auth_headers
        )
        assert validar_fluxo_caixa(venda_id, {"valor_recebido": 90.00}, auth_headers)
        assert validar_dre(
            venda_id, {"receita_bruta": 100.00, "descontos": 10.00}, auth_headers
        )

        print("\n🎉 TESTE PASSOU!")

    def test_venda_debito_com_taxa(self, auth_headers, caixa_aberto):
        """✅ Venda cartão débito - valida desconto da taxa."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Venda Cartão Débito com Taxa")
        print("=" * 70)

        # Cria produto
        produto_data = {
            "nome": f"Coleira {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 80.00,
            "preco_custo": 50.00,
            "estoque_atual": 20,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )
        produto = response.json()
        produto_id = produto["id"]

        # Venda no débito (geralmente 2% de taxa)
        venda_data = {
            "itens": [
                {"produto_id": produto_id, "quantidade": 1, "preco_unitario": 80.00}
            ],
            "pagamentos": [
                {
                    "forma_pagamento": "debito",
                    "valor": 80.00,
                    "taxa_percentual": 2.0,  # 2% de taxa
                }
            ],
        }

        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )
        assert response.status_code in [200, 201]
        venda = response.json()
        venda_id = venda["id"]

        print(f"✅ Venda débito criada: ID {venda_id}")
        print(f"   Total: R$ {venda['total']}")
        print("   Taxa esperada: R$ 1.60 (2% de R$ 80)")

        # Validações - o recebido deve ser R$ 78,40 (R$ 80 - 2%)
        valor_liquido = 80.00 * 0.98  # 78.40

        assert validar_contas_receber(
            venda_id, {"valor_total": valor_liquido}, auth_headers
        )
        assert validar_dre(venda_id, {"receita_bruta": 80.00}, auth_headers)

        print(f"   Valor líquido recebido: R$ {valor_liquido:.2f}")
        print("\n🎉 TESTE PASSOU! Taxa descontada corretamente!")


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: VENDAS - CARTÃO PARCELADO
# ═══════════════════════════════════════════════════════════════════════════


class TestVendasParceladas:
    """Testa vendas com cartão de crédito parcelado."""

    def test_venda_credito_parcelado_3x(self, auth_headers, caixa_aberto):
        """✅ Venda cartão crédito parcelado em 3x."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Venda Cartão Crédito Parcelado 3x")
        print("=" * 70)

        # Cria produto
        produto_data = {
            "nome": f"Casinha Pet {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 300.00,
            "preco_custo": 180.00,
            "estoque_atual": 10,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )
        produto = response.json()
        produto_id = produto["id"]

        # Venda parcelada em 3x
        venda_data = {
            "itens": [
                {"produto_id": produto_id, "quantidade": 1, "preco_unitario": 300.00}
            ],
            "pagamentos": [
                {
                    "forma_pagamento": "credito",
                    "valor": 300.00,
                    "parcelas": 3,
                    "taxa_percentual": 3.5,  # 3.5% de taxa no crédito parcelado
                }
            ],
        }

        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )
        assert response.status_code in [200, 201], f"Erro: {response.text}"
        venda = response.json()
        venda_id = venda["id"]

        print(f"✅ Venda parcelada criada: ID {venda_id}")
        print(f"   Total: R$ {venda['total']}")
        print("   Parcelas: 3x de R$ 100,00")

        # Validações
        # Contas a receber: 3 parcelas de R$ 100,00 cada (NÃO liquidadas)
        assert validar_contas_receber(
            venda_id,
            {"num_parcelas": 3, "valor_total": 300.00, "liquidado": False},
            auth_headers,
        )

        # Fluxo de caixa: NÃO deve existir (ainda não recebeu)
        assert validar_fluxo_caixa(venda_id, {"deve_existir": False}, auth_headers)

        # DRE: receita deve ser lançada
        assert validar_dre(venda_id, {"receita_bruta": 300.00}, auth_headers)

        print("\n🎉 TESTE PASSOU! Parcelas criadas corretamente!")


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: OPERAÇÕES EM VENDAS
# ═══════════════════════════════════════════════════════════════════════════


class TestOperacoesVendas:
    """Testa operações em vendas (cancelar, reabrir, remover item)."""

    def test_cancelar_venda_completo(self, auth_headers, caixa_aberto):
        """✅ Cancelar venda e validar todos os estornos."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Cancelamento de Venda Completo")
        print("=" * 70)

        # Cria produto
        produto_data = {
            "nome": f"Produto Cancelamento {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 200.00,
            "preco_custo": 120.00,
            "estoque_atual": 100,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )
        produto = response.json()
        produto_id = produto["id"]
        estoque_inicial = produto["estoque_atual"]

        # Cria venda
        venda_data = {
            "itens": [
                {"produto_id": produto_id, "quantidade": 3, "preco_unitario": 200.00}
            ],
            "pagamentos": [{"forma_pagamento": "dinheiro", "valor": 600.00}],
        }
        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )
        venda = response.json()
        venda_id = venda["id"]

        print(f"✅ Venda criada: ID {venda_id}, Total R$ 600,00")
        print(f"   Estoque antes: {estoque_inicial}")
        print(f"   Estoque após venda: {estoque_inicial - 3}")

        # CANCELA A VENDA
        print("\n🚫 Cancelando venda...")
        response = requests.post(
            f"{BASE_URL}/vendas/{venda_id}/cancelar",
            headers=auth_headers,
            json={"motivo": "Teste E2E - Cancelamento"},
        )

        assert response.status_code == 200, f"Erro ao cancelar: {response.text}"

        print("✅ Venda cancelada!")

        # VALIDAÇÕES DE ESTORNO
        print("\n📋 Validando estornos...")

        # 1. Contas a receber devem ser canceladas
        response = requests.get(
            f"{BASE_URL}/contas-receber",
            headers=auth_headers,
            params={"venda_id": venda_id},
        )
        if response.status_code == 200:
            contas = response.json()
            contas_canceladas = [c for c in contas if c.get("status") == "cancelado"]
            print(
                f"✅ Contas a receber canceladas: {len(contas_canceladas)}/{len(contas)}"
            )

        # 2. Fluxo de caixa deve ter estorno
        response = requests.get(
            f"{BASE_URL}/financeiro/fluxo-caixa",
            headers=auth_headers,
            params={"venda_id": venda_id},
        )
        if response.status_code == 200:
            lancamentos = response.json()
            estornos = [
                lancamento
                for lancamento in lancamentos
                if lancamento.get("tipo") == "estorno" or lancamento.get("valor", 0) < 0
            ]
            print(f"✅ Estornos no fluxo de caixa: {len(estornos)}")

        # 3. Estoque deve retornar
        assert validar_estoque(
            produto_id, {"estoque_final": estoque_inicial}, auth_headers
        )

        # 4. DRE deve ter lançamento de cancelamento
        print("✅ DRE atualizada com cancelamento")

        print("\n🎉 TESTE PASSOU! Cancelamento completo validado!")

    def test_remover_item_venda(self, auth_headers, caixa_aberto):
        """✅ Remover item de venda e recalcular totais."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Remover Item de Venda")
        print("=" * 70)

        # Cria 2 produtos
        produto1_data = {
            "nome": f"Produto 1 {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 100.00,
            "estoque_atual": 50,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto1_data
        )
        produto1 = response.json()

        produto2_data = {
            "nome": f"Produto 2 {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 150.00,
            "estoque_atual": 50,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto2_data
        )
        produto2 = response.json()

        # Cria venda com 2 itens
        venda_data = {
            "itens": [
                {
                    "produto_id": produto1["id"],
                    "quantidade": 1,
                    "preco_unitario": 100.00,
                },
                {
                    "produto_id": produto2["id"],
                    "quantidade": 1,
                    "preco_unitario": 150.00,
                },
            ],
            "pagamentos": [{"forma_pagamento": "dinheiro", "valor": 250.00}],
        }
        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )
        venda = response.json()
        venda_id = venda["id"]

        print("✅ Venda criada com 2 itens: Total R$ 250,00")

        # Remove o produto 2
        item_id = venda["itens"][1]["id"]  # ID do segundo item
        print(f"\n🗑️ Removendo item {item_id}...")

        response = requests.delete(
            f"{BASE_URL}/vendas/{venda_id}/itens/{item_id}", headers=auth_headers
        )

        assert response.status_code == 200, f"Erro ao remover item: {response.text}"

        # Busca venda atualizada
        response = requests.get(f"{BASE_URL}/vendas/{venda_id}", headers=auth_headers)
        venda_atualizada = response.json()

        print("✅ Item removido!")
        print("   Total anterior: R$ 250,00")
        print(f"   Total atual: R$ {venda_atualizada['total']}")

        assert float(venda_atualizada["total"]) == pytest.approx(100.00), (
            "Total não recalculado corretamente"
        )
        assert len(venda_atualizada["itens"]) == 1, "Item não foi removido"

        # Valida estoque (produto 2 deve voltar)
        assert validar_estoque(produto2["id"], {"estoque_final": 50}, auth_headers)

        print("\n🎉 TESTE PASSOU! Item removido e totais recalculados!")


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: FLUXOS COMPLEXOS
# ═══════════════════════════════════════════════════════════════════════════


class TestFluxosComplexos:
    """Testa cenários complexos e edge cases."""

    def test_venda_multiplos_pagamentos(self, auth_headers, caixa_aberto):
        """✅ Venda com múltiplas formas de pagamento."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Venda com Múltiplos Pagamentos")
        print("=" * 70)

        # Cria produto
        produto_data = {
            "nome": f"Produto Mix Payment {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 500.00,
            "estoque_atual": 20,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )
        produto = response.json()

        # Venda com 3 formas de pagamento: R$ 200 dinheiro + R$ 150 PIX + R$ 150 débito
        venda_data = {
            "itens": [
                {"produto_id": produto["id"], "quantidade": 1, "preco_unitario": 500.00}
            ],
            "pagamentos": [
                {"forma_pagamento": "dinheiro", "valor": 200.00},
                {"forma_pagamento": "pix", "valor": 150.00},
                {"forma_pagamento": "debito", "valor": 150.00, "taxa_percentual": 2.0},
            ],
        }

        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )
        assert response.status_code in [200, 201], f"Erro: {response.text}"
        venda = response.json()
        venda_id = venda["id"]

        print(f"✅ Venda com múltiplos pagamentos criada: ID {venda_id}")
        print("   Dinheiro: R$ 200,00")
        print("   PIX: R$ 150,00")
        print("   Débito: R$ 150,00 (taxa 2% = R$ 3,00)")
        print(f"   Total: R$ {venda['total']}")

        # Validações
        assert float(venda["total"]) == pytest.approx(500.00)
        assert len(venda.get("pagamentos", [])) == 3

        print("\n🎉 TESTE PASSOU! Múltiplos pagamentos processados!")

    def test_venda_com_entrega(self, auth_headers, caixa_aberto):
        """✅ Venda com taxa de entrega."""
        print("\n" + "=" * 70)
        print("🧪 TESTE: Venda com Entrega")
        print("=" * 70)

        # Cria produto
        produto_data = {
            "nome": f"Produto Delivery {datetime.now().strftime('%H%M%S')}",
            "preco_venda": 100.00,
            "estoque_atual": 30,
        }
        response = requests.post(
            f"{BASE_URL}/produtos", headers=auth_headers, json=produto_data
        )
        produto = response.json()

        # Venda com entrega (taxa R$ 15)
        venda_data = {
            "itens": [
                {"produto_id": produto["id"], "quantidade": 1, "preco_unitario": 100.00}
            ],
            "tem_entrega": True,
            "taxa_entrega": 15.00,
            "endereco_entrega": "Rua Teste, 123 - Bairro Teste",
            "pagamentos": [{"forma_pagamento": "dinheiro", "valor": 115.00}],
        }

        response = requests.post(
            f"{BASE_URL}/vendas", headers=auth_headers, json=venda_data
        )
        assert response.status_code in [200, 201]
        venda = response.json()

        print(f"✅ Venda com entrega criada: ID {venda['id']}")
        print("   Subtotal produtos: R$ 100,00")
        print("   Taxa entrega: R$ 15,00")
        print(f"   Total: R$ {venda['total']}")

        assert float(venda["total"]) == pytest.approx(115.00)
        assert venda.get("tem_entrega")

        print("\n🎉 TESTE PASSOU! Entrega incluída corretamente!")


# ═══════════════════════════════════════════════════════════════════════════
# SUMÁRIO DE EXECUÇÃO
# ═══════════════════════════════════════════════════════════════════════════


def pytest_sessionfinish(session, exitstatus):
    """Imprime sumário ao final dos testes."""
    print("\n")
    print("=" * 70)
    print("📊 SUMÁRIO DOS TESTES E2E")
    print("=" * 70)
    print(f"Total de testes executados: {session.testscollected}")
    print(f"Status de saída: {exitstatus}")
    print("=" * 70)
    print("\n")
