# Telefone único por pessoa nas lojas do grupo

## 1. Identificação e resultado esperado

Solicitação complementar de Lucas: impedir novas pessoas com telefone já
vinculado a outra pessoa. Lucas confirmou que a regra vale entre todas as lojas
do mesmo grupo. Empresas independentes continuam separadas. O registro da tarefa
fica no item 16 do checklist de melhorias de 26/10/2026.

Entrega concluída em produção pelo PR **#1573**, integrado por squash na `main`
**`833a962d21701b6b2f2766aa84653f3b52fe50b9`** em 27/10/2026.

## 2. Regra de negócio

Telefone, celular e contatos adicionais compartilham a mesma regra. Máscaras e
DDI brasileiro `55`/`0055` são normalizados apenas pelos comprimentos conhecidos;
não se inventam DDD, nono dígito, ramal ou divisão de números legados. Vazio não
reserva número; permanecem as validações de preenchimento já existentes.

Uma pessoa pode manter seu próprio número. Inativos não fundidos continuam
reservando seus contatos. Um alias já fundido não reserva novamente o telefone.
Duplicidades legadas não são apagadas nem fundidas: manter, retirar ou editar
metadados continua possível; atribuir um número conflitante a outra pessoa é
bloqueado. Reenviar contatos existentes preserva seus IDs.

## 3. Fluxos atendidos

CRUD de Pessoas e modal do PDV, cadastro rápido mobile, usuários/funcionários,
perfil e cadastro e-commerce e importação Excel usam a validação comum. A proteção
no banco também cobre importadores e SQL direto. Na importação Excel, falha de
uma linha é revertida por savepoint e não impede as demais linhas válidas.

O perfil do app deixa de fundir pessoas automaticamente ao mudar identidade.
Retorna conflito sem alterar conta, vínculos ou fichas. A leitura de uma conta já
vinculada não tenta completar telefone ocupado por outra pessoa; preserva o
vínculo sem impedir o acesso por esse preenchimento opcional.

No cadastro público, uma identidade ambígua retorna conflito antes de criar
usuário ou executar fusão. Variações de DDI podem reutilizar a mesma pessoa;
não autorizam escolher entre cadastros conflitantes de forma automática.

## 4. API, interface e privacidade

Conflito retorna HTTP 409 com `detail` textual, `error=pessoa_telefone_duplicado`
e `details` com o campo. O formulário abre Contatos e destaca telefone, celular
ou contato adicional; erros 422 continuam funcionando. Não se expõem nome,
código, ID ou telefone do cadastro conflitante em endpoints públicos.

As consultas de confirmação entre lojas retornam somente booleano. O escopo usa
todos os grupos comerciais ativos comuns; não inclui parceiros veterinários.
O RLS não é ampliado para permitir a leitura dos contatos de outra loja.

## 5. Persistência e concorrência

Migration `zzzzzc20261027a1`, sucessora de `zzzzzb20261027a1`: funções de
normalização/validação, índices funcionais não únicos e triggers. Não reescreve
telefones nem consolida pessoas. Migrações exigem a role administrativa com
BYPASSRLS, pois a função de verificação precisa considerar contatos protegidos
de outras lojas do grupo. Funções internas têm EXECUTE público revogado e
search_path fixo; a função pública valida o escopo do ator.

A ordem é barreira de topologia, escopos de telefone e tuplas. Escritas em lojas
independentes podem seguir paralelas. Novas atribuições exigem READ COMMITTED;
REPEATABLE READ/SERIALIZABLE são recusados para impedir validação com snapshot
antigo. Alterar membros/reativar grupos também verifica colisões entre lojas.

A fusão administrativa bloqueia telefone antes da comissão e das pessoas.
Arquiva o alias antes de copiar contatos dentro da mesma transação; rollback
restaura alias, contatos e referências se qualquer etapa falhar.

## 6. Validação em DEV

Testes focados de normalização, APIs, importação, mobile, usuários, perfil,
transporte HTTP e React aprovados. Os **18 testes PostgreSQL** passaram em banco
descartável local: campos cruzados, DDI, inserção em lote, legado, alias,
concorrência com commit/rollback, loja independente, multigrupos, contexto,
isolação, RLS sem BYPASSRLS, topologia e fusão atômica com falha injetada.

Fixtures e roles dos bancos PostgreSQL descartáveis foram removidos; nenhum dado
de produção foi usado nesses testes. O smoke de migrations passou nos três cenários, com RLS 3/3 e
24 testes PostgreSQL por cenário (18 de telefone e 6 de vigência financeira).

O aceite HTTP real e os **2/2 fluxos headless de interface** em Pessoas e PDV
passaram no runtime DEV da revisão `af83f49ff`. O CRUD de telefone testado é
idêntico ao da fonte final. Uma pessoa fictícia levou a contagem de **40 para
41**; duas tentativas de inclusão com telefone/celular e máscara `+55` retornaram
**409**, sem nova linha. Editar o próprio número retornou **200** e a busca pelo
número encontrou uma única pessoa. Na interface, a contagem permaneceu em
**41 → 41**: erro por campo, aba Contatos ativa, modal e dados preenchidos
preservados. Produto e subtotal do carrinho do PDV permaneceram iguais, sem
salvar venda ou movimentação financeira. Provas em
`runtime/tarefas-telefone-unico-20261027/aceite-http.json` e `aceite-ui.json`, com
capturas no mesmo diretório.

A etapa final do cadastro público ambíguo passou por **33 testes unitários**,
incluindo resposta **409**, **zero usuários criados** e **zero fusões** no caso
de conflito. O gate completo passou na head
**`e2ed899d213da5d95d833e248c6ae93e3915484f`**. Os **13/13 checks do PR**,
incluindo Sonar, foram aprovados. Na main integrada, os **8/8 checks obrigatórios**
e os **nove resultados publicados** ficaram em `SUCCESS`. Evidências em
`runtime/tarefas-telefone-unico-20261027/release-gate-pr1573-e2ed899d.json` e
`runtime/tarefas-telefone-unico-20261027/release-gate-main-833a962d.json`.

## 7. Publicação

O deploy oficial foi concluído em **27/10/2026 às 00:48:45 BRT**, com saída zero,
após a integração do PR **#1573**. A revisão pública confirmou o commit completo
**`833a962d21701b6b2f2766aa84653f3b52fe50b9`** e a migration
**`zzzzzc20261027a1`**.

Backups dessa publicação:

- Banco: `/opt/petshop/backups/db/petshop_prod_20261027_004747.dump`.
- Operacional: `/opt/petshop/backups/deploy_20261027_004645`.

Logs em `runtime/tarefas-telefone-unico-20261027/deploy-producao.log` e
`runtime/tarefas-telefone-unico-20261027/status-producao.log`.

A mudança é web/backend; não altera código nem
dependências nativas do app, portanto não exige novo binário ou OTA adicional.

## 8. Verificação após publicação

A verificação oficial confirmou **cinco containers healthy**, health público
correto, watchdog healthy, revisão pública e migration indicadas acima.

A consulta de metadados, somente de leitura, confirmou **oito triggers ativos**,
**três índices válidos**, **nove funções privadas sem EXECUTE público** e
**dois wrappers SECURITY DEFINER** com owner BYPASSRLS e search_path fixo.
A normalização de prefixos `+55`/`0055` e do DDD `55` foi aprovada com valores
fictícios enviados somente à função. Evidência em
`runtime/tarefas-telefone-unico-20261027/guard-producao.json`.

Nenhuma pessoa fictícia foi cadastrada e nenhuma fusão foi executada em produção
nesta tarefa. As provas transacionais de criação/edição e concorrência
permanecem em DEV/CI.

## 9. Reversão e operação

Preservar cadastros, contas, carimbos e histórico. O downgrade apenas retira a
proteção e seus índices/funções; não desfaz dados. Uma reversão de produção
requer o procedimento e autorização do projeto. Novos conflitos devem ser
resolvidos selecionando a pessoa correta ou corrigindo o telefone, com fusão
administrativa somente quando especificamente autorizada.

## 10. Estado

- [x] Regra de grupo confirmada pelo Lucas.
- [x] Implementação e regressões focadas em DEV.
- [x] Concorrência e RLS comprovados em PostgreSQL descartável.
- [x] Migrations smoke nos três cenários e RLS 3/3.
- [x] Aceite HTTP real e dois fluxos de interface em DEV, sem duplicata ou venda gravada.
- [x] Gate completo e checks do PR/main aprovados.
- [x] PR integrado, publicação e conferência técnica de produção.

**Decisão: item 16 concluído e publicado em produção.** As 15 entregas anteriores
permanecem registradas no checklist. A conferência no aparelho físico da Michele
pertence ao acompanhamento anterior, continua pendente e não integra o aceite
desta extensão de telefone único.

Evidências locais: `runtime/tarefas-telefone-unico-20261027/` (ignorado pelo Git).
