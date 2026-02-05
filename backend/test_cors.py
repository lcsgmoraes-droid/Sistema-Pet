#!/usr/bin/env python
"""Test CORS headers"""

import requests

try:
    # Test CORS preflight (OPTIONS)
    resp = requests.options('http://localhost:8000/api/ia/fluxo/projecoes/1',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'authorization'
        })
    
    print(f'OPTIONS request status: {resp.status_code}')
    print(f'Access-Control-Allow-Origin: {resp.headers.get("access-control-allow-origin", "NOT FOUND")}')
    print(f'Access-Control-Allow-Credentials: {resp.headers.get("access-control-allow-credentials", "NOT FOUND")}')
    print(f'Access-Control-Allow-Methods: {resp.headers.get("access-control-allow-methods", "NOT FOUND")}')
    print(f'Access-Control-Allow-Headers: {resp.headers.get("access-control-allow-headers", "NOT FOUND")}')
    
    if resp.status_code == 200 and resp.headers.get('access-control-allow-origin'):
        print('\n✅ CORS configuration looks good!')
    else:
        print('\n⚠️ CORS might not be properly configured')
        
except Exception as e:
    print(f'❌ Exception: {str(e)}')
