"""
Script simples: Troca código OAuth por access token
"""

import requests
import sys
from dotenv import load_dotenv, set_key
import os

load_dotenv()

def trocar_codigo(codigo):
    """Troca código por token"""
    
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    
    client_id = os.getenv("BLING_CLIENT_ID")
    client_secret = os.getenv("BLING_CLIENT_SECRET")
    
    payload = {
        "grant_type": "authorization_code",
        "code": codigo,
        "redirect_uri": "http://localhost:8000/auth/bling/callback"
    }
    
    # Bling exige Basic Auth
    from requests.auth import HTTPBasicAuth
    auth = HTTPBasicAuth(client_id, client_secret)
    
    print("🔄 Trocando código por token...")
    
    try:
        response = requests.post(url, json=payload, auth=auth)
        
        if response.status_code != 200:
            print(f"❌ Erro {response.status_code}")
            print(response.text)
            return False
        
        data = response.json()
        
        # Salvar tokens no .env
        env_path = ".env"
        set_key(env_path, "BLING_ACCESS_TOKEN", data["access_token"])
        set_key(env_path, "BLING_REFRESH_TOKEN", data["refresh_token"])
        
        print("\n✅ TOKENS OBTIDOS E SALVOS COM SUCESSO!")
        print(f"\n🔑 Access Token: {data['access_token'][:50]}...")
        print(f"🔄 Refresh Token: {data['refresh_token'][:50]}...")
        print(f"⏰ Expira em: {data['expires_in'] // 3600} horas")
        
        print("\n🎉 Configuração concluída!")
        print("   Agora você pode emitir NF-e e NFC-e!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso: python trocar_codigo_token.py SEU_CODIGO_AQUI")
        sys.exit(1)
    
    codigo = sys.argv[1]
    trocar_codigo(codigo)
