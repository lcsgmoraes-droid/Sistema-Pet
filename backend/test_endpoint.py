#!/usr/bin/env python
"""Test the GET /projecoes endpoint"""

import requests
import json

try:
    # Login
    auth_resp = requests.post('http://localhost:8000/auth/login', 
        json={'email': 'admin@test.com', 'password': 'teste123'})
    print(f'Login status: {auth_resp.status_code}')
    
    if auth_resp.status_code != 200:
        print(f'Login failed: {auth_resp.text}')
        exit(1)
    
    token = auth_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test GET projecoes
    resp = requests.get('http://localhost:8000/api/ia/fluxo/projecoes/1?dias=15', 
        headers=headers)
    print(f'\nGET /projecoes status: {resp.status_code}')
    
    if resp.status_code == 200:
        data = resp.json()
        print(f'✅ Projecoes carregadas: {len(data)} registros')
        if data:
            first = data[0]
            print(f'\n✅ Primeira projeção:')
            print(json.dumps(first, indent=2, ensure_ascii=False))
            print(f'\n✅ Campos disponíveis: {list(first.keys())}')
    else:
        print(f'❌ Erro: {resp.status_code}')
        print(resp.text[:500])
        
except Exception as e:
    print(f'❌ Exception: {str(e)}')
    import traceback
    traceback.print_exc()
