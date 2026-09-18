---
tipo: roadmap
atualizado: 2026-09-12
---

# Fase 1 — CI/CD, Boas Práticas, Padronização e Componentização

Parte de [[Roadmap]]. Base: [[CI-CD]], [[Arquitetura]], [[Matriz-de-Riscos]] (item R09).

## Objetivo da fase

Consolidar a fundação de engenharia antes de mapear telas ou mexer em integrações: pipeline confiável, código padronizado, e — o ponto mais importante — arquivos e módulos do tamanho certo, para que a Fase 2 (mapeamento por tela) descreva uma estrutura que vai ficar estável, não uma que está prestes a ser reorganizada.

## 1.1 — CI/CD: consolidar o que já existe, fechar as lacunas conhecidas

O pipeline já é maduro (ver [[CI-CD]]: 8 workflows, gate de release, deploy com backup pré-migration e rollback). Não precisa ser recriado. Ações:

- [ ] **CODEOWNERS** — não existe hoje. Criar mapeando pelo menos: `backend/app/financeiro/` → dono financeiro, `backend/app/intnfe/`+`nfe*` → dono fiscal, `frontend/src/` → dono frontend, `.github/workflows/` + `scripts/deploy_*` → dono de infra/deploy. Vira obrigatório assim que houver mais de uma pessoa commitando com regularidade.
- [ ] **GitHub Environments** para `production` com required reviewers — formaliza em configuração do GitHub a regra que hoje só existe em texto (`AGENTS.md`: "nunca fazer deploy sem autorização explícita").
- [ ] **Deploy automático de homologação** pós-merge em `main` — o workflow `homologacao-isolada.yml` já monta o ambiente completo; falta automatizar o gatilho (hoje é manual/por mudança de infra). Produção continua manual.
- [ ] **Hook local de lint pré-commit** — hoje `.githooks/pre-commit` só bloqueia commit direto em `main`; considerar adicionar `ruff check`/`eslint` rápido como segunda checagem local, para pegar erro antes mesmo do PR (CI já bloqueia, isso só antecipa o feedback).
- [ ] Manter o gate de release e o rollback exatamente como estão — já é o padrão correto para deploy sem Kubernetes (ver [[CI-CD]] "Proposta de evolução").

## 1.2 — Padronização de código: expandir o que já é bloqueante

Confirmado: `ruff check`/`ruff format` já são bloqueantes no backend CI; ESLint/Prettier já configurados no frontend (`npm run lint:core`, `npm run format:core:check`). Ações para aprofundar:

- [ ] **Type checking real no backend** — ⚠️ não identificado uso de `mypy`/`pyright` no `backend-ci.yml`. Avaliar adicionar ao menos em modo não-bloqueante inicialmente, dado o volume de arquivos (~300+).
- [ ] **TypeScript no frontend** — hoje majoritariamente `.jsx`; `frontend/src/stores/whatsappStore.ts` e `services/api.ts` são exceções isoladas. Não propor migração total (custo alto sem evidência de necessidade); propor que **código novo** em áreas críticas (pagamento, fiscal, autenticação) seja escrito em `.tsx`/`.ts` a partir de agora, migrando organicamente.
- [ ] **Convenção de nomenclatura de arquivo por domínio** — hoje mistura `banho_tosa_agenda_capacity.py` (snake_case longo, flat) com `vendas/` (pasta por domínio). Definir formalmente em `docs/BLUEPRINT_BACKEND.md` (já existe o padrão-alvo) que todo domínio **novo ou refatorado** vai para pasta própria — não é preciso reescrever o que já funciona, só não adicionar mais arquivos flat nas áreas legadas.

## 1.3 — Componentização: consolidar a campanha que já existe, não começar do zero

**Achado confirmado nesta rodada, com histórico detalhado em `docs/EVOLUCAO_ENTERPRISE_UI_REFATORACAO.md` (3.365 linhas):** já existe uma campanha extensa e ativa de redução de arquivos grandes, com régua própria (>700 linhas = atenção, >1000 = prioridade, >1500 = crítico), validada por teste automatizado, em backend, frontend e app-mobile.

**Linha do tempo confirmada:**
- 2026-06-24: pico de **144 arquivos** acima de 700 linhas (58 acima de 1000, 12 acima de 1500).
- 2026-07-07 (batch 56/57): campanha zera o inventário — **0 arquivos** acima de 700 linhas nos 3 produtos. Nasce o teste de guarda `backend/tests/unit/test_application_large_files_guard.py` (`assert oversized == {}`), e o gate ainda mais rígido `test_backend_zero_large_files_refactor.py` (nenhum arquivo do backend acima de **1000** linhas, sem exceção, com testes de identidade de objeto `is` provando que a extração não duplicou lógica).
- 2026-08-22: após novas funcionalidades, o número naturalmente volta a **22-23 arquivos** (entropia esperada de desenvolvimento contínuo, já reconhecida no próprio documento).
- **2026-09-12 (contagem ao vivo feita nesta análise, replicando a lógica exata do teste):** o número subiu para **46 arquivos** ≥700 linhas (24 backend, 17 frontend, **5 app-mobile** — antes zerado). ⚠️ **Nada está acima de 1000 linhas** (o gate mais rígido do backend continua válido), mas o teste de 700 linhas provavelmente **falharia se rodado hoje** — não foi confirmado se ele está ativo/passando no CI atual ou se foi ajustado.

Isso significa: **o problema de "arquivo grande demais" já tem processo, métrica e teste de regressão** — só precisa de mais uma rodada de manutenção, igual às duas anteriores. A ação desta fase não é criar isso — é **retomar a limpeza e dar direção estrutural** a ela:

- [ ] **Confirmar o status atual do teste `test_application_large_files_guard.py` no CI** (passando, falhando, ou desabilitado) — primeira ação concreta, antes de qualquer outra, já que o número real (46) diverge do último registro documentado (22).
- [ ] Priorizar os 5 arquivos mais próximos de 1000 linhas como primeira fatia da nova rodada: `backend/app/clientes/crud_routes.py` (966), `frontend/src/pages/centralAjuda/centralAjudaKnowledge.js` (952), `app-mobile/src/screens/funcionario/pdv/FuncionarioPdvContent.tsx` (945), `backend/app/services/base_catalog_enrichment_service.py` (887), `backend/app/routes/ecommerce_public.py` (885).

- [ ] Ao dividir um arquivo grande, preferir o padrão de pasta por domínio (`routes.py` / `schemas.py` / `services.py` / `queries.py` / `events.py`, já documentado em `docs/BLUEPRINT_BACKEND.md`) em vez de só cortar em pedaços menores sem organização temática. Um arquivo dividido em 3 arquivos igualmente "flat" resolve o teste de linha, mas não resolve a navegabilidade.
- [ ] Escolher 2-3 domínios legados mais "flat" como piloto do padrão de pasta ao serem refatorados: candidatos por volume de arquivos soltos — `banho_tosa_*` (~30 arquivos), `veterinario_*` (~25 arquivos), `estoque_*` (~20 arquivos). `campaigns/`, `vendas/`, `clientes/`, `produtos/`, `intnfe/` já são bons exemplos a copiar (já seguem pasta por domínio).
- [ ] Documentar a decisão como atualização de `docs/BLUEPRINT_BACKEND.md` ou um ADR novo se a régua mudar (critério do próprio `docs/adr/README.md`: "decisão que afeta vários módulos ou PRs").
- [ ] Ao terminar cada domínio migrado para o padrão de pasta, atualizar a [[Matriz-de-Cobertura]] e o respectivo documento em [[Funcionalidades]] com a nova localização de arquivo (evita a documentação da Fase 2 ficar desatualizada).

## 1.4 — Auditoria de duplicação e over-parametrização (preparação para a Fase 2)

Esta análise (fase de reconhecimento) mapeou **estrutura**, não duplicação de lógica linha a linha — isso é trabalho novo desta fase:

- [ ] **Duplicação:** revisar especificamente os arquivos "facade de compatibilidade" já identificados (`produtos_models.py`, `financeiro_models.py`, `estoque_models.py` como agregadores que reexportam de arquivos menores) — confirmar que são *apenas* reexportação (padrão aceitável, documentado em [[Arquitetura]]: "arquivos de compatibilidade podem reexportar nomes antigos... devem ser pequenos e apontar para a implementação modular") e não têm lógica de negócio duplicada dentro deles.
- [ ] Rodar uma ferramenta de detecção de código duplicado (ex.: `jscpd` para frontend, algo equivalente para Python) como checagem pontual — não precisa virar gate de CI imediatamente, mas gera uma lista priorizada de onde a mesma regra de negócio existe em mais de um lugar.
- [ ] **Over-parametrização (o oposto):** ao dividir os arquivos grandes da campanha 700-linhas, identificar funções/serviços com muitos parâmetros booleanos/flags de comportamento (sinal comum de que deveriam ser métodos separados em vez de um método genérico com `if/else` por flag) — não foi feito levantamento específico disso nesta rodada; tratar como parte do trabalho de cada domínio migrado para pasta, não como tarefa isolada.

## 1.5 — Confiabilidade e observabilidade (proposta nova, fora da auditoria original)

A auditoria de 2026-09-12 cobriu segurança, arquitetura e funcionalidades, mas não observabilidade/confiabilidade em produção — é uma lacuna própria, não um risco já catalogado em [[Matriz-de-Riscos]]. Faz sentido tratar aqui, na fase de fundação, porque monitoramento é infraestrutura que as fases seguintes (mapeamento de tela, integrações, segurança) vão depender para saber se algo quebrou:

- [ ] **Error tracking em produção** (ex.: Sentry) — já está listado como "próxima feature" desde `docs/PROXIMO_PASSO.md` (fevereiro/2026) e ainda não foi implementado. Sem isso, bugs em produção só aparecem quando um usuário reclama.
- [ ] **Alerta quando um worker de background para** (`worker-bling`, `worker-catalogo`, ver [[Arquitetura]]) — hoje o sintoma de um worker parado (estoque/catálogo desatualizado) só aparece dias depois. Reaproveitar a integração WhatsApp/WAHA já existente no projeto para notificar o responsável.
- [ ] **Conectar `docs/SLOS_INDICADORES_JORNADAS.md` a dados reais** — confirmar se os indicadores ali definidos já são medidos (dashboard) ou se é só a meta declarada; se for só a meta, é o passo natural depois do error tracking.
- [ ] **Testar restauração de backup, não só a rotina de backup** — [[Pendencias]] já lista RPO/RTO formal como não encontrado. Agendar um exercício periódico de restauração real em ambiente isolado (o workflow `homologacao-isolada.yml` já existe e pode ser reaproveitado para isso). Backup nunca restaurado de verdade é uma suposição, não uma garantia.
- [ ] **Teste de carga básico antes de crescer a base de tenants** — não encontrado em nenhum dos 8 workflows de CI hoje (cobrem lint/teste/segurança/E2E, não carga). Simular picos reais de PDV (ex.: sábado de manhã, múltiplos tenants simultâneos) com uma ferramenta simples (k6, Locust) antes que o volume real force essa descoberta em produção.
- [ ] **Painel de status público, ainda que simples** (ex.: `status.corepet.com.br`, mesmo que atualizado manualmente no início) — reduz o volume de "o sistema caiu?" chegando por canais informais quando um pet shop depende do sistema no caixa.

## 1.6 — Biblioteca de campos de formulário (proposta nova, fora da auditoria original)

> ✅ **Implementação real iniciada em `frontend/src/components/v2/`.** O responsável decidiu nomenclatura em português (`InputTexto`, `InputSenha`, `InputData`, `InputDataHora`, `InputPeriodo`, `InputCheck`, `InputRadio`, `InputMoeda`, `InputQuantidade`, `InputPercentual`, `InputTelefone`, `InputCpfCnpj`, `InputCombobox`) em vez dos nomes em inglês propostos abaixo (`MoneyField`, `DateField` etc.) — os nomes em inglês nesta seção ficam como registro do raciocínio original, não como padrão a seguir. Regra adicional definida na prática: os componentes evitam ao máximo receber prop que influencie aparência (cor/tamanho) — quando uma variação real de formato é necessária, vira um componente novo, não um parâmetro. Ver exemplo vivo de cada um em `/ops/styleguide`.

Diretriz trazida pelo responsável, validada contra o código: **nenhuma tela deve usar `<input>`, `<select>`, `<textarea>` nativos diretamente.** Cada tipo de campo (texto, monetário, data, combobox, rádio, checkbox, CPF/CNPJ, telefone, percentual...) deve ser um componente próprio, que reaproveita uma base comum e adiciona por cima máscara, rótulo, validação e comportamento — em vez de cada tela reimplementar isso na hora.

### Estado atual confirmado no código (2026-09-12)

O projeto já tem o começo da ideia, mas de forma parcial e não obrigatória:

| O que existe | Onde | Limitação |
|---|---|---|
| `FormField`, `TextField`, `SelectField`, `CheckboxField` | `frontend/src/components/ui/FormField.jsx` | 3 tipos genéricos só, usados em ~40 arquivos — não é a base de nada mais específico |
| `CurrencyInput` (monetário, máscara manual da direita para a esquerda) | `frontend/src/components/CurrencyInput.jsx` | Implementação isolada, não usa `FormField` (sem label/erro padronizado) |
| `QuantidadeInput` (decimal livre para digitar no PDV) | `frontend/src/components/QuantidadeInput.jsx` | Mesma limitação — isolado, sem label/erro |
| `SubtotalInput` | `frontend/src/components/SubtotalInput.jsx` | Idem |
| `AutocompleteSelect` (combobox com busca, criação de opção) | `frontend/src/components/ui/AutocompleteSelect.jsx` | É o mais completo dos existentes, mas fora da família `FormField` |
| Campo de data mascarado | `frontend/src/pages/veterinario/agenda/AgendaDateInputField.jsx` | Local da agenda do veterinário, não reaproveitável — não existe um `DateField` genérico |
| Máscara de CPF | `frontend/src/pages/Pessoas.jsx` (função `formatarCPF` solta) | Não é componente nem util compartilhado — se outra tela precisar de CPF, reimplementa do zero |

**Não existe:** campo de CNPJ, telefone, percentual, rádio, textarea, senha (com mostrar/ocultar) como componente reaproveitável. **Não existe** nenhuma biblioteca de formulário/máscara no `package.json` (`react-hook-form`, `react-input-mask`, MUI, Ant Design etc. — tudo é feito à mão com Tailwind, o que está correto para o estilo do projeto, só falta organizar). E **`<input>` nativo aparece direto em 356 dos ~1043 arquivos `.jsx`/`.tsx`** do frontend — a maioria das telas hoje não passa por nenhum componente.

### Arquitetura proposta

Em React o equivalente a "herdar" não é `extends` de classe — é **composição**: um campo específico envolve (ou usa por dentro) o campo base, em vez de estender uma classe. A ideia do responsável se traduz assim:

```text
BaseTextField  (primitivo — renderiza o <input> nativo UMA única vez no projeto inteiro)
  │
  ├─ TextField        (já existe em FormField.jsx — hoje é o próprio primitivo, vira wrapper fino sobre BaseTextField)
  ├─ MoneyField        ← substitui/absorve CurrencyInput
  ├─ QuantityField     ← substitui/absorve QuantidadeInput
  ├─ PercentField       (novo — percentual, usado em telas de margem/comissão)
  ├─ CpfCnpjField       (novo — detecta CPF vs CNPJ pelo tamanho, aplica a máscara certa)
  ├─ PhoneField         (novo — (xx) xxxxx-xxxx)
  ├─ DateField          ← generaliza AgendaDateInputField (dd/mm/aaaa, validação de intervalo)
  └─ PasswordField      (novo — com alternância mostrar/ocultar)

BaseSelectField  (primitivo — <select> nativo)
  ├─ SelectField        (já existe em FormField.jsx)
  └─ ComboboxField      ← renomeia/absorve AutocompleteSelect

BaseChoiceField  (primitivo — <input type="checkbox"/"radio">)
  ├─ CheckboxField      (já existe em FormField.jsx)
  └─ RadioGroupField    (novo — não existe nenhuma versão hoje)
```

Regra de ouro para quem for implementar: **o `<input>`/`<select>` nativo só pode aparecer dentro de `BaseTextField`, `BaseSelectField` e `BaseChoiceField`.** Todo o resto do projeto usa os campos derivados.

### Exemplo de composição (não é código final, é o padrão a seguir)

```jsx
// components/ui/fields/BaseTextField.jsx — o único lugar do projeto com <input> de texto nativo
export const BaseTextField = forwardRef(function BaseTextField(
  { label, error, help, required, tone = "default", inputClassName = "", ...inputProps },
  ref,
) {
  return (
    <FormField label={label} error={error} help={help} required={required} tone={tone}>
      <input ref={ref} className={cx(toneClasses[tone].control, inputClassName)} {...inputProps} />
    </FormField>
  );
});

// components/ui/fields/MoneyField.jsx — reaproveita a máscara que já existe em CurrencyInput.jsx,
// hoje solta dentro do próprio componente; a proposta é extrair para um hook e reusar aqui
export function MoneyField({ value, onChange, maxValue, allowNegative, ...fieldProps }) {
  const { display, handleKeyDown } = useCurrencyMask({ value, onChange, maxValue, allowNegative });
  return (
    <BaseTextField
      inputMode="numeric"
      value={display}
      onChange={() => {}}
      onKeyDown={handleKeyDown}
      {...fieldProps} // label, error, help, required, tone passam direto
    />
  );
}
```

`CurrencyInput.jsx` e `QuantidadeInput.jsx` já seguem a convenção certa de `onChange(valorNormalizado)` em vez de `onChange(event)` — manter essa convenção em todos os campos novos, é o que faz um `MoneyField` e um `TextField` serem intercambiáveis do ponto de vista de quem consome.

### Passos concretos, em ordem

- [ ] **Consolidar o que já existe primeiro (baixo risco, alto valor imediato).** Criar `frontend/src/components/ui/fields/`, mover `BaseTextField`/`BaseSelectField`/`BaseChoiceField` para lá a partir do que já está em `FormField.jsx`, e reescrever `CurrencyInput` → `MoneyField`, `QuantidadeInput` → `QuantityField`, `AutocompleteSelect` → `ComboboxField` como wrappers finos sobre a base — sem mudar o comportamento de máscara que já funciona, só padronizar a casca (label/erro/help consistentes, que hoje `CurrencyInput`/`QuantidadeInput` não têm).
- [ ] **Generalizar `AgendaDateInputField` em `DateField`**, tirando-o de `pages/veterinario/agenda/` para `components/ui/fields/`.
- [ ] **Criar os campos que não existem hoje**, por ordem de uso provável: `CpfCnpjField` e `PhoneField` (usados em cadastro de cliente/fornecedor/funcionário — todos reaproveitam a mesma entidade `Cliente`, ver [[Cliente]]), `PercentField` (telas de margem/comissão — commits recentes como "Corrigir margem sobre venda em precificação" sugerem que essa conta já dá trabalho, um campo dedicado com validação de faixa ajuda a evitar o próximo bug parecido), `RadioGroupField`, `PasswordField`.
- [ ] **Não fazer migração em massa dos 356 arquivos com `<input>` nativo de uma vez.** Regra prática: todo código **novo ou tocado** em um PR passa a usar os campos da família; migração de tela antiga acontece quando a tela for mexida por outro motivo (ex.: quando for mapeada na Fase 2, ver [[Fase-2-Funcionalidades-e-Skills]]), não como projeto à parte.
- [ ] **Priorizar a migração oportunista pelos módulos de maior risco primeiro** — Financeiro e PDV (valores monetários errados custam caro), depois Fiscal/Configurações, só depois o resto — mesmo critério de risco já usado no restante deste roadmap.
- [ ] **Adicionar um lint bloqueante** proibindo `<input>`/`<select>`/`<textarea>` em JSX fora de `components/ui/fields/` (regra customizada de ESLint, ou `no-restricted-syntax` apontando para o seletor AST desses elementos) — sem isso, a convenção depende de review manual e tende a se perder com o tempo, do mesmo jeito que o padrão de pasta por domínio (ver 1.2) não é seguido pelo código legado sem um teste automatizado como o da campanha de arquivos grandes (ver 1.3).
- [ ] **Testar cada campo novo com um teste `.mjs` colocado ao lado**, seguindo o padrão que o projeto já usa (`autocompleteSelectUtils.test.mjs`, `ImprimirSaldoCredito.test.mjs`) — cobrindo pelo menos a máscara (entrada → saída esperada) e o caso de valor vazio/inválido.

### Definição de pronto para um campo da família

- [ ] Encaminha `ref` (`forwardRef`) para o `<input>`/`<select>` interno, para casos que precisam de foco programático (ex.: PDV).
- [ ] Aceita `label`, `error`, `help`, `required`, `disabled`, `tone` — herdados do `FormField` já existente, não reinventados por campo.
- [ ] `onChange` entrega o valor já convertido (número, string formatada, boolean), nunca o evento cru.
- [ ] Label associado via `id`/`htmlFor` e erro associado via `aria-describedby` (acessibilidade — ver também [[Fase-2-Funcionalidades-e-Skills]] 2.6, que cobre acessibilidade nas telas de uso diário).
- [ ] Tem pelo menos um teste `.mjs` cobrindo a lógica de máscara/validação.
- [ ] Tem entrada no styleguide (ver item 1.8) criada no mesmo PR — um campo não está "pronto" enquanto não estiver documentado lá.

## 1.7 — Biblioteca de componentes de tela: tipografia, botões e modais (proposta nova, fora da auditoria original)

Mesma lógica do item 1.6, agora para o resto da tela: **título, subtítulo, texto de destaque, texto simples, texto de ajuda, botão e modal também devem ter uma única fonte cada um**, em vez de cada tela (ou cada componente de `components/ui/`) redefinir sua própria escala tipográfica e seu próprio botão/modal com classes Tailwind soltas.

> ✅ **Botões implementados em `frontend/src/components/v2/`** com nomenclatura em português: `BotaoBase` (casca interna, não usar direto numa tela), `BotaoSalva`, `BotaoCancelar`, `BotaoExcluir` (já pede confirmação via `corepetDialog` antes de agir — decisão nova, não estava prevista abaixo), `BotaoAjuda` (sempre só ícone) e `BotaoInteracao` (ação secundária genérica — avançar/voltar/ver detalhes, não abertura de menu). Tipografia e Modal genérico continuam planejados. Ver exemplo vivo em `/ops/styleguide`.

### Estado atual confirmado no código — tipografia, botões e modais (2026-09-12)

Levantamento quantitativo feito nesta rodada, replicável com `grep`:

| Recurso | O que existe | Evidência de duplicação |
|---|---|---|
| **Tipografia** (título/subtítulo/texto) | Nenhum componente — nem `Title`, nem `Text`, nem `HelpText` foi encontrado em nenhum lugar do projeto | `<h1>`–`<h4>` nativos aparecem direto em **530 arquivos**. Pior: os próprios componentes de `components/ui/` já reimplementam a mesma ideia cada um do seu jeito — `PageHeader.jsx` tem seu próprio `<h1 className="text-xl font-bold...">`, `Panel.jsx` tem seu próprio `<h2 className="text-base font-semibold...">`, `EmptyState.jsx` tem seu próprio `<div className="text-sm font-semibold...">` para título — três escalas de "título" ligeiramente diferentes, nenhuma reaproveitando a outra |
| **Botões** | Já existe uma base boa: `ActionButton`/`IconActionButton` (`components/ui/ActionButton.jsx`, `IconActionButton.jsx`) apoiados num sistema de tokens já maduro em `components/ui/actionStyles.js` (`intent` × `tone` × `size`, com regra documentada de quando usar cada cor — `ACTION_COLOR_RULES`) | O problema aqui não é falta de componente-base, é **adoção** (`<button` nativo em **585 arquivos** contra **135** com `ActionButton`) **e falta de um catálogo por ação**: nada garante hoje que todo botão de "salvar" tenha o mesmo ícone+cor+comportamento — cada tela escolhe `intent`/`icon`/texto na mão. Exemplo concreto já reimplementado localmente: `PageHeader.jsx` monta seu próprio botão de ajuda com `IconActionButton` + `HelpCircle` só para o botão de tour — é exatamente o tipo de botão que deveria ser um `HelpButton` reaproveitável, não algo remontado dentro de `PageHeader` |
| **Modais** | `CorePetDialogHost.jsx` é um bom exemplo de **casca única para confirmação/prompt** (substitui `window.confirm`/`window.prompt`, já com `role="dialog"`, `aria-modal`, foco automático, `Escape` para fechar) — mas só serve para confirmar/perguntar, não para conteúdo arbitrário (formulário, wizard, lista) | **151 arquivos** têm seu próprio bloco `fixed inset-0` (a casca de modal reimplementada do zero a cada vez), mas só **18** usam `role="dialog"` — ou seja, boa parte desses ~151 modais não tem semântica de acessibilidade correta, e não há como saber sem abrir cada um |

### Arquitetura proposta — tipografia, botões e modais

**Tipografia** — componentes pequenos, sem lógica, só a escala visual nomeada (extraídos do que já está implícito em `PageHeader`/`Panel`/`EmptyState`, não inventados do zero):

```text
components/ui/typography/
  Title.jsx       — título de página/seção (o que hoje é o <h1> solto em PageHeader.jsx)
  Subtitle.jsx     — linha de apoio abaixo do título (o que hoje é o <p> solto em PageHeader.jsx)
  SectionTitle.jsx — título de bloco/card, menor que Title (o que hoje é o <h2> solto em Panel.jsx)
  Text.jsx         — parágrafo padrão, com variação de tom (default | muted | destaque)
  HelpText.jsx     — texto de ajuda/legenda pequena (o que hoje o FormField.jsx já faz só para campos de formulário)
```

**Botões** — dois níveis, não recriar a base, adicionar uma camada em cima dela:

1. **Base (já existe, só formalizar):** `ActionButton` (ícone + texto) e `IconActionButton` (só ícone), os dois sempre construídos em cima de `actionButtonClasses`/`iconActionButtonClasses` de `actionStyles.js`. Nenhum botão novo nasce com `className` de Tailwind solta reinventando cor/tamanho.
2. **Catálogo por ação (novo — é a peça que falta):** um componente por *intenção* de botão — salvar, cancelar, excluir, ajuda, alternar submenu etc. — que já fixa ícone, `intent`/cor e comportamento, e decide sozinho entre os dois formatos que você descreveu:
   - **Grande** (`size="lg"`, padrão): renderiza via `ActionButton` — ícone + texto.
   - **Pequeno** (`size="sm"`): renderiza via `IconActionButton` — só ícone, e o texto vira `title`/`aria-label` automaticamente (hoje `IconActionButton` aceita `title` como qualquer prop HTML, mas nada obriga a informar — se o chamador esquecer, o botão fica sem nome acessível para leitor de tela; o catálogo por ação resolve isso preenchendo sempre, porque o texto do rótulo é a própria fonte do `title`).

   O texto pode variar por tela ("Salvar", "Salvar cliente", "Gravar alteração") — só o ícone, a cor e o comportamento base ficam fixos, que é exatamente a regra pedida: todo botão que grava algo tem a mesma cara, independente do texto.

**Modais** — uma casca única de uso geral, inspirada na acessibilidade já resolvida em `CorePetDialogHost.jsx` (mesmo `role="dialog"`, `aria-modal`, captura de `Escape`, foco automático ao abrir), mas aberta para receber qualquer conteúdo, não só confirmação/prompt:

```text
components/ui/Modal.jsx
  Modal            — casca (backdrop + painel + role="dialog" + Escape + foco)
  Modal.Header      — título do modal (usa Title/SectionTitle por dentro) + botão fechar
  Modal.Body        — área de conteúdo com scroll próprio quando necessário
  Modal.Footer      — ações (usa ActionButton por dentro — nunca botão cru)
```

### Exemplo de código (não é código final, é o padrão a seguir)

```jsx
// components/ui/typography/Title.jsx
const SIZES = {
  page: "text-xl font-bold text-slate-950 dark:text-slate-100",       // PageHeader hoje
  section: "text-base font-semibold text-slate-900 dark:text-slate-100", // Panel hoje
};

export function Title({ as: Tag = "h1", size = "page", className = "", children }) {
  return <Tag className={cx(SIZES[size], className)}>{children}</Tag>;
}

// components/ui/actions/SaveButton.jsx — um arquivo por ação; ícone/cor fixos, texto e formato variam
export function SaveButton({ label = "Salvar", size = "lg", ...props }) {
  if (size === "sm") {
    return <IconActionButton icon={Save} intent="create" title={label} aria-label={label} {...props} />;
  }
  return (
    <ActionButton icon={Save} intent="create" {...props}>
      {label}
    </ActionButton>
  );
}

// components/ui/actions/CancelButton.jsx
export function CancelButton({ label = "Cancelar", size = "lg", ...props }) {
  if (size === "sm") {
    return <IconActionButton icon={X} intent="neutral" tone="ghost" title={label} aria-label={label} {...props} />;
  }
  return (
    <ActionButton icon={X} intent="neutral" tone="ghost" {...props}>
      {label}
    </ActionButton>
  );
}

// components/ui/actions/DeleteButton.jsx
export function DeleteButton({ label = "Excluir", size = "lg", ...props }) {
  if (size === "sm") {
    return <IconActionButton icon={Trash2} intent="delete" title={label} aria-label={label} {...props} />;
  }
  return (
    <ActionButton icon={Trash2} intent="delete" {...props}>
      {label}
    </ActionButton>
  );
}

// components/ui/actions/HelpButton.jsx — ajuda é quase sempre só ícone; "lg" existe mas raramente usado
export function HelpButton({ label = "Ajuda", size = "sm", ...props }) {
  if (size === "lg") {
    return (
      <ActionButton icon={HelpCircle} intent="neutral" tone="ghost" {...props}>
        {label}
      </ActionButton>
    );
  }
  return <IconActionButton icon={HelpCircle} intent="neutral" title={label} aria-label={label} {...props} />;
}

// components/ui/actions/SubmenuToggleButton.jsx — abre/fecha um submenu; usa o "active" que IconActionButton já suporta
export function SubmenuToggleButton({ label = "Mais opções", active = false, size = "sm", ...props }) {
  const Icon = active ? ChevronUp : ChevronDown;
  if (size === "lg") {
    return (
      <ActionButton icon={Icon} intent="neutral" tone="ghost" {...props}>
        {label}
      </ActionButton>
    );
  }
  return (
    <IconActionButton icon={Icon} intent="neutral" active={active} title={label} aria-label={label} {...props} />
  );
}

// components/ui/Modal.jsx — casca única; conteúdo arbitrário, acessibilidade resolvida uma vez só
export function Modal({ open, onClose, labelledBy, size = "md", children }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => event.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        className={cx(
          "w-full overflow-hidden rounded-2xl bg-white shadow-2xl dark:bg-slate-900",
          MODAL_SIZES[size],
        )}
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </section>
    </div>
  );
}
Modal.Header = ModalHeader;
Modal.Body = ModalBody;
Modal.Footer = ModalFooter;
```

Uso esperado numa tela — repare que quem chama só decide texto/tamanho, nunca ícone ou cor:

```jsx
<Modal open={aberto} onClose={fechar} labelledBy="titulo-modal-x">
  <Modal.Header titleId="titulo-modal-x">Novo fornecedor</Modal.Header>
  <Modal.Body>{/* formulário usando os campos do item 1.6 */}</Modal.Body>
  <Modal.Footer>
    <CancelButton onClick={fechar} />
    <SaveButton label="Salvar fornecedor" onClick={salvar} />
  </Modal.Footer>
</Modal>

{/* numa barra de ferramentas compacta, o mesmo SaveButton vira ícone com tooltip: */}
<SaveButton size="sm" onClick={salvar} />
```

### Passos concretos para tipografia, botões e modais, em ordem

- [ ] **Tipografia — extrair, não inventar.** Criar `components/ui/typography/` com `Title`, `Subtitle`, `SectionTitle`, `Text`, `HelpText`, copiando exatamente as classes que já existem em `PageHeader.jsx`/`Panel.jsx`/`EmptyState.jsx` hoje (visual não muda). Depois, fazer esses três arquivos passarem a usar os novos componentes por dentro — primeira prova de que a extração não quebrou nada.
- [ ] **Botões — base é adoção, catálogo por ação é criação.** `ActionButton`/`IconActionButton` já são a base certa, não recriar. Criar `components/ui/actions/` com um arquivo por intenção de botão — mínimo inicial: `SaveButton`, `CancelButton`, `DeleteButton`, `HelpButton`, `SubmenuToggleButton` — cada um já fixando ícone/`intent`/comportamento e decidindo entre `size="lg"` (ícone+texto) e `size="sm"` (só ícone, com `title`/`aria-label` preenchidos automaticamente pelo próprio rótulo). Primeiro uso real: substituir o botão de ajuda remontado à mão em `PageHeader.jsx` (`onTour`) por um `HelpButton` — prova de conceito de baixo risco antes de espalhar o padrão. Levantar com o responsável quais outras ações se repetem o bastante para merecer entrada no catálogo (candidatos prováveis pela quantidade de modais: "Confirmar", "Voltar", "Exportar" — `ExportActionButton.jsx` já existente é outro candidato a entrar nesse catálogo em vez de ficar solto). Qualquer botão novo usa um item do catálogo quando a ação já tem um, ou `ActionButton`/`IconActionButton` direto quando é uma ação única da tela; migração dos 585 arquivos com `<button>` nativo acontece oportunisticamente (mesma regra do item 1.6 — quando a tela for tocada por outro motivo).
- [ ] **Modais — criar a casca, depois migrar.** Criar `components/ui/Modal.jsx` (`Modal`/`Modal.Header`/`Modal.Body`/`Modal.Footer`) usando `CorePetDialogHost.jsx` como referência de acessibilidade. Escolher 2-3 modais simples já existentes como piloto de migração (bom critério: modais pequenos e sem lógica de wizard, para validar a casca antes de migrar os mais complexos).
- [ ] **Auditoria pontual de acessibilidade nos 151 modais existentes** — não precisa esperar a migração para o novo `Modal.jsx`; confirmar ao menos que `Escape` fecha e que o foco vai para dentro do modal ao abrir é uma correção rápida mesmo nos modais que ainda não foram migrados.
- [ ] **Lint bloqueante para botão** — proibir `<button>` nativo fora de `ActionButton.jsx`/`IconActionButton.jsx` (mesmo mecanismo do item 1.6 para `<input>`). Para modais, o reforço automático é mais difícil (não há uma tag `<modal>` para banir); tratar como item de checklist de revisão de PR (`.github/pull_request_template.md` já tem uma seção de checklist — candidato a um item novo ali) em vez de lint.
- [ ] **Atualizar `docs/BLUEPRINT_BACKEND.md`-equivalente para frontend** (ou criar `docs/BLUEPRINT_FRONTEND.md`, se não existir) documentando que tipografia, botão, modal e os campos do item 1.6 são de uso obrigatório — hoje essa regra só vai existir aqui no roadmap; sem um documento de referência permanente, tende a se perder conforme o roadmap avança de fase.

### Definição de pronto — tipografia, botão e modal

- **Tipografia:** aceita `as`/`size`/`className`, nunca tamanho de fonte/peso definido fora do componente.
- **Botão:** toda ação que se repete em mais de uma tela (salvar, cancelar, excluir, ajuda, alternar submenu...) tem um componente próprio em `components/ui/actions/`, com ícone e `intent` fixos (ver `ACTION_COLOR_RULES` em `actionStyles.js`) e suporte aos dois formatos (`size="lg"` ícone+texto, `size="sm"` só ícone com `title`/`aria-label` automáticos); só texto e `onClick` variam por tela. Ação sem componente próprio (caso único de uma tela) usa `ActionButton`/`IconActionButton` direto — nunca `className` solta reinventando cor/tamanho.
- **Modal:** usa `role="dialog"` + `aria-modal` + `aria-labelledby`, fecha com `Escape`, foco vai para dentro ao abrir, cabeçalho/rodapé usam os componentes de tipografia/botão acima — nunca `<h2>`/`<button>` soltos dentro de um modal novo.
- **Todos os três:** têm entrada no styleguide (ver item 1.8) criada no mesmo PR.

## 1.8 — Styleguide: fonte única das regras de uso (proposta nova, fora da auditoria original)

Ter os componentes (1.6 e 1.7) não resolve sozinho — sem um lugar único que diga **quando** usar cada um, a inconsistência volta pela porta dos fundos: cor errada por `intent` mal escolhido, campo usado fora do contexto certo, modal remontado do zero por quem não sabia que a casca já existia. É o mesmo risco que [[Matriz-de-Riscos]] já registra em R09 sobre o padrão de pasta por domínio: **documentar sozinho não basta se não for fácil de achar e difícil de deixar desatualizado.**

> ✅ **Duas regras de processo definidas na prática, em 2026-09-12, a partir de um bug visual real** (label renderizando com cor errada nos campos legados do próprio style guide):
>
> 1. **Nenhum componente novo é considerado "Pronto" isolado.** Ele precisa aparecer funcionando dentro da seção "Formulário de exemplo" do `/ops/styleguide` (`FormularioExemploSection.jsx`) — vários campos reais lado a lado, do jeito que uma tela de verdade usaria. Um componente só "parece certo" sozinho em uma vitrine; problemas de espaçamento, contraste e alinhamento em conjunto só aparecem quando ele divide espaço com os outros.
> 2. **`mcp__rams__quick_review` é obrigatório em todo componente de `components/v2/` antes de considerá-lo pronto** — rodar nos arquivos alterados, corrigir o que ele apontar, rodar de novo até não sobrar achado sério. Já pegou, na prática desta sessão, contraste insuficiente em estado `dark:` de botões selecionados, `aria-describedby` quebrado quando `id` não é passado, e asterisco de campo obrigatório sem texto para leitor de tela — nenhum desses seria detectado só olhando a tela renderizada.

### Onde mora

- [ ] Criar `docs/GUIA_ESTILO_FRONTEND.md` — nome no mesmo padrão já usado em `docs/` (paralelo a `docs/BLUEPRINT_BACKEND.md`, que já cumpre esse papel para o backend). Referenciar a partir de `Documentacao/README.md` e `Documentacao/Arquitetura.md` como qualquer outro documento oficial do projeto, não como anotação solta.
- [ ] Storybook (ou equivalente) como complemento visual navegável é uma opção válida **mais adiante**, se o time crescer o suficiente para justificar mais uma ferramenta no projeto — não é pré-requisito. A versão em Markdown já resolve o problema central ("onde eu confiro a regra") sem exigir dependência nova.

### O que precisa conter (esqueleto mínimo do documento)

1. **Princípios gerais** — as poucas regras que valem para o sistema inteiro: nenhum `<input>`/`<select>`/`<textarea>`/`<button>`/`<h1>`–`<h4>` nativo fora dos componentes-base de 1.6/1.7; Tailwind é a implementação por dentro dos componentes, nunca a interface que quem monta a tela escreve na mão; todo componente novo nasce com classes `dark:` — hoje é convenção seguida em 100% do que existe em `components/ui/`, vale formalizar antes que alguém quebre isso sem perceber.
2. **Catálogo de componentes**, uma entrada por componente sempre no mesmo formato — **Quando usar** / **Quando não usar** / **Props principais** / **Exemplo mínimo** / **Anti-exemplo** (o erro comum a evitar). Cobre não só os componentes novos de 1.6/1.7, mas os que **já existem em produção sem nenhuma regra escrita hoje**: `LoadingState.jsx`, `ErrorState.jsx`, `EmptyState.jsx`, `Skeletons.jsx`, `Panel.jsx`, `PageHeader.jsx`, `StatusBadge.jsx`, `MetricCard.jsx` (todos em `components/ui/`) — é trabalho represado, não só documentação do que ainda vai nascer.
3. **Regras de layout** — grid para layout 2D / flex para 1D, estrutura padrão de página (`PageHeader` no topo + conteúdo), a escala de espaçamento que `Panel.jsx` já usa (`sm`/`md`/`lg` → `p-3`/`p-4`/`p-4`, hoje só documentada implicitamente no próprio arquivo) formalizada como a escala oficial do projeto. Para responsividade mobile, referenciar `docs/GUIA_RESPONSIVIDADE_MOBILE.md` (já existe e é bom) em vez de duplicar o conteúdo.
4. **Regras de cor/estado** — `ACTION_COLOR_RULES` (`components/ui/actionStyles.js`) já é a fonte certa de "que cor uma ação deve ter"; o styleguide aponta para lá, não reescreve. Idem para estados de tela: quando usar `Skeletons` vs `LoadingState`, quando um erro é `ErrorState` de página inteira vs erro de campo (`FormField` já resolve nos campos, ver 1.6).
5. **Iconografia** — `lucide-react` é a única biblioteca de ícone do projeto (confirmado no `package.json`); os tamanhos já usados em `ICON_SIZES`/`ICON_ACTION_SIZES` (`ActionButton.jsx`/`IconActionButton.jsx`/`actionStyles.js`) viram a referência oficial de tamanho por contexto, não um valor escolhido na hora.
6. **Acessibilidade mínima obrigatória** — centraliza aqui o checklist que hoje está espalhado em três lugares do roadmap (label associado e `aria-describedby` em 1.6, `role="dialog"`/foco/`Escape` em 1.7, contraste e alvo de toque ≥44px em [[Fase-2-Funcionalidades-e-Skills]] 2.6) — um único ponto de referência, os outros passam a linkar para cá em vez de repetir a regra.

### Como não deixar este documento morrer (o risco real do item)

- [ ] **Nasce junto com o primeiro componente, não depois de todos prontos.** Criar o esqueleto (as 6 seções acima, vazias) no mesmo PR que criar `components/ui/fields/` (1.6) — cada campo/componente novo a partir daí entra no styleguide no mesmo PR que o cria, nunca como tarefa separada para "depois".
- [ ] **Checklist de PR.** Adicionar ao `.github/pull_request_template.md` um item conferindo se o PR criou/alterou um componente de `components/ui/` e, se sim, se o styleguide foi atualizado junto — mesmo mecanismo de reforço já usado no restante deste roadmap (CI bloqueante, gate de release) para não depender só de boa vontade.
- [ ] **Dono do documento.** Se/quando existir CODEOWNERS (ver 1.1), `docs/GUIA_ESTILO_FRONTEND.md` entra no mapeamento de dono de frontend — evita o styleguide ficar sem revisor claro quando mudar.

> ⚠️ **Achado real, 2026-09-12, que todo componente v2 com `<input>`/`<select>`/`<textarea>` nativo por dentro precisa saber:** `frontend/src/index.css` tem uma regra legada global (`.dark input:not([type="checkbox"]):not([type="radio"]), .dark select, .dark textarea`) que fixa `background-color`/`border-color`/`color` via variáveis CSS, com especificidade maior que uma classe `dark:` comum do Tailwind — ela silenciosamente vencia a borda vermelha de erro (e potencialmente bg/texto) dos campos v2 no modo escuro, sem gerar nenhum erro ou aviso. Sintoma característico: funciona certo no modo claro, quebra só no escuro. Solução aplicada: usar o modificador `dark:!` (important) do Tailwind nas classes de cor do elemento nativo dentro do componente v2 (ver `InputTexto.jsx` para o padrão). Ao criar um novo componente v2 com elemento nativo, testar sempre nos dois temas antes de considerar pronto — não só no claro.

## 1.9 — `components/` só para peças reaproveitáveis; peça de uso único mora junto da tela (proposta nova, fora da auditoria original)

Observação levantada pelo responsável ao comparar com a convenção do Vue 3 (onde "view"/tela e "componente" reaproveitável são coisas claramente separadas), confirmada no código desta rodada: no frontend deste projeto, `components/` virou uma gaveta para tudo que não é o arquivo principal da página, em vez de ser reservado só para peças genuinamente reaproveitáveis em mais de uma tela.

### Evidência confirmada no código (2026-09-12)

- `frontend/src/components/` tem **529 arquivos**; `frontend/src/pages/` tem **832**.
- Caso concreto de peça de uso único estacionada no lugar errado: `components/campanhas/` tem **66 arquivos** (modais, abas, seções de configuração e de dashboard) — todos consumidos exclusivamente por um único arquivo, `pages/Campanhas.jsx`. Não é um componente reaproveitável, é a própria tela fatiada em arquivos, só que guardada numa pasta com nome de "componente". O mesmo padrão se repete em outras pastas por feature dentro de `components/`: `pdv/`, `produto/`, `veterinario/`, `estoque/`, `financeiro/`, `pessoas/`, `clientes/`, `compras/`, entre outras.
- **O projeto já tem o padrão certo em áreas mais recentes/refatoradas**, prova de que isso não exige inventar nada novo: `pages/banhoTosa/components/`, `pages/veterinario/agenda/`, `pages/produtos/form/`, `pages/veterinario/consultaForm/` já colocam a peça específica de uma tela ao lado da própria tela, em vez de num diretório global.
- `components/ui/` (~34 arquivos: `ActionButton`, `Panel`, `EmptyState`, `FormField` etc., já cobertos nos itens 1.6-1.8) é o único lugar de `components/` que já segue corretamente o conceito de "peça reaproveitável em qualquer tela do sistema" — é o equivalente direto ao que o Vue chama de componente.

### Regra proposta

- **`frontend/src/components/` (raiz e `components/ui/`)** — só peça usada em **mais de uma tela/feature**, sem lógica de negócio de um domínio específico. Se um componente só existe para servir uma tela, ele não pertence aqui, não importa quão grande ou complexo seja.
- **`frontend/src/pages/<feature>/`** — tudo que é específico daquela tela: subcomponentes, modais, abas, seções, hooks locais. Um domínio grande pode (e deve) ter sua própria subpasta `components/` **dentro** de `pages/<feature>/` (exatamente como `pages/banhoTosa/components/` já faz) — a diferença para o `components/` global é o escopo: um vive só dentro daquela feature, o outro é importado de qualquer lugar do sistema.
- Critério prático para decidir na hora de criar um arquivo novo: **"este pedaço seria útil em uma tela completamente diferente, sem nenhuma adaptação de domínio?"** Se sim, `components/ui/`. Se não, `pages/<feature>/components/`.

### Passos concretos para reorganizar `components/` vs `pages/`, em ordem

- [ ] **Não migrar os 529 arquivos de uma vez.** Mesma regra já usada nos itens anteriores: migração oportunista — quando uma tela for tocada por outro motivo (bug, nova funcionalidade, mapeamento da Fase 2), as peças de uso único dela em `components/<feature>/` migram para `pages/<feature>/components/` no mesmo PR.
- [ ] **Escolher 1 feature grande como piloto** — `components/campanhas/` (66 arquivos, todos de uso único confirmado) é o candidato mais claro: mover tudo para `pages/campanhas/components/` prova o processo num caso real antes de generalizar.
- [ ] **Registrar a regra no styleguide (item 1.8)**, na seção de "Princípios gerais" — é exatamente o tipo de regra que esse documento existe para guardar, para não depender de review manual repetindo a mesma explicação a cada PR.
- [ ] **Ao mapear cada tela na Fase 2** (ver [[Fase-2-Funcionalidades-e-Skills]] 2.1), registrar no respectivo documento de [[Funcionalidades]] se os arquivos de apoio daquela tela já estão no lugar certo — vira um efeito colateral útil do mapeamento, não uma auditoria separada.

### Não identificado nesta rodada (item 1.9)

- ❓ Se algum dos arquivos hoje em `components/<feature>/` é, na verdade, usado por mais de uma tela (o levantamento desta rodada confirmou uso único só para `components/campanhas/`; as demais pastas por feature não foram auditadas arquivo a arquivo) — checar antes de mover, para não quebrar um reaproveitamento real que exista sem estar óbvio.

## Critério de avanço para a Fase 2

- CI/CD com CODEOWNERS e Environments configurados.
- Pelo menos 1 domínio legado piloto migrado para o padrão de pasta (prova de conceito do processo).
- Lista inicial de duplicações confirmadas (mesmo que pequena) registrada em [[Pendencias]] ou nova seção deste roadmap.
- Error tracking em produção ativo (item 1.5) — recomendado, não bloqueante.
- `components/ui/fields/` criado com `BaseTextField`/`BaseSelectField`/`BaseChoiceField` e os campos já existentes (`MoneyField`, `QuantityField`, `ComboboxField`, `DateField`) consolidados nele (item 1.6) — recomendado antes da Fase 2 usar esses mesmos campos ao mapear tela por tela.
- `components/ui/typography/` e `components/ui/Modal.jsx` criados, com `PageHeader`/`Panel`/`EmptyState` já migrados para usar a tipografia nova (item 1.7) — mesmo motivo: a Fase 2 vai montar/revisar tela por tela, e deve já encontrar essas peças prontas.
- `components/ui/actions/` criado com pelo menos `SaveButton`, `CancelButton`, `DeleteButton`, `HelpButton` (item 1.7) — recomendado, não bloqueante.
- `docs/GUIA_ESTILO_FRONTEND.md` existe com o esqueleto das 6 seções e pelo menos os componentes de 1.6/1.7 já documentados neles (item 1.8) — a Fase 2 vai mapear tela por tela e deve poder linkar cada tela ao styleguide, não escrever a regra de novo a cada funcionalidade.
- Piloto de reorganização `components/campanhas/` → `pages/campanhas/components/` concluído e regra registrada no styleguide (item 1.9) — recomendado antes da Fase 2 mapear tela por tela, para já registrar a localização correta de cada peça de apoio.

## Não identificado

- ❓ Se há alguma ferramenta de análise de complexidade ciclomática já configurada (não encontrada nesta análise) — útil para achar candidatos a "over-parametrização" de forma objetiva em vez de manual.
