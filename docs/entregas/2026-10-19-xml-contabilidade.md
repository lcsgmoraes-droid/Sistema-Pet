# Ficha de entrega — XML para contabilidade

## Identificação

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| PR | #1526, branch de tarefa existente conforme AGENTS.md |
| Prioridade | P2 |
| Risco | Médio: transmissão de XML fiscal, destinatário e isolamento entre empresas |
| Domínios | Fiscal, configurações, e-mail e tarefas agendadas |

## 1. Necessidade e aceite

Enviar ao contador os XMLs das notas de saída individualmente após autorização,
ou reunir um período em ZIP para download, envio imediato ou agendado. Rotina
mensal opcional envia o mês anterior. Usuário pode combinar opções ou desligar
automatismos. Emissão/estoque/tributação existentes permanecem preservados.

Aceite: configuração persiste; período inclui ambas as datas em Brasília;
notas elegíveis do CNPJ correto; nenhum ZIP parcial silencioso; histórico
informa sucesso/falha e oferece cancelamento/repetição; processamento funciona
com navegador fechado. NFS-e e alterações de emissão/tributação estão fora do escopo.

## 2. Regras e dados

Configuração e fila pertencem ao tenant; migration `zzzzh20261019a1` aditiva,
RLS forçado e índices por tenant/estado. Histórico guarda destinatário, período,
tentativas e resultado; XML/ZIP não são copiados para a fila. Deduplicação
automática por documento/situação e mensal por competência. Claim persistido
e bloqueio de linhas protegem execuções concorrentes.

## 3. Arquitetura e integrações

Rotas `/contabilidade/xml`, schemas dedicados, serviços de coleta/envio e
scheduler do backend líder. Reutiliza clientes IntNFe/Bling e serviço SMTP.
Fila própria permite conservar datas/estado e gerar anexos em memória, sem
introduzir outro processo ou depender da memória do navegador. O caminho
síncrono SMTP na emissão foi descartado porque atrasaria/vincularia a emissão
à disponibilidade do e-mail. Há três tentativas; após queda durante SMTP,
repetição exige conferência humana para reduzir duplicidade.

## 4. Segurança e privacidade

Autenticação, módulo fiscal e `configuracoes.editar` obrigatórios. RLS e filtro
ORM, CNPJ emitente, chave/modelo/protocolo/direção/ambiente validados. Downloads
remotos reaproveitam allowlist HTTPS e limites existentes. Logs sem XML/segredos;
auditoria registra ator e metadados de ações. SMTP usa configuração secreta
existente. Finalidade: entrega fiscal solicitada pela empresa; retenção segue
política do domínio fiscal/auditoria, sem descarte novo de XML nesta entrega.

## 5. Qualidade

Fatias: configuração/fila; arquivos e integrações; hooks/scheduler; API/permissão;
tela V2 e ajuda; testes/revisão. Testes cobrem datas, ZIP/manifesto, faltantes,
idempotência, SMTP, estados e persistência. PostgreSQL local comprova políticas
RLS sob papel sem bypass e reversão da migration. Contratos HTTP cobrem
permissão negada, tenant e entradas inválidas. Emissão/cache existentes têm
regressão focada. Registro de resultados: documento de homologação abaixo.

## 6. Ambientes e homologação

Somente validação local, SQLite descartável e PostgreSQL do container DEV,
com schema/papel exclusivos e rollback. UI Playwright usa APIs simuladas e
dados fictícios, incluindo navegador em outro fuso. SMTP/IntNFe/Bling simulados:
nenhum e-mail real ou emissão fiscal foi disparado. Aceite de negócio do Lucas
e conferência com destinatário real ficam pendentes da publicação autorizada.

## 7. Publicação e rollback

Entrega backend/frontend/banco; sem alteração mobile. Aplicar migration e
reconstruir imagens pelo fluxo oficial depois do merge e autorização. Conferir
health, acesso à nova configuração, download conhecido e histórico do primeiro
envio autorizado. Abortar em falha de migration, exposição entre tenants ou
inconsistência fiscal. Rollback preserva tabelas novas e retorna imagens;
downgrade apaga histórico e exige avaliação explícita da perda.

## 8. Observabilidade e sustentação

Histórico por empresa e logs do scheduler, sem conteúdo fiscal. Sucesso técnico
é aceite SMTP, sem promessa de leitura/caixa de entrada. Credencial indisponível,
XML ausente/inválido e falha de rede devem aparecer como falhas. Alternativa:
baixar lote e entregar ao contador. Incidentes de exposição são bloqueantes;
falhas recorrentes de entrega precisam diagnóstico SMTP e eventual fila/bounce
central, sem alterar o fluxo fiscal em produção por improviso.

## 9. Comunicação

Guia `docs/GUIA_XML_CONTABILIDADE.md`, artigo na Central de Ajuda e catálogo de
Novidades com público ERP. Orientar sobre destinatário salvo, mês anterior,
horário de Brasília, cancelamento e significado do aceite SMTP antes de ativar.

## 10. Fechamento

Implementação e validação técnica local registradas em
`docs/homologacoes/2026-10-19-xml-contabilidade.md`. Publicação em produção e
aceite funcional do responsável pelo negócio pendentes. Esta ficha não autoriza deploy.
