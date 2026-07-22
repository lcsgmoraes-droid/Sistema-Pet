# Plano inicial de tráfego pago — CorePet

Este plano prepara a aquisição de demonstrações do CorePet sem iniciar gastos.
Qualquer campanha, orçamento ou forma de pagamento deve ser confirmada pelo Lucas
antes da publicação.

O primeiro teste foi detalhado em
[`CAMPANHA_META_LOJISTAS.md`](./CAMPANHA_META_LOJISTAS.md). A decisão atual é
começar somente com lojistas pet e separar clínica veterinária e banho e tosa em
campanhas posteriores, evitando dividir um orçamento pequeno entre compradores com
dores diferentes.

## Objetivo de negócio

Gerar contatos qualificados de donos e gestores de:

- pet shops;
- clínicas veterinárias;
- operações de banho e tosa;
- lojas pet com entrega, app ou e-commerce.

A conversão principal deve ser uma **demonstração agendada**, não apenas um clique,
curtida ou seguidor.

## Preparação obrigatória antes de investir

1. Criar um portfólio empresarial da Meta pertencente à CorePet.
2. Criar ou conectar uma Página do Facebook chamada CorePet.
3. Adicionar o Instagram `@corepet.erp` como ativo da CorePet.
4. Criar a conta de anúncios em real brasileiro e com o fuso de Brasília.
5. Conceder à agência somente acesso de parceiro ou tarefas necessárias.
6. Manter a propriedade, a cobrança e os administradores principais com a CorePet.
7. Ativar autenticação em dois fatores e guardar códigos de recuperação.

## Lacuna atual de medição

A landing page envia o interessado diretamente ao WhatsApp, mas o projeto ainda
não possui Meta Pixel nem Conversions API. Isso impede medir com segurança quais
anúncios geraram demonstrações e vendas.

Antes de usar a landing page como destino principal:

- instalar o Meta Pixel com consentimento compatível com a LGPD;
- registrar `PageView`, visualização da landing, clique no WhatsApp e envio de lead;
- implementar o evento `Lead` somente após uma ação realmente concluída;
- adicionar parâmetros UTM em todos os anúncios;
- considerar Conversions API junto ao Pixel para medição mais confiável;
- testar eventos no Gerenciador de Eventos antes de investir.

Referências oficiais:

- [Conversions API](https://www.facebook.com/business/help/AboutConversionsAPI)
- [Formulários de leads](https://www.facebook.com/business/ads/ad-objectives/lead-generation/lead-ads-with-forms)
- [Posicionamentos Advantage+](https://www.facebook.com/business/ads/meta-advantage-plus/placements)

## Primeira campanha recomendada

### Campanha

- Objetivo: `Leads`.
- Configuração: Advantage+ Leads, sem restringir o público em excesso.
- Posicionamentos: Advantage+.
- Região: Brasil.
- Idioma do anúncio: português.
- Conversão inicial: formulário instantâneo da Meta ou Instagram Direct.
- Conversão posterior: formulário do site, depois que Pixel e Conversions API
  estiverem validados.

A Meta informa que campanhas de leads podem combinar formulário instantâneo e
formulário do site. Para o CorePet, o formulário instantâneo reduz a fricção no
início; o site deve ganhar mais orçamento quando a medição estiver pronta.

### Perguntas do formulário

1. Nome.
2. Empresa.
3. Telefone/WhatsApp.
4. E-mail.
5. Cidade e estado.
6. Tipo de operação: pet shop, clínica veterinária, banho e tosa ou operação mista.
7. Quantas unidades possui.
8. Principal desafio: vendas, estoque, financeiro, clientes, entregas ou integração.
9. Melhor período para uma demonstração.
10. Consentimento claro para contato comercial e link para a política de privacidade.

## Público inicial

Usar público amplo com sinais de interesse, deixando o próprio criativo qualificar
o gestor. Sugestões para o Advantage+ Audience:

- gestão de pet shop;
- varejo pet;
- clínica veterinária;
- banho e tosa;
- gestão de estoque;
- sistema ERP;
- empreendedorismo e pequenas empresas.

Evitar um público baseado apenas em amantes de animais: ele tende a encontrar
consumidores finais, não compradores de software de gestão.

## Criativos do primeiro teste

1. `01-corepet-lancamento.png` — posicionamento da marca e visão geral.
2. `02-corepet-ecossistema.png` — ERP, app e e-commerce integrados.
3. `03-corepet-resultados.png` — custos, margem e lucro venda por venda.
4. `frontend/public/marketing/corepet-vende-de-novo-vertical.mp4` — vídeo de
   recorrência e venda ativa para Reels e Stories.

Cada anúncio deve falar diretamente com o responsável pelo negócio. Exemplo de
abertura: **“Você gerencia um pet shop, clínica veterinária ou banho e tosa?”**

## Oferta

Oferta principal: **demonstração guiada do CorePet com diagnóstico rápido da
operação**.

Não prometer economia, crescimento ou resultado financeiro sem prova. Não usar
depoimentos inventados, urgência falsa ou preço promocional sem aprovação.

## Orçamento de teste

Duas opções seguras para validação:

- teste mínimo: `R$ 30/dia por 14 dias` — total máximo de `R$ 420`;
- teste recomendado: `R$ 50/dia por 14 dias` — total máximo de `R$ 700`.

Usar uma única campanha no início para não fragmentar o aprendizado. O orçamento
real só deve ser escolhido depois de confirmar preço, margem, capacidade de
atendimento e quantidade de demonstrações que a equipe consegue realizar.

## Métricas que importam

- custo por lead;
- percentual de leads qualificados;
- custo por lead qualificado;
- demonstrações agendadas;
- comparecimento às demonstrações;
- oportunidades comerciais;
- vendas e custo de aquisição de cliente;
- receita e margem geradas pelos clientes adquiridos.

Curtidas, alcance e seguidores são sinais auxiliares; não definem o sucesso da
campanha de venda do sistema.

## Rotina de otimização

- Não alterar campanha todos os dias.
- Conferir rastreamento e qualidade dos contatos diariamente no início.
- Fazer a primeira leitura de criativos após dados suficientes ou sete dias.
- Pausar somente anúncios com problema claro de qualidade ou mensagem.
- Registrar qual anúncio originou cada demonstração e venda.
- Aumentar orçamento gradualmente apenas quando o custo por lead qualificado e a
  taxa de vendas estiverem aceitáveis.

## Acesso da agência

A agência deve receber acesso como parceira no portfólio empresarial. Ela não deve:

- receber a senha do Instagram ou do e-mail;
- ser proprietária da Página, Instagram, Pixel, conjunto de dados ou conta de anúncios;
- controlar sozinha o método de pagamento;
- criar ativos principais dentro de um portfólio pertencente à própria agência.

A CorePet deve conseguir remover a agência sem perder histórico, públicos, eventos,
anúncios ou meios de cobrança.
