"""
Script para testar e configurar o vínculo com a API da Stone
"""
import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório backend ao path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Carrega variáveis de ambiente
from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

from app.stone_api_client import StoneAPIClient


async def testar_conexao_stone():
    """Testa a conexão com a API da Stone"""
    
    # Obtém credenciais do .env
    client_id = os.getenv("STONE_CLIENT_ID")
    client_secret = os.getenv("STONE_CLIENT_SECRET")
    merchant_id = os.getenv("STONE_MERCHANT_ID")
    sandbox = os.getenv("STONE_SANDBOX", "true").lower() == "true"
    
    print("=" * 60)
    print("🔗 TESTE DE CONEXÃO - API STONE")
    print("=" * 60)
    print(f"\n📋 Configurações:")
    print(f"   Client ID: {client_id[:20]}..." if client_id else "   Client ID: NÃO CONFIGURADO")
    print(f"   Merchant ID: {merchant_id}")
    print(f"   Ambiente: {'SANDBOX (Testes)' if sandbox else 'PRODUÇÃO'}")
    print()
    
    if not client_id or not client_secret or not merchant_id:
        print("❌ ERRO: Credenciais da Stone não configuradas no .env")
        print("\nConfigure as seguintes variáveis no arquivo backend/.env:")
        print("   STONE_CLIENT_ID=seu_client_id")
        print("   STONE_CLIENT_SECRET=seu_client_secret")
        print("   STONE_MERCHANT_ID=seu_merchant_id")
        print("   STONE_SANDBOX=true")
        return False
    
    try:
        # Inicializa cliente Stone
        print("🔄 Inicializando cliente Stone...")
        stone = StoneAPIClient(
            client_id=client_id,
            client_secret=client_secret,
            merchant_id=merchant_id,
            sandbox=sandbox
        )
        
        # Testa autenticação
        print("🔐 Testando autenticação OAuth2...")
        token = await stone._get_access_token()
        
        if token:
            print("✅ AUTENTICAÇÃO REALIZADA COM SUCESSO!")
            print(f"   Token obtido: {token[:30]}...")
            print(f"   Expira em: {stone.token_expires_at}")
            print()
            
            # Testa endpoint de status/health
            print("🔄 Testando conectividade com a API...")
            try:
                # Tenta listar estabelecimentos (merchants)
                resultado = await stone._make_request("GET", f"/v1/merchants/{merchant_id}")
                print("✅ CONEXÃO COM API ESTABELECIDA!")
                print(f"   Merchant: {resultado.get('name', 'N/A')}")
                print(f"   Status: {resultado.get('status', 'N/A')}")
            except Exception as e:
                # Se o merchant específico não existir, ainda é um sucesso de autenticação
                if "404" in str(e) or "not found" in str(e).lower():
                    print("⚠️  Merchant ID não encontrado, mas autenticação funcionou!")
                    print("   Verifique se o STONE_MERCHANT_ID está correto.")
                else:
                    print(f"⚠️  Aviso ao testar endpoint: {str(e)}")
                    print("   A autenticação funcionou, mas houve um problema ao acessar dados.")
            
            print()
            print("=" * 60)
            print("✅ VÍNCULO COM API STONE CONFIGURADO COM SUCESSO!")
            print("=" * 60)
            print("\n📌 Próximos passos:")
            print("   1. O sistema já está pronto para processar pagamentos")
            print("   2. Configure webhooks para receber notificações automáticas")
            print("   3. Em produção, altere STONE_SANDBOX=false no .env")
            print(f"\n🔗 Acesse a dashboard Stone: https://{'sandbox-' if sandbox else ''}conta.stone.com.br/")
            print()
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERRO AO CONECTAR COM API STONE:")
        print(f"   {str(e)}")
        print("\n🔍 Possíveis causas:")
        print("   1. Credenciais inválidas (verifique CLIENT_ID e CLIENT_SECRET)")
        print("   2. Ambiente incorreto (sandbox vs produção)")
        print("   3. Aplicação não autorizada na Stone")
        print("   4. Problemas de rede/conectividade")
        print("\n💡 Dica: Verifique suas credenciais em:")
        print(f"   https://{'sandbox-' if sandbox else ''}conta.stone.com.br/")
        print()
        return False


async def configurar_webhook():
    """Configura webhook para receber notificações da Stone"""
    print("\n" + "=" * 60)
    print("🔔 CONFIGURAÇÃO DE WEBHOOK")
    print("=" * 60)
    print("\nPara receber notificações automáticas de pagamentos:")
    print("1. Acesse: https://conta.stone.com.br/ (ou sandbox)")
    print("2. Vá em 'Configurações' > 'Webhooks'")
    print("3. Configure a URL do webhook:")
    print(f"   https://seu-dominio.com.br/api/stone/webhook")
    print("4. Selecione os eventos que deseja receber")
    print("5. Salve o secret gerado no .env: STONE_WEBHOOK_SECRET=...")
    print()


if __name__ == "__main__":
    print("\n")
    resultado = asyncio.run(testar_conexao_stone())
    
    if resultado:
        asyncio.run(configurar_webhook())
    
    print()
