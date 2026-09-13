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
| Dashboard | `/dashboard` | Concluído | 2026-09-12 | Movida para `pages/v2/DashboardFinanceiro.jsx` (era `pages/DashboardFinanceiro.jsx`; import atualizado em `lazyPages.jsx`). 4 componentes v2 novos nasceram desta tela (13 cartões + 2 estados vazios + 1 filtro de período + 1 link consolidados). Ver detalhe abaixo. Lógica de negócio, chamadas de API e cálculos 100% preservados — só o que renderiza mudou. |

### Login — detalhe da limpeza de CSS (regra do topo desta página)

- **3 `<input>` nativos → componentes v2 já existentes.** Identificador e "Loja" viraram `InputTexto`; a senha virou `InputSenha` — que já resolve sozinha o mostrar/ocultar que a tela reimplementava com `useState` + botão de olho manual (estado e botão removidos, a tela ficou mais simples).
- **Botão de submit nativo → `BotaoInteracao` (tamanho grande, ícone `PawPrint`).** "Entrar" não grava nada — é ação, não salvamento — por isso não é `BotaoSalva`. Texto ("Entrar"/"Entrando...") e `disabled` continuam controlados pela tela; a cor/formato agora vêm do componente. Escolhi um ícone de pata (identidade CorePet) em vez de um ícone genérico de "entrar".
- **Extensão feita na base (motivada por esta tela):** todo `Botao*` e `BotaoAjuda` ganharam a prop `tamanho` (`"pequeno"|"normal"|"grande"`, enum fechado) — o Login usa "grande" no botão principal. `BotaoBase` também ganhou `...rest` (faltava, travava `aria-*`/`data-*` extras que uma tela precisasse passar).
- **Ícone dentro do campo (usuário/cadeado) → removido.** Nenhum componente v2 do catálogo atual tem "ícone à esquerda embutido" — é um padrão que não existe em nenhum outro campo já migrado. Decisão: não criar um slot novo só para esta tela; ela passa a seguir o padrão limpo (label acima, sem ícone) igual ao resto do catálogo. Sinalizado para o responsável revisar se quer esse padrão de volta.
- **Cartões de seleção de empresa (ícone + nome + subtítulo) → continuam exclusivos da tela.** Não existe candidato v2 pronto para isso, e ainda não vi esse padrão se repetir em outra tela para justificar criar um componente novo agora (evitar abstração especulativa). Fica anotado como candidato a um futuro `CartaoSelecao` se aparecer de novo.
- **Botão "Entrar com outra conta" → continua exclusivo da tela.** É um botão com aparência de link de texto (sem borda/fundo), diferente de todo o catálogo de botões v2 (que sempre tem caixa/borda). Candidato a um futuro botão "tipo link" se o padrão se repetir.
- **Links de navegação (Esqueci minha senha / Criar conta) → recoloridos** do teal customizado antigo (`#0f8b8d`) para o azul padrão (`blue-600`) já usado em foco/seleção no resto do v2. **Logo e gradiente de fundo mantidos intactos** — é identidade de marca proposital, não CSS desorganizado, não faz parte desta limpeza.
- **Extensão feita na base:** `InputTexto`/`InputSenha` não tinham suporte a `autoComplete` (necessário para o gerenciador de senhas do navegador reconhecer os campos) — adicionado nos dois, disponível para qualquer tela a partir de agora.

### Dashboard — detalhe da limpeza de CSS (regra do topo desta página)

- **8 `<button>` nativos identificados; 6 viraram componente v2 novo ou já existente, 2 continuam exclusivos da tela.**
- **13 cartões clicáveis (3 componentes diferentes: `MetricCard`/`CompactMetricCard`/`PriorityCard`) → 1 componente novo `CartaoIndicador`.** As três variações tinham a mesma estrutura (ícone + título + valor + detalhe, navegando ao clicar) com paletas de cor levemente diferentes e sem um vocabulário comum. Novo componente: ícone à esquerda colorido por `tom` (`neutro`/`sucesso`/`perigo`/`informativo`/`atencao` — **mesmo vocabulário da prop `variante` do `BotaoBase`**, decisão explícita do responsável para virar padrão do sistema); seta à direita padronizada (antes `PriorityCard` trocava entre seta e check conforme o estado, agora é sempre o mesmo ícone, e o tom do ícone já comunica o status); miolo (`children`) livre para quem chama formatar o valor como quiser. `MetricCard`/`CompactMetricCard`/`PriorityCard` e o arquivo `pages/dashboard/DashboardCards.jsx` foram removidos (nada mais os importava fora desta tela).
- **2 placeholders de "sem dado no período" (gráfico vazio, lista vazia) → 1 componente novo `EstadoVazio`.** Estrutura idêntica nos dois lugares (ícone + mensagem + descrição opcional, borda tracejada). Não fixa altura própria — quem chama controla o espaço por fora, senão o componente ficaria acoplado a "é gráfico" ou "é lista".
- **Filtro de período (6 botões nativos formando um toggle) → componente novo `SeletorOpcoes`.** Não reaproveita o `InputRadio` (campo de formulário, opções preenchem a linha toda) porque aqui é um controle de barra de ferramentas (pills do tamanho do conteúdo, sem label/erro/obrigatoriedade). Cor de "selecionado" trocada do teal customizado (`#0f8b8d`) para `slate-900`/`cyan-500`, igual ao botão "Analisar com IA" ao lado — mesma linguagem visual, sem hex novo.
- **"Ver produtos" (botão-link de texto) → componente novo `BotaoLink`.** É o mesmo padrão que ficou marcado como "candidato a um futuro botão tipo link" na limpeza do Login (seção acima) — na segunda ocorrência, virou componente. Cor trocada do teal customizado para `blue-600`/`cyan-300` (dark), igual aos links do Login.
- **"Entender painel" / "Analisar com IA" / "Atualizar" → `BotaoInteracao`.** São ações, não salvamentos. Diferença deliberada em relação ao desenho original: os 3 eram visualmente hierarquizados por cor (1 escuro de destaque + 2 com apenas borda, sem preenchimento); como todo `Botao*` é chapado por definição (regra já aplicada ao Cancelar e à variante "informativo"), não existe mais um estilo "com só borda" no catálogo — a hierarquia agora vem só do `tamanho` (`Analisar com IA` = normal, os outros dois = pequeno). Sinalizado para o responsável: se isso for pouco para diferenciar visualmente uma ação primária de secundárias no futuro, é candidato a discutir uma variante "terciária"/contorno — mas isso reabriria a regra do chapado, por isso não decidi isso sozinho.
- **2 botões nativos continuam exclusivos da tela:** as linhas clicáveis de "Base de clientes" (botão de largura total com label + valor) e os cabeçalhos clicáveis "A receber"/"A pagar". Nenhum dos dois tem um segundo caso parecido em outra tela ainda — evitar criar componente por uma ocorrência só (mesmo raciocínio já usado nos cartões de seleção de empresa do Login).
- **Paleta de tom duplicada (`STATUS_STYLES` da própria tela vs. `METRIC_STYLES` de `DashboardCards.jsx`) → unificada em `components/v2/utils/tons.js` (`TONS_BADGE`/`TONS_ICONE`).** As duas definiam as mesmas 4-5 cores semânticas cada uma do seu jeito. Os nomes de tom do selo de status no topo da tela (`getExecutiveStatus` em `dashboardOverview.js`) também foram renomeados (`positive→sucesso`, `critical→perigo`, `warning→atencao`, `neutral→neutro`) para usar o mesmo vocabulário — só o nome interno da chave mudou, a regra de negócio que decide qual status mostrar continua igual.
- **Cor arbitrária em hex (`bg-[#0f8b8d]`, `text-[#0f5f63]`, `bg-[#d8eee9]`) → paleta padrão do Tailwind.** Trocada por `cyan`/`slate`/`blue` conforme o contexto (ver itens acima). O gradiente do gráfico (Recharts) manteve os hex `#0f8b8d`/`#e11d48` — ali é obrigatório (é uma prop de cor de SVG, não uma classe Tailwind), não é o mesmo tipo de problema.
- **Gráfico (Recharts) sem adaptação ao dark mode → corrigido com `useTheme()`.** Cor do grid e dos eixos agora troca conforme o tema (`isDark` de `theme/ThemeContext.jsx`); a biblioteca não lê classes `dark:`, então a única forma de resolver é calculando a cor em JS.
- **Acessibilidade:** `animate-spin` do spinner de carregamento trocado para `motion-safe:animate-spin`; loading de tela inteira ganhou `role="status" aria-live="polite"`; filtro de período ganhou `aria-pressed` por opção (antes só cor indicava a seleção); `CartaoIndicador` ganhou `aria-label={titulo}` quando clicável (sem isso, o nome acessível do botão seria a concatenação de título+valor+detalhe, verboso demais).
- ⚠️ Não testado visualmente num navegador autenticado — a tela exige login multiempresa contra o backend e não há credenciais de desenvolvimento documentadas neste ambiente. Validado por build de produção, ESLint, Prettier e revisão `rams` (sem achados reais pendentes); falta a confirmação visual/funcional em execução real.

## Não identificado

- ❓ Se/quando esta frente também deve cobrir `PlatformLogin.jsx` (`/ops/login`, login separado da equipe CorePet) — é uma tela distinta de `Login.jsx`, não decidido ainda se entra nesta mesma leva.
