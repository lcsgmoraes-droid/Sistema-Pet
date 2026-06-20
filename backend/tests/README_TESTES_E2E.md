# Testes E2E

O E2E oficial mantido hoje e o Plano Basico:

```powershell
cd backend
python -m pytest tests/test_plano_basico_e2e.py -m e2e_long -q
```

Ele roda somente quando as variaveis `E2E_*` estao configuradas. Contra
producao, tambem exige `E2E_ALLOW_PRODUCTION=true`.

O workflow correspondente fica em `.github/workflows/e2e-long.yml` e e separado
dos checks obrigatorios de PR para nao deixar cada mudanca lenta.
