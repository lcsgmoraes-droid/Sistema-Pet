#!/usr/bin/env python
"""Test alertas endpoint"""

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
    
    # Test GET /alertas
    resp = requests.get('http://localhost:8000/api/ia/fluxo/alertas/1', headers=headers)
    
    print(f'GET /alertas status: {resp.status_code}')
    print(f'Response body:')
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    
except Exception as e:
    print(f'❌ Exception: {str(e)}')
    import traceback
    traceback.print_exc()
