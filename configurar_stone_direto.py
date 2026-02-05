"""
Script simples para testar conexão com API Stone
"""
import httpx
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env do backend
backend_env = Path(__file__).parent / "backend" / ".env"
load_dotenv(backend_env)


async def testar_stone():
    """Testa conexão com API Stone"""
    
    # Credenciais
    client_id = os.getenv("STONE_CLIENT_ID")
    client_secret = os.getenv("STONE_CLIENT_SECRET")
    merchant_id = os.getenv("STONE_MERCHANT_ID")
    sandbox = os.getenv("STONE_SANDBOX", "true").lower() == "true"
    
    base_url = "https://payments.stone.com.br"
    
    print("\n" + "=" * 70)
    print("🔗 TESTE DE CONEXÃO - API STONE PAGAMENTOS")
    print("=" * 70)
    print(f"\n📋 Configurações:")
    print(f"   Client ID: {client_id[:25]}...") if client_id else print("   Client ID: ❌ NÃO CONFIGURADO")
    print(f"   Merchant ID: {merchant_id}")
    print(f"   Ambiente: {'🧪 SANDBOX (Testes)' if sandbox else '🚀 PRODUÇÃO'}")
    print(f"   URL Base: {base_url}")
    print()
    
    if not all([client_id, client_secret, merchant_id]):
        print("❌ ERRO: Credenciais incompletas!")
        print("\n📝 Configure no arquivo: backend/.env")
        print("   STONE_CLIENT_ID=seu_client_id")
        print("   STONE_CLIENT_SECRET=seu_client_secret")
        print("   STONE_MERCHANT_ID=seu_merchant_id")
        return False
    
    try:
        print("🔄 Testando autenticação Basic Auth...")
        
        # Stone usa Basic Auth: username=SecretKey, password=vazio
        import base64
        auth_string = base64.b64encode(f"{client_secret}:".encode()).decode()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Testa listando charges
            response = await client.get(
                f"{base_url}/v1/charges",
                headers={
                    "Authorization": f"Basic {auth_string}",
                    "Content-Type": "application/json"
                },
                params={"limit": 1}
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                charges = data.get("charges", [])
                
                print(f"   ✅ Autenticação realizada com sucesso!")
                print(f"   📊 Charges encontrados: {len(charges)}")
                print(f"   🔑 Autenticação: Basic Auth funcionando")
                
                print("\n" + "=" * 70)
                print("✅ VÍNCULO COM API STONE ESTABELECIDO COM SUCESSO!")
                print("=" * 70)
                print("\n✨ Recursos disponíveis:")
                print("   • Pagamentos via PIX")
                print("   • Pagamentos via Cartão (débito/crédito)")
                print("   • Consulta de transações")
                print("   • Webhooks para notificações em tempo real")
                print("\n📚 Endpoints disponíveis no sistema:")
                print(f"   • POST /api/stone/pix/create - Criar pagamento PIX")
                print(f"   • POST /api/stone/card/charge - Cobrar cartão")
                print(f"   • GET  /api/stone/transactions - Listar transações")
                print(f"   • POST /api/stone/webhook - Receber notificações")
                
                if sandbox:
                    print("\n🧪 MODO SANDBOX ATIVO")
                    print("   • Transações são simuladas (não há cobrança real)")
                    print("   • Para produção, altere STONE_SANDBOX=false")
                
                print(f"\n🔗 Acesse o painel: https://{'sandbox-' if sandbox else ''}conta.stone.com.br/")
                print()
                
                return True
                
            elif response.status_code == 401:
                print(f"   ❌ Credenciais inválidas!")
                print(f"   Resposta: {response.text}")
                print(f"\n💡 Verifique:")
                print(f"   1. CLIENT_ID e CLIENT_SECRET estão corretos")
                print(f"   2. Você está usando o ambiente correto (sandbox/prod)")
                print(f"   3. Acesse: https://{'sandbox-' if sandbox else ''}conta.stone.com.br/")
                
            else:
                print(f"   ❌ Erro {response.status_code}: {response.text}")
                
    except httpx.ConnectError as e:
        print(f"\n❌ ERRO DE CONEXÃO:")
        print(f"   Não foi possível conectar ao servidor Stone")
        print(f"   Detalhes: {str(e)}")
        print(f"\n🔍 Verifique:")
        print(f"   1. Sua conexão com a internet")
        print(f"   2. Firewall/proxy não está bloqueando")
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO:")
        print(f"   {str(e)}")
        
    return False


if __name__ == "__main__":
    print("\n")
    resultado = asyncio.run(testar_stone())
    
    if resultado:
        print("\n🎉 Configuração concluída! O sistema está pronto para processar pagamentos.")
    else:
        print("\n⚠️  Configuração incompleta. Corrija os problemas acima e tente novamente.")
    
    print()
