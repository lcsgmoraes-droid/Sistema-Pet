# Ficha de entrega — capacidade autenticada e ADRs

## Identificação

| Campo | Valor |
|---|---|
| Título | Linha de base autenticada segura e registro de decisões arquiteturais |
| Data | 2026-08-27 |
| Responsável de negócio | Responsável pelo Sistema Pet |
| Executor técnico | IA |
| Issue/PR | Branch `feat/20260827-0009-capacidade-adrs-enterprise`; PR a abrir |
| Prioridade | P1 |
| Risco | Baixo: ferramenta somente leitura, bloqueio explícito de produção e documentação; sem mudança de runtime do produto |
| Domínios afetados | Homologação, capacidade, arquitetura e governança |

## 1. Necessidade e requisitos

- Problema: o smoke existente media health público, não o caminho autenticado
  com tenant e consultas ao banco.
- Usuários: operação técnica atual e futuras pessoas desenvolvedoras.
- Resultado: medir sessão, clientes, produtos e vendas em homologação, com
  relatório por rota e decisões arquiteturais localizáveis.
- Requisitos: autenticar uma vez, selecionar tenant explícito, executar apenas
  GETs fechados, medir sucesso/latência/throughput e falhar quando qualquer rota
  romper o critério.
- Não funcionais: credenciais fora do comando/Git/saída; produção bloqueada;
  concorrência e volume limitados; resultado honesto sobre amostra.
- Preservado: regras, dados, migrations, frontend, app mobile e produção.
- Fora do escopo: carga de escrita, sandbox de integrações, staging remoto,
  otimização e promessa comercial de escala.
- Aceite: testes de proteção passam, E2E fictício passa, degraus 320/8 e 396/12
  concluem sem falha, e ADRs/guias oficiais ficam ligados pelo índice.

## 2. Regras de negócio e dados

- Nenhuma regra de negócio ou dado de cliente foi alterado.
- A massa pertence exclusivamente ao tenant descartável de homologação.
- Não há migration, importação, retenção ou cópia de dados.
- Consultas são paginadas e preservam o isolamento do token selecionado.

## 3. Arquitetura e integrações

- Novo executor isolado em `scripts/capacity_authenticated.py` e entrada simples
  em `scripts/homologacao_local.ps1`.
- ADR-0001 mantém o monólito modular; ADR-0002 registra defesa multiempresa em
  camadas; ADR-0003 exige medição antes de escala.
- Alternativas rejeitadas: produção como laboratório, rota livre, segredo em
  argumento e microsserviços/infraestrutura antes de medir.
- Integrações externas não participam desta fatia.

## 4. Segurança e privacidade

- Login e tenant usam credenciais aleatórias do arquivo local ignorado pelo Git.
- Token existe apenas em memória e não é exibido.
- Domínios de produção e subdomínios são bloqueados incondicionalmente.
- Não há body de cliente/venda no relatório; somente rota fechada, status,
  contagem e duração.
- Testes cobrem alvo remoto, produção, tenant incorreto, rotas e limites.

## 5. Desenvolvimento e qualidade

- Fatia 1: executor e testes unitários.
- Fatia 2: comando de homologação e execução real.
- Fatia 3: ADRs, governança, evidência e índices.
- Resultado inicial: 15 testes de capacidade aprovados e Ruff aprovado.
- Homologação: build de produção, migrations, health, E2E e duas cargas
  autenticadas aprovados; validações gerais serão executadas antes do PR.

## 6. Ambientes e homologação

- Ambiente: `corepet-homolog` local, isolado, PostgreSQL 14, dois workers
  Uvicorn e imagens construídas pelos Dockerfiles de produção.
- Massa: tenant, usuário, cliente, produto e venda fictícios.
- Registro: `docs/homologacoes/2026-08-27-capacidade-autenticada-adrs.md`.
- Produção não foi consultada ou alterada por esta entrega.

## 7. Publicação e rollback

- Tipo: ferramenta de desenvolvimento/homologação e documentação.
- Não exige migration, frontend, backend ou mobile em produção.
- Publicação: branch, testes, PR e CI; deploy de produto não é necessário para
  obter o benefício local.
- Rollback: reverter o PR remove o executor e os documentos; nenhum dado precisa
  ser restaurado.

## 8. Observabilidade e sustentação

- Sinais: sucesso geral/rota, p50/p95/p99/máxima, throughput, autenticação e
  qualidade da amostra.
- Falha de auth, tenant, transporte, HTTP, sucesso ou latência produz saída não
  aprovada sem mostrar resposta sensível.
- Reincidência de lentidão vira investigação de consulta, pool, banco ou host
  antes de mudança estrutural.

## 9. Mudança, comunicação e treinamento

- Nenhuma rotina do cliente muda.
- Operação técnica ganha um comando documentado em português.
- Não requer comunicação ou treinamento de clientes.

## 10. Fechamento

- [x] Critérios de aceite atendidos.
- [x] Testes e evidências registrados.
- [x] Tenant, permissões, dados e auditoria preservados.
- [x] Documentação oficial atualizada.
- [x] Homologação registrada.
- [x] Publicação, observabilidade e rollback definidos.
- [x] Comunicação/treinamento avaliados.
- [x] PR revisável, sem segredo, backup, dump ou artefato indevido.

Decisão final: aprovado tecnicamente para PR. Não há deploy de runtime nesta
fatia.

Pendências: massa representativa, métricas de host/banco, degraus maiores e
staging remoto permanecem condicionados ao crescimento e às evidências.
