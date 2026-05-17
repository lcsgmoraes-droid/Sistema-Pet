# Plano E2E minimo do Plano Basico

Data: 2026-05-17

Objetivo: transformar o E2E atual em uma trilha segura, curta e repetivel para
validar o Plano Basico sem depender de dados reais, conta pessoal ou ambiente de
producao.

## Escopo minimo

O E2E minimo deve validar uma jornada feliz e uma barreira de permissao:

1. Login com usuario descartavel.
2. Confirmacao do tenant ativo e modulos liberados para Plano Basico.
3. Criacao de cliente descartavel.
4. Criacao de produto descartavel com estoque inicial controlado.
5. Venda PDV simples com pagamento PIX ou dinheiro.
6. Confirmacao de efeitos colaterais essenciais:
   - venda finalizada;
   - pagamento registrado;
   - estoque baixado;
   - auditoria/request_id presente quando aplicavel.
7. Tentativa de acessar uma area fora do Plano Basico deve retornar bloqueio
   esperado.

## Dados descartaveis

Prefixo unico por execucao:

```text
E2E-PB-{YYYYMMDDHHMMSS}
```

Todos os registros criados devem carregar o prefixo no nome, codigo, observacao
ou metadata disponivel. Isso permite limpeza manual ou automatica sem risco de
apagar dado real.

Usuario recomendado para ambiente local/staging:

```text
e2e.plano.basico+{timestamp}@mlprohub.test
```

Senha deve vir de variavel de ambiente, nunca fixa em workflow publico.

## Suites

Suite rapida obrigatoria em PR:

- Import/config smoke.
- Auth basico.
- Health.
- Build frontend.
- Testes unitarios focados de regras criticas.

Suite E2E longa, inicialmente manual/agendada:

- Roda contra ambiente local ou staging descartavel.
- Nunca roda contra producao sem autorizacao explicita.
- Gera relatorio resumido com ids criados, tempo total e falhas.

## Variaveis esperadas

```text
E2E_BASE_URL
E2E_USER_EMAIL
E2E_USER_PASSWORD
E2E_TENANT_ID
```

Sem essas variaveis, a suite deve pular com mensagem clara, nao falhar de forma
ruidosa.

Variaveis opcionais:

```text
E2E_BLOCKED_PATH=/banho-tosa/configuracao
E2E_TIMEOUT_SECONDS=20
E2E_ALLOW_PRODUCTION=false
```

Contra `mlprohub.com.br`, a suite so roda quando `E2E_ALLOW_PRODUCTION=true`
estiver definido explicitamente.

## Criterio de aceite

- A suite nao usa clientes, produtos, vendas ou usuarios reais.
- Cada teste cria seus proprios dados ou valida que eles existem em fixture
  descartavel.
- Cada etapa tem assert de status HTTP e assert de efeito no dominio.
- Falha deve indicar o passo exato: auth, tenant, cliente, produto, venda,
  pagamento, estoque ou permissao.
- O workflow de CI separa suite rapida obrigatoria de suite E2E longa.

## Caminho de implementacao

1. Criar `backend/tests/test_plano_basico_e2e.py` lendo variaveis de ambiente e
   pulando quando ausentes.
2. Criar a primeira jornada minima com login, selecao de tenant, barreira de
   modulo, cliente, produto, estoque, venda e finalizacao.
3. Adicionar marcador `pytest.mark.e2e_long`.
4. Criar comando documentado para execucao local:

```powershell
$env:E2E_BASE_URL="http://localhost:8000"
$env:E2E_USER_EMAIL="e2e.plano.basico@mlprohub.test"
$env:E2E_USER_PASSWORD="<senha-local>"
$env:E2E_TENANT_ID="<tenant-local-ou-staging>"
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_plano_basico_e2e.py -m e2e_long -q
```

5. Depois de estabilizar local/staging, criar workflow agendado separado.

## Implementacao inicial

Status:

- Suite criada em `backend/tests/test_plano_basico_e2e.py`.
- Marcador `e2e_long` registrado em `backend/pytest.ini`.
- Sem `E2E_BASE_URL`, `E2E_USER_EMAIL`, `E2E_USER_PASSWORD` e
  `E2E_TENANT_ID`, a suite pula com mensagem clara.
- Contra `mlprohub.com.br`, a suite tambem exige `E2E_ALLOW_PRODUCTION=true`
  para evitar escrita acidental em producao.
