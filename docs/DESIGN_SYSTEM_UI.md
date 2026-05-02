# Design System UI - Sistema Pet

Este documento define regras visuais obrigatorias para novas telas, refactors e componentes reutilizaveis do frontend.

## Principios

- Antes de criar um componente novo, procurar componente existente em `frontend/src/components`.
- Regras de negocio nao devem ficar presas na tela; a tela coleta dados e chama uma regra/servico central.
- Componentes compartilhados devem manter o mesmo comportamento, cor, fonte, espacamento e estados em todos os modulos.
- Evitar cor por modulo quando a cor representa acao. A cor da acao deve ter o mesmo significado em todo o sistema.
- Usar icone quando a acao for reconhecivel, com texto quando a acao precisar ser explicitada.
- Manter botoes, campos e cards com densidade operacional: profissional, legivel e sem excesso decorativo.

## Regra de cores por acao

| Acao semantica | Uso | Cor padrao |
| --- | --- | --- |
| `create` | Novo, adicionar, cadastrar, incluir | verde/emerald |
| `edit` | Editar, salvar alteracao, atualizar cadastro | azul |
| `delete` | Excluir, remover, cancelar destrutivo | vermelho |
| `neutral` | Fechar, voltar, limpar, atualizar lista, navegar | slate/cinza |
| `warning` | Alerta, conflito, pendencia, acao sensivel reversivel | amber |

Exemplos:

- `+ Novo pet` usa `create`, portanto sempre verde.
- `Editar pessoa` usa `edit`, portanto sempre azul.
- `Excluir venda` usa `delete`, portanto sempre vermelho.
- `Atualizar` usa `neutral`, exceto quando for uma acao de gravacao.
- `Cancelar venda` usa `delete` se muda estado de negocio de forma destrutiva.
- `Cancelar modal` usa `neutral`, porque apenas fecha a interface.

## Implementacao no codigo

A fonte inicial de classes semanticas fica em:

`frontend/src/components/ui/actionStyles.js`

Use `actionButtonClasses` em novos botoes e em refactors graduais:

```jsx
import { actionButtonClasses } from "../ui/actionStyles";

<button className={actionButtonClasses({ intent: "create", tone: "soft", size: "sm" })}>
  Novo pet
</button>
```

Evite classes diretas como `bg-orange-600`, `text-cyan-700` ou `border-blue-200` em botoes de acao quando existir uma intencao semantica clara.

## Checklist para novas alteracoes frontend

- O componente existente foi procurado antes de criar outro?
- A cor do botao vem da intencao da acao, nao do gosto da tela?
- O mesmo componente fica igual em Consulta, Banho & Tosa, PDV e demais modulos?
- Estados `disabled`, `hover`, carregamento e erro estao previstos?
- O texto cabe no mobile e no desktop?
- A tela ficou operacional e escaneavel, sem estilo de landing page?
