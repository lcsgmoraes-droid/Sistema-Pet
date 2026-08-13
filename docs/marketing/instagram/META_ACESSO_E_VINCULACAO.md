# Meta: acesso, Página, Instagram e conta de anúncios

Este documento registra o diagnóstico e o procedimento iniciado em 10/08/2026 para
recuperar o acesso aos ativos publicitários da CorePet. Ele deve ser consultado antes de abrir
uma disputa de administrador ou criar outro portfólio empresarial.

## Ativos principais

- Portfólio empresarial CorePet ERP: `1045222268428516`.
- Instagram: `@corepet.erp`.
- Conta de anúncios e pagamentos: `1557793569067552`.
- Página do Facebook conectada ao Instagram: `CorePet ERP`, ID
  `1218972974636167`.

Esses identificadores não são senhas. Mesmo assim, não compartilhar permissões,
códigos de autenticação ou credenciais fora dos canais oficiais da Meta.

## Causa confirmada

O Instagram estava conectado a uma Página antiga/inacessível e seu usuário
empresarial estava com o acesso às Configurações do portfólio marcado pela Meta
como expirado ou recusado.

Isso produzia uma situação enganosa:

- o Facebook do Lucas conseguia abrir o portfólio, mas via zero contas de anúncios;
- a tentativa de adicionar a conta existente dizia que o Lucas não tinha acesso;
- a solicitação genérica de acesso retornava erro;
- o Instagram continuava mostrando a conta e o saldo pré-pago de R$ 700,00;
- abrir diretamente o ID da conta pelo Facebook podia desviar para outra conta de
  anúncios acessível ao Lucas.

A resolução estava no vínculo Página + Instagram e na aprovação do usuário
empresarial do próprio Instagram. Depois disso, a conta de anúncios pôde ser
confirmada no portfólio e atribuída ao Lucas. Não criar outro Facebook, outro
portfólio ou outra conta de anúncios para este ativo.

## Procedimento validado

1. Criar ou confirmar uma Página do Facebook chamada `CorePet ERP`, administrada
   pelo Facebook pessoal do Lucas.
2. Nas configurações da Página, conectar o Instagram `@corepet.erp`.
3. Se a Meta informar que o Instagram já está conectado a outra Página, escolher
   **Trocar de Página** e confirmar a nova Página CorePet ERP.
4. Durante o vínculo, adicionar o Instagram ao portfólio empresarial CorePet ERP e
   concluir a autorização solicitada pela Meta.
5. Entrar nas ferramentas comerciais usando o perfil salvo do Instagram
   `@corepet.erp`.
6. Se a Meta mostrar que o pedido de acesso às Configurações expirou ou foi
   recusado, clicar em **Enviar solicitação**.
7. Trocar o perfil ativo das ferramentas comerciais para **Facebook — Lucas
   Guerra**.
8. Abrir **Configurações da empresa > Pedidos** no portfólio CorePet ERP.
9. Localizar o pedido enviado por `corepet.erp` para acessar as Configurações do
   portfólio e aprovar **Controle total: tudo**.
10. Voltar ao perfil comercial do Instagram e abrir **Configurações da empresa >
    Contas de anúncios**.
11. Confirmar que a conta `1557793569067552` aparece como propriedade da CorePet
    ERP.
12. Na conta de anúncios, usar **Atribuir pessoas** para adicionar **Facebook —
    Lucas Guerra** com **Gerenciar contas de anúncios / acesso total**.
13. Verificar o acesso no Gerenciador de Anúncios e conferir a cobrança pelo caminho
    **Instagram > Configurações > Pagamentos de anúncios**.

## Estado verificado em 10/08/2026

- a Página CorePet ERP de ID `1218972974636167` está conectada ao Instagram
  `@corepet.erp`;
- o Instagram está conectado à conta publicitária `1557793569067552`;
- a conta de anúncios pertence ao portfólio CorePet ERP e aparece normalmente no
  Gerenciador de Anúncios;
- Lucas Guerra tem acesso total à Página, ao Instagram e à conta de anúncios;
- o saldo disponível foi conferido em `R$ 700,00`, com pagamento manual de
  `R$ 700,00` registrado como financiado em 22/07/2026;
- o limite diário definido pela Meta aparece como `R$ 388,94`;
- existe uma segunda Página homônima no portfólio, ID `1261447097047911`, que não
  é a Página conectada ao Instagram. Não remover até confirmar que nenhum
  formulário, publicação ou ativo antigo depende dela;
- o procedimento correto para aceitar os Termos de Anúncios de Cadastro é
  `https://www.facebook.com/ads/leadgen/tos/`, escolhendo a Página conectada;
- em 10/08/2026, a Meta respondeu `Unable to accept Terms of Service for this
  page. Please retry later.`. Isso é a única trava técnica restante para a campanha
  de formulário;
- nenhuma campanha foi publicada ou ligada durante a recuperação.

O acesso administrativo e a propriedade dos ativos estão resolvidos. Antes de
publicar uma campanha de Leads, repetir o aceite dos termos pela Página correta e
confirmar que o erro `#1892234` desapareceu no conjunto de anúncios.

## Regra para próximos ativos

Não iniciar anúncios de um novo Instagram comercial antes de concluir, nesta
ordem:

1. Página do Facebook pertencente à empresa;
2. Instagram conectado à Página correta;
3. Página e Instagram dentro do portfólio da empresa;
4. Lucas com controle total do portfólio e de cada conta de anúncios;
5. autenticação em dois fatores ativa;
6. agência adicionada como parceira, nunca como proprietária;
7. cobrança e saldo conferidos no mesmo ID da conta de anúncios.

Não compartilhar a senha do Instagram, do Facebook ou do e-mail com a agência.
Conceder somente as tarefas necessárias pelo acesso de parceiro da Meta.
