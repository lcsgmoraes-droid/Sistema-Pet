"""
Script para renovar tokens do Bling quando o refresh_token expira
Requer autorização manual via navegador
"""
import requests
import base64
import json
from pathlib import Path

# Suas credenciais (do .env)
CLIENT_ID = "3e0a1e84306203b3119c9410f73ca4fe4aa9fbea"
CLIENT_SECRET = "ad8a54353648c3402bd4a069bcc90dade61d9b4db7e9337dde7421bcf3a1"
REDIRECT_URI = "http://localhost:8000/auth/bling/callback"

print("=" * 60)
print(" 🔄 RENOVAÇÃO DE TOKENS DO BLING")
print("=" * 60)
print()
print("📋 PASSO 1: Autorize no navegador")
print()
print("Cole esta URL no navegador:")
print()
print(f"https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}")
print()
print("-" * 60)
print()

# Solicitar o código
codigo = input("📝 PASSO 2: Cole aqui o CODE da URL de retorno: ").strip()

if not codigo:
    print("❌ Código não fornecido. Encerrando.")
    exit(1)

print()
print("⏳ Trocando código por tokens...")
print()

# Preparar autenticação Basic
credentials = f'{CLIENT_ID}:{CLIENT_SECRET}'
encoded = base64.b64encode(credentials.encode()).decode()

# Trocar código por tokens
headers = {
    'Authorization': f'Basic {encoded}',
    'Content-Type': 'application/x-www-form-urlencoded'
}

data = {
    'grant_type': 'authorization_code',
    'code': codigo,
    'redirect_uri': REDIRECT_URI
}

try:
    response = requests.post(
        'https://www.bling.com.br/Api/v3/oauth/token',
        headers=headers,
        data=data
    )
    
    if response.status_code == 200:
        tokens = response.json()
        
        print("✅ Tokens obtidos com sucesso!")
        print()
        print("📦 NOVOS TOKENS:")
        print("-" * 60)
        print(f"ACCESS_TOKEN: {tokens['access_token']}")
        print(f"REFRESH_TOKEN: {tokens['refresh_token']}")
        print(f"EXPIRA EM: {tokens['expires_in']} segundos ({tokens['expires_in']/3600:.1f} horas)")
        print("-" * 60)
        print()
        
        # Atualizar .env
        env_path = Path(__file__).parent.parent / '.env'
        
        if env_path.exists():
            print("📝 Atualizando arquivo .env...")
            
            lines = []
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('BLING_ACCESS_TOKEN='):
                        lines.append(f'BLING_ACCESS_TOKEN={tokens["access_token"]}\n')
                    elif line.startswith('BLING_REFRESH_TOKEN='):
                        lines.append(f'BLING_REFRESH_TOKEN={tokens["refresh_token"]}\n')
                    else:
                        lines.append(line)
            
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print("✅ Arquivo .env atualizado com sucesso!")
            print()
            print("🎉 CONCLUÍDO! Seus tokens foram renovados.")
            print("💡 O sistema agora pode emitir notas fiscais novamente.")
            
            # Remover arquivo de controle antigo
            control_file = Path(__file__).parent.parent / 'bling_token_control.json'
            if control_file.exists():
                control_file.unlink()
                print("🗑️ Arquivo de controle antigo removido.")
            
        else:
            print("⚠️ Arquivo .env não encontrado.")
            print("📋 Atualize manualmente com os tokens acima.")
        
    else:
        print(f"❌ Erro ao obter tokens: {response.status_code}")
        print(f"Resposta: {response.text}")
        
except Exception as e:
    print(f"❌ Erro na requisição: {e}")

print()
print("=" * 60)
