---
name: ux-ecommerce-e-checkout
description: Use ao criar ou revisar fluxos de compra e de preenchimento — PDV (carrinho, pagamento, finalização), loja online e app do cliente (carrinho, entrega, checkout), cadastros e formulários longos (pessoa, endereço, telefone), erros de validação, busca, filtros e listagens de produtos. Traz as boas práticas de checkout e e-commerce do Baymard Institute adaptadas ao Sistema Pet.
---

# UX de e-commerce e checkout (Baymard) no Sistema Pet

Resumo de achados **públicos** do Baymard Institute (artigo "Current state of checkout UX" e a base
de exemplos em baymard.com/ecommerce-design-examples). Os números são do estudo deles, não nossos:
servem para priorizar, não para prometer resultado. As diretrizes completas (700+) são pagas; não
invente o que não está aqui.

## O que o estudo diz (e o que fazer aqui)

| Achado | Aplicação no Sistema Pet |
|---|---|
| Checkout ruim é causa frequente de abandono (cerca de 70% abandonam o carrinho; 64% dos sites têm checkout "medíocre" ou pior) | Tratar o fluxo de pagamento (PDV e loja online) como a tela mais importante: cada campo e cada passo precisa se justificar |
| **Compra como convidado** deve ser a opção mais visível (18% abandonaram por não querer criar conta) | Loja online e app: comprar sem criar senha; criar conta só depois, opcional |
| Regras de senha rígidas custam acessos (até 19% de abandono entre quem já tem conta) | Mínimo simples (6 a 8 caracteres); nada de exigir símbolo e maiúscula sem motivo de segurança real |
| Mostrar **data (ou intervalo) de entrega**, não só "rápida" ou "econômica" | Entrega da loja online e rotas: "chega até quinta, 12/11" |
| **Contagem regressiva** para o horário-limite do pedido, em vez de horário fixo | "Peça nos próximos 2h10 para receber amanhã" (só se o limite for real) |
| Todas as formas de receber (entrega, retirada na loja, local) **no mesmo seletor** | Não obrigar a voltar ao carrinho para trocar entrega por retirada |
| Quantidade com **botões** (− e +), ou botões mais campo; evitar só digitar | Carrinho do PDV e da loja: botões grandes (44 px) com campo editável |
| Marcar **obrigatórios e opcionais** de forma explícita (32% não viram um obrigatório quando só os opcionais eram marcados) | Padrão do v2: asterisco + "(obrigatório)" para leitor de tela; opcional dito no rótulo quando o formulário é misto |
| Campos opcionais atrasam (5% a 30% mais tempo) | Esconder "Complemento", "Empresa", "Linha 2" atrás de um link; não usar rádio ou lista suspensa para algo totalmente opcional |
| **Erros específicos**, não genéricos (94% dos sites erram nisso): "falta 1 dígito no cartão" em vez de "cartão inválido" | Toda validação diz o que está errado e como corrigir; destacar o campo exato (já é regra global do projeto) |
| **Explicar por que pede o telefone** (mais de 70% relutam; sem explicação inventam número ou saem) | Cadastro de pessoa e checkout: ajuda curta ("para avisar sobre a entrega pelo WhatsApp") ou tornar opcional |

## Checklist ao revisar um fluxo de compra ou cadastro

1. Dá para concluir o caminho principal **sem** criar conta, sem campos que não servem a essa compra?
2. Cada campo tem motivo? Se pedimos telefone, CPF ou e-mail, a tela diz para quê?
3. Obrigatório e opcional estão claros? Opcionais raros ficam recolhidos?
4. A quantidade, a entrega e o pagamento podem ser trocados sem sair do passo?
5. As mensagens de erro são específicas e aparecem no campo certo, durante a digitação?
6. A data de entrega e o custo total aparecem **antes** do último clique (nada de surpresa no fim)?
7. Funciona no celular com uma mão (alvos de 44 px, teclado certo: numérico para telefone e CPF)?
8. O PDV continua rápido por teclado (sem animação em ação repetida; ver `animacao-no-sistema-pet`)?

## Listagens, busca e filtros

O Baymard dedica seções inteiras a listas de produtos, ordenação, filtros, comparação e busca com
sugestões e página de "nada encontrado". As regras detalhadas são pagas; use o bom senso das
heurísticas (`/ux-laws`): filtros visíveis e removíveis, contagem de resultados, ordenação clara,
e uma página "nenhum resultado" que ofereça saída (limpar filtros, sugerir termos). Em tabelas de
listagem do sistema valem as regras do AGENTS.md (coluna Ações primeiro, `BotaoMenuAcoes` com 3
ou mais ações).

## Fontes

- https://baymard.com/blog/current-state-of-checkout-ux
- https://baymard.com/ecommerce-design-examples (76 tipos de página; exemplos anotados)
