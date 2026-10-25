# Conferência do Portal iFood pelo componente V2

## Escopo

Ampliação em DEV do mesmo componente usado pelo cadastro do produto e pela
Central do iFood. O usuário registra a disponibilidade observada no Portal,
inclusive quando a automação de estoque está ativa e seu acompanhamento está
estável. Não cria outro cadastro nem uma tela paralela.

Esta entrega não publica código ou anúncios em produção, não amplia a
allowlist do SKU 227 e não altera o intervalo da rotina. O teste real de
estoque da release anterior é evidência separada desta mudança de interface.

## Passo a passo para o usuário

1. No cadastro, abra **Conferir vínculo e envio**. Na Central do iFood,
   use o menu de ações do produto e **Conferir vínculo e publicação**.
   Confira a empresa, a loja e o EAN apresentados.
2. No Portal do Parceiro da mesma loja, faça uma nova busca pelo EAN e veja
   se é o mesmo produto e apresentação. A atualização de uma página de
   detalhes antiga pode apresentar dados anteriores.
3. Na seção **Acompanhe e registre a conferência no Portal**, informe
   **Produto localizado** ou **Produto não localizado**.
4. Se localizou o produto, em **Disponibilidade no Portal** escolha **Ativo**,
   **Inativo** ou **Não conferi**. A escolha inicia em **Não conferi** e não é
   preenchida pelo estoque ou pelo histórico. Uma quantidade zero não é
   transformada automaticamente em item inativo.
5. Informe preço e estoque somente se conferiu esses valores. Vazio é
   desconhecido; zero é uma declaração explícita. Informar esses campos
   registra a observação e não modifica o cadastro ou o anúncio.
6. Marque **Conferi agora a loja, o EAN e o resultado acima no Portal do
   Parceiro** e use **Registrar conferência manual**. Mudar qualquer uma das
   observações desmarca o aceite e exige uma nova confirmação consciente.
7. Se outro envio ou conferência mudar o acompanhamento, o aceite anterior
   não vale para a nova situação. Os campos em edição são preservados.
   Atualize o acompanhamento se solicitado, reconfira o Portal e marque um
   novo aceite. Não é feito registro automático com uma nova referência.
8. O histórico apresenta a disponibilidade, preço, estoque, responsável e
   data da declaração. A declaração humana não se torna uma confirmação
   automática de publicação pelo iFood nem confirma envios futuros.

Quando o produto é marcado como não localizado, a nova declaração limpa os
campos de disponibilidade, preço e estoque. O histórico anterior permanece.
Trocar para outro produto também não reaproveita a observação em edição.

## Automação e pendências

O registro factual com histórico automático usa `kind=observation`. Não
revisa o vínculo nem altera `IfoodStockSyncState`, submissões, último saldo
aceito, chave de tentativa, falhas, fila ou `next_attempt_at`. Essa proteção
vale também se as flags da rotina estiverem desligadas, mas seu estado já
existir. Não há chamada de publicação, atualização remota ou ativação da
rotina por esse registro.

Envio manual e alteração de vínculo continuam bloqueados quando a automação
está ativa. A observação é permitida somente com acompanhamento estável;
`sending`, `uncertain` e `backoff` não são recuperados por esse fluxo comum.
Uma tentativa incerta exige conciliação específica, preservando as provas
originais. Registrar observação não é autorização para repetir uma tentativa.

Ausente, inativo ou disponibilidade desconhecida geram um bloqueio derivado
de novos despachos até uma conferência posterior de produto localizado e
ativo. O bloqueio não reescreve o estado ou recibo histórico. O resumo exibe
o motivo da espera e identifica o saldo como o último calculado pela
automação, que pode diferir do saldo atual mostrado no cadastro/lista.

Um estoque observado diferente do último aceito produz uma orientação de
divergência. Não troca a referência da fila, não reinicia o intervalo nem
provoca um PATCH para igualar a declaração. Quando o bloqueio de observação
é resolvido, continuam valendo as proteções, falhas e intervalos anteriores.

## Contrato e concorrência

O GET de acompanhamento retorna `confirmation_context_token`, opaco para a
interface. O POST de confirmação deve devolver o token capturado no momento
do aceite. A API valida a identidade e o histórico sob os locks existentes;
um token ausente ou referente a contexto alterado recusa o registro com 409.

A tela não substitui silenciosamente o token no envio da observação. Um novo
token desmarca o aceite, preservando os campos. Após 409, bloqueia ações até
atualização explícita e exige novo aceite; não dispara GET ou POST de
recuperação automaticamente. Resposta atrasada de outro produto não
preenche a tela atual. Cliques repetidos não geram operações concorrentes.

`portal_active` é nullable: `true`, `false` e `null` são fatos distintos. Não
é deduzido de `present`, quantidade, preço ou conferência anterior. O histórico
mostra **Não conferida** para registros antigos sem essa informação.

## Interface e validação

Foi reutilizado o `InputRadio` pronto do catálogo V2. Não foram criados
campos HTML crus, novo componente genérico ou formulário paralelo. O
componente e seu hook continuam compartilhados pelo cadastro e pela central.

Os testes de frontend cobrem disponibilidade com três estados, histórico sem
preenchimento indevido, produto ausente, troca de produto, rascunho, capacidade
revogada, operação automática estável, contexto alterado e 409 sem repetição.
O resumo cobre os três bloqueios derivados sem afirmar que o saldo histórico
é o estoque atual durante a espera.

Validação de frontend concluída: 35 casos nos dois arquivos focados de hook
e componente; 338 casos no conjunto `npm run test:ifood`. ESLint e Prettier
passaram nos quatro arquivos alterados e `npm run build` concluiu. O build
local não foi versionado.

Na validação de backend, passaram 197 testes focados: catálogo, estoque DEV,
estoque LIVE com transporte injetado e 11 casos novos de observação. A rodada
PostgreSQL passou 19 casos, incluindo 12 novos de concorrência, isolamento,
tokens antigos e migração. A revisão independente não encontrou bloqueadores.

O runtime isolado de DEV aplicou as migrações `w` e `x` e conferiu por hash os
65 arquivos de backend da imagem contra o fonte. O ensaio HTTP com PostgreSQL
registrou cinco observações no SKU fictício, recusou token repetido com 409,
distinguiu zero de desconhecido e confirmou os bloqueios derivados. Não
alterou produtos, lotes, movimentos, vendas, pagamentos, vínculo, fila ou
tentativas e não realizou chamadas ao provedor.

Na interface do DEV, uma conferência foi deixada em edição enquanto o
acompanhamento mudou por outro processo. O registro antigo foi recusado,
mantendo disponibilidade, preço e quantidade digitados. Atualizar preservou
esses campos e exigiu novo aceite; o registro seguinte foi gravado como
observação, sem publicação.

O cadastro foi aberto separadamente, sem salvar o produto: apresentou o mesmo
componente com a disponibilidade em **Não conferi** e campos observados vazios,
embora o histórico anterior mostrasse item ativo. Os testes antigos de pausa,
saldo zero e reposição também passaram usando o contexto atual exigido pelo
novo contrato; mantiveram as verificações de preço, conteúdo e janela.

Evidências de runtime e credenciais permanecem fora do Git. Nenhum resultado
deste documento autoriza deploy ou alteração do ambiente de produção.
