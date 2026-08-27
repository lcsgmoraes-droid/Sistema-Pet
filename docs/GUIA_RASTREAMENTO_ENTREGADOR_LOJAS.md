# Rastreamento do entregador nas lojas

Estado da decisao: preparado para uma futura versao nativa, sem envio automatico
para producao ou para as lojas.

## Como o recurso funciona

1. O entregador abre uma rota e toca em `Iniciar Rota`.
2. O CorePet explica que a localizacao sera compartilhada com a loja e o cliente
   somente durante aquela rota.
3. No Android, o app inicia um servico de localizacao visivel e mostra uma
   notificacao permanente enquanto a rota estiver ativa.
4. O entregador pode abrir o mapa ou bloquear a tela sem interromper o servico.
5. Ao finalizar ou cancelar a rota, o rastreamento deve ser encerrado.
6. Ao sair da conta, qualquer rastreamento ativo tambem e encerrado antes de
   limpar a sessao.

O Android nao pede `ACCESS_BACKGROUND_LOCATION`. Ele usa apenas localizacao
precisa/aproximada concedida durante o uso e um Foreground Service iniciado por
acao direta do entregador. Isso reduz o escopo da permissao e o risco de
rejeicao. No iOS, o rastreamento em segundo plano continua dependendo da
permissao `Sempre`.

## Permissoes Android da proxima compilacao

- `ACCESS_COARSE_LOCATION`
- `ACCESS_FINE_LOCATION`
- `FOREGROUND_SERVICE`
- `FOREGROUND_SERVICE_LOCATION`
- `POST_NOTIFICATIONS`

Deve continuar ausente:

- `ACCESS_BACKGROUND_LOCATION`

## Declaracao na Google Play

Na Play Console, revisar `Conteudo do app` e declarar o tipo de Foreground
Service como `Location`.

Texto-base sugerido para a justificativa:

> O entregador inicia manualmente uma rota no CorePet. Durante essa rota, uma
> notificacao permanente informa que a localizacao esta sendo compartilhada
> com a loja e com o cliente vinculado a entrega. O servico permite continuar o
> acompanhamento quando o entregador abre o aplicativo de mapas ou bloqueia a
> tela e e encerrado quando a rota e finalizada ou cancelada.

Antes de enviar a versao, conferir tambem:

- politica de privacidade publicada em `https://corepet.com.br/privacidade`;
- formulario de Seguranca de dados coerente com localizacao precisa;
- credenciais de teste de uma conta de entregador;
- descricao da funcionalidade igual ao comportamento real do app.

## Video curto para a revisao

Gravar em um Android real, preferencialmente em ate 30 segundos:

1. abrir o CorePet com uma conta de entregador;
2. abrir uma rota pendente e mostrar o aviso de localizacao;
3. tocar em `Iniciar Rota` e aceitar a permissao durante o uso;
4. mostrar a notificacao `CorePet — rota em andamento`;
5. abrir o Maps e mostrar no ERP que a posicao continua sendo atualizada;
6. voltar ao CorePet, finalizar a rota e mostrar que a notificacao desapareceu.

## Validacao antes das lojas

- testar em aparelho Android com a tela ligada, bloqueada e com o Maps aberto;
- testar permissao aceita, negada e revogada nas configuracoes;
- confirmar que forcar a parada do app interrompe o rastreamento e que a tela
  informa o estado limitado ao abrir novamente;
- confirmar que nenhuma localizacao e enviada antes de iniciar ou depois de
  finalizar a rota;
- validar no ERP e no app do cliente o horario do ultimo ponto recebido;
- gerar primeiro um build `preview` para teste interno;
- somente depois preparar novos numeros de versao/build e a submissao de loja.

## Pendencia Apple

A App Store Connect mostra um contrato atualizado do Apple Developer Program.
O titular da conta precisa revisar e aceitar esse contrato antes do envio de
uma nova versao iOS.
