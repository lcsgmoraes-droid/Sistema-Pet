# Guia CorePet — integração com o iFood

**Situação: rascunho, pendente de validação do vínculo e da publicação.**

Última atualização: 23/10/2026. Público: responsáveis pelo catálogo de lojas
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

## 5. Se o produto já estiver publicado

**Etapa pendente de validação do fluxo de vínculo.**

Antes de criar outro anúncio, compare o item existente com o produto do CorePet:

- nome e apresentação, incluindo peso, volume ou quantidade por embalagem;
- código de barras, quando houver;
- código interno da loja e identidade do item publicado;
- situação atual, preço e disponibilidade.

O vínculo precisa apontar para o mesmo produto e para a mesma apresentação.
Encontrar um nome semelhante não basta para confirmar essa correspondência.
Somente após essa conferência será definido o vínculo e o envio de preço ou
estoque. O procedimento completo ainda não foi validado; este guia não presume
que já exista um botão ou uma rotina automática para executá-lo.

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

**Prévia ainda em validação.** A conexão bem-sucedida já foi observada em
produção, mas a correção da listagem da prévia foi implementada e testada somente
em DEV. A conferência visual da correção e sua aplicação em produção ainda não
foram concluídas. Este rascunho não apresenta o preparo da prévia nem o envio
como etapas finalizadas e não fornece passos de publicação ainda não validados.

Para um item novo, confirme antes que ele realmente não existe no catálogo.
Para um item publicado, conclua a correspondência antes de atualizar. O piloto
não deve substituir nem reiniciar o catálogo inteiro.

## 8. Confirme o resultado da publicação

**Etapa pendente de execução e validação.**

Os marcos precisam ser conferidos separadamente:

| Situação | O que comprova |
|---|---|
| Aplicativo autorizado pela loja | A loja concedeu os acessos apresentados ao aplicativo CorePet |
| Conexão do ERP conferida | O CorePet foi validado com a mesma loja autorizada |
| Pronto para envio | O cadastro passou nas validações locais |
| Vínculo confirmado | O produto local corresponde ao item remoto conferido |
| Envio solicitado | Uma solicitação foi encaminhada |
| Solicitação aceita | O iFood aceitou o processamento da solicitação |
| Publicação conferida | O resultado foi verificado no catálogo e no canal |
| Estoque integrado | A atualização de estoque foi testada e conferida |

**Pronto para envio não significa publicado.** O sucesso de uma requisição
também não substitui a conferência do resultado visível. Os nomes da tabela
explicam os marcos de validação; não são uma promessa de que todos já apareçam
como status na interface atual.

Depois da primeira publicação validada, poderão ser testados estoque, pausa,
reativação e promoções. A entrada de pedidos e a baixa de estoque por venda
também exigem validação própria antes de serem consideradas automáticas.

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

**Preciso cadastrar tudo novamente?** Primeiro analise os itens já publicados.
O objetivo é aproveitar o catálogo existente e evitar duplicidade; o vínculo
operacional ainda precisa passar pela validação descrita neste guia.

**Marcar “Vender no iFood” já publica?** A seleção registra a intenção no
CorePet. Não comprova que um envio ou uma publicação aconteceu.

**Por que a margem não foi calculada?** Confira o custo do produto e as
premissas de taxas. Um valor desconhecido não deve ser substituído por zero
apenas para fazer aparecer um resultado.

**O estoque já sincroniza só porque o produto está pronto?** Não. Confirme o
vínculo, a ativação da rotina e um teste real de atualização antes de depender
dessa sincronização na operação diária.

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
