#!/usr/bin/env python
"""Test the POST /simular-cenario endpoint"""

import requests
import json

try:
    # Login
    auth_resp = requests.post('http://localhost:8000/auth/login', 
        json={'email': 'admin@test.com', 'password': 'teste123'})
    
    if auth_resp.status_code != 200:
        print(f'Login failed: {auth_resp.text}')
        exit(1)
    
    token = auth_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test POST /simular-cenario
    for cenario in ['otimista', 'pessimista', 'realista']:
        resp = requests.post('http://localhost:8000/api/ia/fluxo/simular-cenario/1', 
            headers=headers,
            json={'cenario': cenario})
        
        print(f'\nPOST /simular-cenario ({cenario}):')
        print(f'Status: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'✅ Cenário simulado!')
            print(f'   Projeções ajustadas: {len(data.get("projecoes_ajustadas", []))} registros')
            if data.get('projecoes_ajustadas'):
                print(f'   Primeira: {json.dumps(data["projecoes_ajustadas"][0], indent=4, ensure_ascii=False)}')
        else:
            print(f'❌ Erro: {resp.status_code}')
            print(resp.text[:200])
        
except Exception as e:
    print(f'❌ Exception: {str(e)}')
    import traceback
    traceback.print_exc()
