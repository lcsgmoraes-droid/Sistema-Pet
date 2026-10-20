# Homologação técnica local — XML para contabilidade

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Entrega | Envio individual de nota/evento, mensal do mês anterior e lotes manuais com ZIPs por tipo |
| PR | Publicação exclusiva de XML, separada do #1526 |
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
| H02 | Individual e mensal independentes; período avulso só manual | Aprovado: quatro combinações persistidas na UI e API; ativação individual sem disparar histórico |
| H03 | Período inclusivo, Brasília e XML original | Aprovado: ZIP/manifesto sem alterar conteúdo assinado |
| H04 | Entrada, homologação, outro CNPJ e XML inválido/ausente | Aprovado: exclusões corretas e bloqueio de lote incompleto |
| H05 | Canceladas, substituição NFC-e e CC-e com várias sequências | Aprovado: consulta oficial IntNFe, XML original preservado e faltante bloqueia lote; ZIPs por tipo |
| H06 | Enviar manualmente, cancelar e repetir falha | Aprovado: UI mockada, contratos HTTP e persistência/retry |
| H07 | Mês anterior do dia 1 ao último dia, fevereiro 28/29, meses 30/31 e virada de ano | Aprovado; competência fixa e idempotente, inclusive recuperação após indisponibilidade |
| H08 | API sem permissão e empresa diferente | Aprovado: bloqueio HTTP e escopo tenant |
| H09 | RLS PostgreSQL sem bypass | Aprovado: leitura, alteração, exclusão e inserção entre tenants bloqueadas |
| H10 | Migrations/reversão e monitoramento de eventos | Aprovado: smoke limpo/histórico/UUID; RLS preservado, identidade fiscal e bytes do evento persistidos |
| H11 | Tela desktop, 390px/320px e mês civil em Brasília | Aprovado: sem overflow e dia/hora visíveis mesmo com SMTP ausente |
| H12 | Emissão/cache/documentos/e-mail preexistentes | Aprovado na regressão focada |

## Evidências e comandos

- Backend: **274 testes aprovados** na execução combinada de
  `test_xml_contabilidade_{service,bling,hooks,reconciliation,routes,migration,mensal_migration,eventos,individual,eventos_migration,documentos_lookup,pacotes}`,
  evolução, documentos, cache, cliente/emissão IntNFe, rotas operacionais e e-mail.
- Registry multiempresa: **4 testes aprovados**; nenhum modelo novo fora da proteção.
- `test_xml_contabilidade_postgres.py` e `test_xml_contabilidade_eventos_postgres.py`:
  **3 testes aprovados** com PostgreSQL real
  local; migrations criam/revertem e migram legados sob papel sem bypass,
  preservando FORCE RLS e restaurando `app.tenant_id`.
- `scripts/ci_migration_smoke.py`: **clean/history/production_uuid = ok**,
  head `zzzzj20261019a1`, sem débito de RLS. Log local ignorado:
  `runtime/xml-contabilidade-qa/migration-eventos-smoke.log`.
- Frontend: **7 testes de datas/configurações/erros aprovados** e contrato das rotas aprovado.
  ESLint/Ruff dos arquivos novos/alterados aplicáveis aprovados.
- `npm run build`: aprovado; aviso de tamanho do chunk PDV já existente.
- Playwright com APIs simuladas: salvar as quatro combinações individual/mensal, selecionar
  período manual sem alterar a competência mensal, download/envio e erro JSON
  de pacote bloqueado aprovados; zero erros em React StrictMode, sem overflow
  em 390/320px. Evidências ignoradas:
  `runtime/xml-contabilidade-qa/individual-tipos-{desktop,mobile,sem-smtp}.png` e
  `individual-tipos-evidencias.json`.
- `git diff --check`: aprovado. Builds, capturas e logs não são versionados.
- Homologação local reconstruída pelo script oficial, migrations aplicadas e
  frontend/backend saudáveis. A aba autenticada do Chrome do Lucas foi atualizada
  e confirmou as opções individual/mensal, ZIPs por tipo, dias/horário visíveis
  e período manual separado. Captura ignorada:
  `runtime/xml-contabilidade-qa/individual-tipos-dev-aberto.png`.

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

## Ajustes para publicação exclusiva (#1530)

- Autorização do Lucas nesta tarefa: publicar somente XML para contabilidade e
  testar o envio para o destinatário indicado. O iFood do #1526 ficou separado.
- **297 testes focados aprovados**, incluindo mês com 1.201 notas sem truncar,
  consulta explícita de canceladas no Bling, filtro de emitente antes dos limites,
  reaproveitamento da coleta do período e eventos antigos já recebidos.
- O limite de documentos passou a 10.000; os limites de bytes e anexos continuam
  protegendo a entrega SMTP. A preparação não repete HTTP de todo o legado Bling.
- O gate completo de release passou na branch exclusiva; a formatação detectada
  no CI foi corrigida. O namespace fiscal HTTP apontado pelo Sonar é um
  identificador oficial sem conexão de rede, anotado especificamente como falso
  positivo. O IIFE da tela explicita o descarte da promessa com `void`.
- A consulta de produção foi somente leitura e auditada: SMTP configurado; uma
  emissão de setembro ainda tem situação oficial de processamento. Isso deve
  bloquear o lote desse mês, sem omitir a nota nem apresentar sucesso parcial.
- Nenhuma emissão, cancelamento ou alteração manual de situação fiscal foi feita
  para gerar massa de teste. Resultados de envio real serão registrados após deploy.
- A revisão final identificou que o normalizador legado interpreta o código 2
  com chave como autorização. A consulta oficial específica de canceladas agora
  preserva o payload bruto e marca o status efetivo como cancelado, exigindo seu
  comprovante fiscal. Testes com o normalizador real cobrem NF-e e NFC-e, inclusive
  a mesma nota retornada nas duas consultas sem consumir duas posições do limite
  e o bloqueio pelo coletor real quando falta o XML oficial do cancelamento.

Validação técnica local aprovada. Aceite funcional do Lucas e publicação em
produção pendentes. Próximo passo: revisar a tela e conferir destinatário/SMTP
antes de autorizar a publicação e ativar qualquer rotina na operação real.
