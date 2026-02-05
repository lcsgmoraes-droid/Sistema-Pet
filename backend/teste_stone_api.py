"""
Script de teste para integração Stone
Testa conexão e funcionalidades básicas da API Stone
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.stone_api_client import StoneAPIClient
from decimal import Decimal
import uuid


async def testar_conexao_stone():
    """Testa conexão com a API Stone"""
    
    print("="*60)
    print("🧪 TESTE DE CONEXÃO COM API STONE")
    print("="*60)
    print()
    
    # Configuração de teste (SUBSTITUA COM SUAS CREDENCIAIS)
    # Para obter credenciais de teste, acesse: https://portal.stone.com.br/
    CLIENT_ID = "seu_client_id_aqui"
    CLIENT_SECRET = "seu_client_secret_aqui"
    MERCHANT_ID = "seu_merchant_id_aqui"
    SANDBOX = True  # True = ambiente de testes
    
    print("📋 Configuração:")
    print(f"   Client ID: {CLIENT_ID}")
    print(f"   Merchant ID: {MERCHANT_ID}")
    print(f"   Ambiente: {'SANDBOX (Testes)' if SANDBOX else 'PRODUÇÃO'}")
    print()
    
    # Verifica se credenciais foram configuradas
    if CLIENT_ID == "seu_client_id_aqui":
        print("❌ ERRO: Configure suas credenciais Stone antes de executar o teste!")
        print()
        print("Para obter credenciais:")
        print("1. Acesse https://portal.stone.com.br/")
        print("2. Cadastre-se como desenvolvedor")
        print("3. Crie uma aplicação")
        print("4. Copie Client ID, Client Secret e Merchant ID")
        print("5. Edite este arquivo e cole as credenciais")
        return
    
    # Inicializa cliente Stone
    print("🔌 Inicializando cliente Stone...")
    client = StoneAPIClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        merchant_id=MERCHANT_ID,
        sandbox=SANDBOX
    )
    
    try:
        # TESTE 1: Autenticação
        print("\n" + "-"*60)
        print("TESTE 1: Autenticação OAuth2")
        print("-"*60)
        
        token = await client._get_access_token()
        print(f"✅ Token obtido com sucesso!")
        print(f"   Token: {token[:20]}...")
        
        # TESTE 2: Criar pagamento PIX
        print("\n" + "-"*60)
        print("TESTE 2: Criar Pagamento PIX")
        print("-"*60)
        
        external_id = f"teste-pix-{uuid.uuid4()}"
        
        pix_result = await client.criar_pagamento_pix(
            amount=Decimal("10.50"),
            description="Teste de pagamento PIX",
            external_id=external_id,
            customer_name="Cliente Teste",
            customer_document="12345678900",
            customer_email="teste@email.com",
            expiration_minutes=15
        )
        
        print(f"✅ Pagamento PIX criado!")
        print(f"   Payment ID: {pix_result.get('id')}")
        print(f"   Status: {pix_result.get('status')}")
        print(f"   Valor: R$ 10,50")
        
        # Exibe dados do PIX
        pix_data = pix_result.get('pix', {})
        if pix_data:
            print(f"\n   📱 Dados do PIX:")
            print(f"   QR Code: {pix_data.get('qr_code', '')[:50]}...")
            if pix_data.get('qr_code_url'):
                print(f"   URL do QR Code: {pix_data.get('qr_code_url')}")
            if pix_data.get('copy_paste'):
                print(f"   Copia e Cola: {pix_data.get('copy_paste')[:50]}...")
        
        payment_id = pix_result.get('id')
        
        # TESTE 3: Consultar pagamento
        print("\n" + "-"*60)
        print("TESTE 3: Consultar Status do Pagamento")
        print("-"*60)
        
        await asyncio.sleep(2)  # Aguarda 2 segundos
        
        status_result = await client.consultar_pagamento(payment_id)
        print(f"✅ Status consultado!")
        print(f"   Payment ID: {status_result.get('id')}")
        print(f"   Status: {status_result.get('status')}")
        print(f"   Criado em: {status_result.get('created_at')}")
        
        # TESTE 4: Listar pagamentos
        print("\n" + "-"*60)
        print("TESTE 4: Listar Pagamentos")
        print("-"*60)
        
        payments = await client.listar_pagamentos(
            limit=5,
            status='pending'
        )
        
        print(f"✅ Listagem obtida!")
        print(f"   Total de pagamentos pendentes: {len(payments)}")
        
        if payments:
            print(f"\n   Últimos pagamentos:")
            for i, payment in enumerate(payments[:3], 1):
                print(f"   {i}. {payment.get('id')} - R$ {payment.get('amount', 0)/100:.2f} - {payment.get('status')}")
        
        # TESTE 5: Cancelar pagamento de teste
        print("\n" + "-"*60)
        print("TESTE 5: Cancelar Pagamento de Teste")
        print("-"*60)
        
        if payment_id and status_result.get('status') == 'pending':
            try:
                cancel_result = await client.cancelar_pagamento(
                    payment_id=payment_id,
                    reason="Teste automatizado"
                )
                print(f"✅ Pagamento cancelado!")
                print(f"   Payment ID: {payment_id}")
            except Exception as e:
                print(f"⚠️  Não foi possível cancelar: {str(e)}")
        else:
            print(f"⏭️  Pulando cancelamento (status: {status_result.get('status')})")
        
        # RESUMO FINAL
        print("\n" + "="*60)
        print("✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        print("="*60)
        print()
        print("Próximos passos:")
        print("1. Configure as credenciais no sistema via POST /api/stone/config")
        print("2. Configure webhook no dashboard Stone")
        print("3. Teste pagamentos reais no ambiente sandbox")
        print("4. Quando estiver pronto, mude para produção (sandbox=false)")
        print()
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {str(e)}")
        print()
        print("Possíveis causas:")
        print("- Credenciais inválidas")
        print("- Ambiente Stone fora do ar")
        print("- Configuração incorreta")
        print("- Sem acesso à internet")
        print()
        import traceback
        traceback.print_exc()


async def testar_cartao_sandbox():
    """Testa pagamento com cartão no sandbox"""
    
    print("\n" + "="*60)
    print("🧪 TESTE DE PAGAMENTO COM CARTÃO (SANDBOX)")
    print("="*60)
    print()
    
    # Configuração (mesma do teste anterior)
    CLIENT_ID = "seu_client_id_aqui"
    CLIENT_SECRET = "seu_client_secret_aqui"
    MERCHANT_ID = "seu_merchant_id_aqui"
    
    if CLIENT_ID == "seu_client_id_aqui":
        print("❌ Configure as credenciais primeiro!")
        return
    
    client = StoneAPIClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        merchant_id=MERCHANT_ID,
        sandbox=True
    )
    
    try:
        print("💳 Criando pagamento com cartão de teste...")
        
        # Cartão de teste da Stone (sempre aprovado no sandbox)
        result = await client.criar_pagamento_cartao(
            amount=Decimal("50.00"),
            description="Teste pagamento cartão",
            external_id=f"teste-cartao-{uuid.uuid4()}",
            card_number="4111111111111111",  # Visa de teste
            card_holder_name="CLIENTE TESTE",
            card_expiration_date="12/25",
            card_cvv="123",
            installments=2,
            customer_name="Cliente Teste",
            customer_document="12345678900",
            customer_email="teste@email.com"
        )
        
        print(f"✅ Pagamento processado!")
        print(f"   Payment ID: {result.get('id')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Valor: R$ 50,00")
        print(f"   Parcelas: 2x")
        
        card_data = result.get('card', {})
        if card_data:
            print(f"   Cartão: {card_data.get('brand')} **** {card_data.get('last_digits')}")
        
        fee = result.get('fee_amount', 0) / 100
        net = result.get('net_amount', 0) / 100
        print(f"   Taxa: R$ {fee:.2f}")
        print(f"   Líquido: R$ {net:.2f}")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")


def main():
    """Executa todos os testes"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         TESTE DE INTEGRAÇÃO STONE PAGAMENTOS               ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    print("Escolha o teste:")
    print("1. Teste completo (PIX + Consultas)")
    print("2. Teste de cartão (sandbox)")
    print("3. Ambos")
    print()
    
    opcao = input("Digite a opção (1, 2 ou 3) [1]: ").strip() or "1"
    
    print()
    
    if opcao in ["1", "3"]:
        asyncio.run(testar_conexao_stone())
    
    if opcao in ["2", "3"]:
        asyncio.run(testar_cartao_sandbox())
    
    print("\n✨ Testes finalizados!\n")


if __name__ == "__main__":
    main()
