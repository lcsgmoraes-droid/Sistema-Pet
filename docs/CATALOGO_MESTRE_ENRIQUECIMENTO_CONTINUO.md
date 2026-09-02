# Enriquecimento continuo do catalogo mestre

## Objetivo

O worker melhora o catalogo global sem atualizar o cadastro operacional de
nenhuma loja. O Atacadao e uma fonte inicial de consulta; todo resultado novo e
gravado somente nas tabelas `catalogo_mestre_*`.

## Primeira fase

Esta fase processa apenas a pendencia `descricao_completa` de produtos ativos
classificados como:

- racao;
- petisco;
- areia sanitaria.

O texto gerado e salvo como rascunho com `status_revisao=pendente`, modelo,
versao do prompt, data, confianca e alertas. Uma sincronizacao posterior com o
Atacadao nao sobrescreve esse rascunho porque a proveniencia do campo deixa de
ser `tenant_produto`.

O worker nao gera ou altera automaticamente:

- medicamentos, bula ou posologia;
- EAN/GTIN;
- dados fiscais;
- composicao, tabela nutricional ou tabela de consumo;
- imagens de embalagens de marca;
- brinquedos e acessorios genericos.

Esses campos exigem fonte oficial ou licenciada e, nos dados veterinarios,
revisao especializada.

## Protecoes operacionais

- Dupla ativacao: `CATALOGO_MESTRE_WORKER_ENABLED` e
  `CATALOGO_MESTRE_WORKER_APPLY_ENABLED` precisam estar habilitadas.
- O compose de producao deixa ambas desabilitadas por padrao.
- Cada tarefa recebe uma reserva com expiracao e usa `SKIP LOCKED` no PostgreSQL.
- Cada tentativa gera uma linha de auditoria em
  `catalogo_mestre_enriquecimento_execucoes`.
- O limite diario e persistente e inclui tentativas que terminaram em erro.
- Falhas usam retentativa exponencial; ao atingir o maximo, a tarefa muda para
  `falha_permanente`.
- Descricoes existentes nunca sao sobrescritas.
- O contexto enviado ao provedor nao inclui IDs do tenant ou do produto de
  origem.

## Configuracao

| Variavel | Padrao | Funcao |
| --- | ---: | --- |
| `CATALOGO_MESTRE_WORKER_ENABLED` | `false` | Liga o agendamento. |
| `CATALOGO_MESTRE_WORKER_APPLY_ENABLED` | `false` | Autoriza gravacao no catalogo mestre. |
| `CATALOGO_MESTRE_OPENAI_MODEL` | `gpt-5.6` | Modelo de geracao estruturada. |
| `CATALOGO_MESTRE_OPENAI_REASONING_EFFORT` | `low` | Esforco de raciocinio e controle de custo. |
| `CATALOGO_MESTRE_WORKER_INTERVAL_SECONDS` | `60` | Intervalo entre lotes. |
| `CATALOGO_MESTRE_WORKER_BATCH_SIZE` | `1` | Produtos por lote, limitado a 10. |
| `CATALOGO_MESTRE_WORKER_DAILY_LIMIT` | `25` | Tentativas por dia, limitado a 500. |
| `CATALOGO_MESTRE_WORKER_MAX_ATTEMPTS` | `5` | Tentativas por pendencia. |
| `CATALOGO_MESTRE_WORKER_LEASE_SECONDS` | `900` | Duracao da reserva da tarefa. |

## Ativacao recomendada

1. Implantar a migration e o novo container ainda com as duas travas em `false`.
2. Confirmar o heartbeat e que nenhuma execucao foi criada.
3. Com nova autorizacao de producao, iniciar com lote 1 e limite diario 5.
4. Revisar os cinco primeiros rascunhos e a trilha de proveniencia.
5. Somente depois elevar gradualmente o limite diario.

## Proximas fases

1. Curadoria e aprovacao dos rascunhos de descricao.
2. Coleta de paginas e imagens oficiais/licenciadas de fabricantes.
3. Inclusao de produtos ausentes por marca, variante e EAN verificado.
4. Dados de racao extraidos do rotulo oficial.
5. Medicamentos vinculados a registro e bula oficiais, com revisao veterinaria.
6. Dados fiscais tratados como referencia e validados por operacao, UF e regime.

EANs recebidos antes dessa identificacao ficam na fila privada de candidatos.
Essa fila nao e consumida pelo worker de descricoes e nao cria produto por nome
de arquivo: primeiro exige fonte oficial de identidade e decisao de escopo.
