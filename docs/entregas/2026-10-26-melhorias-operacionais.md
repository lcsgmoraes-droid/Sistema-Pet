# Melhorias operacionais: PDV, buscas, recebimentos e comissões

## Identificação

| Campo                  | Valor                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------- |
| Data                   | 26/10/2026                                                                            |
| Responsável de negócio | Lucas Guerra                                                                          |
| Executor técnico       | Codex, com revisão entre as frentes                                                   |
| Issue/PR               | PR ainda em preparação na branch `feat/20261019-1708-cadastro-e-central-ifood`        |
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
contas nem recalcular snapshots anteriores. A correção real do vínculo do app tem
aceite próprio e permanece pendente de execução.

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
  para histórico. Foram aplicadas em PostgreSQL DEV; produção ainda não foi migrada.
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

Não há integração externa nova. A publicação mobile usa EAS Update após o backend,
nos runtimes 1.0.3 e 1.0.4 para Android/iOS. Falhas de rede nas consultas mantêm erro
visível e tentativa de atualização; falhas financeiras não devem confirmar baixa
parcial de um lote transacional.

## 4. Segurança e privacidade

Autenticação, permissões e módulo contratado continuam exigidos. Consultas,
grupos, provisionamento e recebimentos filtram tenant; referências estrangeiras
não podem ser reutilizadas por outra empresa. A fusão exige autorização e revisão
administrativa, sem alterar o papel de acesso ou quitar cobranças.

O caso real foi consultado com autorização, em modo de leitura. Credenciais,
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

Build frontend de produção, ESLint e Prettier completos passaram na etapa
registrada. O check inicial e as frentes focadas passaram; o
`FLUXO_UNICO.bat release-check` completo segue pendente de conclusão após as
últimas correções. Isso não declara toda a suíte ou a produção aprovadas.

## 6. Ambientes e homologação

Testes com escrita usaram DEV local e massa fictícia, com autenticação própria.
Ensaios PostgreSQL da fusão usaram transação e rollback; não persistiram o caso
real. Credenciais de teste e capturas de navegador ficam em diretórios ignorados.
Em produção ocorreram somente as consultas autorizadas registradas no checklist.

O checklist e o procedimento de vínculo registram a homologação técnica local.
Não foi emitido aceite humano de funcionamento no aparelho da cliente: a
correção real da Michele, a atualização OTA aplicada e a conferência no app
autenticado permanecem pendentes. A falha preexistente da suíte de política de
push está descrita no inventário; ela não foi ocultada nem declarada aprovada.

O contrato `test-modal-nova-conta-pagar-refactor.mjs` também já falha em
`origin/main`: exige a rota antiga `/clientes/?tipo_cadastro=fornecedor`, ausente
nos arquivos do modal, enquanto o controller da base já consulta
`/clientes/?is_fornecedor=true`. Teste e controller atuais são idênticos aos da
base; o seletor compartilhado já filtrava `is_fornecedor: true`. A comparação foi
registrada sem alterar esse teste ou ampliar o escopo da entrega.

## 7. Publicação e rollback

Entrega de backend, frontend, migrations, documentação e mobile OTA. Checkpoints
registrados: implementação `ac143f11a` e integração da main `297059ce8`. O commit
final e o PR deverão constar no registro de publicação quando preparados.

Sequência prevista: concluir o gate e a revisão; finalizar a branch/PR pelo fluxo
oficial; aplicar A1 → A2 → A3 → A4 e publicar backend/frontend; conferir health,
revisão implantada e smoke; executar a correção administrativa autorizada do
vínculo após conferir a prévia; publicar a OTA nos dois runtimes. Preservar
versão, runtime e números dos binários instalados, seguindo o
[guia de release mobile](../GUIA_RELEASE_APP_MOBILE_EAS.md).

Publicação, migrations de produção, OTA e correção real ainda não ocorreram nesta
ficha. A autorização e seus limites estão registrados no checklist; a execução
continua condicionada às etapas pendentes.

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
Enquanto não houver publicação, usar os fluxos existentes; recorrência após o
smoke deve reabrir o item correspondente do checklist.

## 9. Mudança, comunicação e treinamento

Atualizada a base da **Central de Ajuda**, em
`frontend/src/pages/centralAjuda/centralAjudaKnowledge.js`, com edição da pessoa
no PDV, recebimento parcelado/caixa e grupos/comissão fixa. A página existente
carrega esse catálogo; não foi criado outro fluxo de ajuda.

Após disponibilização, orientar operadores sobre o lápis da pessoa, conferência
do caixa e dados do cartão. Orientar gestores sobre seleção múltipla, grupos,
valor por unidade para novas vendas e diferença entre pagamento e repasse.
Conferir o carimbo no app real depois da correção e aplicação da OTA. Não anunciar
essas etapas como concluídas antes do registro de publicação e do smoke.

## 10. Fechamento

- [x] Requisitos e evidências DEV registrados, com limites explícitos.
- [x] Tenant, permissões, dados e auditoria avaliados.
- [x] Documentação e Central de Ajuda atualizadas.
- [x] Plano de publicação, observabilidade, rollback e comunicação definido.
- [ ] Gate completo final e PR revisável concluídos.
- [ ] Publicação e smoke registrados.
- [ ] Correção real do vínculo e conferência no aparelho concluídas.

Decisão: **aceite técnico DEV com pendências de fechamento**. Lucas e o executor
concluirão as etapas abertas na sequência do checklist; não há prazo de publicação
confirmado nesta ficha.
