# Plano de Rebranding e Migracao para CorePet

## Objetivo

Transformar o Sistema Pet / Pet Shop Pro na marca CorePet, deixando ERP, app mobile, e-commerce, dominio, identidade visual e comunicacao comercial prontos para venda sem quebrar a operacao atual.

A mudanca deve acontecer em etapas. Primeiro o novo dominio deve funcionar em paralelo com o dominio atual. Depois a identidade visual deve ser aplicada nas interfaces, comunicacoes e apps. Por ultimo, o dominio antigo pode virar redirecionamento, se essa decisao for tomada.

## Principios da migracao

- Nao quebrar acessos atuais de clientes, usuarios, funcionarios e administradores.
- Manter `mlprohub.com.br` funcionando durante a transicao.
- Ativar `corepet.com.br` como dominio adicional antes de qualquer redirecionamento definitivo.
- Separar dados internos de marca publica. Logins e tenants existentes, como `admin@mlprohub.com.br`, nao devem ser alterados automaticamente.
- Evitar mudancas grandes sem validacao em producao.
- Aplicar a nova identidade em camadas: dominio, configuracoes tecnicas, marca visual, app mobile, materiais comerciais.

## Nome da marca

- Nome principal: CorePet
- Dominio registrado: `corepet.com.br`
- Posicionamento sugerido: plataforma de gestao integrada para petshops.
- Tom desejado: profissional, confiavel, moderno, operacional e simples.
- Evitar: identidade infantilizada, excesso de patas, linguagem muito "fofa" ou visual que pareca apenas loja pet. O produto e um sistema de gestao.

Sugestoes de assinatura:

- CorePet - Gestao integrada para petshops
- CorePet - ERP, app e e-commerce para petshops
- CorePet - O centro da operacao do seu petshop

## Decisoes de identidade ja tomadas

- Direcao visual atual: simbolo CP arredondado, com cachorro e gato em negativo e coleiras em dourado.
- Variantes escolhidas como base: opcoes 3 e 4 da rodada visual, por serem mais amigaveis, menos duras e mais claramente ligadas ao mundo pet.
- Tom visual: profissional e operacional, mas com pet explicito no simbolo para nao ficar distante do segmento.
- Ativos principais criados:
  - `frontend/public/brand/corepet/corepet-horizontal.png`
  - `frontend/public/brand/corepet/corepet-symbol.png`
  - `frontend/public/brand/corepet/corepet-icon-32.png` ate `corepet-icon-1024.png`
  - `frontend/public/favicon.svg`
- Fontes dos mockups guardadas em `docs/assets/corepet/source/`.
- Paleta operacional inicial: verde petróleo para marca principal, dourado como acento e neutros claros no ERP.

## Fase 1 - Dominio e infraestrutura

### DNS no Registro.br

Configurar `corepet.com.br` nos DNS do Registro.br ou apontar para o provedor usado pela aplicacao.

Registros previstos:

- `corepet.com.br` apontando para o servidor de producao atual.
- `www.corepet.com.br` apontando para o mesmo destino.
- Manter `mlprohub.com.br` ativo durante a transicao.

Decisao pendente:

- Usar DNS do Registro.br ou migrar DNS para outro provedor, como Cloudflare.

### Nginx e certificado SSL

No servidor de producao:

- Adicionar `corepet.com.br` e `www.corepet.com.br` ao bloco de servidor.
- Emitir certificado SSL para o novo dominio.
- Garantir que `/api/health` responda pelo novo dominio.
- Testar login, sessao, renovacao de token e navegacao.

### Redirecionamento

No inicio, nao redirecionar `mlprohub.com.br` para `corepet.com.br`.

Etapas recomendadas:

1. `corepet.com.br` funciona em paralelo.
2. Testes internos validam o dominio novo.
3. Clientes novos passam a receber links CorePet.
4. Quando estiver estavel, decidir se `mlprohub.com.br` redireciona ou continua como dominio legado.

## Fase 2 - Configuracoes tecnicas do sistema

### Variaveis e URLs

Revisar configuracoes que hoje usam `mlprohub.com.br`, incluindo:

- `FRONTEND_URL`
- `ECOMMERCE_BASE_URL`
- `EXPO_PUBLIC_API_URL`
- URLs de termos e privacidade
- URLs usadas em e-mails
- URLs de callback, confirmacao e recuperacao de senha
- CORS
- cookies e dominio de sessao
- webhooks futuros de pagamento

Ocorrencias ja identificadas:

- `app-mobile/eas.json`
- `app-mobile/src/config.ts`
- `app-mobile/src/screens/auth/RegisterScreen.tsx`
- `backend/app/routes/ecommerce_auth.py`
- `backend/app/routes/ecommerce_notify_routes.py`
- `backend/app/routes/ecommerce_aparencia_routes.py`
- documentos de deploy e seguranca que mencionam health checks de `mlprohub.com.br`

### Compatibilidade de login

Nao trocar automaticamente e-mails de login, tenants ou historicos. O dominio novo e publico/comercial; os dados existentes continuam preservados.

Exemplo:

- Usuario/tenant `admin@mlprohub.com.br` pode continuar existindo.
- Sistema publico passa a aparecer como CorePet.
- Novos e-mails comerciais podem ser criados depois, como `contato@corepet.com.br` ou `suporte@corepet.com.br`.

## Fase 3 - Identidade visual

### Logo

Criar pelo menos 3 caminhos visuais para escolha:

1. CorePet SaaS
   - Visual moderno, limpo, confiavel.
   - Simbolo abstrato ligado a gestao, dados, conexao ou nucleo.

2. CorePet Operacional
   - Mais direto para ERP, rotina, caixa, estoque, financeiro e atendimento.
   - Visual forte para sistema de gestao.

3. CorePet Pet Sutil
   - Traz elemento pet discreto, sem parecer infantil.
   - Pode usar cauda, orelha, coleira, cruz veterinaria simplificada ou modulo em forma de pet.

Entregaveis desejados:

- Logo horizontal.
- Logo reduzida/icone.
- Versao clara e escura.
- Favicon.
- App icon.
- Splash screen mobile.
- Arquivo vetorial ou fonte editavel.

### Paleta de cores

Direcao recomendada:

- Base profissional e limpa.
- Cor primaria forte e confiavel.
- Cor secundaria com energia suficiente para chamar acoes.
- Estados bem definidos: sucesso, alerta, erro, informacao.

Evitar:

- Interface inteira dominada por uma unica familia de cor.
- Visual escuro demais.
- Tons infantis demais.
- Gradientes roxo/azul dominantes sem necessidade.

### Tipografia

Requisitos:

- Boa leitura em tabelas, dashboards e telas densas.
- Funcionar em ERP, e-commerce e app mobile.
- Nao depender de fonte dificil de carregar.

Possiveis caminhos:

- Manter tipografia atual se ela ja for boa para produto.
- Adotar uma familia limpa e amplamente suportada, como Inter, Manrope ou similar.

## Fase 4 - Aplicacao da marca no ERP

Itens a revisar:

- Titulo da aba do navegador.
- Nome no menu lateral.
- Tela de login.
- Header/topbar.
- Favicon.
- Logo compacta.
- Textos de boas-vindas.
- Rodape, se houver.
- Modais e mensagens que falam "Pet Shop Pro" ou "Sistema Pet".
- Relatorios, PDFs e exports.
- E-mails transacionais.
- Termos, privacidade e paginas institucionais.

Recomendacao:

Comecar por login, menu lateral, favicon e titulo do navegador. Depois revisar o restante por modulo.

## Fase 5 - App mobile

O app mobile precisa ser tratado com mais cuidado porque pode exigir novo build/APK/publicacao.

Itens a revisar:

- Nome exibido do app.
- Icone.
- Splash screen.
- URL da API.
- Links de termos e privacidade.
- Textos de login/cadastro.
- Textos de e-commerce/app cliente.
- Textos do app do funcionario e entregador.

Observacao:

Se o app instalado usa `EXPO_PUBLIC_API_URL` fixo para `mlprohub.com.br`, sera necessario gerar nova build para apontar para o dominio novo quando essa troca for desejada.

## Fase 6 - E-commerce

Itens a revisar:

- Dominio publico da loja.
- Links de cadastro, login e recuperacao.
- E-mails enviados ao cliente.
- Nome exibido no checkout.
- Politicas, termos e privacidade.
- SEO: titulo, descricao, favicon e metatags.
- Webhooks de pagamento, quando forem integrados.

Decisao pendente:

- O e-commerce vai ficar em `corepet.com.br/loja`, em subdominio, ou cada tenant tera dominio proprio?

Possiveis modelos:

- `corepet.com.br/{slug-da-loja}`
- `{slug-da-loja}.corepet.com.br`
- dominio proprio do cliente apontando para a plataforma

## Fase 7 - Materiais comerciais

Criar materiais para venda:

- Landing page institucional.
- Pitch curto da CorePet.
- Apresentacao comercial.
- Print/demo com nova identidade.
- Texto para WhatsApp.
- Proposta comercial.
- Politica de planos.
- Pagina de ajuda/FAQ.

Mensagem central sugerida:

"A CorePet centraliza a operacao do petshop: vendas, estoque, financeiro, DRE, ponto de equilibrio, app, e-commerce, entregas, campanhas e relacionamento com o cliente."

## Fase 8 - Auditoria de ocorrencias antigas

Fazer buscas no codigo e documentacao por:

- `Pet Shop Pro`
- `Sistema Pet`
- `mlprohub`
- `petshop`
- `PetShop`
- URLs absolutas antigas
- e-mails antigos
- titulos de pagina

Classificar cada ocorrencia como:

- Deve trocar agora.
- Deve trocar depois.
- Deve permanecer por compatibilidade.
- Apenas documentacao historica.

## Ordem recomendada de execucao

1. Criar identidade visual base da CorePet.
2. Configurar DNS e SSL do `corepet.com.br`.
3. Ativar dominio novo em paralelo.
4. Ajustar variaveis e URLs para suportar dominio novo sem quebrar o antigo.
5. Aplicar logo, favicon, nome e cores no ERP.
6. Ajustar textos publicos e e-mails.
7. Ajustar app mobile e gerar build quando necessario.
8. Ajustar e-commerce.
9. Criar materiais comerciais.
10. Decidir redirecionamento definitivo do dominio antigo.

## Checklist tecnico inicial

- [x] Definir logo principal.
- [x] Definir paleta de cores inicial.
- [x] Definir favicon e app icon.
- [x] Definir assinatura/slogan inicial.
- [ ] Configurar DNS `corepet.com.br`.
- [ ] Configurar `www.corepet.com.br`.
- [ ] Emitir SSL.
- [ ] Atualizar Nginx.
- [ ] Validar `/api/health` pelo dominio novo.
- [ ] Validar login pelo dominio novo.
- [ ] Revisar CORS/cookies.
- [ ] Revisar variaveis de producao.
- [x] Revisar primeira camada do app mobile.
- [x] Revisar primeira camada do e-commerce.
- [x] Revisar primeira camada de e-mails transacionais.
- [ ] Revisar PDFs e relatorios.
- [ ] Criar materiais de venda.

## Registro de execucao

- `f50f6c6dd` - plano inicial de rebranding CorePet.
- `051e006d4` - aplicacao inicial da identidade no ERP: logo, favicon, titulo, login, layout e ativos.
- `34b275d0e` - textos publicos CorePet em landing, planos, ajuda, legal, app/e-commerce e e-mails do e-commerce.
- `d7e6c9f52` - runtime de produto: e-mails de auth, remetente padrao, alertas Ops, health, calendario veterinario, mensagens de Bling/WhatsApp e area Ops.
- `cb721054f` - app mobile: nome exibido, paleta, icone/splash, telas de entrada, login, cadastro, perfil, compartilhamento e notificacoes veterinarias.
- Rodada atual - SEO e configuracao: sitemap, robots, exemplos de `.env`, CORS padrao com dominio CorePet e compatibilidade explicita com dominio legado.

## Riscos e cuidados

- Sessao/login pode falhar se cookies ou CORS estiverem presos ao dominio antigo.
- App mobile pode continuar usando dominio antigo ate nova build.
- Links enviados por e-mail podem continuar apontando para `mlprohub.com.br` se nao forem revisados.
- Webhooks de pagamento precisam ter URLs estaveis antes de ativar gateway.
- Trocar tenants/e-mails antigos automaticamente pode quebrar historico e suporte.
- Redirecionar cedo demais pode atrapalhar clientes e testes.

## Decisoes pendentes

- A CorePet sera apenas marca do sistema ou tambem nome da empresa?
- Qual sera o e-mail oficial: `contato@corepet.com.br`, `suporte@corepet.com.br`, outro?
- O dominio antigo sera mantido como legado ou redirecionado depois?
- O e-commerce dos tenants usara subdominio, slug ou dominio proprio?
- A identidade visual deve ser mais SaaS, mais operacional ou com elemento pet sutil?
- O app mobile sera publicado nas lojas ou distribuido por APK inicialmente?

## Proximo passo recomendado

Antes de alterar codigo, escolher a direcao visual da marca. Depois disso, fazer uma primeira rodada tecnica pequena:

1. DNS e SSL do dominio novo.
2. Suporte ao novo dominio sem remover o antigo.
3. Troca visual inicial no ERP: nome, logo, favicon e titulo.

Essa sequencia permite mostrar a CorePet funcionando rapidamente, com baixo risco para a operacao atual.
