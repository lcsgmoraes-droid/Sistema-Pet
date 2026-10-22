# Taxas temporárias na calculadora iFood

| Campo | Valor |
|---|---|
| Data / responsável | 2026-10-21 / Lucas |
| Branch | `codex/ifood-taxas-simulacao` |
| Ambiente | DEV isolado `corepet-ifood-dev`, `http://127.0.0.1:18081` |
| Escopo | Simular preço e contribuição com taxas descartáveis |
| Executor / prioridade | Codex / P2 |
| Risco | Médio: estimativa financeira e separação entre rascunho e dados salvos |
| Domínios | Produto canônico e catálogo iFood |

## 1. Necessidade e requisitos

Lojistas precisam experimentar preços e taxas sem alterar o contrato cadastrado.
Aceite: recalcular contribuição e pendências com premissas temporárias,
restaurar as taxas salvas sem perder o preço em edição e preservar produto e
regras. A simulação deve continuar disponível a quem pode visualizar produtos.
Publicação remota e alteração do custo do produto estão fora deste escopo.

A calculadora da central permite escolher entre as taxas salvas na loja e taxas
temporárias: comissão de entrega própria, comissão de entrega iFood, pagamento,
tributos, despesa por unidade e meta opcional. Os campos usam componentes V2 e o
mesmo editor de domínio das regras da loja. Valor desconhecido continua distinto
de zero explicitamente informado.

## 2. Regras de negócio e dados

O preço, as taxas e a meta simulados ficam identificados na calculadora. Restaurar
as taxas da loja preserva o preço digitado. Alternar modalidade, atualizar a oferta
ou atravessar o início/fim da promoção preserva o rascunho de taxas. O custo do
produto, o estoque, a promoção e o acréscimo continuam vindo do cadastro.

## 3. Arquitetura e integrações

`POST /integracoes/ifood/catalogo/produto/simular-preco` aceita o objeto opcional
fechado `custos_simulados`, limitado aos seis campos de rentabilidade. Campo
omitido herda a regra salva; `null` significa desconhecido; zero é válido. Os
limites são compartilhados com a configuração: percentuais até 100%, meta até
99,99% e despesa até R$ 1.000.000, sem negativos, infinitos ou NaN.

O cálculo usa snapshots em memória, sem modificar os objetos ORM, criar regra,
executar DML/commit ou abrir cliente do iFood. Mantém `produtos.visualizar` e o
isolamento entre empresas. Não é necessária permissão de editar configurações
para experimentar taxas.

## 4. Segurança e privacidade

Usa autenticação e tenant da sessão existente; IDs de outra empresa retornam 404.
Não cria dados pessoais, novos segredos, permissões ou logs financeiros. As taxas
descartáveis existem somente na requisição e na memória da calculadora, sem
retenção em banco ou armazenamento do navegador. Respostas antigas são canceladas
e não podem liberar aplicação de um preço ainda não recalculado.

Aplicar preço continua sendo uma ação separada e autorizada por `produtos.editar`.
O PUT envia somente `preco_ifood`; depois é consultada a oferta canônica para
atualizar a central. Margens e pendências hipotéticas nunca viram oferta salva.
Se a gravação funcionar e a consulta falhar, a mensagem reconhece o salvamento e
bloqueia nova aplicação até recuperar a oferta.

## 5. Desenvolvimento e qualidade

- 102 testes backend iFood aprovados, incluindo ausência de gravação/envio com
  provedor habilitado, configuração ausente, empresa, leitura sem edição,
  promoção, herança, zero, nulo e valores inválidos.
- 67 testes frontend iFood aprovados, incluindo 19 testes do hook da calculadora:
  cancelamento de respostas antigas, rascunhos, restauração, promoção, aplicação
  apenas do preço e recuperação após falha da releitura.
- ESLint e Prettier focados, Ruff lint/formato e `npm run build` aprovados.
- HTTP real contra PostgreSQL DEV: produto fictício 2, preço salvo R$ 150 e custo
  R$ 60. Simulação de R$ 100 com comissões 15%/25%, pagamento 3%, tributos 4% e
  despesa R$ 2 produziu contribuição própria R$ 16/16% e iFood R$ 6/6%.
  Zero explícito produziu R$ 40; taxa desconhecida impediu calcular; comissão de
  100% produziu contribuição negativa; percentual 101 retornou HTTP 422.
- Comparação HTTP antes/depois confirmou preço, catálogo e regras salvos
  idênticos, e a simulação sem overrides voltou às taxas reais da loja.
- Navegador DEV: campos temporários V2 conferidos; preço de R$ 100 produziu
  R$ 16/16% na entrega própria e R$ 6/6% na entrega iFood. Restaurar taxas
  manteve R$ 100 digitado e voltou a R$ 10/10% na entrega iFood. Reabrir a tela
  confirmou o preço salvo de R$ 150, estoque 4 e contribuição própria real
  R$ 61,50/41%. A comparação HTTP posterior à edição visual também foi idêntica.
  Nenhum botão de aplicar preço ou salvar regras foi acionado.

## 6. Ambientes e homologação

Não há migration ou mudança de dependências. A preparação usa somente o DEV
isolado existente na porta 18081 e seus dados fictícios. Produção e seus dados
não foram alterados. Escrita, operação e polling iFood permanecem desativados
nesse DEV. A estimativa unitária continua sem incluir custos por pedido ou fixos.

Backend e frontend foram reconstruídos com os Dockerfiles do projeto no Compose
isolado. A instalação inicial das dependências do frontend levou sete minutos;
uma imagem temporária com bundle local permitiu iniciar a conferência enquanto
ela concluía. Ao final, o DEV voltou à imagem do Dockerfile oficial e a tela foi
reaberta nessa versão, sem modificar os dados fictícios.

Revisão técnica independente sem bugs acionáveis. O aceite de negócio em DEV
deve anteceder uma futura solicitação de publicação. O envio de anúncios ao
iFood continua fora desta entrega.

Registro de homologação: [cenários e resultados](../homologacoes/2026-10-21-taxas-temporarias-ifood.md).

## 7. Publicação e rollback

Entrega de frontend/backend, sem migration. Base `a3a8ff475`, branch identificada
na tabela. Uma publicação futura exige revisão do PR, release-check e autorização
explícita; o backend deve aceitar o payload novo antes da nova interface entrar.
Smoke futuro: saúde, simulação e configuração canônica intacta. Reverter código e
imagens anteriores se taxas hipotéticas aparecerem no catálogo salvo; não há
dado novo persistido para migrar ou apagar. Nenhuma publicação feita nesta tarefa.

## 8. Observabilidade e sustentação

A calculadora identifica taxas temporárias, meta simulada e oferta salva. Erros
de consulta permitem tentar novamente e mantêm rascunhos; aplicação fica bloqueada
sem oferta confiável. O indicador de sucesso é contribuição/memória coerentes
com as premissas enquanto GETs canônicos continuam idênticos. Como alternativa,
usar as taxas salvas da loja. Persistência inesperada deve interromper o aceite.

## 9. Mudança, comunicação e treinamento

A ajuda contextual explica taxa desconhecida, zero explícito, meta opcional,
restauração e aplicação somente do preço. Demonstração em DEV ao Lucas antes da
liberação aos lojistas; não há alteração na rotina de cadastro geral nem manual
externo a atualizar. Orientar o usuário a confirmar condições reais do contrato
antes de salvar regras da loja por sua tela própria.

## 10. Fechamento

Critérios técnicos, evidências, isolamento, documentação, homologação,
observabilidade e rollback registrados. Sem segredos ou artefatos locais no PR.
Decisão técnica: aprovado para revisão em DEV. Pendente somente aceite de negócio
do Lucas antes de uma eventual solicitação de produção, sem prazo imposto.
