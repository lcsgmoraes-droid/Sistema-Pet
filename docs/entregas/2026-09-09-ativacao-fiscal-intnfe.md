# Ficha de entrega — ativação fiscal opcional IntNFe

## Identificação

| Campo | Valor |
|---|---|
| Data | 2026-09-09 |
| Responsável de negócio | Lucas Guerra |
| Executor técnico | Codex |
| Issue/PR | Consultar o PR da branch `codex/fix-modal-entrega-teclado` com o título de ativação fiscal IntNFe. |
| Prioridade | P2 — preparação do piloto fiscal |
| Risco | Médio: provisionamento externo, credenciais e isolamento entre empresas. Desligado por padrão. |
| Domínios | Configurações, integração fiscal e segurança de tenant. |

## 1. Necessidade e requisitos

Preparar o vínculo fiscal quando o usuário optar pela emissão, sem depender da
IntNFe no cadastro inicial da conta. Aceite desta etapa: ação em Integrações,
validação cadastral, criação/vínculo, credenciais protegidas, situação do A1 e
tratamento de conflito/resposta perdida. O restante do CorePet continua operando.
Emitir notas e habilitar produção estão fora do escopo desta entrega.

## 2. Regras de negócio e dados

`Tenant` é a fonte do CNPJ e dos nomes. `IntNFeConnection` armazena uma conexão
por tenant, com unicidade também por CNPJ e emitente remoto. Nova migration
`zzn20260909a1` com RLS forçada, dados cadastrais, segredo cifrado, estado,
protocolo, timestamps e reserva da operação. Sem importação de dados reais.
Reserva com bloqueio da empresa e escrita condicionada ao identificador da
operação evitam duplicação concorrente e sobrescrita por processo antigo.

## 3. Arquitetura e integrações

Backend `app/intnfe`, tela nas configurações, cliente HTTP com origem fixa e
rotas autenticadas. Ativação opcional escolhida porque a conta comercial pode
existir sem necessidade fiscal imediata. Contratos, timeout, ausência de retry e
reconciliação estão no [guia](../ATIVACAO_FISCAL_INTNFE.md) e no catálogo INT-018.
Não há criação alternativa quando o provedor estiver indisponível.

## 4. Segurança e privacidade

Exige sessão, módulo `integracoes` e permissão `configuracoes.editar`. O tenant
não vem do corpo enviado pela tela. Nenhum segredo sai nas respostas, na
auditoria ou em erros de schema. Criptografia reutiliza a chave mestra existente.
Uma conta encontrada exige credenciais próprias válidas, sem rotação automática.
Finalidade dos dados: provisionamento fiscal autorizado. Segredos permanecem
enquanto o vínculo existir; exclusão/rotação assistida e retenção formal para a
operação fiscal completa ficam para a etapa de produção. O guia não autoriza
apagar vínculos para contornar conflitos ou repetir uma criação incerta.

## 5. Desenvolvimento e qualidade

- 37 testes aprovados: serviço, cliente HTTP simulado, rotas autenticadas,
  permissões, isolamento ORM, segredo protegido, concorrência/recuperação,
  roundtrip da migration SQLite e geração do DDL PostgreSQL com política RLS.
  Inclui 3 testes com PostgreSQL 14 descartável: upgrade/downgrade real,
  leitura/escrita entre empresas com papel sem bypass e reserva simultânea em
  duas conexões, com somente uma operação vencedora.
- Comando, a partir de `backend`, com `DATABASE_URL=sqlite://` e `ENVIRONMENT=test`:
  `python -m pytest tests/unit/test_intnfe_activation.py tests/unit/test_intnfe_client.py tests/unit/test_intnfe_migration.py -q --tb=short -x`.
- Os 3 testes adicionais estão em `tests/integration/test_intnfe_postgres.py`;
  exigem `INTNFE_TEST_POSTGRES_URL` para um banco local descartável chamado
  `intnfe_test`. Não usam a URL da aplicação e não devem apontar para dados reais.
- Build frontend `npm run build` aprovado; lint dos arquivos da tela e Ruff dos
  novos módulos/testes aprovados; `git diff --check` sem erro de whitespace.
- Conferência no Chrome de uma prévia local do componente real: estado inicial,
  formulário de credenciais e transição simulada para certificado pendente.
  Rótulos acessíveis, segredo do formulário mascarado e mensagens de homologação.
  A prévia usa dados fictícios, sem backend/IntNFe real; não é E2E autenticado.
- Não foi realizado teste de carga. O piloto direto de API obteve autorização
  em homologação na nota 1/003, com XML conferido; isso não valida emissão
  pelo CorePet. O DANFE apresentou divergência de formatação numérica.

## 6. Ambientes e homologação

Validação local Windows, Python 3.12/SQLite/PostgreSQL 14 e build Vite. Variáveis
descritas no guia, com flag desligada por padrão. Após a recuperação do Docker
pela tarefa de infraestrutura, os testes de RLS/concorrência em PostgreSQL
passaram. Executados `FLUXO_UNICO.bat dev-up` e upgrade das migrations pendentes
`zzm20260909a1`/`zzn20260909a1` no PostgreSQL 16 DEV, sem alterar produção.
Smoke no backend DEV: `/health` HTTP 200 e `/intnfe/status` sem sessão HTTP 403.
No piloto remoto, o conflito HTTP 409 foi superado após a equipe IntNFe remover
os emitentes. A LJ foi criada sob **CorePet — Lucas Guerra**, com autenticação
própria HTTP 200. Após Lucas fornecer o PFX, o A1 foi enviado e reconhecido:
HTTP 200, válido até 02/04/2027. Houve recuperação controlada da credencial do
emitente recém-criado após perda da resposta de cadastro. A primeira nota
direta de API, 1/001 em homologação, foi aceita com HTTP 202 e depois rejeitada
com `SCHEMA` em ICMS-ST e PIS/COFINS. O reteste com dados idênticos gerou a
nota 2/001 e retornou 539 (duplicidade), sem repetir os erros de XML. Por
sugestão de Lucas, somente a série foi alterada para 3 e a nota 1/003 foi
autorizada. XML conferido, com protocolo, cStat 100 e tpAmb 2. O DANFE teve
produtos/desconto/total/quantidade corrigidos, confirmados por nova consulta
às 23:19, sem emissão. Restam modalidade do frete (XML 9, HTML 0) e formatação
decimal do item. A série 001 segue pendente de conciliação antes de reutilizá-la.
Detalhes no [registro](../FISCAL_INTNFE_PILOTO_HOMOLOGACAO.md) e no
[diagnóstico](../DIAGNOSTICO_INTNFE_NFE_HOMOLOGACAO_2026-09-09.md).
Esta ficha registra a validação técnica parcial; homologação operacional com
Lucas e IntNFe continua pendente e não foi dispensada.

## 7. Publicação e rollback

Entrega de backend/frontend/documentação; nenhum build mobile ou deploy.
Revisão isolada usando como base `codex/base-antes-ativacao-intnfe`, uma fotografia
da branch antes desta entrega: ela já continha trabalho de créditos e outros
commits pendentes de integração à `main`. O PR desta etapa permanece rascunho;
antes de integrar à `main`, concluir/reconciliar essa base e conferir a cadeia
de migrations. Não incluir silenciosamente os trabalhos anteriores como parte
da ativação fiscal.
Aplicar migration antes do novo backend e manter flag desligada até validar o
ambiente. Em futura publicação autorizada: seguir `FLUXO_UNICO.bat release-check`
e `prod-up`, reconstruindo backend. Smoke: sessão autorizada, estado, isolamento
e uma ativação homologada. Abortar em exposição entre empresas, segredo em
resposta, repetição de criação incerta ou divergência de contrato remoto.
Rollback preferencial: desligar a flag, preservar a tabela e restaurar versão
anterior. Não fazer downgrade destrutivo após salvar credenciais reais sem plano
de preservação e reconciliação. Esta ficha não autoriza produção.

## 8. Observabilidade e sustentação

Auditoria `intnfe_ativar`, `intnfe_consultar` e `intnfe_vincular` com estado/código/
protocolo. Indicador de progresso: vínculo confirmado e certificado conferido,
sem criação duplicada. Falha isolada no piloto é P2; exposição de credenciais ou
acesso cruzado exige tratamento de incidente de segurança. Alternativa segura:
continuar operação comercial e corrigir o cadastro externo com suporte.
Reincidência de resposta perdida exige contrato de idempotência/recuperação com
o fornecedor antes de expandir a ativação aos clientes.

## 9. Mudança, comunicação e treinamento

Orientar Lucas e equipe sobre ativação opcional, diferença entre códigos do
integrador/emitente e pendências do A1. O guia é o material desta fase. Atualizar
a Central de Ajuda voltada a clientes quando o fluxo de emissão for homologado.
Marco de comunicação aos clientes: liberação futura da funcionalidade.

## 10. Fechamento

- [x] Implementação da etapa de vínculo e validações locais registradas.
- [x] Proteções de tenant, permissões, segredos e auditoria implementadas/testadas localmente.
- [x] Documentação, observabilidade, comunicação e rollback definidos.
- [x] RLS/concorrência e migration validadas em PostgreSQL.
- [ ] E2E autenticado do fluxo completo com conta DEV autorizada e emissor real.
- [x] Emissor real e certificado reconhecidos no piloto direto da API IntNFe.
- [x] Retestar os mesmos dados: erros anteriores de schema não se repetiram.
- [ ] Conciliar duplicidade 539 antes de reutilizar a série 001 em homologação.
- [x] Primeira nota de produto autorizada em homologação: 1/003, XML conferido.
- [x] Corrigir produtos, desconto, total e quantidade no DANFE; nova consulta confirmada.
- [ ] Corrigir modalidade do frete no DANFE e padronizar decimais da linha do item.

Decisão: preparada para revisão, com pendências de homologação. Não liberada
para produção. Responsáveis: equipe IntNFe pelo contrato; Lucas e Codex
pela execução do piloto integrado e primeiro documento em homologação.
Prazo: antes da ativação de clientes reais; primeira nota conforme roteiro do piloto.
