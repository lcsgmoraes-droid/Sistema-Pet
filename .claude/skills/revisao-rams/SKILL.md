---
name: revisao-rams
description: Use depois de criar ou alterar qualquer tela, componente ou CSS do frontend (e antes de commitar) para fazer a revisão de design e acessibilidade com o Rams — a ferramenta MCP `rams` (quick_review, review_files, verify_fixes). Explica o que o Rams checa, como a nota é calculada, como chamar a ferramenta sem erro e como tratar os achados no Sistema Pet.
---

# Revisão de design com o Rams

Rams (rams.ai) revisa código de interface contra **356 regras** em 8 categorias e devolve nota de 0
a 100 e correções. A regra do CLAUDE.md global manda usá-lo no fluxo de UI; aqui está o jeito certo.

## O que ele olha

| Categoria | Exemplos |
|---|---|
| Acessibilidade (36) | contraste, rótulos, foco, nome de botão só com ícone (WCAG 2.1 AA e 2.2, WAI-ARIA) |
| Cor (28) | cor fixa em hexadecimal, cor como único diferenciador |
| Tipografia (43) | tamanhos, hierarquia, medida de linha |
| Espaçamento (30) | ritmo, alinhamento |
| Componentes (23) | estados (vazio, carregando, erro), consistência |
| UX (77) | clareza, feedback, prevenção de erro |
| Movimento (59) | animação sem `prefers-reduced-motion`, `transition: all` |
| Acabamento (38) | os "cheiros" de interface genérica: degradês gratuitos, sombras brilhantes, botões cheios todos iguais |

**Nota:** crítico limita a nota (1 crítico: máximo 59; 2: 49; 3 ou mais: 39). Nota de 60 ou mais
significa que não há crítico. Achados são julgamentos de revisão, não erros de linter: avalie cada
um com bom senso.

## Como usar (e armadilhas)

1. **Durante o trabalho:** `quick_review` nos arquivos alterados, depois de cada componente ou
   refatoração. Custa pouco.
2. **Antes de commitar:** `review_files` uma vez, para a nota e os patches.
3. **Depois de corrigir:** `verify_fixes` com o código novo (é grátis).
4. **Passe o código REAL e completo** de cada arquivo (caminho verdadeiro + conteúdo inteiro). Já
   falhamos mandando texto de exemplo: a ferramenta devolve "no_json" e não revisa nada.
5. Erro 503 ou "Retry": tente de novo uma vez. Persistindo, siga o trabalho e **diga na entrega
   que a revisão do Rams não rodou**; nunca afirme que passou.
6. Auditoria da base inteira (dezenas de arquivos) gasta cota: só com autorização do Lucas.

## Como tratar os achados aqui

- Corrija o que for real; descarte com justificativa o que conflita com o padrão do projeto
  (componentes `v2`, cores de atenção amarelo/laranja/vermelho, `BotaoMenuAcoes` etc.).
- Nunca "resolver" um achado trocando por elemento nativo: o AGENTS.md exige os componentes de
  `frontend/src/components/v2/`.
- Cor nunca é o único sinal: texto ou ícone junto (regra do projeto e do Rams).
- Movimento: ver `animacao-no-sistema-pet` (sempre respeitar `prefers-reduced-motion`).
- Na mensagem final, informe a nota e o que foi corrigido ou descartado e por quê.

Fonte: https://rams.ai
