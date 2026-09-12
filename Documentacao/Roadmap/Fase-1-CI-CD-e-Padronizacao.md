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

## Critério de avanço para a Fase 2

- CI/CD com CODEOWNERS e Environments configurados.
- Pelo menos 1 domínio legado piloto migrado para o padrão de pasta (prova de conceito do processo).
- Lista inicial de duplicações confirmadas (mesmo que pequena) registrada em [[Pendencias]] ou nova seção deste roadmap.
- Error tracking em produção ativo (item 1.5) — recomendado, não bloqueante.
- `components/ui/fields/` criado com `BaseTextField`/`BaseSelectField`/`BaseChoiceField` e os campos já existentes (`MoneyField`, `QuantityField`, `ComboboxField`, `DateField`) consolidados nele (item 1.6) — recomendado antes da Fase 2 usar esses mesmos campos ao mapear tela por tela.

## Não identificado

- ❓ Se há alguma ferramenta de análise de complexidade ciclomática já configurada (não encontrada nesta análise) — útil para achar candidatos a "over-parametrização" de forma objetiva em vez de manual.
