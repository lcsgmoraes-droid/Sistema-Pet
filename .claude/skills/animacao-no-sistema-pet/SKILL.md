---
name: animacao-no-sistema-pet
description: Use antes de adicionar, revisar ou remover qualquer animação, transição, micro-interação ou feedback de movimento no frontend ou no app mobile do Sistema Pet. Diz quais skills de animação usar em cada caso e as restrições do nosso projeto (Tailwind, componentes v2, react-hot-toast, dnd-kit, Expo, PDV, acessibilidade).
---

# Animação no Sistema Pet

Os skills de animação do Emil Kowalski (instalados em `.claude/skills/`, origem em
`emil-design-eng/ORIGEM.md`) são genéricos. Esta página diz **qual usar** e **o que é específico
daqui**. Em caso de conflito, valem o AGENTS.md e as regras globais de UX.

## Qual skill chamar

| Preciso de... | Skill |
|---|---|
| Decidir se algo deve animar e escolher curva e duração | `emil-design-eng` |
| Construir uma animação do zero (web) | `animate` |
| Construir animação, gesto ou haptics no app Expo | `animate-expo` |
| Criticar movimento já escrito | `review-animations` |
| Auditar o app inteiro e gerar um plano | `improve-animations` |
| Descobrir onde falta movimento (só leitura) | `find-animation-opportunities` |
| Animação engasgando | `animation-performance` |
| Descrever um efeito que não sei nomear | `animation-vocabulary` |
| Gesto, mola e arrastar fluido | `apple-design` |
| Tela no celular com cara de "site" | `mobile-native` |
| Testar com dado ruim (nome enorme, lista vazia) | `break-ui` |
| Comparar várias versões de um componente | `prototype` |

## Restrições do projeto

1. **Frequência manda.** No **PDV**, caixa, atalhos de teclado e qualquer ação repetida dezenas de
   vezes por dia: **sem animação** (ou quase). Movimento fica para o ocasional: modais, abas,
   toasts, abrir ficha, mover card no CRM.
2. **Nunca anime ação iniciada por teclado.** Operadores usam atalhos.
3. **Menos de 300 ms** na interface; entradas com `ease-out`; saída mais rápida que entrada;
   nunca `transition: all`; nunca sair de `scale(0)` (comece em 0,95 com opacidade).
4. **Só `transform` e `opacity`** para animar. Evite largura, altura, margem.
5. **`prefers-reduced-motion`:** manter opacidade e cor, remover deslocamento. Hover só sob
   `@media (hover: hover) and (pointer: fine)`.
6. **Feedback em até 400 ms** (Doherty): se a operação demora, mostre carregando na hora (esqueleto,
   não tela vazia). Um único carregamento por tela de edição (regra do AGENTS.md).
7. **Componentes:** use os de `frontend/src/components/v2/` (o `ModalPadrao` já define a casca
   e **não fecha clicando fora**: não mude isso). Animação nova vira ajuste do componente v2, não
   código solto na tela, e entra no catálogo do styleguide.
8. **Toasts:** o projeto usa `react-hot-toast`. Não instale o Sonner.
9. **Arrastar e soltar (CRM):** `@dnd-kit` já instalado; arrasto pela alça, com teclado e toque
   (ver `frontend/src/pages/crm/`). Não troque de biblioteca.
10. **Cores de atenção:** amarelo, laranja e vermelho só para o que pede atenção; movimento para
    chamar atenção deve ser raro e nunca piscante.
11. **Texto da interface em português** e respostas de revisão no formato "Antes | Depois | Por
    quê" que o `emil-design-eng` pede.

Depois de mexer em interface, rode a revisão do Rams (skill `revisao-rams`).
