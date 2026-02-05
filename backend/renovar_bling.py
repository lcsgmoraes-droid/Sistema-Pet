import requests
import base64
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

client_id = '3e0a1e84306203b3119c9410f73ca4fe4aa9fbea'
client_secret = 'ad8a54353648c3402bd4a069bcc90dade61d9b4db7e9337dde7421bcf3a1'
redirect_uri = 'http://localhost:8000/auth/bling/callback'

# Abrir navegador
url = 'https://www.bling.com.br/Api/v3/oauth/authorize?' + urlencode({
    'response_type': 'code',
    'client_id': client_id,
    'redirect_uri': redirect_uri,
    'state': 'petshop'
})

print('\n' + '='*70)
print('  RENOVAÇÃO DE TOKENS BLING')
print('='*70)
print('\nAbrindo navegador...')
webbrowser.open(url)

# Pedir código imediatamente
code = input('\n⚡ COLE O CÓDIGO AGORA (RÁPIDO!): ').strip()

# Limpar código se vier com parâmetros
if 'code=' in code:
    code = code.split('code=')[1].split('&')[0]

print('\nTrocando código por tokens...')

# Basic Auth
credentials = f'{client_id}:{client_secret}'
encoded = base64.b64encode(credentials.encode()).decode()

headers = {
    'Authorization': f'Basic {encoded}',
    'Content-Type': 'application/x-www-form-urlencoded'
}

data = {
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': redirect_uri
}

r = requests.post('https://www.bling.com.br/Api/v3/oauth/token', headers=headers, data=data)

if r.status_code == 200:
    tokens = r.json()
    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']
    
    print('\n✓ Tokens obtidos com sucesso!')
    print(f'  Access: {access_token[:50]}...')
    print(f'  Refresh: {refresh_token[:50]}...')
    
    # Atualizar .env
    env_path = Path('.env')
    lines = []
    
    for line in env_path.read_text(encoding='utf-8').split('\n'):
        if line.startswith('BLING_ACCESS_TOKEN='):
            lines.append(f'BLING_ACCESS_TOKEN={access_token}')
        elif line.startswith('BLING_REFRESH_TOKEN='):
            lines.append(f'BLING_REFRESH_TOKEN={refresh_token}')
        else:
            lines.append(line)
    
    env_path.write_text('\n'.join(lines), encoding='utf-8')
    
    print('\n✓ Arquivo .env atualizado!')
    
    # Testar conexão
    print('\nTestando conexão com Bling...')
    test_response = requests.get(
        'https://www.bling.com.br/Api/v3/nfe',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    if test_response.status_code in [200, 404]:
        print('✓ CONEXÃO FUNCIONANDO!')
        print('\n' + '='*70)
        print('  🎉 SISTEMA PRONTO PARA EMITIR NF-e/NFC-e!')
        print('='*70)
        print('\nPróximos passos:')
        print('1. Reinicie o backend (Ctrl+C e execute INICIAR_BACKEND.bat)')
        print('2. Faça uma venda de teste')
        print('3. Emita sua primeira nota fiscal!')
    else:
        print(f'⚠ Status inesperado: {test_response.status_code}')
        print(f'Resposta: {test_response.text}')
else:
    print(f'\n❌ Erro {r.status_code}')
    print(f'Detalhes: {r.text}')
    print('\nDica: O código expira em segundos. Rode o script novamente e cole mais rápido!')
