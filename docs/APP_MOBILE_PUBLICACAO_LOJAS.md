# Publicacao do App Mobile - Play Store e App Store

Atualizado em: 2026-06-21

Este guia organiza o que falta para publicar o app CorePet nas lojas. Ele separa
o que ja esta pronto no codigo, o que pode ser feito pelo time tecnico e o que
precisa ser feito pelo titular das contas Apple/Google.

## Estado atual do app

- Nome publico configurado: `CorePet`.
- Android package: `br.com.corepet.app`.
- iOS bundle identifier: `br.com.corepet.app`.
- Deep link configurado: `corepet://`.
- API de producao configurada no EAS: `https://corepet.com.br/api`.
- Politica de privacidade publica: `https://corepet.com.br/privacidade`.
- Termos de uso publicos: `https://corepet.com.br/termos`.
- Firebase Android configurado com `app-mobile/google-services.json`.
- Notificacoes Android ja testadas em aparelho real.
- Profile EAS `production` configurado para canal `production`.
- Android nativo alinhado com `CorePet`, `br.com.corepet.app`, deep link
  `corepet://` e notificacoes.

## O que o tecnico consegue fazer

1. Validar o app localmente:

```powershell
cd app-mobile
npm run check
```

2. Gerar build Android de loja:

```powershell
cd app-mobile
eas build --platform android --profile production
```

3. Gerar build iOS de loja:

```powershell
cd app-mobile
eas build --platform ios --profile production
```

4. Subir build Android para teste interno/fechado depois que a Play Console
estiver criada e o primeiro app existir.

5. Subir build iOS para TestFlight depois que a conta Apple Developer,
App Store Connect e credenciais iOS estiverem liberadas.

6. Publicar updates OTA pelo canal correto quando a mudanca for apenas
JavaScript/assets e o runtime for compativel:

```powershell
cd app-mobile
eas update --channel production --platform all --message "ajuste app mobile"
```

## O que Lucas precisa fazer nas contas

### Google Play Console

- Criar ou acessar a conta Google Play Developer.
- Concluir verificacao de identidade e pagamento da conta, se ainda faltar.
- Criar o app `CorePet`.
- Informar que o app e gratuito, categoria de negocio/produtividade ou compras,
  conforme estrategia escolhida na Play Console.
- Adicionar e-mail de suporte publico.
- Adicionar URL de politica de privacidade:
  `https://corepet.com.br/privacidade`.
- Preencher Data Safety com base na secao "Respostas de privacidade" deste guia.
- Configurar classificacao indicativa.
- Criar teste interno ou teste fechado.
- Se a conta Google Play for pessoal nova, preparar pelo menos 12 testadores
  opt-in por 14 dias continuos antes de pedir acesso a producao.

### Apple Developer / App Store Connect

- Criar ou acessar a conta Apple Developer Program.
- Aceitar contratos e termos pendentes em App Store Connect.
- Criar o app `CorePet`.
- Reservar o bundle id `br.com.corepet.app`, se ainda nao existir.
- Adicionar URL de politica de privacidade:
  `https://corepet.com.br/privacidade`.
- Preencher App Privacy com base na secao "Respostas de privacidade" deste guia.
- Liberar ou criar credenciais de push/APNs para o app iOS.
- Configurar TestFlight para teste antes de enviar para revisao da App Store.

## Dados para cadastro nas lojas

### Identificacao

- Nome do app: `CorePet`.
- Nome curto Android: `CorePet`.
- Bundle/package: `br.com.corepet.app`.
- Site: `https://corepet.com.br`.
- Politica de privacidade: `https://corepet.com.br/privacidade`.
- Termos de uso: `https://corepet.com.br/termos`.

### Descricao curta sugerida

CorePet conecta clientes, loja e equipe em compras, pedidos, pets e notificacoes.

### Descricao completa sugerida

CorePet e o aplicativo conectado ao Sistema Pet para clientes e equipes de lojas
pet. Pelo app, clientes podem acessar a loja, consultar produtos, fazer pedidos,
acompanhar pagamentos, visualizar historico de compras e receber notificacoes
sobre compras e status de pedidos.

Para operacoes habilitadas, o app tambem pode oferecer recursos de perfil para
funcionarios, entregadores e veterinarios, respeitando as permissoes e os dados
da loja selecionada.

Principais recursos:

- compra online com pagamento integrado;
- historico de pedidos por canal;
- notificacoes de compra e atualizacao de status;
- cadastro e consulta de pets;
- acesso por loja/tenant;
- perfis operacionais conforme permissao da loja.

O uso depende de cadastro ativo em uma loja participante do CorePet.

### Categoria sugerida

- Google Play: `Compras` ou `Negocios`.
- App Store: `Compras` ou `Produtividade`.

Escolha recomendada para a primeira publicacao: `Compras`, porque o app tem foco
em compra, pedido e relacionamento do cliente com a loja.

## Respostas de privacidade

Esta secao ajuda a preencher Google Play Data Safety e Apple App Privacy. Ela
nao substitui revisao juridica, mas reflete o funcionamento atual do produto.

### Dados coletados e vinculados ao usuario

- Nome.
- E-mail.
- Telefone.
- CPF, quando informado pela loja ou pelo cliente.
- Endereco de entrega.
- Dados de login e identificadores de usuario.
- Historico de compras, pedidos, pagamentos e status.
- Dados de pets cadastrados pelo usuario ou pela loja.
- Fotos de pets, quando o usuario usa esse recurso.
- Localizacao aproximada ou precisa, quando recurso de loja proxima/rota estiver
  habilitado e autorizado.
- Token de notificacao push.
- Logs tecnicos de uso, erro, seguranca e sessao.

### Finalidades

- Funcionalidade do app.
- Gerenciamento de conta.
- Processamento de pedidos e pagamentos.
- Entrega/retirada e comunicacoes transacionais.
- Seguranca, prevencao de fraude e auditoria.
- Suporte ao usuario.
- Melhorias de estabilidade e diagnostico tecnico.
- Comunicacoes promocionais apenas quando houver base adequada e preferencia
  aplicavel.

### Compartilhamento com terceiros

O app pode compartilhar dados necessarios com:

- provedor de hospedagem e banco de dados;
- Expo/EAS e servicos de notificacao push;
- Firebase/Google para notificacoes Android;
- Apple/APNs para notificacoes iOS;
- Mercado Pago ou gateway de pagamento usado pela loja;
- servicos de e-mail, atendimento, logs e monitoramento;
- mapas/rotas quando recurso de localizacao estiver habilitado;
- a loja responsavel pelo atendimento e pelo pedido.

### Dados sensiveis

O app nao deve solicitar dados sensiveis de saude humana. Dados de pets e
informacoes veterinarias podem ser operacionais e devem ser tratados com acesso
restrito, pois podem se relacionar ao tutor.

### Rastreamento para publicidade

Estado recomendado para a primeira publicacao: declarar que o app nao usa dados
para rastrear usuarios entre apps/sites de terceiros para publicidade.

Se no futuro entrar SDK de anuncios, remarketing, analytics publicitario ou
atribuição, esta resposta precisa ser revisada antes de publicar update.

## Permissoes do app

### Android

- `POST_NOTIFICATIONS`: enviar notificacoes de compra, pagamento e status.
- `READ_MEDIA_IMAGES`: permitir foto de pet ou selecao de imagem quando o
  usuario acionar esse recurso.
- `VIBRATE`: permitir alerta vibratorio de notificacoes.
- `RECORD_AUDIO` e `SYSTEM_ALERT_WINDOW`: declaradas como removidas no Manifest;
  nao devem ser solicitadas ao usuario nem usadas pela publicacao de loja.

### iOS

- Camera: escanear codigo de barras quando recurso operacional estiver habilitado.
- Fotos: adicionar foto do pet.
- Localizacao em uso: sugerir loja proxima e apoiar rotas/entrega quando o
  perfil ou recurso exigir.
- Notificacoes: avisar compras, pagamentos, separacao, retirada e eventos
  transacionais.

## Checklist antes de enviar para revisao

- [ ] `npm run check` passa em `app-mobile`.
- [ ] `npx expo-doctor` revisado. Alerta esperado: projeto tem pasta nativa
      `android/`; por isso mudancas de nome, icone, permissoes e plugins devem
      ser refletidas tambem no projeto nativo, nao apenas no `app.json`.
- [ ] Build Android production gerado pelo EAS.
- [ ] Build iOS production gerado pelo EAS.
- [ ] Android instalado via teste interno/fechado e validado em aparelho real.
- [ ] iOS instalado via TestFlight e validado em iPhone real.
- [ ] Login de cliente validado.
- [ ] Compra pelo app validada.
- [ ] Pagamento Mercado Pago validado.
- [ ] Webhook atualizando pedido validado.
- [ ] Notificacao de compra recebida.
- [ ] Notificacao de status recebida.
- [ ] Historico de pedidos exibindo canal e itens.
- [ ] Politica de privacidade abre publicamente.
- [ ] Termos de uso abrem publicamente.
- [ ] Screenshots das lojas capturadas.
- [ ] Descricao, categoria, suporte e classificacao indicativa preenchidos.

## Pendencias que dependem de acesso externo

- Conta Google Play Developer ativa.
- Conta Apple Developer Program ativa.
- App criado nas duas lojas.
- Credenciais APNs/iOS configuradas.
- Chave de Service Account da Play Console para submissao automatica via EAS,
  se quisermos usar `eas submit` depois da primeira submissao.
- Testadores Android, caso a conta Play exija teste fechado de 12 pessoas por
  14 dias.
