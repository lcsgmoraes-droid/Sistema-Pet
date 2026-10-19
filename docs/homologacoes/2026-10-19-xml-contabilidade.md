# Homologação técnica local — XML para contabilidade

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Entrega | Envio mensal do mês anterior completo e lotes manuais com eventos fiscais |
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
| H02 | Somente mensal; emissão e agendamento avulso removidos | Aprovado: API rejeita legados, worker cancela pendências e não retoma históricos |
| H03 | Período inclusivo, Brasília e XML original | Aprovado: ZIP/manifesto sem alterar conteúdo assinado |
| H04 | Entrada, homologação, outro CNPJ e XML inválido/ausente | Aprovado: exclusões corretas e bloqueio de lote incompleto |
| H05 | Canceladas, substituição NFC-e e CC-e com várias sequências | Aprovado: consulta oficial IntNFe, assinatura preservada e evento faltante bloqueia ZIP |
| H06 | Enviar manualmente, cancelar e repetir falha | Aprovado: UI mockada, contratos HTTP e persistência/retry |
| H07 | Mês anterior do dia 1 ao último dia, fevereiro 28/29, meses 30/31 e virada de ano | Aprovado; competência fixa e idempotente, inclusive recuperação após indisponibilidade |
| H08 | API sem permissão e empresa diferente | Aprovado: bloqueio HTTP e escopo tenant |
| H09 | RLS PostgreSQL sem bypass | Aprovado: leitura, alteração, exclusão e inserção entre tenants bloqueadas |
| H10 | Migrations/reversão e desativação dos fluxos antigos | Aprovado: smoke limpo/histórico/UUID; RLS preservado e contexto restaurado |
| H11 | Tela desktop, 390px/320px e mês civil em Brasília | Aprovado: sem overflow e dia/hora visíveis mesmo com SMTP ausente |
| H12 | Emissão/cache/documentos/e-mail preexistentes | Aprovado na regressão focada |

## Evidências e comandos

- Backend: **236 testes aprovados** na execução combinada de
  `test_xml_contabilidade_{service,bling,hooks,reconciliation,routes,migration,mensal_migration,eventos}`,
  evolução, documentos, cache, cliente/emissão IntNFe, rotas operacionais e e-mail.
- Registry multiempresa: **4 testes aprovados**; nenhum modelo novo fora da proteção.
- `test_xml_contabilidade_postgres.py`: **2 testes aprovados** com PostgreSQL real
  local; migrations criam/revertem e migram legados sob papel sem bypass,
  preservando FORCE RLS e restaurando `app.tenant_id`.
- `scripts/ci_migration_smoke.py`: **clean/history/production_uuid = ok**,
  head `zzzzi20261019a1`, sem débito de RLS. Log local ignorado:
  `runtime/xml-contabilidade-qa/migration-mensal-smoke.log`.
- Frontend: **5 testes de datas/erros aprovados** e contrato das rotas aprovado.
  ESLint/Ruff dos arquivos novos/alterados aplicáveis aprovados.
- `npm run build`: aprovado; aviso de tamanho do chunk PDV já existente.
- Playwright com APIs simuladas: salvar apenas configuração mensal, selecionar
  período manual sem alterar a competência mensal, download/envio e erro JSON
  de pacote bloqueado aprovados; zero erros em React StrictMode, sem overflow
  em 390/320px. Evidências ignoradas:
  `runtime/xml-contabilidade-qa/mensal-{desktop,mobile,sem-smtp}.png` e
  `mensal-evidencias.json`.
- `git diff --check`: aprovado. Builds, capturas e logs não são versionados.
- Homologação local reconstruída pelo script oficial, migrations aplicadas e
  frontend/backend saudáveis. A aba autenticada do Chrome do Lucas foi atualizada
  e confirmou a tela mensal, dias/horário visíveis e período manual separado.
  Captura ignorada: `runtime/xml-contabilidade-qa/mensal-dev-aberto.png`.

## Inconsistências e limites

O teste legado `menuConfig.test.mjs` tem duas falhas já presentes no HEAD
anterior: lista esperada sem `/ifood` e badge antigo de convites. A comparação
com o código original confirmou a preexistência; não houve alteração desses
testes para mascarar resultado.

Não foi comprovada entrega em caixa de entrada real, nem houve chamada a
IntNFe/Bling de produção. O contrato de eventos foi conferido na documentação
oficial; chamadas dos testes são simuladas. O OpenAPI público Bling não oferece
listagem de eventos, então a coleta desse legado depende de XMLs disponíveis
ou embutidos e não garante descobrir CC-e externas desconhecidas.
O recebimento permanece para o primeiro envio autorizado pelo
responsável. Aceite SMTP não significa leitura ou entrega na caixa de entrada.

## Decisão

Validação técnica local aprovada. Aceite funcional do Lucas e publicação em
produção pendentes. Próximo passo: revisar a tela e conferir destinatário/SMTP
antes de autorizar a publicação e ativar qualquer rotina na operação real.
