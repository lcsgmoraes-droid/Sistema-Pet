# Ficha de entrega — XML para contabilidade

## Identificação

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| PR | Publicação exclusiva de XML, separada do #1526 conforme solicitação do Lucas |
| Prioridade | P2 |
| Risco | Médio: transmissão de XML fiscal, destinatário e isolamento entre empresas |
| Domínios | Fiscal, configurações, e-mail e tarefas agendadas |

## 1. Necessidade e aceite

Enviar cada XML de nota emitida no CorePet pela IntNFe em produção ou de seu
evento registrado individualmente, como
opção independente do envio mensal da competência anterior completa. Usuário
escolhe dia/hora da execução mensal; períodos livres ficam exclusivamente no
download/envio manual. Lotes separam ZIPs por tipo: notas, cancelamentos,
cartas de correção e demais eventos. Emissão, estoque e tributação existentes
permanecem preservados.

Aceite: configuração persiste; período inclui ambas as datas em Brasília;
notas CorePet elegíveis do CNPJ correto, incluindo canceladas e todos os eventos
oficiais retornados pelo emissor, inclusive evento do período em nota antiga;
nenhum ZIP parcial silencioso; histórico
informa sucesso/falha e oferece cancelamento/repetição; processamento funciona
com navegador fechado. Notas emitidas no Bling ou importadas de marketplaces,
NFS-e e alterações de emissão/tributação estão fora do escopo.

## 2. Regras e dados

Configuração e fila pertencem ao tenant; migration `zzzzh20261019a1` aditiva e
`zzzzi20261019a1` desativa/cancela fluxos legados pendentes por empresa,
RLS forçado e índices por tenant/estado. Histórico guarda destinatário, período,
tentativas e resultado; XML/ZIP não são copiados para a fila. Deduplicação
mensal por competência e individual por nota/identidade de evento. Histórico
antigo é preservado sem disparar retroativos na ativação. Não há agendamentos
de períodos livres. Monitoramento e comprovantes de eventos são persistidos
com RLS forçado e varredura periódica. Claim persistido
e bloqueio de linhas protegem execuções concorrentes.

## 3. Arquitetura e integrações

Rotas `/contabilidade/xml`, schemas dedicados, serviços de coleta/envio e
scheduler do backend líder. Reutiliza o cliente IntNFe e o serviço SMTP.
A origem é a venda com `nfe_provider=intnfe` e `nfe_ambiente=1`; o cache de notas
importadas não participa da seleção, do monitor ou de trabalhos individuais antigos.
Fila própria permite conservar datas/estado e gerar anexos em memória, sem
introduzir outro processo ou depender da memória do navegador. O caminho
síncrono SMTP na emissão foi descartado porque atrasaria/vincularia a emissão
à disponibilidade do e-mail. Há três tentativas; após queda durante SMTP,
repetição exige conferência humana para reduzir duplicidade.

## 4. Segurança e privacidade

Autenticação, módulo fiscal e `configuracoes.editar` obrigatórios. RLS e filtro
ORM, CNPJ emitente, chave/modelo/protocolo/direção/ambiente validados. Downloads
remotos usam o cliente autenticado IntNFe e limites existentes. Logs sem XML/segredos;
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
dados fictícios, incluindo navegador em outro fuso. SMTP e IntNFe são simulados
nesses testes. Após a publicação exclusiva autorizada do PR #1530, um XML
individual real chegou ao Gmail indicado, com SHA-256 recebido conferido.
O ajuste de origem exclusiva CorePet será validado e publicado no PR #1531.

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
`docs/homologacoes/2026-10-19-xml-contabilidade.md`. O PR #1530 foi publicado
com autorização do Lucas. O PR #1531 restringe a origem às notas CorePet e
aguarda os gates e a conferência dos envios reais. Esta ficha não autoriza deploy.
