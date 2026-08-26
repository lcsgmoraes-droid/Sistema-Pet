# Registro de homologação — telemetria de jornadas críticas

## Identificação

| Campo | Valor |
|---|---|
| Entrega | Medição sanitizada de login, seleção de empresa e finalização de venda |
| Issue/PR | Branch `feat/20260826-1638-telemetria-jornadas-login-venda`; PR a registrar após o push |
| Commit/versão testada | Worktree da branch antes do commit final, migration `zxe20260826a1` |
| Data e horário | 2026-08-26, período da tarde, horário de Brasília |
| Ambiente | HOMOLOG Docker local isolada |
| Responsável técnico | IA |
| Responsável pelo aceite de negócio | Responsável pelo Sistema Pet |
| Tenant/massa de teste | Tenant, usuário e venda fictícios gerados pelo script oficial |

## Pré-condições

- Configuração: Docker Compose de homologação, PostgreSQL 14, backend e frontend
  reconstruídos a partir da branch.
- Volume PostgreSQL novo; cadeia Alembic executada do zero até
  `zxe20260826a1 (head)`.
- Credenciais aleatórias locais preservadas em `.env.homolog.local`, ignorado
  pelo Git e não exibido nas evidências.
- Dependências externas não participam desta entrega.
- Risco conhecido: a amostra inicial não é suficiente para aprovar SLA; serve
  para provar coleta, cálculo e integração.
- Nenhum dado real foi copiado ou acessado.

## Cenários de aceite

| ID | Cenário | Resultado esperado | Resultado obtido | Evidência | Status |
|---|---|---|---|---|---|
| H01 | Aplicar migrations em PostgreSQL vazio | Cadeia chega a um único head e cria a tabela | `zxe20260826a1 (head)` | `homologacao_local.ps1 -Acao subir` e `alembic current` | aprovado |
| H02 | Health de frontend e backend | Ambos respondem saudáveis | Health verde antes e depois do E2E | Saída do script oficial | aprovado |
| H03 | Login e seleção de empresa fictícios | Fluxo autentica e seleciona tenant sem regressão | Jornada E2E concluída | `test_plano_basico_e2e.py`: 1 aprovado | aprovado |
| H04 | Finalização de venda fictícia | Venda conclui e permanece idempotente | E2E concluiu a venda | Saída do E2E e evento terminal | aprovado |
| H05 | Medição das três jornadas | Eventos são agregados sem conteúdo de negócio | Em duas execuções controladas: 8 tentativas, 7 elegíveis, 7 sucessos, 1 rejeição esperada e 0 falhas | Resumo do serviço contra PostgreSQL | aprovado |
| H06 | Latência e regra de amostra | Percentis são calculados e amostra abaixo de 100 não aprova/reprova SLO | p50/p95/p99 presentes; status `baseline_low` | Resumo de homologação | aprovado |
| H07 | Isolamento multempresa | Nova tabela global é intencional e não cria dívida RLS inesperada | Lista inesperada vazia | `assert_no_unexpected_no_rls_tables`: `[]` | aprovado |
| H08 | Falha da telemetria | Cliente recebe resposta normal mesmo sem coleta | Resposta 200 preservada quando o gravador lança exceção | Teste unitário fail-open | aprovado |
| H09 | Privacidade do evento | Não gravar body, ID real da venda ou identificação pessoal direta | Campos fechados e template `/vendas/{venda_id}/finalizar` | Testes unitário e de contrato | aprovado |
| H10 | Painel administrativo | Componente compila e usa agregação do backend | Prettier, ESLint e build Vite aprovados | Build de produção e contrato do painel | aprovado |

## Inconsistências

Nenhuma inconsistência P0, P1, P2 ou P3 foi encontrada nesta homologação.

Pendências planejadas, não classificadas como defeito da entrega: automatizar
purge/agregação, ampliar as jornadas e aguardar linha de base de 30 dias antes de
ratificar metas.

## Evidências

- 40 testes focados aprovados após o teste adicional de fail-open.
- `test_plano_basico_e2e.py`: 1 cenário E2E aprovado.
- Ruff, Prettier e ESLint sem erro.
- Vite gerou build de produção com sucesso.
- PostgreSQL: `zxe20260826a1 (head)`.
- Resumo real após duas execuções controladas: 8 tentativas; 7 elegíveis; 7
  sucessos; 1 rejeição esperada; 0 falhas; taxa elegível de 100% na amostra
  pequena.
- Catraca RLS: nenhuma tabela inesperada sem política.

As evidências não incluem senha, token, UUID do tenant, payload ou dado pessoal.

## Decisão

- [x] Aprovado.
- [ ] Aprovado com pendências não bloqueantes registradas.
- [ ] Reprovado.

Justificativa: critérios funcionais, de banco, privacidade, isolamento,
compilação e continuidade foram atendidos em ambiente isolado.

Responsável pelo aceite: responsável pelo Sistema Pet, representado pela
autorização de continuidade do trabalho; autorização de produção permanece
separada.

Data: 2026-08-26.

Próximo passo: concluir branch/PR, aguardar CI verde e pedir autorização
explícita antes de qualquer comando de produção.
