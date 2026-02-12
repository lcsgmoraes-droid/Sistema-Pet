# API de Auditoria - Guia Rápido

## 🚀 Início Rápido

### 1. Executar Backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 2. Obter Token de Admin

```python
import requests

response = requests.post(
    "http://localhost:8000/auth/login",
    json={
        "username": "admin",
        "password": "sua_senha"
    }
)

token = response.json()["access_token"]
```

### 3. Consultar Replays

```python
headers = {"Authorization": f"Bearer {token}"}

# Listar todos os replays
response = requests.get(
    "http://localhost:8000/audit/replays",
    headers=headers
)

print(response.json())
```

## 📚 Documentação Completa

- **Fase 5.6**: [FASE5_6_AUDITORIA_EXPOSTA_IMPLEMENTADO.md](../FASE5_6_AUDITORIA_EXPOSTA_IMPLEMENTADO.md)
- **Fase 5 Completa**: [FASE5_COMPLETA.md](../FASE5_COMPLETA.md)
- **Exemplos de Uso**: [exemplo_uso_auditoria_api.py](../exemplo_uso_auditoria_api.py)

## 🧪 Executar Testes

```bash
# Todos os testes de auditoria
pytest tests/test_audit_api.py -v

# Com cobertura
pytest tests/test_audit_api.py --cov=app.audit --cov-report=html
```

## 📊 Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/audit/replays` | GET | Lista replays |
| `/audit/replays/{id}` | GET | Detalhes de replay |
| `/audit/rebuilds` | GET | Lista rebuilds |
| `/audit/rebuilds/{id}` | GET | Detalhes de rebuild |
| `/audit/summary` | GET | Resumo agregado (BI) |

**Autorização**: Todos os endpoints requerem permissão de administrador.

## 🎯 Casos de Uso

### BI/Analytics

```python
# Obter resumo mensal para dashboard
summary = requests.get(
    "http://localhost:8000/audit/summary?start_date=2025-01-01",
    headers=headers
).json()

print(f"Taxa de sucesso: {summary['successful_replays'] / summary['total_replays'] * 100:.1f}%")
```

### Troubleshooting

```python
# Buscar falhas recentes
failed = requests.get(
    "http://localhost:8000/audit/replays?status=failure",
    headers=headers
).json()

for replay in failed['items']:
    print(f"Erro: {replay['error']}")
```

### Governança

```python
# Listar operações dos últimos 30 dias
start_date = (datetime.now() - timedelta(days=30)).isoformat()

replays = requests.get(
    f"http://localhost:8000/audit/replays?start_date={start_date}",
    headers=headers
).json()

print(f"Replays nos últimos 30 dias: {replays['metadata']['total_items']}")
```

## ✅ Status

- ✅ Implementação completa
- ✅ 22/22 testes passando
- ✅ Documentação completa
- ✅ Exemplos práticos
- ✅ Integrado no main.py

## 📞 Suporte

Para dúvidas, consultar a documentação completa ou os testes de exemplo.
