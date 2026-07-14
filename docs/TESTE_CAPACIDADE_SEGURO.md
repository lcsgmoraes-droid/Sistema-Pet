# Teste de capacidade seguro

Atualizado em: 2026-07-13

## Objetivo

Medir uma linha de base de disponibilidade e latencia sem criar, editar ou apagar
dados. O teste usa apenas `GET` em endpoints de saude permitidos e, por padrao,
aceita somente `localhost`.

Este smoke nao substitui um teste de jornada autenticada, banco sob carga ou
dimensionamento definitivo. Ele detecta degradacao basica do servidor e produz
uma referencia repetivel de requisicoes por segundo e latencias.

## Execucao local recomendada

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

## Criterio inicial

Para o smoke local de linha de base:

- pelo menos 99% de respostas aprovadas;
- latencia p95 de no maximo 500 ms;
- nenhuma escrita ou dado real envolvido.

Os limites podem ser ajustados pelos argumentos `--min-success-rate` e
`--max-p95-ms`, mas o resultado deve registrar os valores usados.

## Protecoes

- concorrencia maxima: 50;
- requisicoes maximas por execucao: 5.000;
- somente `/health`, `/api/health` e `/health/watchdog`;
- alvo remoto exige HTTPS;
- qualquer alvo fora de localhost e bloqueado sem `--allow-production`;
- `--allow-production` nao representa autorizacao: antes de usar contra producao,
  Lucas precisa autorizar explicitamente a execucao e a quantidade/concurrencia.

## Producao

Nao executar em producao como rotina automatica. Quando houver autorizacao, comecar
com uma janela pequena e observar `/ops` durante o teste. Exemplo conservador:

```powershell
python scripts/capacity_smoke.py --base-url https://corepet.com.br --path /api/health --requests 50 --concurrency 5 --allow-production
```

Para testar jornadas autenticadas de clientes, criar uma etapa futura em ambiente
de staging com dados ficticios. Nunca usar senha ou token real dentro do script,
comando, log ou documento versionado.

## Linha de base local

Execucao em 2026-07-13, backend local, `GET /health`:

| Requisicoes | Concorrencia | Sucesso | Req/s | p50 | p95 | p99 | Maxima |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 10 | 100% | 442,30 | 15,15 ms | 49,94 ms | 78,08 ms | 96,35 ms |

Resultado: aprovado no criterio inicial. Esta medicao prova o funcionamento do
executor e cria uma referencia local; nao representa a capacidade definitiva do
servidor DigitalOcean nem de jornadas autenticadas com banco.
