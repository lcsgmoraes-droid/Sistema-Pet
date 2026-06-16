"""
🔐 Script para configurar OAuth2 do Bling
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv, set_key
import requests
import webbrowser

# Carregar variáveis
load_dotenv()

CLIENT_ID = os.getenv("BLING_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLING_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/auth/bling/callback"


def main():
    print("\n" + "=" * 60)
    print("🔐 CONFIGURAÇÃO OAUTH2 - BLING API")
    print("=" * 60 + "\n")

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ ERRO: CLIENT_ID ou CLIENT_SECRET não configurados no .env")
        return

    print("✅ Credenciais encontradas:")
    print(f"   Client ID: {CLIENT_ID}")
    print(f"   Client Secret: {CLIENT_SECRET[:10]}...")
    print()

    # Passo 1: URL de autorização
    auth_url = (
        f"https://www.bling.com.br/Api/v3/oauth/authorize?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}"
    )

    print("📋 PASSO 1: Autorizar aplicativo")
    print("-" * 60)
    print("Vou abrir a URL de autorização no navegador.")
    print("Após autorizar, copie o código que aparece na URL.\n")

    input("Pressione ENTER para abrir o navegador...")
    webbrowser.open(auth_url)

    print("\n⚠️  Se o navegador não abrir, acesse manualmente:")
    print(f"\n{auth_url}\n")

    # Passo 2: Obter código
    print("\n📋 PASSO 2: Código de autorização")
    print("-" * 60)
    print("Após autorizar, você será redirecionado para:")
    print(f"{REDIRECT_URI}?code=CODIGO_AQUI")
    print()

    code = input("Cole o código aqui: ").strip()

    if not code:
        print("❌ Código não fornecido. Abortando.")
        return

    # Passo 3: Trocar código por tokens
    print("\n📋 PASSO 3: Obtendo tokens...")
    print("-" * 60)

    token_url = "https://www.bling.com.br/Api/v3/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = requests.post(token_url, json=payload)
        response.raise_for_status()
        data = response.json()

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")

        if not access_token or not refresh_token:
            print("❌ ERRO: Resposta inválida da API Bling")
            print(f"Response: {data}")
            return

        # Salvar no .env
        env_path = Path(__file__).parent.parent / ".env"
        set_key(env_path, "BLING_ACCESS_TOKEN", access_token)
        set_key(env_path, "BLING_REFRESH_TOKEN", refresh_token)

        print("✅ TOKENS OBTIDOS COM SUCESSO!")
        print(f"   Access Token: {access_token[:50]}...")
        print(f"   Refresh Token: {refresh_token[:50]}...")
        print(f"   Expira em: {expires_in} segundos (~{expires_in // 3600} horas)")
        print()
        print("✅ Tokens salvos no arquivo .env")
        print()
        print("🎉 CONFIGURAÇÃO CONCLUÍDA!")
        print()
        print("Próximos passos:")
        print("1. Reinicie o backend (se estiver rodando)")
        print("2. Teste a conexão: GET /nfe/config/testar-conexao")
        print("3. Emita sua primeira nota!")

    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO ao obter tokens: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")


if __name__ == "__main__":
    main()
