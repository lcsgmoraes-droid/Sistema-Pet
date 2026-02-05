"""
Script para configurar OAuth2 do Bling API v3
Execute este script para obter e configurar os tokens de acesso
"""

import requests
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
import secrets
import hashlib
import base64
import os
from pathlib import Path

# Cores para terminal
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
END = '\033[0m'

REDIRECT_URI = "http://localhost:8000/callback"

def gerar_code_verifier():
    """Gera code verifier para PKCE"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def gerar_code_challenge(verifier):
    """Gera code challenge a partir do verifier"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

def main():
    print(f"\n{BLUE}{'='*70}")
    print("   CONFIGURAÇÃO BLING API - OAUTH2")
    print(f"{'='*70}{END}\n")
    
    # Passo 1: Obter credenciais
    print(f"{YELLOW}PASSO 1: Criar aplicação no Bling{END}")
    print("\n1. Acesse: https://developer.bling.com.br/")
    print("2. Faça login com sua conta Bling")
    print("3. Vá em 'Minhas Aplicações' > 'Criar Aplicação'")
    print("4. Preencha:")
    print("   - Nome: Sistema Pet Shop")
    print(f"   - Redirect URI: {REDIRECT_URI}")
    print("   - Escopos necessários:")
    print("     ✓ NFe.Create (emitir notas)")
    print("     ✓ NFe.Read (consultar notas)")
    print("     ✓ NFe.Update (cancelar notas)")
    print("\n5. Após criar, copie o CLIENT_ID e CLIENT_SECRET\n")
    
    client_id = input(f"{GREEN}Cole o CLIENT_ID: {END}").strip()
    client_secret = input(f"{GREEN}Cole o CLIENT_SECRET: {END}").strip()
    
    if not client_id or not client_secret:
        print(f"{RED}❌ Erro: CLIENT_ID e CLIENT_SECRET são obrigatórios!{END}")
        return
    
    # Passo 2: Autorização
    print(f"\n{YELLOW}PASSO 2: Autorizar aplicação{END}\n")
    
    # Gerar PKCE
    code_verifier = gerar_code_verifier()
    code_challenge = gerar_code_challenge(code_verifier)
    
    # URL de autorização
    auth_params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'state': secrets.token_urlsafe(16),
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    
    auth_url = f"https://www.bling.com.br/Api/v3/oauth/authorize?{urlencode(auth_params)}"
    
    print("🌐 Abrindo navegador para autorização...")
    print(f"\n{CYAN}URL:{END} {auth_url}\n")
    
    try:
        webbrowser.open(auth_url)
    except:
        print(f"{YELLOW}⚠ Não foi possível abrir automaticamente.{END}")
        print(f"Copie e cole esta URL no navegador:\n{auth_url}\n")
    
    print(f"{YELLOW}➤ Após autorizar, você será redirecionado para:{END}")
    print(f"{REDIRECT_URI}?code=CODIGO_AQUI")
    print(f"\n{CYAN}O navegador vai dar erro 'página não encontrada' - ISSO É NORMAL!{END}")
    print(f"{GREEN}Copie apenas o CÓDIGO da URL (tudo depois de 'code=' e antes de '&'){END}\n")
    
    authorization_code = input(f"{GREEN}Cole o código de autorização: {END}").strip()
    
    # Limpar código se vier com URL inteira
    if 'code=' in authorization_code:
        authorization_code = authorization_code.split('code=')[1].split('&')[0]
    
    if not authorization_code:
        print(f"{RED}❌ Erro: Código de autorização é obrigatório!{END}")
        return
    
    # Passo 3: Trocar código por tokens
    print(f"\n{YELLOW}PASSO 3: Obtendo tokens de acesso...{END}\n")
    
    token_url = "https://www.bling.com.br/Api/v3/oauth/token"
    token_data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': code_verifier,
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    try:
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()
        tokens = response.json()
        
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        expires_in = tokens.get('expires_in', 3600)
        
        print(f"{GREEN}✓ Tokens obtidos com sucesso!{END}")
        print(f"{CYAN}  Expira em: {expires_in // 3600} horas{END}\n")
        
        # Passo 4: Testar conexão
        print(f"{YELLOW}PASSO 4: Testando conexão com Bling...{END}\n")
        
        test_url = "https://www.bling.com.br/Api/v3/nfe"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        test_response = requests.get(test_url, headers=headers)
        
        if test_response.status_code in [200, 404]:  # 404 é OK (sem notas ainda)
            print(f"{GREEN}✓ Conexão com Bling funcionando!{END}\n")
        else:
            print(f"{YELLOW}⚠ Resposta inesperada: {test_response.status_code}{END}")
            print(f"Mas os tokens foram obtidos. Vamos continuar.\n")
        
        # Passo 5: Salvar no .env
        print(f"{YELLOW}PASSO 5: Configurando arquivo .env{END}\n")
        
        env_vars = {
            'BLING_CLIENT_ID': client_id,
            'BLING_CLIENT_SECRET': client_secret,
            'BLING_ACCESS_TOKEN': access_token,
            'BLING_REFRESH_TOKEN': refresh_token
        }
        
        # Caminho do .env (mesmo diretório do script)
        env_path = Path(__file__).parent / '.env'
        
        # Ler .env existente ou criar novo
        env_content = {}
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Atualizar com novas variáveis do Bling
        env_content.update(env_vars)
        
        # Escrever de volta
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        
        print(f"{GREEN}✓ Arquivo .env atualizado em: {env_path}{END}\n")
        
        # Resumo final
        print(f"{BLUE}{'='*70}")
        print("   ✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"{'='*70}{END}\n")
        
        print(f"{GREEN}Variáveis configuradas:{END}")
        print(f"  ✓ BLING_CLIENT_ID")
        print(f"  ✓ BLING_CLIENT_SECRET")
        print(f"  ✓ BLING_ACCESS_TOKEN (válido por ~6 horas)")
        print(f"  ✓ BLING_REFRESH_TOKEN (renova automaticamente)\n")
        
        print(f"{YELLOW}📋 Próximos passos:{END}")
        print(f"  1. {CYAN}Reinicie o backend{END} para carregar as novas variáveis")
        print(f"     > Feche o terminal do backend (Ctrl+C)")
        print(f"     > Execute novamente: INICIAR_BACKEND.bat")
        print(f"  2. {CYAN}Teste a conexão{END} (opcional):")
        print(f"     > Abra: http://localhost:8000/nfe/config/testar-conexao")
        print(f"  3. {CYAN}Faça uma venda de teste{END} e emita sua primeira NFC-e!\n")
        
        print(f"{RED}⚠ IMPORTANTE:{END}")
        print(f"  • O token expira em ~6 horas")
        print(f"  • O sistema renova automaticamente usando o refresh_token")
        print(f"  • Não compartilhe o arquivo .env com ninguém")
        print(f"  • Guarde backup do refresh_token em local seguro\n")
        
        print(f"{GREEN}🎉 Tudo pronto! Seu sistema já pode emitir NF-e/NFC-e!{END}\n")
        
    except requests.exceptions.RequestException as e:
        print(f"{RED}❌ Erro ao obter tokens:{END}")
        print(f"{RED}{str(e)}{END}\n")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"{RED}Detalhes do erro:{END}")
                print(f"{RED}{error_data}{END}\n")
            except:
                print(f"{RED}Resposta da API:{END}")
                print(f"{RED}{e.response.text}{END}\n")
        
        print(f"{YELLOW}💡 Verifique se:{END}")
        print("  • CLIENT_ID e CLIENT_SECRET estão corretos")
        print("  • O código não expirou (válido por ~10 minutos)")
        print(f"  • A Redirect URI está configurada como: {REDIRECT_URI}")
        print("  • Você autorizou os escopos corretos (NFe.Create, NFe.Read, NFe.Update)\n")
        return

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠ Configuração cancelada pelo usuário.{END}\n")
    except Exception as e:
        print(f"\n{RED}❌ Erro inesperado: {str(e)}{END}\n")
        import traceback
        traceback.print_exc()

    main()
