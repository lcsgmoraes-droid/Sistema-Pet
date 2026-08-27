# Teste de capacidade seguro

Atualizado em: 2026-08-27

## Objetivo

Medir uma linha de base de disponibilidade e latencia sem criar, editar ou apagar
dados. O teste usa apenas `GET` em endpoints de saude permitidos e, por padrao,
aceita somente `localhost`.

Existem dois níveis complementares:

1. `capacity_smoke.py` mede apenas health público;
2. `capacity_authenticated.py` autentica, seleciona um tenant fictício e mede
   consultas reais de sessão, clientes, produtos e vendas em homologação.

Nenhum dos dois, isoladamente, representa dimensionamento definitivo. Eles
detectam regressões, geram uma referência repetível e mostram onde aprofundar a
medição.

## Smoke público local

Com o backend local ativo:

```powershell
python scripts/capacity_smoke.py --base-url http://localhost:8000 --path /health --requests 100 --concurrency 10
```

Saida registrada:

- respostas aprovadas e falhas;
- percentual de sucesso;
- requisicoes por segundo;
- latencias minima, p50, p95, p99 e maxima;
- resultado final conforme os criterios informados.

### Critério inicial do smoke

Para o smoke local de linha de base:

- pelo menos 99% de respostas aprovadas;
- latencia p95 de no maximo 500 ms;
- nenhuma escrita ou dado real envolvido.

Os limites podem ser ajustados pelos argumentos `--min-success-rate` e
`--max-p95-ms`, mas o resultado deve registrar os valores usados.

### Proteções do smoke

- concorrencia maxima: 50;
- requisicoes maximas por execucao: 5.000;
- somente `/health`, `/api/health` e `/health/watchdog`;
- alvo remoto exige HTTPS;
- qualquer alvo fora de localhost e bloqueado sem `--allow-production`;
- `--allow-production` nao representa autorizacao: antes de usar contra producao,
  Lucas precisa autorizar explicitamente a execucao e a quantidade/concurrencia.

### Produção

Nao executar em producao como rotina automatica. Quando houver autorizacao, comecar
com uma janela pequena e observar `/ops` durante o teste. Exemplo conservador:

```powershell
python scripts/capacity_smoke.py --base-url https://corepet.com.br --path /api/health --requests 50 --concurrency 5 --allow-production
```

O smoke público não autoriza carga autenticada em produção.

### Linha de base pública local

Execucao em 2026-07-13, backend local, `GET /health`:

| Requisicoes | Concorrencia | Sucesso | Req/s | p50 | p95 | p99 | Maxima |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 10 | 100% | 442,30 | 15,15 ms | 49,94 ms | 78,08 ms | 96,35 ms |

Resultado: aprovado no criterio inicial. Esta medicao prova o funcionamento do
executor e cria uma referencia local; nao representa a capacidade definitiva do
servidor DigitalOcean nem de jornadas autenticadas com banco.

## Capacidade autenticada em homologação

Pré-condições:

1. Docker Desktop saudável;
2. homologação preparada e ativa;
3. tenant e usuário fictícios validados pelo E2E oficial.

Execução padrão:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao capacidade -Requisicoes 320 -Concorrencia 8
```

O wrapper injeta credenciais somente no processo filho. Senha e token não são
argumentos, não aparecem no JSON e não entram no Git.

### Consultas fixas

| Jornada técnica | Método e rota | Tipo |
|---|---|---|
| Sessão e tenant | `GET /auth/me-multitenant` | Leitura |
| Clientes | `GET /clientes/?skip=0&limit=20` | Leitura paginada |
| Produtos | `GET /produtos/?page=1&page_size=20` | Leitura paginada |
| Vendas | `GET /vendas?page=1&per_page=20` | Leitura paginada |

Não existe argumento para informar uma rota livre. Criação, finalização,
cancelamento, estoque e finanças ficam fora da carga padrão.

### Critérios iniciais autenticados

- sucesso geral e por rota de pelo menos 99,5%;
- p95 geral e por rota de no máximo 1.500 ms;
- no máximo 2.000 requisições e concorrência 20 por execução;
- cada rota precisa atender ao critério; uma média geral não esconde uma rota
  lenta;
- menos de 100 amostras por rota é marcado como linha de base de baixa amostra.

### Proteções autenticadas

- padrão restrito a `localhost`/`127.0.0.1`;
- staging remoto exige HTTPS e `--allow-remote`;
- produção é bloqueada incondicionalmente, inclusive subdomínios;
- tenant deve estar explicitamente presente na lista devolvida pelo login;
- resposta de erro registra somente etapa, status ou tipo de transporte;
- corpo de cliente, venda, credencial e token nunca entra no relatório.

## Linha de base autenticada

Execução em 2026-08-27, homologação Docker local, PostgreSQL 14, duas réplicas
Uvicorn, massa fictícia pequena, após E2E funcional aprovado:

| Requisições | Concorrência | Sucesso | Req/s | p50 | p95 | p99 | Máxima |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 320 | 8 | 100% | 157,65 | 48,87 ms | 79,73 ms | 107,27 ms | 113,84 ms |
| 396 | 12 | 100% | 151,63 | 76,85 ms | 119,29 ms | 148,39 ms | 174,58 ms |

Detalhe por rota, 80 amostras cada:

| Rota | Sucesso | p50 | p95 | Máxima |
|---|---:|---:|---:|---:|
| Sessão/tenant | 100% | 39,37 ms | 68,04 ms | 93,37 ms |
| Clientes | 100% | 61,55 ms | 90,63 ms | 111,35 ms |
| Produtos | 100% | 53,73 ms | 75,75 ms | 113,84 ms |
| Vendas | 100% | 41,67 ms | 67,58 ms | 107,27 ms |

Login e seleção do tenant, executados uma vez antes da carga, totalizaram
270,13 ms. O resultado passou nos critérios iniciais e prova que o executor,
autenticação, isolamento e quatro consultas críticas funcionam sob essa carga.

No segundo degrau, cada rota recebeu 99 amostras e permaneceu com 100% de
sucesso. O maior p95 individual foi 133,89 ms em clientes; o maior tempo isolado
foi 174,58 ms em produtos. A autenticação inicial totalizou 274,32 ms.

Classificação: `baseline_low_sample`, porque houve 80 e 99 amostras por rota nas
duas execuções. As medições não provam capacidade para 100 ou 1.000 empresas: a
massa é pequena, o host é local e integrações/escritas não participaram.

## Próximos degraus antes de ampliar a faixa de clientes

1. repetir em homologação com volume fictício representativo de clientes,
   produtos e vendas;
2. coletar CPU, memória, conexões/pool e consultas lentas durante os testes;
3. executar degraus de concorrência, sempre respeitando rate limits;
4. criar staging remoto quando a repetibilidade ou a faixa comercial justificar;
5. só então testar escrita idempotente e integrações com sandbox em cenários
   separados, com limpeza comprovada;
6. revisar SLOs após 30 dias de telemetria real, sem transformar meta em SLA por
   inferência.

Essa política está formalizada no ADR-0003 em `docs/adr/README.md`.
