# Guia de Producao de Videos com IA - Sistema Pet

Uso: padronizar a criacao de videos curtos do Sistema Pet usando gravacao de
tela, narracao, legendas e apoio de IA.

## Objetivo

Criar videos que ajudem em tres frentes:

1. Vender o sistema para novos clientes.
2. Mostrar as principais telas e funcionalidades.
3. Ensinar a configuracao inicial para novos usuarios.

Os videos devem mostrar o produto real sempre que possivel. IA entra para
roteiro, voz, legenda, cortes, imagens de apoio e adaptacao de formatos, nao
para inventar telas que o sistema ainda nao tem.

## Padrao de gravacao

| Item | Padrao recomendado |
|---|---|
| Formato principal | Vertical 9:16 para Reels, Shorts e TikTok |
| Formato secundario | Horizontal 16:9 para YouTube, landing page e treinamento |
| Duracao venda | 15s a 35s |
| Duracao demo | 45s a 90s |
| Resolucao | 1080p ou superior |
| Zoom do navegador | 90% a 100%, conforme a tela |
| Dados | Apenas dados ficticios ou base demonstracao |
| Voz | Tom simples, consultivo e direto |
| Legenda | Sempre usar legenda curta, frase por frase |
| CTA | Uma acao clara por video |

## Fluxo de producao

1. Escolher o objetivo do video.
2. Selecionar um roteiro em `ROTEIROS_CRIATIVOS_VENDA.md` ou
   `ROTEIROS_DEMO_FUNCIONALIDADES.md`.
3. Preparar a base demonstracao com dados ficticios.
4. Gravar a tela sem dados reais de cliente.
5. Gerar ou revisar narracao com IA.
6. Editar cortes, zooms e legendas.
7. Exportar em 9:16 e, quando util, 16:9.
8. Salvar o arquivo final com nome padronizado.
9. Registrar o video usado, tela gravada e data de gravacao.

## Nomes de arquivo

Formato:

`sistema-pet_<tipo>_<tema>_<formato>_<aaaa-mm-dd>.mp4`

Exemplos:

- `sistema-pet_venda_lucro-real_9x16_2026-06-28.mp4`
- `sistema-pet_demo_pdv-estoque_16x9_2026-06-28.mp4`
- `sistema-pet_onboarding_primeiros-passos_9x16_2026-06-28.mp4`

## Prompt base para roteiro

```text
Crie um roteiro curto para video do Sistema Pet.

Contexto:
- Publico: donos e gestores de pet shop, banho e tosa, clinica veterinaria ou loja pet.
- Produto: sistema de gestao para operacao pet, com PDV, estoque, financeiro, compras/XML, banho e tosa, veterinario, ecommerce/app e relatorios.
- Objetivo do video: [venda | demonstracao | onboarding].
- Tela ou funcionalidade: [informar tela].
- Dor principal: [informar dor].
- Duracao: [15s | 30s | 60s].

Regras:
- Linguagem simples e brasileira.
- Comece com um gancho forte.
- Nao prometa resultado financeiro garantido.
- Mostre que o sistema organiza a rotina e reduz retrabalho.
- Inclua narracao, texto na tela, sugestao de cortes e CTA.
```

## Prompt base para legenda

```text
Transforme esta narracao em legendas curtas para video vertical.

Regras:
- Maximo de 8 palavras por bloco.
- Frases diretas.
- Sem linguagem exagerada.
- Destacar palavras como venda, estoque, financeiro, agenda, lucro, recebimento e relatorio quando fizer sentido.

Narracao:
[colar narracao]
```

## Prompt base para voz

```text
Reescreva esta narracao para voz humana, natural e consultiva.

Tom:
- Dono de software falando com dono de pet shop.
- Confiante, direto e sem exagero.
- Evitar promessas absolutas.
- Frases curtas para facilitar gravacao.

Narracao original:
[colar narracao]
```

## Prompt base para imagem de apoio

Use imagem de apoio apenas quando o video nao precisar inspecionar a tela real.
Para demos, a tela do sistema deve ser o destaque.

```text
Crie uma imagem realista para apoiar um video de software de gestao pet.

Cenario:
- Pet shop moderno e organizado no Brasil.
- Balcao com computador, produtos pet, agenda de servicos e atendimento ao cliente.
- Clima profissional, claro, confiavel e cotidiano.

Regras:
- Sem marcas reais.
- Sem texto legivel na imagem.
- Sem exagero futurista.
- Nao mostrar interface inventada do Sistema Pet.
```

## Checklist antes de publicar

- A tela mostrada existe no sistema atual.
- Nao ha dados reais de cliente, CPF, telefone, email ou endereco.
- O video tem uma unica mensagem principal.
- O gancho aparece nos primeiros 3 segundos.
- A legenda nao cobre botoes ou numeros importantes.
- O CTA aparece no final e combina com o objetivo.
- O arquivo foi exportado em formato correto.
- O video foi assistido inteiro antes de publicar.

## Cuidados de promessa

Evitar:

- "Dobre seu lucro".
- "Nunca mais tenha erro".
- "Sistema 100% automatico".
- "Garantia de aumento de vendas".

Preferir:

- "Veja seu lucro com mais clareza".
- "Reduza retrabalho no caixa".
- "Organize estoque, vendas e financeiro no mesmo lugar".
- "Tenha uma rotina mais facil de conferir".
