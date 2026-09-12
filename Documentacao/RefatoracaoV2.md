---
tipo: log
atualizado: 2026-09-12
---

# Refatoração v2 — telas

Registro vivo de cada tela em que aplicamos os componentes de `frontend/src/components/v2/`. Complementa [[Roadmap]] (itens 1.6-1.9) e [[Fase-2-Funcionalidades-e-Skills]] (mapeamento tela por tela) — aqui é o diário de execução, lá é o plano. Ver também [[Matriz-de-Cobertura]] para o mapa geral de telas do sistema.

## Regras desta frente (definidas com o responsável em 2026-09-12)

- **Só ajuste visual.** Nenhuma tela tem sua funcionalidade alterada nesta frente — mesma lógica, mesmas chamadas de API, mesmo comportamento. Só troca o que renderiza por dentro.
- **Vai devagar, uma tela por vez.** Sem lote grande — cada tela é seu próprio commit, revisada antes de seguir para a próxima.
- **Toda tela trabalhada migra para `frontend/src/pages/v2/`.** Diferente de `components/v2/` (aditivo, sem risco de rota), mover uma página muda o caminho de import e a rota registrada em `lazyPages.jsx`. Risco aceito conscientemente pelo responsável — o ganho é conseguir garantir visualmente, pela própria estrutura de pastas, quais telas já foram e quais faltam.
- **Limpeza de CSS por tela.** Para todo CSS específico daquela tela (classe própria, `.css` dedicado, estilo inline), decidir explicitamente um dos três caminhos e registrar qual foi escolhido:
  1. **Vira um componente v2 novo** — o padrão se repete ou tem potencial claro de repetir em outra tela.
  2. **Continua exclusivo da tela** — não faz sentido virar componente reaproveitável (registrar o motivo).
  3. **Substituído por um componente v2 que já existe** — a tela só não sabia que já tínhamos isso pronto.
- **Tela só fecha "finalizada".** Nenhum ❓ fica pendente pra depois — se surgir uma pergunta sobre a tela durante o trabalho (payload de API, regra de negócio, existência de alguma proteção), o levantamento é feito ali mesmo, na hora, antes de passar para a próxima tela.
- **Skill por tela.** Toda tela concluída ganha uma skill em `.claude/skills/<nome>/SKILL.md` (piloto: [[Fase-2-Funcionalidades-e-Skills]] item 2.3) — fonte de verdade sobre a tela (fluxo, o que cada botão faz, dependências, o que ela não faz), carregada automaticamente quando alguém mexe naquela área.

## Telas

| Tela | Rota | Status | Data | Resumo dos ajustes |
|---|---|---|---|---|
| Login | `/login` | Concluído | 2026-09-12 | Movida para `pages/v2/Login.jsx` (era `pages/Login.jsx`; import atualizado em `lazyPages.jsx`, rota `/login` sem mudança). Ver detalhe abaixo, a skill `.claude/skills/login/SKILL.md` e [[Autenticacao]] para o fluxo de login multiempresa que a tela implementa (lógica 100% preservada). |

### Login — detalhe da limpeza de CSS (regra do topo desta página)

- **3 `<input>` nativos → componentes v2 já existentes.** Identificador e "Loja" viraram `InputTexto`; a senha virou `InputSenha` — que já resolve sozinha o mostrar/ocultar que a tela reimplementava com `useState` + botão de olho manual (estado e botão removidos, a tela ficou mais simples).
- **Botão de submit nativo → `BotaoInteracao` (tamanho grande, ícone `PawPrint`).** "Entrar" não grava nada — é ação, não salvamento — por isso não é `BotaoSalva`. Texto ("Entrar"/"Entrando...") e `disabled` continuam controlados pela tela; a cor/formato agora vêm do componente. Escolhi um ícone de pata (identidade CorePet) em vez de um ícone genérico de "entrar".
- **Extensão feita na base (motivada por esta tela):** todo `Botao*` e `BotaoAjuda` ganharam a prop `tamanho` (`"pequeno"|"normal"|"grande"`, enum fechado) — o Login usa "grande" no botão principal. `BotaoBase` também ganhou `...rest` (faltava, travava `aria-*`/`data-*` extras que uma tela precisasse passar).
- **Ícone dentro do campo (usuário/cadeado) → removido.** Nenhum componente v2 do catálogo atual tem "ícone à esquerda embutido" — é um padrão que não existe em nenhum outro campo já migrado. Decisão: não criar um slot novo só para esta tela; ela passa a seguir o padrão limpo (label acima, sem ícone) igual ao resto do catálogo. Sinalizado para o responsável revisar se quer esse padrão de volta.
- **Cartões de seleção de empresa (ícone + nome + subtítulo) → continuam exclusivos da tela.** Não existe candidato v2 pronto para isso, e ainda não vi esse padrão se repetir em outra tela para justificar criar um componente novo agora (evitar abstração especulativa). Fica anotado como candidato a um futuro `CartaoSelecao` se aparecer de novo.
- **Botão "Entrar com outra conta" → continua exclusivo da tela.** É um botão com aparência de link de texto (sem borda/fundo), diferente de todo o catálogo de botões v2 (que sempre tem caixa/borda). Candidato a um futuro botão "tipo link" se o padrão se repetir.
- **Links de navegação (Esqueci minha senha / Criar conta) → recoloridos** do teal customizado antigo (`#0f8b8d`) para o azul padrão (`blue-600`) já usado em foco/seleção no resto do v2. **Logo e gradiente de fundo mantidos intactos** — é identidade de marca proposital, não CSS desorganizado, não faz parte desta limpeza.
- **Extensão feita na base:** `InputTexto`/`InputSenha` não tinham suporte a `autoComplete` (necessário para o gerenciador de senhas do navegador reconhecer os campos) — adicionado nos dois, disponível para qualquer tela a partir de agora.

## Não identificado

- ❓ Se/quando esta frente também deve cobrir `PlatformLogin.jsx` (`/ops/login`, login separado da equipe CorePet) — é uma tela distinta de `Login.jsx`, não decidido ainda se entra nesta mesma leva.
