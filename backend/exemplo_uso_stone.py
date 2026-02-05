"""
Exemplo de uso da integração Stone
Demonstra como usar os endpoints da API
"""

import requests
import json
from decimal import Decimal


# Configuração base
BASE_URL = "http://localhost:8000"
TOKEN = "seu_token_jwt_aqui"  # Obtenha via POST /auth/login


def configurar_stone():
    """
    Passo 1: Configurar credenciais Stone
    Execute apenas uma vez por tenant
    """
    print("=" * 60)
    print("PASSO 1: Configurar Stone")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/stone/config"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "client_id": "seu_client_id_stone",
        "client_secret": "seu_client_secret_stone",
        "merchant_id": "seu_merchant_id",
        "webhook_secret": "seu_webhook_secret",  # Opcional
        "sandbox": True,  # True = testes, False = produção
        "enable_pix": True,
        "enable_credit_card": True,
        "enable_debit_card": False,
        "max_installments": 12,
        "webhook_url": f"{BASE_URL}/api/stone/webhook"
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        print("✅ Configuração salva com sucesso!")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
    
    print()


def criar_pagamento_pix():
    """
    Passo 2: Criar um pagamento PIX
    """
    print("=" * 60)
    print("PASSO 2: Criar Pagamento PIX")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/stone/payments/pix"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "amount": 100.50,  # R$ 100,50
        "description": "Venda #123 - Ração Premium",
        "external_id": "venda-123-2024-02-03",  # ID único!
        "customer_name": "João Silva",
        "customer_document": "12345678900",
        "customer_email": "joao@email.com",
        "expiration_minutes": 30,  # PIX expira em 30 minutos
        "venda_id": 123  # Opcional: vincular com venda
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Pagamento PIX criado!")
        print(f"   Transaction ID: {result['transaction']['id']}")
        print(f"   Status: {result['transaction']['status']}")
        print()
        print("📱 Dados do PIX:")
        print(f"   QR Code: {result['pix']['qr_code'][:50]}...")
        print(f"   URL da Imagem: {result['pix']['qr_code_url']}")
        print(f"   Copia e Cola: {result['pix']['copy_paste'][:50]}...")
        print(f"   Expira em: {result['pix']['expiration']}")
        
        return result['transaction']['id']
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return None
    
    print()


def criar_pagamento_cartao():
    """
    Passo 3: Criar pagamento com cartão
    """
    print("=" * 60)
    print("PASSO 3: Criar Pagamento com Cartão")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/stone/payments/card"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # ATENÇÃO: Use HTTPS em produção!
    # Dados de cartão são sensíveis!
    data = {
        "amount": 250.00,
        "description": "Venda #124 - Banho e Tosa",
        "external_id": "venda-124-2024-02-03",
        "card_number": "4111111111111111",  # Cartão de teste
        "card_holder_name": "MARIA SANTOS",
        "card_expiration_date": "12/25",  # MM/YY
        "card_cvv": "123",
        "installments": 3,  # 3 parcelas
        "customer_name": "Maria Santos",
        "customer_document": "98765432100",
        "customer_email": "maria@email.com",
        "venda_id": 124
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Pagamento processado!")
        print(f"   Transaction ID: {result['transaction']['id']}")
        print(f"   Status: {result['transaction']['status']}")
        print(f"   Cartão: {result['transaction']['card_brand']} **** {result['transaction']['card_last_digits']}")
        print(f"   Parcelas: {result['transaction']['installments']}x")
        print(f"   Taxa: R$ {result['transaction']['fee_amount']}")
        print(f"   Líquido: R$ {result['transaction']['net_amount']}")
        
        return result['transaction']['id']
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return None
    
    print()


def consultar_pagamento(transaction_id):
    """
    Passo 4: Consultar status de um pagamento
    """
    print("=" * 60)
    print("PASSO 4: Consultar Pagamento")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/stone/payments/{transaction_id}"
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        transaction = result['transaction']
        
        print("✅ Status obtido!")
        print(f"   Transaction ID: {transaction['id']}")
        print(f"   Status: {transaction['status']}")
        print(f"   Valor: R$ {transaction['amount']}")
        print(f"   Método: {transaction['payment_method']}")
        print(f"   Criado em: {transaction['created_at']}")
        
        if transaction['status'] == 'approved':
            print(f"   ✅ Pago em: {transaction['paid_at']}")
        
        return transaction
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return None
    
    print()


def listar_pagamentos():
    """
    Passo 5: Listar todos os pagamentos
    """
    print("=" * 60)
    print("PASSO 5: Listar Pagamentos")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/stone/payments"
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    # Filtros opcionais
    params = {
        "status": "approved",  # pending, approved, cancelled, refunded
        "payment_method": "pix",  # pix, credit_card, debit_card
        "limit": 10,
        "offset": 0
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"✅ Total: {result['total']} pagamentos")
        print()
        
        for transaction in result['transactions']:
            print(f"   • {transaction['id']} - R$ {transaction['amount']} - {transaction['status']}")
            print(f"     {transaction['description']}")
            print()
        
        return result['transactions']
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
        return []
    
    print()


def cancelar_pagamento(transaction_id):
    """
    Passo 6: Cancelar um pagamento pendente
    """
    print("=" * 60)
    print("PASSO 6: Cancelar Pagamento")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/stone/payments/{transaction_id}/cancel"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "reason": "Cliente desistiu da compra"
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Pagamento cancelado!")
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
    
    print()


def estornar_pagamento(transaction_id):
    """
    Passo 7: Estornar um pagamento aprovado
    """
    print("=" * 60)
    print("PASSO 7: Estornar Pagamento")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/stone/payments/{transaction_id}/refund"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "amount": 50.00,  # Estorno parcial (ou null para estorno total)
        "reason": "Produto com defeito"
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Pagamento estornado!")
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)
    
    print()


def exemplo_completo():
    """
    Executa um fluxo completo de teste
    """
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           EXEMPLO DE USO - STONE PAGAMENTOS                ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Verifica se token está configurado
    if TOKEN == "seu_token_jwt_aqui":
        print("❌ ERRO: Configure o TOKEN primeiro!")
        print()
        print("Para obter o token:")
        print("1. Faça login: POST /auth/login")
        print("2. Copie o token retornado")
        print("3. Cole na variável TOKEN deste arquivo")
        print()
        return
    
    print("Este exemplo demonstra como usar a integração Stone.")
    print()
    
    input("Pressione ENTER para continuar...")
    print()
    
    # 1. Configurar Stone (apenas uma vez)
    configurar_stone()
    input("Pressione ENTER para continuar...")
    
    # 2. Criar pagamento PIX
    pix_id = criar_pagamento_pix()
    if pix_id:
        input("Pressione ENTER para continuar...")
        
        # 4. Consultar status
        consultar_pagamento(pix_id)
        input("Pressione ENTER para continuar...")
    
    # 3. Criar pagamento com cartão
    card_id = criar_pagamento_cartao()
    if card_id:
        input("Pressione ENTER para continuar...")
        
        # 4. Consultar status
        consultar_pagamento(card_id)
        input("Pressione ENTER para continuar...")
    
    # 5. Listar pagamentos
    listar_pagamentos()
    input("Pressione ENTER para continuar...")
    
    print()
    print("✨ Exemplo concluído!")
    print()
    print("Próximos passos:")
    print("- Integre no seu frontend")
    print("- Configure webhooks")
    print("- Teste em produção")
    print()


if __name__ == "__main__":
    exemplo_completo()
