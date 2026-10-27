# Melhorias operacionais: PDV, buscas, recebimentos e comissões

## Identificação

| Campo                  | Valor                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------- |
| Data                   | 26/10/2026                                                                            |
| Responsável de negócio | Lucas Guerra                                                                          |
| Executor técnico       | Codex, com revisão entre as frentes                                                   |
| Issue/PR               | PR #1567 integrado por squash na `main`: `3f2e78f34ecfae558431008832452fa9ad22dfb6`   |
| Prioridade             | P1: integridade financeira e continuidade da operação                                 |
| Risco                  | Alto: recebimentos, comissões, migrations e correção administrativa de vínculo de app |
| Domínios               | Pessoas, produtos, PDV, campanhas, histórico, financeiro, caixas e app mobile         |

O estado de cada item e as evidências estão no
[checklist operacional](../TAREFAS_MELHORIAS_OPERACIONAIS_2026-10-26.md).
Consultar também o [inventário das buscas](../INVENTARIO_BUSCAS_PESSOAS_PRODUTOS.md)
e o [procedimento do vínculo de app/carimbo](../CORRECAO_VINCULO_APP_CARIMBOS.md).

## 1. Necessidade e requisitos

Lucas relatou dificuldade para editar pessoas durante a venda, buscas diferentes
entre telas, históricos lentos, recebimentos sem parcelamento/caixa explícito,
status e observações incorretos após baixa em lote e falta de grupos/comissão fixa.
O caso de carimbo manual no app e o alcance da importação também exigiram diagnóstico.

O aceite é editar a pessoa preservando a venda, pesquisar por código público e
palavras com prioridade consistente, abrir históricos por páginas e registrar
recebimentos completos com parcelas, caixa, data e observação. Comissões devem
permitir grupos reutilizáveis e valor por unidade para novas vendas, sem duplicar
contas nem recalcular snapshots anteriores. A correção real do vínculo do app foi
executada e validada tecnicamente; a conferência no aparelho físico permanece
como acompanhamento separado.

O escopo abrange os 15 itens do checklist e 85 campos/telas/adaptadores mapeados.
Regras de elegibilidade de estoque, permissões, scanner e consultas especializadas
permanecem nos respectivos serviços. Novo binário mobile e reprocessamento de
comissões antigas ficam fora do escopo.

## 2. Regras de negócio e dados

- Códigos de pessoa/produto exibidos ao usuário vêm do cadastro público; IDs
  internos continuam nos vínculos técnicos.
- Recebimento identifica o caixa escolhido. Mais de um caixa pode estar reaberto;
  a escolha não transfere movimentos anteriores entre caixas.
- O pagamento do cliente no cartão e o repasse da operadora são eventos distintos.
  Repasse permanece previsto até liquidação, inclusive em uma parcela com prazo
  zero; sua liquidação não gera outra comissão nem snapshot de comissão zero.
- Parcelamento preserva o total em centavos; baixas e reenvios mantêm vínculos,
  data, observação e histórico, com proteção contra duplicação e NSU repetida.
- Comissão fixa é por unidade: R$ 5,00 × 2 = R$ 10,00. Quantidades fracionadas e
  recebimentos parciais são proporcionais. Novas configurações não recalculam
  vendas anteriores; grupos provisionam somente comissões já calculadas e sem
  conta a pagar.
- A vigência passa a usar a inclusão técnica imutável da venda, com relógio do
  banco e fuso explícito. Venda já aberta mantém a regra de sua inclusão, mesmo
  quando o primeiro pagamento ou outras parcelas ocorrem após a mudança. A data
  comercial editável não troca a regra. Na entrada dessa proteção, as regras
  legadas atuais formam o baseline das vendas existentes; não se reconstituem
  versões anteriores que nunca foram guardadas. Alterações futuras, inclusões e
  desativações/exclusões são versionadas no mesmo commit.
- Migrations A1/A2/A3 criam grupos/valor fixo, dados de recebimento/caixa e índices
  para histórico. A publicação oficial aplicou o grafo de migrations até a head
  única `zzzzzb20261027a1`, incluindo A4 e o caminho fiscal integrado da `main`.
- A4 acrescenta a âncora técnica e o histórico de vigência, com RLS e vínculo de
  pessoa preservável na fusão. A âncora não aceita alteração nem data enviada
  pelo usuário; snapshots de comissão anteriores permanecem intactos.
- A consulta confirmou dados importados do Simplesvet até 18/09/2026: 111.266
  vendas, desde 19/11/2019. Isso não comprova a data de execução da importação.
- A correção do caso real exige unificação administrativa revisada. Histórico,
  perfis, cargo, referências de vendas, créditos e grants devem ser preservados,
  conforme o procedimento específico; não lançar carimbo compensatório.

## 3. Arquitetura e integrações

As células V2 `BuscaPessoa`, `BuscaProduto` e `BuscaProdutoMultiplo` compartilham
apresentação e ordenação. Adaptadores mantêm as APIs e os filtros de domínio;
requisições canceladas/atrasadas não substituem a seleção atual. A edição de
pessoa no PDV reutiliza a edição existente.

Recebimentos compartilham campos de forma, cartão, parcelas e caixa. Serviços
financeiros mantêm transação, bloqueio, tenant e idempotência; grupos reutilizam
o provisionamento de comissões. O histórico pagina no banco com índices próprios.
Duplicar os formulários e recalcular comissão histórica foram descartados para
preservar manutenção e rastreabilidade.

Não há integração externa nova neste escopo operacional. A publicação mobile usou
EAS Update após o backend, nos runtimes 1.0.3 e 1.0.4 para Android/iOS. Falhas de rede nas consultas mantêm erro
visível e tentativa de atualização; falhas financeiras não devem confirmar baixa
parcial de um lote transacional.

## 4. Segurança e privacidade

Autenticação, permissões e módulo contratado continuam exigidos. Consultas,
grupos, provisionamento e recebimentos filtram tenant; referências estrangeiras
não podem ser reutilizadas por outra empresa. A fusão exige autorização e revisão
administrativa, sem alterar o papel de acesso ou quitar cobranças.

O caso real foi consultado com autorização, em modo de leitura, e a fusão
administrativa foi executada após a autorização específica. Credenciais,
tokens, telefones e prévias completas ficam fora do Git. Logs identificam operação,
estado e referências necessárias à auditoria; não devem registrar segredos.
Os dados pessoais continuam destinados ao cadastro, atendimento, acesso e histórico
financeiro existentes. Não há novo uso ou política de retenção.

Regressões verificaram isolamento, proteção de perfis, NSU, reenvio e rollback.

## 5. Desenvolvimento e qualidade

A entrega foi dividida em busca/PDV, financeiro/caixas, histórico/app e comissões,
com revisão cruzada dos pontos de maior risco. Contagens registradas no checklist,
sem somar suítes sobrepostas:

| Verificação concluída                                       | Resultado registrado     |
| ----------------------------------------------------------- | ------------------------ |
| iFood/frontend                                              | 324/324                  |
| Operacional/frontend                                        | 51/51                    |
| Faturamento/frontend                                        | 233/233                  |
| Gate financeiro e regressões                                | 301 aprovados, 6 pulados |
| Conferência focada após ajustes finais de metadados         | 29 aprovados             |
| Navegador real: edição no PDV e gestor                      | 2/2                      |
| Navegação adicional de buscas                               | 4/4                      |
| Ensaio de fusão com e sem colisão de perfil, PostgreSQL DEV | 2/2                      |

Também estão registrados aceites HTTP de cartão/parcelas, caixa explícito, NSU,
histórico e comissão fixa; o navegador comprovou seleção múltipla, persistência
do grupo e preservação da venda anterior. Duas baixas de comissão totalizaram
R$ 0,82 + R$ 0,81 = R$ 1,63, sem duplicação no reenvio.

Na complementação A4, quatro cenários PostgreSQL verificaram fronteiras de
vigência, fuso de São Paulo, exclusão/desativação, tenant, transferência na fusão
e recusa da alteração da âncora. Foram repetidos nos três bancos descartáveis do
smoke de migração. O aceite em navegador também recebeu uma venda ainda aberta e
uma parcela pendente após mudar R$ 3,00 para R$ 5,00: ambas mantiveram R$ 3,00.
A venda criada antes da primeira regra permaneceu sem comissão; somente a nova
venda recebeu R$ 5,00. Esses aceites não substituem o novo gate da revisão final.

Dois cenários adicionais com conexões simultâneas reproduziram a troca indevida
de regra após um commit concorrente. O bloqueio por empresa foi corrigido:
alterações de regra e inclusão da venda aguardam a transação anterior, enquanto
duas vendas da mesma empresa e operações de outra empresa continuam concorrentes.
Os seis cenários PostgreSQL passaram após essa correção; a fusão adquire o mesmo
bloqueio antes de bloquear pessoas, preservando a ordem de aquisição.

Build frontend de produção, ESLint e Prettier completos passaram. O
`FLUXO_UNICO.bat release-check` completo foi aprovado sobre a árvore `6dbed4d3`,
integrada pelo PR #1567. Os oito checks oficiais passaram no commit da `main`
`3f2e78f34ecfae558431008832452fa9ad22dfb6`; a evidência está em
`runtime/tarefas-melhorias-20261026/release-gate-main-3f2e78f3.json`. As contagens
anteriores registram suas etapas de validação e não devem ser somadas.

## 6. Ambientes e homologação

Testes automatizados com escrita usaram DEV local e massa fictícia, com autenticação própria.
Ensaios PostgreSQL da fusão usaram transação e rollback; não persistiram o caso
real. Credenciais de teste e capturas de navegador ficam em diretórios ignorados.
Em produção foram executados o deploy oficial, as migrations e a fusão autorizada
do vínculo da Michele, além das consultas e verificações registradas no checklist.

O checklist e o procedimento de vínculo registram a homologação técnica e os
resultados produtivos. A correção real da Michele e a publicação OTA dos dois
runtimes foram concluídas; o handler de benefícios para a conta 84 retorna o
saldo correto. A conferência humana no aparelho físico permanece pendente, separada do
aceite técnico publicado. A falha preexistente da suíte de política de push está
descrita no inventário; ela não foi ocultada nem declarada aprovada.

O contrato `test-modal-nova-conta-pagar-refactor.mjs` também já falha em
`origin/main`: exige a rota antiga `/clientes/?tipo_cadastro=fornecedor`, ausente
nos arquivos do modal, enquanto o controller da base já consulta
`/clientes/?is_fornecedor=true`. Teste e controller atuais são idênticos aos da
base; o seletor compartilhado já filtrava `is_fornecedor: true`. A comparação foi
registrada sem alterar esse teste ou ampliar o escopo da entrega.

## 7. Publicação e rollback

Entrega de backend, frontend, migrations, documentação e mobile OTA. Checkpoints
históricos: implementação `ac143f11a` e integração da main `297059ce8`. O PR
**#1567** foi integrado por squash no commit
**`3f2e78f34ecfae558431008832452fa9ad22dfb6`** da `main`.

O deploy oficial foi concluído em **26/10/2026 às 22:35:49 BRT**, com a head
`zzzzzb20261027a1` e revisão servida `3f2e78f3`. Os **cinco containers estão
healthy**; health público e watchdog também foram conferidos. O upgrade seguiu o
grafo oficial até a união de A4 com a linha fiscal da `main`.

Backups registrados:

- Banco: `/opt/petshop/backups/db/petshop_prod_20261026_223444.dump`.
- Operacional: `/opt/petshop/backups/deploy_20261026_223341`.

Publicação OTA concluída com saída zero no canal `production`, para Android e
iOS, usando o mesmo JavaScript/assets do commit publicado:

| Runtime | Horário da publicação em 26/10/2026 (BRT) | Grupo OTA                              |
| ------- | ----------------------------------------- | -------------------------------------- |
| 1.0.4   | 22:36:47                                  | `9e3a71b4-8882-4a7d-a778-0e8fbaffa060` |
| 1.0.3   | 22:37:02                                  | `b736b409-f55d-41e7-aad1-348339ee6c99` |

Versões, runtimes, números e configurações dos binários foram preservados,
conforme o [guia de release mobile](../GUIA_RELEASE_APP_MOBILE_EAS.md). O resumo
dos quatro updates, com IDs por plataforma e horários UTC, está em
`runtime/tarefas-melhorias-20261026/ota-publicacao-resumo.json`.

A fusão autorizada foi concluída às **22:38:01 BRT**, auditoria **227**:
principal **47188/código 2061**, duplicado **50401/código 10851** inativo e
apontando ao principal. Conta **84**, cargos de `UserTenant`, crédito zero e
flags de cliente/funcionária foram preservados. As **306 vendas** mantiveram IDs,
números, status e totais; carimbo **13739** preservado, com retorno de **1/meta 12**
no handler `meus_beneficios`.

Os seis grants **391–396** conservaram IDs, datas, notas e concedentes ao serem
transferidos. O total final é de **sete perfis**: o serviço materializou o perfil
`funcionario` derivado da flag legada já existente, com grant **458** auditado pelo
ator **83**. A conferência posterior somente de leitura aprovou essa derivação
específica, sem aceitar perfis adicionais arbitrários. O procedimento detalhado
e os limites de preservação estão no documento de vínculo.

Abortar diante de falha no gate, migration, health, isolamento, saldo ou conferência
da prévia. Rollback de aplicação/OTA usa a revisão/grupo anterior pelo fluxo
oficial. Preservar pagamentos, comissões e histórico já gravados; não executar
downgrade destrutivo com dados novos. A fusão não possui desfazer automático:
guardar prévia/auditoria e tratar qualquer reversão como correção administrativa
específica, sem restaurar banco inteiro ou apagar movimentações.

## 8. Observabilidade e sustentação

Conferir o histórico financeiro com data, observação, caixa e operação original;
reenvios devem manter os mesmos valores e referências. No cartão, comparar
previsto, realizado e liquidação; no relatório, conferir código público e grupo.
Históricos devem abrir por página e permitir nova tentativa em falha de rede.

Indicadores de sucesso: venda preservada após edição, buscas com código exato em
primeiro lugar, saldo pago fora de vencidos, ausência de comissão duplicada e
carimbo disponível na pessoa correta após a correção autorizada. Divergência de
saldo, repasse ou acesso entre empresas é incidente P1: interromper a operação
afetada e investigar pelos vínculos/auditoria, sem repetir baixas ou carimbos.
Recorrência após a publicação deve reabrir o item correspondente do checklist.

Na conferência operacional de produção, o histórico de Fernanda abriu em
**1.584 ms** (aproximadamente **1,58 s**) e a paginação avançou de **1/21** para
**2/21**. O título **11119** de Osvaldo consta como **recebido integralmente**,
com saldo **zero**, data **26/10/2026** e observação
**“Baixa em lote - pix”** no histórico. As consultas não registraram baixa nem
outra alteração financeira.

Essa conferência também encontrou uma pendência de exibição: o modal de detalhes
da conta ainda mostra o ID interno **47644** como código do cliente, em vez do
código público **1848**. O item 05 do checklist foi reaberto; a correção pontual
está em andamento e ainda requer validação e publicação. Evidências em
`runtime/tarefas-melhorias-20261026/fernanda-historico-producao.json` e
`runtime/tarefas-melhorias-20261026/osvaldo-conta-producao.json`.

## 9. Mudança, comunicação e treinamento

Atualizada a base da **Central de Ajuda**, em
`frontend/src/pages/centralAjuda/centralAjudaKnowledge.js`, com edição da pessoa
no PDV, recebimento parcelado/caixa e grupos/comissão fixa. A página existente
carrega esse catálogo; não foi criado outro fluxo de ajuda.

Após disponibilização, orientar operadores sobre o lápis da pessoa, conferência
do caixa e dados do cartão. Orientar gestores sobre seleção múltipla, grupos,
valor por unidade para novas vendas e diferença entre pagamento e repasse.
O vínculo, saldo do carimbo e publicação OTA já foram confirmados tecnicamente.
A conferência no aparelho físico da cliente continua como acompanhamento humano;
não declarar esse teste como realizado sem sua confirmação.

## 10. Fechamento

- [x] Requisitos e evidências DEV registrados, com limites explícitos.
- [x] Tenant, permissões, dados e auditoria avaliados.
- [x] Documentação e Central de Ajuda atualizadas.
- [x] Plano de publicação, observabilidade, rollback e comunicação definido.
- [x] Gate completo final e PR integrado registrados.
- [x] Publicação principal, migrations, OTA e smoke técnico registrados.
- [x] Correção real do vínculo e saldo do benefício conferidos em produção.
- [ ] Correção pontual do código público no modal de detalhes validada e publicada.
- [ ] Conferência humana no aparelho físico da cliente, como acompanhamento separado.

Decisão: **entrega principal publicada, com ajuste pontual de exibição em
fechamento**. O item 05 permanece aberto até a correção do modal ser validada e
publicada. A conferência no aparelho físico não bloqueia a entrega técnica do
vínculo; seu estado permanece explícito no checklist.
