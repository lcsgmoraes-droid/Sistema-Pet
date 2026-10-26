# Guia CorePet — integração com o iFood

**Situação: rascunho, pendente de validação do vínculo e da publicação.**

Última atualização: 25/10/2026. Público: responsáveis pelo catálogo de lojas
pet shop que usam ou desejam usar o iFood. Plataforma: ERP web CorePet.

Este guia acompanha a implantação da integração. A consulta do catálogo e a
preparação local estão disponíveis. A solicitação e a aprovação de acesso do
aplicativo e o teste de conexão do ERP foram conferidos em uma jornada assistida.
O vínculo de itens existentes, o envio e a confirmação da publicação ainda
precisam ser validados antes de este documento virar um manual definitivo.

## Objetivo

Preparar produtos no próprio cadastro do CorePet e acompanhar sua integração
com o iFood. Para lojas que já vendem no canal, a implantação deve preservar os
anúncios existentes e começar pela conferência de um único produto.

A integração deste guia é feita pelo aplicativo próprio **CorePet**, criado no
iFood Developer. Outro integrador que já apareça na conta serve apenas como
informação da operação anterior; ele não é o aplicativo usado nesta implantação.

O cadastro do produto é único: a Central do iFood abre o mesmo componente de
cadastro e edição usado no restante do ERP.

## Antes de começar

- Tenha acesso à empresa correta no CorePet e ao iFood da mesma loja.
- Confirme quem atualiza preços e estoque hoje e se existe outro integrador.
- Separe um produto simples, embalado, com identificação e estoque disponíveis.
- Para estimar contribuição, confira o custo do produto e as taxas reais do
  contrato. Deixe como desconhecido o que ainda não foi confirmado.
- Combine quais informações o CorePet assumirá e quais continuarão sendo
  atualizadas pela rotina atual durante o piloto.

## 1. Confira a empresa selecionada

1. Entre no CorePet e confira o nome da empresa selecionada.
2. No iFood, confira a loja selecionada antes de consultar seu catálogo.
3. Verifique que os dois acessos correspondem ao mesmo estabelecimento.
4. Só então pesquise o produto por SKU, nome ou código de barras.

Uma pesquisa sem resultado em outra empresa não comprova ausência do produto.
Se houver dúvida sobre a empresa selecionada, corrija o acesso antes de criar
cadastros, alterar configurações ou tentar publicar.

## 2. Consulte o catálogo atual no iFood

Para pet shops, consulte a **Gestão de Catálogo** no Portal do Parceiro. O
catálogo dessa operação pertence ao fluxo de pet shops e mercados, também
chamado de **Groceries / Item**.

Se o **Cardápio** do Gestor de Pedidos mostrar **Nenhum restaurante disponível**,
isso, sozinho, não significa que a loja esteja sem produtos. Acesse o **Portal
do Parceiro → Catálogo** e confira a loja novamente.

Na Gestão de Catálogo, confira as situações apresentadas, como produtos ativos,
inativos, em análise ou para cadastrar. Em **Serviços e soluções → Integrações**,
verifique os integradores existentes. Um integrador aparecer como ativo não
comprova, por si só, que ele atualize preços ou estoque: confirme a operação
atual antes de assumir essas atualizações pelo CorePet.

Os nomes e a organização das telas externas podem variar. Se o caminho não
estiver disponível, registre a tela encontrada e peça orientação antes de
alterar uma integração que a loja já utiliza.

## 3. Consulte o produto no CorePet

1. Abra **Vendas e relacionamento → iFood**.
2. Pesquise o SKU do produto piloto e confira nome, apresentação e identificação.
3. Abra o cadastro do produto pelo atalho da central para revisar os dados.
4. Confira preço normal, custo, estoque disponível e eventual promoção exclusiva
   do iFood.
5. Revise as pendências e orientações apresentadas, incluindo foto e descrição.

Depois de conferir o produto piloto, a ação **Selecionar para iFood** registra
a intenção de venda no CorePet. Na jornada assistida, a central confirmou
**Produto selecionado** e passou a mostrar o item como **Pronto para envio**.
Essa ação salva a seleção local; não envia um anúncio. Confira que somente o
produto escolhido para o piloto entrou na seleção.

Se o atalho redirecionar à página pública ou ao login, entre novamente no
CorePet, confirme a empresa e retome a consulta. Só considere o cadastro
conferido depois que os dados do produto aparecerem.

O estoque disponível para o canal é calculado a partir do CorePet, considerando
reservas e segurança. Esse número na central não comprova que o mesmo saldo já
tenha sido enviado ao iFood.

## 4. Entenda preço, contribuição e pendências

- **Preço específico do iFood:** quando informado, é o preço regular exclusivo
  desse canal. Sem ele, o CorePet usa a regra de preço da loja.
- **Preço vigente:** considera a promoção exclusiva do iFood quando ela estiver
  dentro do período definido. Promoções de outros canais não são copiadas.
- **Contribuição estimada:** considera o preço, o custo do produto, a comissão
  do cenário escolhido, a taxa de pagamento, os tributos estimados e as demais
  despesas por unidade. Custos por pedido e custos fixos ficam fora da estimativa.
- **Taxa desconhecida:** impede calcular a contribuição. Zero é uma informação
  explícita e só deve ser usado quando aquela cobrança realmente não existir.
- **Pendências:** mostram o que ainda precisa de conferência ou preenchimento
  para o canal. A seleção para vender no iFood é independente dos demais canais.

O cenário de entrega na calculadora serve para estimar os custos; ele não
configura a entrega do produto nem altera o contrato da loja.

Para experimentar um preço sem gravar, use **Simular preço e margem**. Confira
os valores calculados e não acione **Aplicar preço ao produto** durante uma
consulta. Aplicar preço altera o preço específico salvo no CorePet; não é uma
confirmação de publicação no iFood.

## 5. Confira o vínculo e escolha o caminho de um produto

**Fluxo assistido implementado; rótulos revisados no código, ainda pendentes de
conferência visual em DEV e de validação real em produção.** Os passos abaixo
continuam em rascunho: não registram uma publicação ou um vínculo já concluídos.

Na Central do iFood, abra as ações do produto e escolha **Conferir vínculo e
publicação**. No cadastro único do produto, o mesmo fluxo fica no bloco
**Vínculo e publicação assistida**, pelo botão **Conferir vínculo e envio**.
Se houver alterações em edição, salve o cadastro antes das ações. O fluxo usa
a versão salva; não salva nem publica os campos em edição por conta própria.

O piloto trabalha com **um produto por vez**, sem operação em lote e sem
iniciar uma sincronização automática contínua. Confira a empresa, a loja, o
EAN e a apresentação, incluindo peso ou quantidade por embalagem. Nome
semelhante ou preço igual não bastam para estabelecer a correspondência.

### Produto já existente: vincular e atualizar somente estoque

1. Em **1. Confira o mesmo EAN no Portal**, use **Abrir Portal do Parceiro** e
   localize o mesmo EAN na loja correta. Confira também a apresentação e a
   situação do item.
2. Escolha **Já existe no iFood**, marque a confirmação da conferência e use
   **Registrar conferência do EAN**. Isso grava o vínculo e a declaração humana
   no CorePet; **não envia alteração ao iFood** e não copia automaticamente
   preços ou saldos do Portal para o cadastro.
3. Confira que o produto está selecionado para vender no iFood e que o saldo
   disponível no CorePet corresponde ao teste combinado. Corrija e salve pelo
   cadastro e pelos procedimentos normais de estoque, se necessário. O saldo
   enviado considera as reservas e a segurança; não é um saldo livre digitado
   na tela de envio.
4. Em **2. Prepare e revise antes de enviar**, desmarque **Preço regular** e
   deixe marcada somente **Estoque disponível**. Use **Preparar prévia de um
   produto**. **Preparar não envia nada ao iFood.**
5. Revise o EAN, o estoque e as pendências. Para este teste, a prévia deve
   mostrar apenas a atualização de estoque, sem preço regular enviado.
   Atualizar somente estoque preserva preço, promoção, nome, descrição, foto
   e canais existentes no iFood.
6. Somente com o teste autorizado, as pendências resolvidas e o envio
   habilitado, marque a confirmação da revisão e use **Enviar atualização de
   preço e/ou estoque**. O alcance é o campo escolhido, de um único produto.
   Confira o resultado conforme a seção 8.

### Produto novo: conferir ausência e preparar a criação

1. Consulte o EAN nas listas disponíveis do Portal da mesma loja, incluindo
   ativos, inativos, em análise e para cadastrar. Um item inativo ou em análise
   não deve ser tratado como ausente. Se a pesquisa não for conclusiva,
   esclareça a correspondência antes de tentar criar.
2. Em **1. Confira o mesmo EAN no Portal**, escolha **Não encontrei este EAN no
   Portal**, marque a confirmação da pesquisa e use **Registrar conferência do
   EAN**. Essa ação registra a ausência declarada; **não cria um anúncio** nem
   representa uma busca automática de todo o catálogo remoto.
3. Em **2. Prepare e revise antes de enviar**, use **Preparar prévia de um
   produto**. Revise o EAN, nome, apresentação, foto, descrição, preço, estoque
   e eventual promoção incluída na criação. Resolva as pendências no cadastro
   existente e salve antes de preparar novamente.
4. Somente com o teste autorizado e o envio habilitado, marque a confirmação
   da revisão e use **Publicar este produto**. A criação envolve somente esse
   produto, sem substituir ou reiniciar o catálogo da loja.
5. Mesmo depois de o envio ser aceito, confira o Portal conforme a seção 8.
   O aceite ainda não comprova publicação ou visibilidade no aplicativo.

Se mudar o EAN, a loja, o preço, o estoque ou o vínculo depois da preparação,
atualize o acompanhamento e prepare uma nova prévia antes de enviar. Quando o
envio estiver desabilitado, a prévia continua sendo somente uma conferência;
ela não libera uma publicação.

## 6. Autorize o aplicativo CorePet no iFood

**Solicitação e aprovação observadas na jornada assistida.** As etapas do
integrador e do lojista usam acessos diferentes.

### Solicitação feita pelo integrador CorePet

Esta parte é feita pela equipe responsável pela integração, no acesso próprio
do CorePet ao iFood Developer. O lojista comum não precisa entrar nessa conta.

1. O integrador abre **Meus aplicativos → CorePet → Permissões → Pedir
   autorização**.
2. Informa a identificação da loja, busca e confere o estabelecimento correto.
   A identificação pode ser consultada pelo responsável da loja em **Portal do
   Parceiro → Configurações → Perfil da loja**.
3. Revisa a solicitação, os aceites e as responsabilidades apresentados e a
   envia somente após confirmação do responsável.
4. O Developer pode exibir **Aguardando Ativação**, enquanto o cartão do CorePet
   no Portal do Parceiro apresenta **Permissão pendente**. Isso indica que falta
   a aprovação da loja.

### Aprovação feita pelo responsável da loja

1. No Portal do Parceiro da loja correta, abra **Serviços e soluções →
   Integrações**.
2. Localize o cartão **CorePet**, com permissão pendente, e use **Mais Ações →
   Permitir**.
3. Revise os acessos solicitados. Na jornada validada foram apresentados
   **Pedidos, Item, Eventos e Merchant**, além dos [Termos de Uso do
   iFood](https://developer.ifood.com.br/pt-BR/terms-of-use/partner). Se a
   solicitação recebida for diferente ou o aplicativo não for CorePet, esclareça
   a divergência antes de continuar.
4. Confirme os acessos e aceite os termos somente se estiver de acordo. Depois,
   use **Autorizar**.
5. Confira a resposta **Integração autorizada** e o cartão **CorePet — Ativo**.

Essa confirmação comprova a autorização da loja para o aplicativo. Ela ainda
não comprova conexão do ERP, publicação de produto, sincronização de estoque ou
entrada de pedidos. Não altere outra integração apenas porque o CorePet passou
a aparecer como ativo.

## 7. Confira a conexão do ERP e revise a primeira prévia

**Configuração e teste de conexão observados com sucesso.** A validação da
conexão é separada da ativação das rotinas e do envio de produtos.

1. No CorePet da empresa correta, abra **Configurações → Integrações → Abrir
   integração iFood**.
2. Confira o campo **Merchant ID da loja no iFood** com o identificador da mesma
   loja autorizada. Consulte a origem em **Portal do Parceiro → Configurações →
   Perfil da loja**. Não copie o identificador do aplicativo, de outra unidade
   ou de uma loja de testes.
3. Durante a preparação, mantenha **Ativar integração para esta empresa**
   desmarcado até concluir a validação. Se precisar corrigir a identificação,
   revise a configuração e use **Salvar configuração**, preservando as demais
   regras que não fazem parte da correção.
4. Use **Testar conexão**. Confira o selo **Conexão validada** e a mensagem
   **Loja localizada e conexão validada no iFood.**
5. Confirme que a opção de ativação continua desmarcada enquanto o restante do
   piloto é preparado. O teste bem-sucedido não exige iniciar as rotinas.
6. Se aparecer **Requer atenção** ou erro no teste, registre o resultado e
   procure o suporte para investigar. Não considere a conexão validada nem
   avance para publicação com base somente no cartão Ativo do Portal.

A implantação precisa confirmar que o ERP está conectado à mesma loja que
autorizou o aplicativo CorePet, com o catálogo correto de pet shop. A aprovação
no Portal do Parceiro não substitui essa conferência.

**Ativo no Portal do Parceiro** confirma a autorização do aplicativo. A opção
de ativação no ERP controla uma configuração da rotina da empresa. São estados
distintos; um não comprova o funcionamento do outro. Se a autorização estiver
ativa e o teste falhar, o suporte deve conferir se o ERP está usando o mesmo
aplicativo CorePet que recebeu a autorização da loja. A conexão só pode ser
considerada validada depois da conferência e de um teste bem-sucedido.

Antes do primeiro envio, a prévia deverá identificar um único produto, a loja,
a situação de vínculo, os campos que serão enviados e os valores antes e depois.
As informações que não fazem parte do teste devem ser preservadas.

**A prévia local de preparação já foi conferida em produção**, assim como a
conexão do ERP. O novo fluxo assistido das seções 5 e 8 é uma etapa separada:
seus rótulos foram revisados no código e ainda precisam de conferência visual
em DEV e de validação real em produção. Não considere vínculo ou envio
concluídos com base somente na prévia local.

Para um item novo, confirme antes que ele realmente não existe no catálogo.
Para um item publicado, conclua a correspondência antes de atualizar. O piloto
não deve substituir nem reiniciar o catálogo inteiro.

## 8. Confirme o resultado da publicação

**Roteiro em rascunho, pendente de conferência visual e execução real.**

Depois do envio assistido da seção 5, acompanhe **3. Acompanhe e registre a
conferência no Portal**:

1. Se aparecer **Aceito pela API — confira no Portal**, o iFood retornou o
   aceite de processamento (HTTP 202). Isso **não confirma a publicação** nem
   que o preço ou estoque já mudou no Portal ou no aplicativo.
2. Abra o Portal da mesma loja e pesquise o mesmo EAN. Para criação, confira
   o produto e a apresentação. Para atualização somente de estoque, confira
   o novo saldo e que preço e promoção foram preservados.
3. Informe **Produto localizado** ou **Produto não localizado**, conforme a
   conferência. Preço e estoque conferidos são opcionais: deixe vazio o que
   não verificou. Zero significa um valor explicitamente conferido, não
   ausência de informação.
4. Marque a confirmação da conferência e use **Registrar conferência manual**.
   O CorePet guarda a declaração humana com responsável e data. Ela não é
   uma confirmação automática do iFood e não confirma envios posteriores.
5. Se aparecer falha, envio em andamento ou resultado desconhecido, preserve
   o histórico e confira o Portal antes de tentar novamente. Não repita um
   envio apenas porque a resposta demorou; respeite as pendências e o
   intervalo apresentados pelo acompanhamento.

Os marcos precisam ser conferidos separadamente:

| Situação | O que comprova |
|---|---|
| Aplicativo autorizado pela loja | A loja concedeu os acessos apresentados ao aplicativo CorePet |
| Conexão do ERP conferida | O CorePet foi validado com a mesma loja autorizada |
| Pronto para envio | O cadastro passou nas validações locais |
| Conferência do EAN registrada | O responsável declarou a presença ou ausência do mesmo EAN no Portal; nenhum envio foi feito por essa ação |
| Prévia preparada | Os dados salvos de um produto foram preparados para revisão; nada foi enviado |
| Envio solicitado | Uma solicitação foi encaminhada |
| Aceito pela API | O iFood aceitou o processamento; o resultado ainda precisa de conferência |
| Conferência manual registrada | Um responsável registrou o que encontrou no Portal, com data; não é confirmação automática |
| Atualização de estoque conferida | O saldo do teste foi verificado no Portal, sem comprovar uma rotina contínua de sincronização |

**Pronto para envio não significa publicado.** O sucesso de uma requisição
também não substitui a conferência do resultado visível. A tabela explica os
marcos de validação; o roteiro e os rótulos ainda serão conferidos nas telas.

Este piloto cobre os dois caminhos assistidos: criar um produto novo e
vincular um existente para atualizar somente estoque. Pausa, reativação,
alteração de promoções, entrada de pedidos e baixa de estoque por venda
exigem validação própria antes de serem consideradas disponíveis ou automáticas.

## Estoque automático do SKU 227 — ensaio em DEV

Este ensaio é separado da publicação do SKU `018631.1`. Usa uma cópia de teste
do SKU `227`, já vinculado pelo mesmo EAN, e um simulador local do iFood. Não
ativa sincronização contínua na loja real nem libera os demais produtos.

1. Abra a empresa de testes, confira o SKU `227`, o EAN e o vínculo existente.
   Registre o saldo inicial conhecido e guarde os preços dos quatro canais.
2. Na Central iFood ou no mesmo componente do cadastro, abra **Conferir vínculo
   e envio**. O bloco **Estoque automático — piloto DEV** apresenta o saldo
   disponível, o último saldo enviado ou conferido e eventuais pendências.
3. Faça uma venda de uma unidade em DEV. Partindo de 21 disponíveis, o saldo
   deve chegar a 20. Se houver reserva anterior, concluir a baixa não pode
   descontar essa unidade novamente.
4. Cancele a venda de teste. O saldo disponível deve voltar a 21. Liberar uma
   reserva sem baixa também deve recompor apenas a disponibilidade.
5. Registre uma entrada de duas unidades. O saldo deve chegar a 23. Confira
   que o preço do ERP, app, ecommerce e iFood permaneceu igual ao início.
6. Mudanças próximas são agrupadas: quando chegar a próxima oportunidade de
   envio, o sistema usa o saldo mais recente, sem reproduzir saldos antigos.
   Reiniciar o worker não apaga o histórico nem permite repetir uma tentativa
   cujo resultado ficou desconhecido.

**Recebido não significa aplicado.** O HTTP 202 indica recebimento na fila.
A conferência manual do Portal continua sendo evidência separada. Em DEV, o
simulador comprova a solicitação e seu conteúdo; não comprova aplicação no
iFood real. Para uma falha sem resultado conhecido, desative o piloto e
confira o resultado antes de registrar uma nova conferência e retomar.
Enquanto a automação estiver ativa, envio manual e alteração da conferência
desse vínculo ficam bloqueados para evitar duas operações concorrentes.

O primeiro ensaio do SKU 227 usou produto sem lotes. A correção seguinte em DEV
também cobre produtos com lotes: o cancelamento recompõe os mesmos lotes da
baixa e preserva o custo registrado na saída. Não escolhe lotes novos nem usa
o custo atual do cadastro. Isso vale também para linhas repetidas do mesmo SKU
quando a origem é rastreável. Históricos contraditórios ou sem origem suficiente
exigem conciliação antes do cancelamento; não há reparo automático de saldos
antigos nem de composições antigas de kits virtuais.

Para conferir esse cenário, registre os saldos dos lotes antes da venda e
compare cada um após cancelar. Uma reposição posterior deve criar ou aumentar
o lote da entrada, preservando os anteriores. Repetir o cancelamento não pode
gerar nova entrada. Esse ensaio usa DEV com simulador; a aplicação no iFood
real segue o piloto separado descrito abaixo.

Detalhes operacionais para implantação: as flags `IFOOD_STOCK_SYNC_DEV_ENABLED`
e `IFOOD_STOCK_SYNC_POLLING_ENABLED` começam desligadas. A allowlist exige
empresa, loja, ID do produto, SKU 227 e EAN `7898242031448` exatos; exige também
vínculo existente e conferência do saldo. No modo DEV, produção/staging e URL
externa são bloqueados, mesmo com credenciais herdadas. O PATCH contém apenas
`barcode` e `inventory.stock`, sem preço, promoção ou ativação do item.

A rotina consulta o banco a cada 30 segundos, respeita reservas, segurança e
pausa local, e mantém o intervalo conservador de 35 minutos entre tentativas.
Esse intervalo é uma proteção do CorePet; a regra publicada pelo iFood é de
volumetria por catálogo na janela, não um prazo individual comprovado por SKU.
Nos testes automatizados, o relógio é avançado para validar a janela sem
esperar 35 minutos reais. Referências: [atualização parcial](https://developer.ifood.com.br/en-US/docs/groceries/guides/modules/item/endpoints),
[volumetria](https://developer.ifood.com.br/en-US/docs/groceries/guides/modules/item/introduction)
e [processamento assíncrono](https://developer.ifood.com.br/en-US/docs/groceries/guides/modules/item/how-it-works).

## Estoque automático real — piloto restrito ao SKU 227

Este procedimento prepara o teste real autorizado pelo Lucas. Não registra que
o deploy ou o teste já ocorreu. A homologação e suas evidências devem registrar
separadamente cada resultado observado. A publicação de anúncios, a ponte de
pedidos em DEV e a integração financeira não são ativadas por este procedimento.

O único produto permitido é o SKU `227`, **Special Dog Carne Adultos 20 kg**,
produto CorePet `5867`, EAN `7898242031448`, na loja Atacadão das Rações Avenida
Brasil, merchant `adf87cbc-3858-413b-ae1e-3be36b1533e2`. O UUID da empresa fica
na configuração protegida e é conferido pelo código. Informar outro tenant,
merchant, produto, SKU ou EAN bloqueia o envio. Nenhum outro produto é liberado.

O modo real exige `IFOOD_STOCK_SYNC_LIVE_ENABLED=true`,
`IFOOD_STOCK_SYNC_POLLING_ENABLED=true`, escrita de catálogo habilitada e
`IFOOD_STOCK_SYNC_DEV_ENABLED=false`. O ambiente e seus aliases presentes devem
ser `production` ou `prod`, sem mistura com DEV ou staging. O endereço aceito é
somente `https://merchant-api.ifood.com.br`, com barra final opcional. Não são
aceitos proxies de ambiente, redirecionamento ou outro servidor neste piloto.

### Publicar o código com a rotina desligada

1. Conclua o gate de DEV e o CI do commit final. Compare o commit atualmente
   servido em produção com a `main` e registre tudo que entrará no deploy.
   Siga o [fluxo único](FLUXO_UNICO_DEV_PROD.md) e o
   [deploy oficial](PRODUCAO_DEPLOY_SSH.md), com a autorização de produção já
   registrada para o escopo correspondente.
2. Antes do deploy, mantenha `IFOOD_STOCK_SYNC_LIVE_ENABLED=false` e
   `IFOOD_STOCK_SYNC_POLLING_ENABLED=false` na configuração protegida de
   produção. A flag DEV permanece `false`. Não copie dados, configurações de
   simulador nem evidências do banco DEV para produção.
3. Execute o deploy oficial, com reconstrução do backend e aplicação da
   migração `zzzzw20261025a1`. Confira saúde dos serviços e commit servido.
   Preserve as referências do backup e do deploy. Publicar o código com essas
   flags desligadas não inicia a sincronização.
4. Confira a configuração efetiva dentro do backend sem exibir credenciais.
   O Compose de produção declara cada variável de estoque explicitamente;
   alterar apenas o arquivo `.env` não modifica um container que já está
   rodando. Não habilite a rotina no `worker-bling`.

### Conferir a referência e testar a atualização automática

1. Com a automação ainda desligada, confirme a empresa, o vínculo existente,
   o EAN e a apresentação no CorePet e no Portal da mesma loja. O anúncio
   precisa estar presente e ativo. Registre o estoque físico, reservas, saldo
   disponível para o canal e preços de ERP, app, ecommerce e iFood. Preserve
   lotes, custo, promoções e os outros produtos.
2. Consulte o produto por uma **nova busca do EAN no catálogo do Portal**.
   Não use apenas o recarregamento de uma página de detalhes já aberta: a URL
   dessa tela pode carregar uma cópia antiga dos dados. Registre o saldo
   anunciado atual e o horário da conferência.
3. Se o Portal e o CorePet já mostrarem o mesmo saldo inteiro `S`, com `S > 1`,
   altere temporariamente **somente o estoque desse item no Portal** para
   `S − 1`. Não faça venda, retirada, entrada ou ajuste no estoque físico do
   CorePet para provocar o teste. Confirme por nova busca que o Portal mostra
   `S − 1`; a diferença deve ser de uma unidade, sem alterar preço.
4. No mesmo componente de **Conferir vínculo e envio**, registre uma
   conferência humana verdadeira: produto presente, ativo e saldo `S − 1`
   efetivamente visto no Portal. Não registre `S − 1` se a alteração não
   apareceu. Se já existir uma diferença natural entre os dois sistemas, use
   o saldo real observado como referência, sem criar outra diferença.
5. Preencha a configuração protegida de escopo: `IFOOD_STOCK_SYNC_TENANT_ID`
   da empresa autorizada, `IFOOD_STOCK_SYNC_MERCHANT_ID` da loja acima,
   `IFOOD_STOCK_SYNC_PRODUCT_ID=5867`, `IFOOD_STOCK_SYNC_SKU=227` e
   `IFOOD_STOCK_SYNC_BARCODE=7898242031448`. Confira os identificadores antes
   de habilitar as flags LIVE e POLLING; DEV continua desligada.
6. Recrie somente o backend, usando a mesma imagem aprovada, para carregar a
   configuração. Não substitua esse passo por `docker restart`. Confira que
   o scheduler líder registrou o job do piloto real. O intervalo mínimo é de
   30 segundos; a janela conservadora de 35 minutos continua valendo para
   tentativas anteriores. Não avance relógio nem reduza a janela em produção.
7. Aguarde a rotina automática ler o saldo atual do banco. No cenário sem
   outras movimentações, ela deve enviar um PATCH com apenas o EAN e
   `inventory.stock=S`, devolvendo o anúncio ao saldo original. Não use o
   botão de envio manual para substituir esse teste. Acompanhe a tentativa
   marcada como API real no cadastro e na Central do iFood.
8. **HTTP 202 significa aceito para processamento, não aplicado.** Consulte
   novamente o Portal até verificar o saldo `S`. Não repita PATCHes para
   tentar acelerar o processamento. Confirme que um ciclo seguinte, sem
   mudança de saldo, não cria outro envio.
9. Compare todos os preços e os dados de estoque preservados com o início.
   Registre o conteúdo do PATCH, o aceite e a conferência externa como provas
   separadas. Se uma venda real ocorrer durante o teste, o saldo esperado
   passa a ser o disponível atual correto; não restaure um saldo antigo.

Esse teste comprova uma atualização automática real do produto autorizado.
Venda, cancelamento e reposição já possuem ensaios próprios em DEV; só afirmar
validação desses eventos em produção quando forem observados separadamente.
Se `S` não permitir o teste de uma unidade, não force ajuste físico nem use
outro produto: mantenha a rotina desligada até definir o cenário apropriado.

Enquanto a automação estiver habilitada, envios manuais e alterações da
conferência desse vínculo ficam bloqueados. Para registrar uma conferência
posterior, desligue a rotina primeiro. Uma tentativa sem resultado conhecido
exige conferir o Portal antes de retomar; o sistema não faz repetição cega.

### Interromper ou reverter o piloto

1. Defina LIVE e POLLING como `false`, mantenha DEV `false` e recrie somente
   o backend para carregar a configuração. Confira a interrupção do job.
   Desligar flags impede novas tentativas; não desfaz uma requisição já aceita
   pelo iFood e não restaura estoque remotamente por conta própria.
2. Faça nova busca no Portal e confira o saldo efetivo. Se a redução
   temporária de uma unidade ainda estiver aplicada, restaure somente esse
   saldo no Portal após conferir o disponível atual correto no CorePet.
   Preserve preços, lotes, reservas e os outros produtos.
3. Preserve `IfoodStockSyncState`, tentativas e conferências. Não apague
   registros nem troque sua origem para desbloquear um envio. O histórico
   distingue `local_simulator` de `ifood_api`, e mudar o modo de um estado
   existente bloqueia o piloto.
4. Não execute downgrade destrutivo depois de histórico real. A migração
   recusa remover a origem quando existe estado ou tentativa automática da
   API real. Se for necessário voltar código, revise a compatibilidade com
   o banco e siga o [checklist de rollback](PRODUCAO_ROLLBACK_CHECKLIST.md).

## Pedido de teste no PDV — somente DEV

O piloto de pedidos é separado do envio de catálogo. Ele usa uma empresa
fictícia no DEV e um único pedido da loja de testes do iFood; não habilita o
recebimento de vendas no PDV de produção.

**Validação desta etapa em 24/10/2026:** o pedido oficial de testes **#1420** foi
confirmado no iFood às 20h43, recebido no CorePet e concluído pela interface em
DEV. Somente uma unidade do SKU `018631.1` foi importada: uma venda, uma reserva
e uma baixa FIFO. Reimportar e repetir a conclusão não duplicou esses registros.
Os demais produtos, empresas e preços do ERP, app e ecommerce foram preservados;
produção não foi alterada. O ensaio sintético anterior permanece uma evidência
separada.

O pedido online registrou R$ 73,90 como pagamento externo iFood, sem nova entrada
em caixa. O repasse líquido, sua data e a margem continuam pendentes do
Financial oficial desse pedido. A ligação das taxas por venda já está
implementada em DEV, mas não cria cobranças que o iFood ainda não forneceu.
Esse aceite vale para o pedido e o fluxo de estoque deste piloto em DEV;
não libera produção, operação contínua nem valida os relatórios gerais.

1. Com a equipe de implantação, confirme a empresa, a loja de testes, o pedido
   autorizado e o único produto do piloto. Neste primeiro ensaio, o pedido deve
   ter uma unidade do SKU 018631.1, para retirada ou entrega com frete
   explicitamente informado, igual ou maior que zero, e sem cupom ou desconto.
   A reserva e a baixa continuam sendo de uma unidade do produto. A equipe deve
   conferir o modo de pagamento recebido do iFood, sem trocá-lo para dinheiro.
2. No DEV, abra **Configurações → Integrações → iFood → Pedidos para
   homologação**. Confira o pedido e os dados da sacola. Receber o pedido no
   painel ainda não reserva estoque nem cria uma venda.
3. No bloco **Piloto do PDV em DEV**, use **Enviar ao PDV de teste**. Confira a
   indicação de estoque reservado e o vínculo **Abrir venda no PDV**. Repetir a
   ação deve manter a mesma venda e a mesma reserva.
4. Abra a venda e confira canal iFood, produto, quantidade e valor. Para dinheiro
   presencial autorizado, registre o valor exato do item mais frete, sem outras
   taxas. Para pagamento online, confira **Pagamento online no iFood** e use
   **Concluir venda e baixar estoque**, na Central ou no PDV. Não registre outro
   pagamento; esse modo não abre a cobrança do caixa. A finalização registra a
   baixa de estoque uma única vez e encerra a reserva.
5. Volte ao painel e use **Atualizar pedidos** para conferir a reserva e a baixa
   gravadas no CorePet. Esse botão apenas relê os dados locais; **Buscar eventos
   agora** consulta o iFood e é uma ação diferente.

No modo online, o resumo separa produto, frete, valor operacional, taxa de
serviço do iFood e total do consumidor. Por exemplo: item de R$ 65,00 + frete de
R$ 8,90 = R$ 73,90 operacionais; com R$ 1,99 de serviço do iFood, o consumidor
paga R$ 75,89. Esse total não é o repasse líquido da loja. O piloto aceita essa
taxa somente quando a origem comprova que pertence ao iFood; outras condições
ficam bloqueadas. O frete online positivo exige entrega sob responsabilidade da
loja comprovada no pedido.

**Repasse a conciliar** significa que o recebimento líquido e sua data ainda
precisam ser conferidos. As taxas e a margem têm pendências próprias: uma cobrança
conhecida pode aparecer antes da confirmação bancária. Concluir a venda online
registra a evidência externa e a baixa do produto; não registra dinheiro recebido
em caixa ou banco nem dá o repasse como
recebido. Se o modo de pagamento ou o escopo do piloto não puder ser comprovado,
a cobrança manual continua bloqueada.

Outros pedidos, itens, pagamentos ou empresas não autorizados ficam bloqueados
no piloto. Não altere os itens da venda para contornar o bloqueio. Quando o
cancelamento remoto já tiver sido recebido e registrado no CorePet, a finalização
local fica bloqueada. A conferência e o cancelamento local continuam sendo ações
explícitas; receber novamente o mesmo evento não deve duplicar movimentos.

### Cancelar o pedido de teste no CorePet

Este ensaio usa outro pedido fictício, com uma unidade do mesmo SKU `018631.1`.
O pedido oficial **1420** fica preservado como evidência da reserva e da baixa.
Antes de agir, confira que está no DEV, na empresa e na venda de teste corretas.

1. Anote o saldo físico, as reservas, o disponível e os lotes antes do pedido.
2. Para testar **antes da baixa**, abra a venda ainda aberta e use **Cancelar**
   no PDV. A reserva deve ser liberada, sem entrada física nem mudança nos lotes.
   A Central mostra **Cancelado no CorePet** e **Reserva liberada, sem entrada física**.
3. Para testar **depois da baixa**, use outro pedido de teste, conclua sua venda
   uma vez e confira a saída. Depois use **Cancelar**. O sistema exige a prova
   original da saída e recompõe uma unidade nos mesmos lotes, com o mesmo CMV;
   não escolhe novos lotes pelo FIFO nem usa o custo atual do cadastro. A Central
   mostra **Lotes originais recompostos**. Uma prova ausente ou divergente exige
   conferência antes do retorno; um lote bloqueado ou vencido não é liberado por
   causa do cancelamento.
4. Confira novamente saldos, lotes e histórico. Repetir a solicitação ou receber
   o evento de cancelamento novamente não pode criar outra entrada ou reserva.
   Um novo pedido não pode ser importado retroativamente a partir de um pedido
   já encerrado.

**Cancelar no CorePet não cancela o pedido no iFood nem reembolsa o consumidor.**
Esta ação local não solicita o cancelamento no iFood e não cria reembolso em caixa ou banco.
No online, a linha de pagamento continua no histórico, com status local cancelado
para deixar de compor saldos ativos; a evidência original da aprovação externa é
preservada. O resumo passa a mostrar **Estorno iFood a conferir**, sem inventar
valor devolvido. O cancelamento e eventual reembolso no iFood e no Financial
continuam sendo conferências separadas.

**Situação do ensaio:** o cancelamento antes da baixa foi conferido no DEV,
incluindo repetição da mesma solicitação e evento duplicado, mantendo o saldo de
referência em físico **29**, reservado **3**, disponível **26**. O ensaio pela tela
após a baixa ainda está em curso. Os testes automatizados locais passaram, mas
o gate completo e o CI do commit final desta ampliação ainda precisam ser registrados.

Os botões de entrega e retirada usados pelo app/ecommerce não operam o pedido
iFood. A situação no provedor, a disponibilidade ao consumidor e os custos
financeiros precisam de conferências próprias. O roteiro técnico e as condições
do ensaio estão em [Pedidos e homologação](INTEGRACAO_IFOOD_FASE2_PEDIDOS.md).

A finalização da venda iFood não dispara emissão fiscal automática. A emissão
manual continua disponível conforme as permissões e regras fiscais da empresa.

## Financeiro em DEV: taxas por venda, custo histórico e repasses

A calculadora continua sendo uma previsão com as premissas da loja. A aba
**Financeiro**, disponível nesta entrega somente em DEV/homologação, separa essa
estimativa dos eventos e títulos retornados pelo módulo Financial. Isso ainda
não libera a consulta das cobranças reais do Atacadão nem conclui a homologação
Financial de produção. A aprovação dos módulos operacionais não substitui a
[homologação Financial](https://developer.ifood.com.br/en-US/docs/food/guides/modules/financial/homologation).

### Usar o custo original de uma venda

1. Em DEV, abra **Central do iFood → Financeiro**, escolha o período dos eventos
   importados e use **Conferir venda** no pedido escolhido.
2. Se o pedido já foi importado pelo piloto do PDV, confira o vínculo da ponte
   e o CMV original. Essa associação exata é aproveitada automaticamente;
   não precisa criar outro vínculo nem preencher uma confirmação manual.
3. Para pedidos sem essa ponte, no bloco de custos históricos pesquise o
   **Número ou ID da venda ERP** e confira a mesma venda no ERP. A busca não
   escolhe por coincidência de valor, data, cliente ou produto.
4. Selecione a venda, registre a justificativa, marque a confirmação de que ela
   corresponde ao pedido e use **Confirmar vínculo com venda ERP**. A associação
   é local e auditada; ela não cria venda, caixa, recebível ou baixa de estoque.
5. Confira o CMV histórico total e os comprovantes das linhas. Só são aceitas
   vendas da mesma empresa, do canal iFood, finalizadas e sem cancelamento ou
   devolução, com custo original comprovado em todos os itens.
6. Se o CMV manual ficar **Não informado**, a contribuição usa automaticamente
   esse custo histórico. Um CMV manual informado, inclusive zero, tem prioridade
   explícita. Receita, tributos e outros custos ainda precisam ser conhecidos
   e justificados; o CMV histórico sozinho não completa a contribuição.

O custo atual do produto não completa uma prova antiga ausente. Alterações nos
itens ou em seus comprovantes após a confirmação, devolução e cancelamento
geram pendência. A confirmação precisa ser feita com cuidado: o sistema não
reatribui o vínculo nem reutiliza a mesma venda para outro pedido silenciosamente.
Os custos manuais continuam separados e versionados; não são sobrescritos pela leitura.

### Conferir as taxas e o que ainda falta

No resumo da venda, confira cada linha de **Comissão iFood** e **Taxa de pagamento
iFood**, com nome, valor e origem. Uma parcela recebida permanece visível mesmo
que outra ainda falte. Uma taxa de R$ 0,00 só deixa de estar pendente quando o
Financial trouxer explicitamente esse zero. A previsão pelas taxas do contrato
continua na calculadora e não substitui a cobrança da venda.

Frete pago pelo cliente e serviço cobrado pelo iFood do consumidor são dados do
checkout, separados dos custos da loja. Se o iFood fizer a entrega, sua despesa
de logística também precisa ser identificada no extrato. Lançamentos desconhecidos,
ajustes, valores sem pedido ou conflitos de vínculo/período continuam com aviso;
o sistema não atribui esses custos por suposição.

Quando uma cobrança atrasada for importada, o sistema cruza o ID exato do pedido
com a venda e completa somente o que puder comprovar. Uma revisão substitui a
cobrança anterior, sem somá-la duas vezes. As telas conectadas consultam novamente
o ERP a cada 30 segundos enquanto visíveis, ao voltar à aba e após a importação.
Essas leituras usam os eventos locais: não refazem a venda, CMV, reserva, baixa,
pagamento ou caixa e não consultam o iFood por conta de abrir um relatório.

A busca automática no provedor é uma configuração separada, desligada por padrão
e limitada ao pedido/SKU autorizado no piloto DEV. Usa a competência mensal ou a
janela exata já importada, respeitando o limite de 33 dias. Outras competências e
ajustes fora dessa janela exigem conferência própria; não ficam conciliados
automaticamente. A equipe deve manter o escopo de testes e as permissões restritos.

**Referência do pedido #1420:** o CMV original é R$ 43,94; após a baixa oficial,
o estoque físico é 29, reservado 3 e disponível 26. Ainda não há Financial oficial
desse pedido. Para validar a atualização das telas em DEV, o ensaio temporário
usou fonte sintética rotulada, com comissão R$ 6,50, pagamento R$ 0,00 e revisão da
comissão para R$ 7,50. Isso não comprova cobrança real nem libera margem real.
Os dados temporários foram removidos e a configuração foi restaurada, preservando
CMV, estoque, reservas, lotes e caixa. Esse ensaio e sua validação técnica passaram
em DEV, sem envolver produção ou comprovar cobranças oficiais do pedido.

### Conferir repasses do provedor

1. No bloco **Repasses**, escolha o período e se deseja consultar por apuração
   ou por data prevista de pagamento. A competência do arquivo de conciliação
   é escolhida separadamente.
2. Use **Conferir repasse** para revisar tipo, valor, situação e pendências.
   Repasse, boleto e retenção são tipos distintos. Um título conferido no
   provedor continua com recebimento bancário não conferido.
3. Quando a consulta externa estiver habilitada em DEV, use **Consultar arquivo
   de conciliação** para solicitar e acompanhar o arquivo mensal. O sistema
   conserva a solicitação, respeita o intervalo entre tentativas e usa o arquivo
   completo já importado. Falhas preservam a evidência anterior.
4. Se o arquivo trouxer somente `id_saldo`, sem relação documentada com um
   título, o vínculo permanece pendente. Coincidência de datas ou valores não
   resolve essa pendência. Erro terminal ou conflito sem solicitação conhecida
   exige conferência; o sistema não gera solicitações repetidas para contornar isso.

Se aparecer que o iFood não encontrou lançamentos, a geração do arquivo falhou
para aquela loja e competência. Isso não significa saldo zero. O acompanhamento
automático termina e os dados anteriores são preservados; confira o motivo antes
de uma nova consulta. Em homologação, pode ser necessário solicitar ao iFood uma
massa de testes válida.

Um extrato baixado no Portal do Parceiro tem formato próprio. Sua conferência
separada não substitui o arquivo gerado pela API nem confirma o crédito no banco.

Abrir a tela ou consultar os dados locais não chama o iFood. Nenhuma dessas
ações publica anúncios nem marca caixa, banco ou contabilidade como conciliados.
O roteiro técnico e as limitações estão em [Financial em DEV](IFOOD_FINANCIAL_DEV.md).

## Teste inicial e checklist

Para conferir produto e calculadora, use a simulação sem salvar alterações do
produto nem enviar anúncios. Configurar e autorizar a integração são ações
separadas, descritas nas etapas anteriores.

- [ ] Empresa e loja correspondem ao mesmo estabelecimento.
- [ ] Aplicativo CorePet autorizado pelo responsável no Portal do Parceiro.
- [ ] Merchant ID do ERP corresponde à mesma loja autorizada.
- [ ] Conexão do ERP com essa mesma loja conferida separadamente.
- [ ] Produto piloto encontrado na empresa correta.
- [ ] Situação do produto no catálogo iFood conferida.
- [ ] Apresentação e identificação comparadas.
- [ ] Custo, preço e estoque revisados.
- [ ] Contribuição calculada com premissas confirmadas, ou impedimento explicado.
- [ ] Pendências de cadastro compreendidas.
- [ ] Nenhuma mudança salva durante uma simulação de consulta.
- [ ] Vínculo, envio e resultado externo registrados somente após comprovação.

## Dúvidas comuns

**O que significa “Pendente iFood” nos relatórios?** A venda foi registrada, mas
as cobranças da plataforma ainda precisam ser conciliadas. O sistema mantém
faturamento e custos conhecidos visíveis, sem apresentar taxa ausente como zero
nem inventar lucro ou margem final. Se o período contiver uma venda pendente,
os totais de rentabilidade desse conjunto também ficam pendentes. Filtrar outros
canais continua mostrando os resultados conhecidos dessas vendas.

Na lista de vendas, alternar impostos não elimina essa pendência. DRE, ponto de
equilíbrio, rankings por margem e exportações preservam a mesma indicação. A
previsão baseada no contrato continua sendo uma simulação separada. Uma taxa de
pagamento isolada, mesmo zero, não comprova a comissão e os demais custos do
iFood. Em DEV, a ligação por pedido já aplica os componentes recebidos e atualiza
o que faltar quando houver nova evidência válida. Até lá, a pendência permanece;
uma simulação nunca libera margem real. O aviso de taxas e margem é separado
da confirmação de recebimento do repasse no banco.

**Preciso cadastrar tudo novamente?** Primeiro analise os itens já publicados.
O objetivo é aproveitar o catálogo existente e evitar duplicidade; o vínculo
operacional ainda precisa passar pela validação descrita neste guia.
Esse é um teste separado da criação do SKU `018631.1`: falta escolher outro
produto já publicado, conferir seu EAN e sua apresentação na mesma loja e só
então registrar o vínculo. Reutilizar o item criado no primeiro teste não comprova
o aproveitamento de um anúncio preexistente.

**Marcar “Vender no iFood” já publica?** A seleção registra a intenção no
CorePet. Não comprova que um envio ou uma publicação aconteceu.

**Por que a margem não foi calculada?** Confira o custo do produto e as
premissas de taxas. Um valor desconhecido não deve ser substituído por zero
apenas para fazer aparecer um resultado.

**O estoque já sincroniza só porque o produto está pronto?** Não. Confirme o
vínculo e um teste real de atualização. Os envios assistidos continuam separados
da rotina automática. O piloto automático real exige ativação operacional
explícita e fica restrito ao SKU `227`; não libera a sincronização dos demais.

**Pausar ou programar uma promoção no CorePet garante a mudança no iFood?**
Não presuma esse resultado sem a validação do envio e da confirmação externa.

**O CorePet está Ativo no Portal, mas o teste de conexão falha. Está integrado?**
A autorização da loja foi concedida, mas a conexão do ERP ainda precisa ser
validada. Confira a identificação da loja, mantenha a rotina desativada durante
a investigação e encaminhe a mensagem do teste ao suporte. O suporte também
confere se o aplicativo usado pelo ERP corresponde ao autorizado pela loja.
Não compartilhe credenciais em mensagens ou capturas.

## Manutenção deste guia

Publicar o artigo resumido na Central de Ajuda somente depois de revisar os
passos contra a interface disponível. Substituir as partes pendentes por passos
observados e resultados comprovados, preservando a distinção entre consulta,
salvamento local e envio externo.

Guias e capturas destinados aos clientes devem usar dados fictícios ou
anonimizados, sem credenciais, contatos pessoais ou informações financeiras
reais. Padrão editorial: [Central de Ajuda e Novidades](CENTRAL_AJUDA_E_NOVIDADES.md).
