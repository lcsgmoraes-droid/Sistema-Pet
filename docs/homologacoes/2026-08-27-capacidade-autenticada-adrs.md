# Registro de homologação — capacidade autenticada e ADRs

## Identificação

| Campo | Valor |
|---|---|
| Entrega | Linha de base autenticada segura e registro de decisões arquiteturais |
| Issue/PR | Branch `feat/20260827-0009-capacidade-adrs-enterprise`; PR a abrir |
| Commit/versão testada | Working tree da branch; versão final será identificada no PR |
| Data e horário | 2026-08-27, 00h, horário de Brasília |
| Ambiente | HOMOLOG Docker local isolada |
| Responsável técnico | IA |
| Responsável pelo aceite de negócio | Responsável pelo Sistema Pet |
| Tenant/massa de teste | Tenant e dados fictícios gerados pelo fluxo oficial |

## Pré-condições

- Docker Desktop 4.73.0 reparado sem factory reset; Engine 29.4.3 saudável.
- Imagens de frontend/backend construídas pelos Dockerfiles de produção.
- PostgreSQL 14 próprio, migrations concluídas e health verde.
- Credenciais aleatórias em `.env.homolog.local`, sem exibição.
- Integrações externas desativadas; nenhum dado real copiado.

## Cenários de aceite

| ID | Cenário | Resultado esperado | Resultado obtido | Evidência | Status |
|---|---|---|---|---|---|
| H01 | Construir e subir homologação | Migrations, backend e frontend saudáveis | Ambiente disponível em `127.0.0.1:18080` | `homologacao_local.ps1 -Acao subir` | aprovado |
| H02 | Jornada funcional antes da carga | Login, tenant, permissões, cliente, produto e venda fictícios funcionam | 1 E2E aprovado em 1,62 s | `homologacao_local.ps1 -Acao validar` | aprovado |
| H03 | Carga 320/8 | >=99,5% e p95 <=1.500 ms em todas as rotas | 320/320; p95 79,73 ms; 157,65 req/s | Saída JSON do executor | aprovado |
| H04 | Carga 396/12 | Resultado permanece dentro da meta no degrau maior | 396/396; p95 119,29 ms; 151,63 req/s | Saída JSON do executor | aprovado |
| H05 | Sessão autenticada | 80 consultas aprovadas | 100%; p95 68,04 ms | Resumo por rota | aprovado |
| H06 | Clientes | 80 consultas aprovadas | 100%; p95 90,63 ms | Resumo por rota | aprovado |
| H07 | Produtos | 80 consultas aprovadas | 100%; p95 75,75 ms | Resumo por rota | aprovado |
| H08 | Vendas | 80 consultas aprovadas | 100%; p95 67,58 ms | Resumo por rota | aprovado |
| H09 | Proteção de produção | Domínio real recusado mesmo com alvo remoto | Teste automatizado aprovado | `test_capacity_authenticated.py` | aprovado |
| H10 | Segredos | Senha/token ausentes do comando e relatório | Apenas variáveis do processo e métricas técnicas | Revisão do executor e teste | aprovado |
| H11 | ADRs navegáveis | Decisões, alternativas e revisão localizáveis | Índice e ADR-0001/0002/0003 criados | `docs/adr/README.md` | aprovado |

## Inconsistências

Nenhuma inconsistência funcional foi encontrada.

Limite conhecido: 80 amostras por rota formam `baseline_low_sample`. A massa é
pequena e o host é local; o resultado não dimensiona 100 ou 1.000 empresas.

## Evidências

- Testes focados: 15 aprovados.
- Ruff: aprovado.
- Parser PowerShell: aprovado.
- Build Docker frontend/backend: aprovado.
- Migrations e health: aprovados.
- E2E oficial: 1 aprovado.
- Carga: 320 sucessos, 0 falhas, 157,65 req/s, p50 48,87 ms, p95 79,73 ms,
  p99 107,27 ms e máxima 113,84 ms.
- Autenticação inicial: 270,13 ms no total.
- Segundo degrau: 396 sucessos, 0 falhas, 151,63 req/s, p50 76,85 ms, p95
  119,29 ms, p99 148,39 ms e máxima 174,58 ms; autenticação em 274,32 ms.

Nenhuma evidência contém senha, token, tenant real ou dado pessoal.

## Decisão

- [x] Aprovado.
- [ ] Aprovado com pendências não bloqueantes registradas.
- [ ] Reprovado.

Justificativa: os controles, a jornada funcional e a primeira carga autenticada
atenderam aos critérios em ambiente isolado, sem escrita durante a medição.

Responsável pelo aceite: responsável pelo Sistema Pet, pela autorização de
continuidade do trabalho. Isso não constitui autorização de produção.

Data: 2026-08-27.

Próximo passo: validar a suíte geral, abrir PR e acumular linhas de base com massa
maior antes de aprovar nova faixa de escala.
