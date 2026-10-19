# Homologação técnica local — XML para contabilidade

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Entrega | Configuração e entrega de XMLs de saída ao contador |
| PR | #1526 |
| Versão | Alterações desta ficha na branch de tarefa, antes da publicação |
| Ambiente | Local: SQLite descartável, PostgreSQL DEV e navegador com APIs simuladas |
| Executor | Codex; aceite de negócio pelo Lucas pendente |
| Massa | Empresas, CNPJs, XMLs e destinatários fictícios |

## Pré-condições

Nenhum dado foi copiado para produção. SMTP e emissores externos foram
simulados nos testes de fluxo. O teste PostgreSQL cria apenas schema/papel
temporários no banco local `postgres`, encerrando em rollback. O smoke oficial
criou bancos locais com prefixo exclusivo e removeu-os ao finalizar.

## Cenários

| ID | Cenário | Resultado |
|---|---|---|
| H01 | Configurar destinatário e automatismos; desligar sem SMTP | Aprovado na UI simulada e persistência SQLite |
| H02 | Individual após autorização; repetição e notas históricas | Aprovado: fila sem SMTP na emissão, deduplicação e corte de ativação |
| H03 | Período inclusivo, Brasília e XML original | Aprovado: ZIP/manifesto sem alterar conteúdo assinado |
| H04 | Entrada, homologação, outro CNPJ e XML inválido/ausente | Aprovado: exclusões corretas e bloqueio de lote incompleto |
| H05 | Notas canceladas e eventos embutidos | Aprovado: assinatura preservada e ausência de evento declarada |
| H06 | Enviar/agendar, cancelar e repetir falha | Aprovado: UI mockada, contratos HTTP e persistência/retry |
| H07 | Mensal, dia 31 em mês curto e uma entrega por competência | Aprovado em testes de regra/fila |
| H08 | API sem permissão e empresa diferente | Aprovado: bloqueio HTTP e escopo tenant |
| H09 | RLS PostgreSQL sem bypass | Aprovado: leitura, alteração, exclusão e inserção entre tenants bloqueadas |
| H10 | Migration/reversão e histórico | Aprovado: smoke oficial em banco limpo, histórico e tenants UUID |
| H11 | Tela desktop, 390px/320px, fuso Los Angeles | Aprovado: sem overflow da página/calendário, agendamento mantém Brasília |
| H12 | Emissão/cache/documentos/e-mail preexistentes | Aprovado na regressão focada |

## Evidências e comandos

- Backend: **170 testes aprovados** na execução combinada de
  `test_xml_contabilidade_{service,bling,hooks,reconciliation,routes,migration}`,
  evolução, documentos, cache, emissão IntNFe, rotas operacionais e e-mail.
- Registry multiempresa: **4 testes aprovados**; nenhum modelo novo fora da proteção.
- `test_xml_contabilidade_postgres.py`: **1 teste aprovado** com PostgreSQL real
  local; migration cria/reverte e RLS é exercitado sob papel sem bypass.
- `scripts/ci_migration_smoke.py`: **clean/history/production_uuid = ok**,
  head `zzzzh20261019a1`, sem débito de RLS. Log local ignorado:
  `runtime/xml-contabilidade-qa/migration-smoke.log`.
- Frontend: **5 testes de datas/erros aprovados** e contrato das rotas aprovado.
  ESLint/Ruff dos arquivos novos/alterados aplicáveis aprovados.
- `npm run build`: aprovado; aviso de tamanho do chunk PDV já existente.
- Playwright com APIs simuladas: salvar, download, enviar, agendar, cancelar,
  repetir falha, seleção de período e desligamento sem SMTP aprovados, zero
  erros de página. Evidências locais ignoradas em
  `runtime/xml-contabilidade-qa/{desktop.png,mobile-calendario.png,mobile-320-calendario.png,evidencias.json}`.
- `git diff --check`: aprovado. Builds, capturas e logs não são versionados.

## Inconsistências e limites

O teste legado `menuConfig.test.mjs` tem duas falhas já presentes no HEAD
anterior: lista esperada sem `/ifood` e badge antigo de convites. A comparação
com o código original confirmou a preexistência; não houve alteração desses
testes para mascarar resultado.

Não foi comprovada entrega em caixa de entrada real, nem houve chamada a
IntNFe/Bling de produção. Isso permanece para o primeiro envio autorizado pelo
responsável. Aceite SMTP não significa leitura ou entrega na caixa de entrada.

## Decisão

Validação técnica local aprovada. Aceite funcional do Lucas e publicação em
produção pendentes. Próximo passo: revisar a tela e conferir destinatário/SMTP
antes de autorizar a publicação e ativar qualquer rotina na operação real.
